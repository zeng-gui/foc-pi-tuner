"""极点配置法PI参数整定算法。

通过设定闭环极点位置来设计PI控制器参数。

电流环公式:
    Kp = 2 × pole × L - R
    Ki = pole² × L

    其中 pole 为期望极点位置（通常等于期望带宽 ωc）。

速度环公式:
    Kp = J × (p1 + p2) / Kt
    Ki = J × p1 × p2 / Kt

    其中 p1, p2 为期望的两个极点位置。
"""

from src.core.algorithms.base import TuningAlgorithm
from src.core.models import ControlLoop, MotorParameters, PIParameters


class PolePlacementTuning(TuningAlgorithm):
    """极点配置法PI参数整定算法。

    通过设定闭环系统极点位置来计算PI增益。
    相比带宽法，极点配置法考虑了电阻项的影响，
    在电阻较大时能获得更准确的结果。
    """

    def can_execute(self, params: MotorParameters) -> bool:
        """判断给定参数是否满足极点配置法执行条件。"""
        return params.can_tune_current_loop()

    def execute_current_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
    ) -> tuple[PIParameters, PIParameters]:
        """执行电流环PI参数整定。

        公式:
            Kp = 2 × pole × L - R
            Ki = pole² × L

        Args:
            params: 电机参数对象。
            bandwidth: 电流环期望带宽 (rad/s)，作为极点位置。

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
        pole = bandwidth

        d_params = PIParameters(
            Kp=2 * pole * ld - rs,
            Ki=pole * pole * ld,
            loop_type=ControlLoop.CURRENT_D,
            bandwidth=bandwidth,
        )
        q_params = PIParameters(
            Kp=2 * pole * lq - rs,
            Ki=pole * pole * lq,
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
            Kp = J × (p1 + p2) / Kt
            Ki = J × p1 × p2 / Kt

        Args:
            params: 电机参数对象。
            bandwidth: 速度环期望带宽 (rad/s)。
            damping: 阻尼比，用于计算两个极点位置。

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
        wn = bandwidth

        # 根据阻尼比计算两个极点位置
        # 对于二阶系统: s² + 2ζωn·s + ωn² = (s + p1)(s + p2)
        p1 = wn * damping
        p2 = wn / damping if damping > 0 else wn

        return PIParameters(
            Kp=j * (p1 + p2) / kt,
            Ki=j * p1 * p2 / kt,
            loop_type=ControlLoop.SPEED,
            bandwidth=bandwidth,
        )
