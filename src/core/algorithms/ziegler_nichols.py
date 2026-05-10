"""Ziegler-Nichols法PI参数整定算法。

基于系统时间常数的经典整定方法。

电流环公式:
    τ = L / R (电机时间常数)
    Kp = 0.9 × R
    Ki = Kp / (3.33 × τ)

速度环公式:
    τ_eq = 1 / ωc (电流环等效时间常数)
    Kp = J / (Kt × τ_eq)
    Ki = Kp / (2 × τ_eq)
"""

from src.core.algorithms.base import TuningAlgorithm
from src.core.models import ControlLoop, MotorParameters, PIParameters


class ZieglerNicholsTuning(TuningAlgorithm):
    """Ziegler-Nichols法PI参数整定算法。

    基于系统时间常数的经典整定方法，适用于一阶惯性系统。
    对于电机控制，将电流环近似为一阶系统进行整定。
    """

    def can_execute(self, params: MotorParameters) -> bool:
        """判断给定参数是否满足Z-N法执行条件。"""
        return params.can_tune_current_loop()

    def execute_current_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
    ) -> tuple[PIParameters, PIParameters]:
        """执行电流环PI参数整定。

        公式:
            τ = L / R
            Kp = 0.9 × R
            Ki = Kp / (3.33 × τ)

        Args:
            params: 电机参数对象。
            bandwidth: 未使用，Z-N法基于时间常数计算。

        Returns:
            (d轴PI参数, q轴PI参数) 元组。
        """
        if params.Rs is None:
            raise ValueError("Rs未设置，无法整定电流环")
        if params.Ld is None and params.Lq is None:
            raise ValueError("Ld和Lq均未设置，无法整定电流环")

        rs = params.Rs
        ld = params.get_Ld()
        lq = params.get_Lq()

        # d轴
        tau_d = ld / rs
        kp_d = 0.9 * rs
        ki_d = kp_d / (3.33 * tau_d) if tau_d > 0 else 0

        # q轴
        tau_q = lq / rs
        kp_q = 0.9 * rs
        ki_q = kp_q / (3.33 * tau_q) if tau_q > 0 else 0

        d_params = PIParameters(
            Kp=kp_d,
            Ki=ki_d,
            loop_type=ControlLoop.CURRENT_D,
            bandwidth=bandwidth,
        )
        q_params = PIParameters(
            Kp=kp_q,
            Ki=ki_q,
            loop_type=ControlLoop.CURRENT_Q,
            bandwidth=bandwidth,
        )
        return d_params, q_params

    def execute_speed_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
        damping: float = 0.707,
    ) -> PIParameters:
        """执行速度环PI参数整定。

        公式:
            τ_eq = 1 / ωc
            Kp = J / (Kt × τ_eq)
            Ki = Kp / (2 × τ_eq)

        Args:
            params: 电机参数对象。
            bandwidth: 电流环带宽 (rad/s)，用于计算等效时间常数。
            damping: 未使用。

        Returns:
            速度环PI参数。
        """
        if params.Psi_f is None:
            raise ValueError("Psi_f未设置，无法整定速度环")
        if params.J is None:
            raise ValueError("J未设置，无法整定速度环")
        if params.p is None:
            raise ValueError("极对数p未设置，无法整定速度环")

        kt = params.get_Kt()
        j = params.J

        # 电流环等效时间常数
        tau_eq = 1.0 / bandwidth if bandwidth > 0 else 0.001

        kp = j / (kt * tau_eq) if tau_eq > 0 else 0
        ki = kp / (2 * tau_eq) if tau_eq > 0 else 0

        return PIParameters(
            Kp=kp,
            Ki=ki,
            loop_type=ControlLoop.SPEED,
            bandwidth=bandwidth,
        )
