"""带宽法PI参数整定算法。

基于控制带宽设计PI控制器参数，适用于FOC电流环和速度环。

电流环公式:
    Kp = ωc × L
    Ki = ωc × Rs

    其中 ωc 为电流环期望带宽 (rad/s)，L 为对应轴电感：
    - d轴使用 Ld
    - q轴使用 Lq

速度环公式:
    Kp = 2 × ζ × ωn × J / Kt
    Ki = ωn² × J / Kt

    其中 ωn 为速度环期望带宽 (rad/s)，ζ 为阻尼比（默认0.707），
    J 为转动惯量，Kt = 1.5 × p × Psi_f 为转矩常数。
"""

from src.core.algorithms.base import TuningAlgorithm
from src.core.models import ControlLoop, MotorParameters, PIParameters


class BandwidthTuning(TuningAlgorithm):
    """带宽法PI参数整定算法。

    通过设定期望控制带宽，根据电机物理参数直接计算PI增益。
    方法简单直观，是FOC工程中最常用的整定手段。

    电流环设计基于一阶系统近似，将电流环闭环传递函数设计为：
        G(s) = ωc / (s + ωc)

    速度环设计基于二阶系统近似，自然频率 ωn 决定响应速度，
    阻尼比 ζ 决定超调量（ζ=0.707 为最优阻尼）。
    """

    def can_execute(self, params: MotorParameters) -> bool:
        """判断给定参数是否满足带宽法执行条件。

        电流环需要: Rs, Ld/Lq
        速度环需要: Rs, Ld/Lq, Psi_f, J, p

        Args:
            params: 电机参数对象。

        Returns:
            True 表示至少可整定电流环。
        """
        return params.can_tune_current_loop()

    def execute_current_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
    ) -> tuple[PIParameters, PIParameters]:
        """执行电流环PI参数整定。

        公式:
            Kp = ωc × L
            Ki = ωc × Rs

        Args:
            params: 电机参数对象，需要 Rs 和 Ld/Lq。
            bandwidth: 电流环期望带宽 (rad/s)。

        Returns:
            (d轴PI参数, q轴PI参数) 元组。

        Raises:
            ValueError: 当 Rs 或 Ld/Lq 缺失时。
        """
        if params.Rs is None:
            raise ValueError("Rs未设置，无法整定电流环")
        if params.Ld is None and params.Lq is None:
            raise ValueError("Ld和Lq均未设置，无法整定电流环")

        rs = params.Rs
        ld = params.get_Ld()
        lq = params.get_Lq()

        d_params = PIParameters(
            Kp=bandwidth * ld,
            Ki=bandwidth * rs,
            loop_type=ControlLoop.CURRENT_D,
            bandwidth=bandwidth,
        )
        q_params = PIParameters(
            Kp=bandwidth * lq,
            Ki=bandwidth * rs,
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
            Kp = 2 × ζ × ωn × J / Kt
            Ki = ωn² × J / Kt

        其中 Kt = 1.5 × p × Psi_f。

        Args:
            params: 电机参数对象，需要 Rs, Ld/Lq, Psi_f, J, p。
            bandwidth: 速度环期望带宽 (rad/s)。
            damping: 阻尼比，默认 0.707（最优阻尼）。

        Returns:
            速度环PI参数。

        Raises:
            ValueError: 当必要参数缺失时。
        """
        if params.Psi_f is None:
            raise ValueError("Psi_f未设置，无法整定速度环")
        if params.J is None:
            raise ValueError("J未设置，无法整定速度环")
        if params.p is None:
            raise ValueError("极对数p未设置，无法整定速度环")

        kt = params.get_Kt()
        j = params.J
        wn = bandwidth

        return PIParameters(
            Kp=2 * damping * wn * j / kt,
            Ki=wn * wn * j / kt,
            loop_type=ControlLoop.SPEED,
            bandwidth=bandwidth,
        )
