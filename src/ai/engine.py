"""AI决策引擎。

集成大语言模型，提供智能参数估算、波形分析、故障诊断和调参建议。
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Generator, Optional

from src.ai.providers.base import AIConfig, AIMessage, AIProvider, ResponseFormat
from src.core.models import MotorParameters, TuningResult

logger = logging.getLogger(__name__)


# System Prompt模板
_SYSTEM_PARAM_ESTIMATION = """你是一名专业的PMSM电机控制工程师，擅长根据不完整的电机参数进行合理估算。

## 任务
根据用户提供的部分电机参数，估算缺失的参数值。

## 要求
1. 基于电机类型和已知参数，给出合理的估算值
2. 每个估算值需给出置信度（高/中/低）和估算依据
3. 考虑参数之间的物理关系（如Ld≈Lq对于表贴式电机）
4. 结果必须为JSON格式

## 输出格式
```json
{
  "estimated_params": {
    "参数名": {
      "value": 估算值,
      "unit": "单位",
      "confidence": "高/中/低",
      "reason": "估算依据"
    }
  },
  "motor_type": "推测的电机类型",
  "warnings": ["注意事项"]
}
```"""

_SYSTEM_WAVEFORM_ANALYSIS = """你是一名电机控制调试专家，擅长分析电流环和速度环的响应波形。

## 任务
分析用户提供的电机运行数据或波形特征，诊断控制性能。

## 分析维度
1. 电流环响应：上升时间、超调、稳态误差、纹波
2. 速度环响应：跟踪性能、抗扰性、低速平稳性
3. 系统稳定性：是否有振荡、发散趋势

## 输出要求
- 明确指出问题所在
- 给出可能的原因分析
- 提供具体的调整建议（包括参数调整方向）"""

_SYSTEM_FAULT_DIAGNOSIS = """你是一名电机驱动故障诊断专家，擅长分析FOC控制系统中的各类故障。

## 任务
根据用户描述的故障现象，分析可能的原因并给出排查建议。

## 常见故障类型
1. 过流保护触发
2. 速度振荡或不稳定
3. 启动失败或堵转
4. 位置传感器故障
5. 母线电压异常
6. 温度保护触发

## 输出要求
- 按可能性从高到低列出原因
- 每个原因附带排查步骤
- 给出紧急处理建议（如有安全风险）"""

_SYSTEM_TUNING_ADVICE = """你是一名FOC控制参数整定专家，擅长根据整定结果给出优化建议。

## 任务
分析PI参数整定结果，给出针对性的优化和调试建议。

## 分析要点
1. 参数合理性：Kp、Ki是否在合理范围
2. 带宽匹配：电流环和速度环带宽比是否合理
3. 动态性能：预估的超调量和调节时间是否满足要求
4. 鲁棒性：参数对电机参数变化的敏感度

## 输出要求
- 给出具体的参数调整方向（增大/减小）
- 说明调整的原因和预期效果
- 提供现场调试的步骤建议"""


@dataclass
class ConversationContext:
    """对话上下文管理。

    Attributes:
        messages: 对话历史消息列表。
        max_history: 最大保留历史轮数。
        system_prompt: 系统提示词。
    """

    messages: list[AIMessage] = field(default_factory=list)
    max_history: int = 10
    system_prompt: str = ""

    def add_user_message(self, content: str) -> None:
        """添加用户消息。"""
        self.messages.append(AIMessage(role="user", content=content))
        self._trim_history()

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息。"""
        self.messages.append(AIMessage(role="assistant", content=content))

    def get_messages(self) -> list[AIMessage]:
        """获取完整的对话消息列表（含system prompt）。"""
        result: list[AIMessage] = []
        if self.system_prompt:
            result.append(AIMessage(role="system", content=self.system_prompt))
        result.extend(self.messages)
        return result

    def clear(self) -> None:
        """清空对话历史（保留system prompt）。"""
        self.messages.clear()

    def _trim_history(self) -> None:
        """裁剪历史消息，保留最近的对话轮次。"""
        max_messages = self.max_history * 2  # 每轮包含user和assistant
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]


class AIEngine:
    """AI决策引擎。

    集成大语言模型，为FOC电机控制提供智能辅助功能：
    - 智能参数估算
    - 波形分析
    - 故障诊断
    - 调参建议

    Attributes:
        provider: AI提供商实例。
        default_config: 默认调用配置。
    """

    def __init__(
        self,
        provider: AIProvider,
        default_config: Optional[AIConfig] = None,
    ) -> None:
        """初始化AI引擎。

        Args:
            provider: AI提供商实例。
            default_config: 默认调用配置，None则使用默认值。
        """
        self.provider = provider
        self.default_config = default_config or AIConfig()
        self._context = ConversationContext()

    def _chat(
        self,
        messages: list[AIMessage],
        config: Optional[AIConfig] = None,
        stream: bool = False,
    ) -> str | Generator[str, None, None]:
        """内部调用方法。

        Args:
            messages: 消息列表。
            config: 调用配置。
            stream: 是否流式。

        Returns:
            响应文本或流式生成器。
        """
        cfg = config or self.default_config
        if stream:
            return self.provider.stream_chat(messages, cfg)
        return self.provider.chat(messages, cfg)

    def estimate_params(
        self,
        motor_params: MotorParameters,
        config: Optional[AIConfig] = None,
    ) -> str:
        """智能参数估算。

        根据已知电机参数，利用AI估算缺失参数。

        Args:
            motor_params: 已知的电机参数。
            config: 调用配置，None则使用默认配置。

        Returns:
            包含估算结果的JSON字符串。
        """
        # 构建已知参数描述
        known_params = {}
        param_fields = {
            "Rs": ("定子电阻", "Ω"),
            "Ld": ("d轴电感", "H"),
            "Lq": ("q轴电感", "H"),
            "Psi_f": ("永磁体磁链", "Wb"),
            "J": ("转动惯量", "kg·m²"),
            "B": ("粘性摩擦系数", "N·m·s/rad"),
            "p": ("极对数", ""),
            "Pn": ("额定功率", "W"),
            "Tn": ("额定转矩", "N·m"),
            "Nn": ("额定转速", "rpm"),
            "In": ("额定电流", "A"),
            "Vdc": ("母线电压", "V"),
        }

        for attr, (name, unit) in param_fields.items():
            value = getattr(motor_params, attr, None)
            if value is not None:
                known_params[name] = {"value": value, "unit": unit}

        missing = motor_params.check_completeness()
        missing_names = []
        for names in missing.values():
            missing_names.extend(names)

        user_msg = (
            f"已知电机参数:\n{json.dumps(known_params, ensure_ascii=False, indent=2)}\n\n"
            f"缺失参数: {', '.join(missing_names)}\n\n"
            "请估算缺失的参数值。"
        )

        messages = [
            AIMessage(role="system", content=_SYSTEM_PARAM_ESTIMATION),
            AIMessage(role="user", content=user_msg),
        ]

        cfg = config or self.default_config
        return self.provider.chat(messages, cfg)

    def analyze_response(
        self,
        response_data: dict,
        config: Optional[AIConfig] = None,
    ) -> str:
        """波形分析。

        分析电机运行响应数据，诊断控制性能。

        Args:
            response_data: 响应数据字典，包含波形特征或运行数据。
                示例: {
                    "loop_type": "current_q",
                    "rising_time": 0.001,
                    "overshoot": 15.0,
                    "steady_state_error": 0.02,
                    "ripple": 0.05,
                }
            config: 调用配置，None则使用默认配置。

        Returns:
            分析结果文本。
        """
        user_msg = (
            f"电机运行数据:\n"
            f"{json.dumps(response_data, ensure_ascii=False, indent=2)}\n\n"
            "请分析上述数据，评估控制性能并给出优化建议。"
        )

        messages = [
            AIMessage(role="system", content=_SYSTEM_WAVEFORM_ANALYSIS),
            AIMessage(role="user", content=user_msg),
        ]

        cfg = config or self.default_config
        return self.provider.chat(messages, cfg)

    def diagnose_fault(
        self,
        symptoms: str | dict,
        config: Optional[AIConfig] = None,
    ) -> str:
        """故障诊断。

        根据故障现象描述，分析可能原因并给出排查建议。

        Args:
            symptoms: 故障现象描述，可以是文本字符串或结构化字典。
                示例: {
                    "fault_type": "过流保护",
                    "occurrence": "启动时",
                    "current_level": "额定电流的3倍",
                    "motor_state": "堵转"
                }
            config: 调用配置，None则使用默认配置。

        Returns:
            诊断结果文本。
        """
        if isinstance(symptoms, dict):
            symptom_text = json.dumps(symptoms, ensure_ascii=False, indent=2)
        else:
            symptom_text = symptoms

        user_msg = (
            f"故障现象:\n{symptom_text}\n\n"
            "请分析可能的故障原因并给出排查建议。"
        )

        messages = [
            AIMessage(role="system", content=_SYSTEM_FAULT_DIAGNOSIS),
            AIMessage(role="user", content=user_msg),
        ]

        cfg = config or self.default_config
        return self.provider.chat(messages, cfg)

    def get_tuning_advice(
        self,
        result: TuningResult,
        motor_params: Optional[MotorParameters] = None,
        config: Optional[AIConfig] = None,
    ) -> str:
        """调参建议。

        分析PI参数整定结果，给出优化建议。

        Args:
            result: 整定结果。
            motor_params: 电机参数（可选，用于提供上下文）。
            config: 调用配置，None则使用默认配置。

        Returns:
            调参建议文本。
        """
        # 构建整定结果描述
        result_info: dict = {"warnings": result.warnings, "suggestions": result.suggestions}

        if result.current_d is not None:
            result_info["current_d"] = {
                "Kp": result.current_d.Kp,
                "Ki": result.current_d.Ki,
                "bandwidth": result.current_d.bandwidth,
                "settling_time": result.current_d.settling_time,
                "overshoot": result.current_d.overshoot,
            }

        if result.current_q is not None:
            result_info["current_q"] = {
                "Kp": result.current_q.Kp,
                "Ki": result.current_q.Ki,
                "bandwidth": result.current_q.bandwidth,
                "settling_time": result.current_q.settling_time,
                "overshoot": result.current_q.overshoot,
            }

        if result.speed is not None:
            result_info["speed"] = {
                "Kp": result.speed.Kp,
                "Ki": result.speed.Ki,
                "bandwidth": result.speed.bandwidth,
                "settling_time": result.speed.settling_time,
                "overshoot": result.speed.overshoot,
            }

        # 添加电机参数上下文
        motor_info = ""
        if motor_params is not None:
            motor_info = (
                f"\n电机参数:\n"
                f"- Rs={motor_params.Rs}Ω, Ld={motor_params.Ld}H, Lq={motor_params.Lq}H\n"
                f"- Psi_f={motor_params.Psi_f}Wb, J={motor_params.J}kg·m², p={motor_params.p}\n"
            )

        user_msg = (
            f"PI参数整定结果:\n"
            f"{json.dumps(result_info, ensure_ascii=False, indent=2)}"
            f"{motor_info}\n"
            "请分析整定结果，给出优化建议和现场调试步骤。"
        )

        messages = [
            AIMessage(role="system", content=_SYSTEM_TUNING_ADVICE),
            AIMessage(role="user", content=user_msg),
        ]

        cfg = config or self.default_config
        return self.provider.chat(messages, cfg)

    def chat_with_context(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        config: Optional[AIConfig] = None,
        stream: bool = False,
    ) -> str | Generator[str, None, None]:
        """带上下文的对话。

        支持多轮对话，自动管理对话历史。

        Args:
            user_message: 用户消息。
            system_prompt: 系统提示词，None则不设置。
            config: 调用配置，None则使用默认配置。
            stream: 是否流式返回。

        Returns:
            响应文本或流式生成器。
        """
        if system_prompt is not None:
            self._context.system_prompt = system_prompt

        self._context.add_user_message(user_message)
        messages = self._context.get_messages()

        if stream:
            return self._stream_with_context(messages, config)

        response = self.provider.chat(messages, config or self.default_config)
        self._context.add_assistant_message(response)
        return response

    def _stream_with_context(
        self,
        messages: list[AIMessage],
        config: Optional[AIConfig] = None,
    ) -> Generator[str, None, None]:
        """流式对话并收集完整响应以更新上下文。

        Args:
            messages: 消息列表。
            config: 调用配置。

        Yields:
            响应文本片段。
        """
        full_response = []
        for chunk in self.provider.stream_chat(messages, config or self.default_config):
            full_response.append(chunk)
            yield chunk

        self._context.add_assistant_message("".join(full_response))

    def clear_context(self) -> None:
        """清空对话上下文。"""
        self._context.clear()
