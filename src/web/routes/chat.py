"""AI聊天API路由。"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import load_ai_config
from src.ai.engine import AIEngine
from src.ai.providers.base import AIConfig
from src.ai.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

router = APIRouter()


def get_ai_engine() -> Optional[AIEngine]:
    """获取AI引擎实例。

    从配置文件加载AI配置，创建OpenAI兼容提供商和AI引擎。
    如果配置不存在或初始化失败，返回None。

    Returns:
        AIEngine实例或None。
    """
    config = load_ai_config()
    if config and config.get("api_key"):
        ai_config = config
        timeout = ai_config.get("timeout", 60.0)
        provider = OpenAIProvider(
            api_key=ai_config["api_key"],
            base_url=ai_config["base_url"],
            provider="deepseek",
            timeout=timeout,
        )
        # 传递配置到AI引擎
        ai_model_config = AIConfig(
            model=ai_config.get("model", "deepseek-v4-flash"),
            temperature=ai_config.get("temperature", 0.7),
            max_tokens=ai_config.get("max_tokens", 2048),
            timeout=timeout,
        )
        return AIEngine(provider, default_config=ai_model_config)
    return None


class ChatRequest(BaseModel):
    """聊天请求。"""

    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    """聊天响应。"""

    reply: str


def get_default_reply(message: str) -> str:
    """根据问题类型返回默认调参建议。

    Args:
        message: 用户输入的消息。

    Returns:
        调参建议文本。
    """
    message_lower = message.lower()

    # 电流环振荡
    if "振荡" in message or "震荡" in message or "oscillation" in message_lower:
        return """## 电流环振荡分析

**可能原因：**
1. Kp过大，带宽过高
2. 电流采样噪声
3. 死区补偿不当

**调参建议：**
- 将Kp减小30%~50%
- 检查电流采样滤波
- 确认PWM死区设置

**公式参考：**
$$K_p = \\omega_c \\times L$$

如果振荡频率接近开关频率，说明带宽过高，需要降低 ωc。"""

    # 超调
    if "超调" in message or "overshoot" in message_lower:
        return """## 速度环超调分析

**可能原因：**
1. 阻尼比过小
2. Ki过大

**调参建议：**
- 增大Kp（提高阻尼比）
- 或减小Ki
- 推荐阻尼比 ζ = 0.707

**公式参考：**
$$K_p = 2\\zeta\\omega_n \\frac{J}{K_t}$$

增大Kp可提高阻尼比，减小超调。"""

    # 响应慢
    if "响应慢" in message or "太慢" in message or "slow" in message_lower:
        return """## 响应速度分析

**可能原因：**
1. 带宽不足
2. Kp偏小

**调参建议：**
- 适当增大Kp
- 提高期望带宽

**公式参考：**
$$K_p = \\omega_c \\times L$$

增大Kp可提高带宽，加快响应。注意不要超过开关频率的1/10。"""

    # 启动过流
    if "过流" in message or "启动" in message or "overcurrent" in message_lower:
        return """## 启动过流分析

**可能原因：**
1. 电流环参数过大
2. 初始位置不准
3. 软启动未启用

**调参建议：**
- 降低电流环Kp 50%
- 启用电流限幅
- 检查初始位置检测

**安全提示：**
先在低电流下测试，确认稳定后再增加。"""

    # 低速抖动
    if "抖动" in message or "低速" in message or "jitter" in message_lower:
        return """## 低速抖动分析

**可能原因：**
1. 编码器分辨率不足
2. 电流采样噪声
3. 观测器参数不当

**调参建议：**
- 增加电流滤波
- 检查编码器信号
- 适当降低电流环带宽

**公式参考：**
低速时反电动势小，电流环更容易受噪声影响。"""

    # 默认回复
    return """## FOC调参助手

我可以帮您分析以下问题：

1. **电流环问题**：振荡、稳态误差、响应慢
2. **速度环问题**：超调、振荡、跟踪误差
3. **启动问题**：过流、反转、位置检测
4. **低速问题**：抖动、不稳

请描述您遇到的具体现象，或提供电机参数让我帮您整定。

**常用公式：**
- 电流环：Kp = ωc × L, Ki = ωc × R
- 速度环：Kp = 2ζωnJ/Kt, Ki = ωn²J/Kt"""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """AI聊天接口。

    如果配置了AI API Key，使用大模型回复。
    否则返回内置的调参建议。

    Args:
        request: 聊天请求。

    Returns:
        聊天响应。
    """
    engine = get_ai_engine()
    if engine:
        try:
            reply = engine.chat_with_context(
                request.message,
                system_prompt="你是FOC电机控制调参专家，擅长分析电机参数、诊断控制问题、提供调参建议。请用专业但易懂的语言回答用户问题。",
            )
            return ChatResponse(reply=reply)
        except Exception as e:
            logger.error(f"AI API调用失败: {e}", exc_info=True)

    # 使用默认回复
    reply = get_default_reply(request.message)
    return ChatResponse(reply=reply)
