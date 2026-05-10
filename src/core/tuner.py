"""FOC PI参数主整定器。

协调参数验证、算法选择和整定计算，提供一站式PI参数整定接口。
"""

import math
from typing import Optional

from src.core.algorithms import (
    BandwidthTuning,
    PolePlacementTuning,
    TuningAlgorithm,
    ZieglerNicholsTuning,
)
from src.core.models import (
    ControlLoop,
    MotorParameters,
    PIParameters,
    TuningMethod,
    TuningResult,
)
from src.core.validator import ParamValidator


# 默认带宽 (rad/s)
_DEFAULT_CURRENT_BW = 2000.0   # 电流环默认带宽，约等于 2π × 318Hz
_DEFAULT_SPEED_BW = 200.0      # 速度环默认带宽，约等于 2π × 32Hz

# 电流环带宽安全上限（相对于开关频率）
_MAX_CURRENT_BW_RATIO = 0.2   # ωc_max ≈ 0.2 × 2π × fsw，避免接近开关频率


class FOCPITuner:
    """FOC PI参数整定器。

    协调参数验证、算法选择和整定计算流程，
    为PMSM电流环和速度环提供完整的PI参数整定。

    Attributes:
        params: 电机参数。
        method: 整定方法。
        validator: 参数验证器。
    """

    def __init__(
        self,
        motor_params: MotorParameters,
        method: TuningMethod = TuningMethod.AUTO,
    ) -> None:
        """初始化整定器。

        Args:
            motor_params: 电机参数对象。
            method: 整定方法，默认自动选择。
        """
        self.params = motor_params
        self.method = method
        self.validator = ParamValidator()
        self._algorithm: Optional[TuningAlgorithm] = None

    def _get_algorithm(self) -> TuningAlgorithm:
        """获取当前方法对应的整定算法实例。

        Returns:
            整定算法实例。

        Raises:
            ValueError: 当方法未知时。
        """
        if self._algorithm is not None:
            return self._algorithm

        method = self.method
        if method == TuningMethod.AUTO:
            method = self.auto_select_method()

        algo_map: dict[TuningMethod, type[TuningAlgorithm]] = {
            TuningMethod.BANDWIDTH: BandwidthTuning,
            TuningMethod.POLE_PLACEMENT: PolePlacementTuning,
            TuningMethod.ZIEGLER_NICHOLS: ZieglerNicholsTuning,
        }
        cls = algo_map.get(method)
        if cls is None:
            raise ValueError(f"未知整定方法: {method}")
        self._algorithm = cls()
        return self._algorithm

    def auto_select_method(self) -> TuningMethod:
        """根据电机参数特征自动选择最佳整定方法。

        选择逻辑：
        - 优先使用带宽法（最通用、最直观）
        - 当电阻较大（>1Ω）时，极点配置法可补偿电阻项，更准确

        Returns:
            推荐的整定方法。
        """
        # 电阻较大时极点配置法更准确（补偿了Kp中的R项）
        if self.params.Rs is not None and self.params.Rs > 1.0:
            return TuningMethod.POLE_PLACEMENT
        return TuningMethod.BANDWIDTH

    def _resolve_current_bw(self, bandwidth: Optional[float]) -> float:
        """解析电流环带宽参数。

        Args:
            bandwidth: 用户指定的带宽，None则使用默认值。

        Returns:
            电流环带宽 (rad/s)。
        """
        if bandwidth is not None:
            return bandwidth
        return _DEFAULT_CURRENT_BW

    def _resolve_speed_bw(self, bandwidth: Optional[float]) -> float:
        """解析速度环带宽参数。

        Args:
            bandwidth: 用户指定的带宽，None则使用默认值。

        Returns:
            速度环带宽 (rad/s)。
        """
        if bandwidth is not None:
            return bandwidth
        return _DEFAULT_SPEED_BW

    def tune_current_loop(
        self,
        bandwidth: Optional[float] = None,
        damping: float = 0.707,
    ) -> tuple[PIParameters, PIParameters]:
        """整定电流环PI参数。

        Args:
            bandwidth: 电流环期望带宽 (rad/s)，None则使用默认值。
            damping: 阻尼比（部分算法使用），默认0.707。

        Returns:
            (d轴PI参数, q轴PI参数) 元组。

        Raises:
            ValueError: 当电机参数不足以整定电流环时。
        """
        if not self.params.can_tune_current_loop():
            raise ValueError(
                "电机参数不足以整定电流环，至少需要 Rs 和 Ld/Lq"
            )

        algo = self._get_algorithm()
        bw = self._resolve_current_bw(bandwidth)
        d_params, q_params = algo.execute_current_loop(self.params, bw)

        # 估算响应特性
        d_resp = self.estimate_response(d_params.Kp, d_params.Ki, ControlLoop.CURRENT_D)
        d_params.settling_time = d_resp["settling_time"]
        d_params.overshoot = d_resp["overshoot"]

        q_resp = self.estimate_response(q_params.Kp, q_params.Ki, ControlLoop.CURRENT_Q)
        q_params.settling_time = q_resp["settling_time"]
        q_params.overshoot = q_resp["overshoot"]

        return d_params, q_params

    def tune_speed_loop(
        self,
        bandwidth: Optional[float] = None,
        damping: float = 0.707,
    ) -> PIParameters:
        """整定速度环PI参数。

        Args:
            bandwidth: 速度环期望带宽 (rad/s)，None则使用默认值。
            damping: 阻尼比，默认0.707（最优阻尼）。

        Returns:
            速度环PI参数。

        Raises:
            ValueError: 当电机参数不足以整定速度环时。
        """
        if not self.params.can_tune_speed_loop():
            raise ValueError(
                "电机参数不足以整定速度环，需要 Rs, Ld/Lq, Psi_f, J, p"
            )

        algo = self._get_algorithm()
        bw = self._resolve_speed_bw(bandwidth)
        speed_params = algo.execute_speed_loop(self.params, bw, damping)

        resp = self.estimate_response(speed_params.Kp, speed_params.Ki, ControlLoop.SPEED)
        speed_params.settling_time = resp["settling_time"]
        speed_params.overshoot = resp["overshoot"]

        return speed_params

    def tune_all(
        self,
        current_bw: Optional[float] = None,
        speed_bw: Optional[float] = None,
        damping: float = 0.707,
    ) -> TuningResult:
        """执行完整的PI参数整定。

        流程：
        1. 验证电机参数
        2. 根据参数完整度决定可整定的环路
        3. 调用对应算法计算PI参数
        4. 生成性能预估和调参指导

        Args:
            current_bw: 电流环期望带宽 (rad/s)，None则使用默认值。
            speed_bw: 速度环期望带宽 (rad/s)，None则使用默认值。
            damping: 阻尼比，默认0.707。

        Returns:
            包含PI参数、警告和调参指导的完整结果。
        """
        result = TuningResult()
        result.warnings.extend(self._validate_params())

        # 根据参数完整度整定可用环路
        if self.params.can_tune_current_loop():
            try:
                d_params, q_params = self.tune_current_loop(current_bw, damping)
                result.current_d = d_params
                result.current_q = q_params
            except ValueError as e:
                result.warnings.append(f"电流环整定失败: {e}")

        if self.params.can_tune_speed_loop():
            try:
                speed_params = self.tune_speed_loop(speed_bw, damping)
                result.speed = speed_params
            except ValueError as e:
                result.warnings.append(f"速度环整定失败: {e}")

        # 生成优化建议和调参指导
        result.suggestions = self._generate_suggestions(result)
        result.tuning_guide = self.generate_tuning_guide(result)

        return result

    def _validate_params(self) -> list[str]:
        """验证电机参数，返回警告信息列表。"""
        warnings: list[str] = []
        validation = self.validator.validate_all(self.params)
        warnings.extend(validation.warnings)

        missing = self.params.check_completeness()
        missing_names: list[str] = []
        for names in missing.values():
            missing_names.extend(names)
        if missing_names:
            warnings.append(f"缺失参数: {', '.join(missing_names)}")

        return warnings

    def _generate_suggestions(self, result: TuningResult) -> list[str]:
        """根据整定结果生成优化建议。"""
        suggestions: list[str] = []

        # 检查电流环带宽是否合理
        if result.current_q is not None and result.current_q.bandwidth is not None:
            bw = result.current_q.bandwidth
            if bw > 10000:
                suggestions.append(
                    f"电流环带宽({bw:.0f} rad/s)较高，"
                    "确保PWM频率足够高且电流采样延迟较小"
                )
            elif bw < 500:
                suggestions.append(
                    f"电流环带宽({bw:.0f} rad/s)较低，"
                    "电流响应可能较慢，适合低速应用"
                )

        # 检查速度环带宽与电流环带宽的关系
        if (
            result.speed is not None
            and result.speed.bandwidth is not None
            and result.current_q is not None
            and result.current_q.bandwidth is not None
        ):
            ratio = result.current_q.bandwidth / result.speed.bandwidth
            if ratio < 5:
                suggestions.append(
                    f"电流环/速度环带宽比({ratio:.1f})偏小，"
                    "建议电流环带宽至少为速度环的5~10倍"
                )

        # 检查超调量
        if result.speed is not None and result.speed.overshoot is not None:
            if result.speed.overshoot > 15:
                suggestions.append(
                    "速度环预估超调量较大，可适当增大阻尼比或降低带宽"
                )

        return suggestions

    def estimate_response(
        self,
        Kp: float,
        Ki: float,
        loop_type: ControlLoop,
    ) -> dict:
        """估算PI控制器的响应特性。

        基于PI参数推导闭环系统的带宽、调节时间和超调量。

        Args:
            Kp: 比例增益。
            Ki: 积分增益。
            loop_type: 环路类型。

        Returns:
            包含 bandwidth, settling_time, overshoot 的字典。
        """
        if Kp <= 0 or Ki <= 0:
            return {
                "bandwidth": 0.0,
                "settling_time": float("inf"),
                "overshoot": 0.0,
            }

        if loop_type in (ControlLoop.CURRENT_D, ControlLoop.CURRENT_Q):
            # 电流环近似为一阶系统: G_cl = Ki / (s + Ki/Kp)
            # 近似带宽 ≈ Ki / Kp
            bandwidth = Ki / Kp
            # 调节时间 ≈ 4 / bandwidth (2%准则)
            settling_time = 4.0 / bandwidth if bandwidth > 0 else float("inf")
            # 一阶系统无超调
            overshoot = 0.0
        else:
            # 速度环闭环传递函数:
            #   G_cl = Kt*(Kp*s + Ki) / (J*s^2 + Kt*Kp*s + Kt*Ki)
            # 自然频率 ωn = sqrt(Kt*Ki / J)
            # 阻尼比 ζ = Kp*sqrt(Kt) / (2*sqrt(Ki*J))
            kt = self.params.get_Kt()
            j = self.params.J
            wn = math.sqrt(kt * Ki / j)
            zeta = Kp * math.sqrt(kt) / (2.0 * math.sqrt(Ki * j))

            bandwidth = wn
            if 0 < zeta < 1.0:
                # 欠阻尼系统
                settling_time = 4.0 / (zeta * wn)
                overshoot = 100.0 * math.exp(
                    -math.pi * zeta / math.sqrt(1.0 - zeta * zeta)
                )
            else:
                # 过阻尼或临界阻尼
                settling_time = 4.0 / wn if wn > 0 else float("inf")
                overshoot = 0.0

        return {
            "bandwidth": bandwidth,
            "settling_time": settling_time,
            "overshoot": overshoot,
        }

    def generate_tuning_guide(self, result: TuningResult) -> list[str]:
        """生成调参指导建议。

        基于整定结果和预估性能，给出针对性的现场调试指导。

        Args:
            result: 整定结果。

        Returns:
            调参指导字符串列表。
        """
        guide: list[str] = []

        # 电流环调参指导
        if result.current_q is not None:
            guide.append("--- 电流环调参指导 ---")
            guide.append(
                "若电流响应慢: 适当增大Kp以提高响应速度"
            )
            guide.append(
                "若电流振荡: 适当减小Kp，检查电流采样是否准确"
            )
            guide.append(
                "若存在稳态误差: 适当增大Ki以消除静差"
            )
            guide.append(
                "若启动电流过大: 减小Kp并加入电流限幅保护"
            )

        # 速度环调参指导
        if result.speed is not None:
            guide.append("--- 速度环调参指导 ---")
            guide.append(
                "若速度超调过大: 增大阻尼比或减小Kp"
            )
            guide.append(
                "若速度响应慢: 适当增大Ki提高跟踪速度"
            )
            guide.append(
                "若速度振荡: 同时减小Kp和Ki，先稳定再优化"
            )
            guide.append(
                "若低速抖动: 检查编码器分辨率，适当增大滤波系数"
            )

        return guide
