"""核心数据模型定义。

定义电机参数、PI参数、整定结果等核心数据结构。
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class ControlLoop(Enum):
    """控制环路类型。"""

    CURRENT_D = auto()  # d轴电流环
    CURRENT_Q = auto()  # q轴电流环
    SPEED = auto()      # 速度环


class TuningMethod(Enum):
    """整定方法。"""

    AUTO = auto()           # 自动选择
    BANDWIDTH = auto()      # 带宽法
    POLE_PLACEMENT = auto() # 极点配置法
    ZIEGLER_NICHOLS = auto() # Ziegler-Nichols法


@dataclass
class MotorParameters:
    """电机参数。

    Attributes:
        Rs: 定子电阻 (Ω)
        Ld: d轴电感 (H)
        Lq: q轴电感 (H)
        Psi_f: 永磁体磁链 (Wb)
        J: 转动惯量 (kg·m²)
        B: 粘性摩擦系数 (N·m·s/rad)
        p: 极对数
        Pn: 额定功率 (W)
        Tn: 额定转矩 (N·m)
        Nn: 额定转速 (rpm)
        In: 额定电流 (A)
        Vdc: 母线电压 (V)
    """

    # 电气参数
    Rs: Optional[float] = None
    Ld: Optional[float] = None
    Lq: Optional[float] = None
    Psi_f: Optional[float] = None

    # 机械参数
    J: Optional[float] = None
    B: Optional[float] = None
    p: Optional[int] = None

    # 额定参数
    Pn: Optional[float] = None
    Tn: Optional[float] = None
    Nn: Optional[float] = None
    In: Optional[float] = None
    Vdc: Optional[float] = None

    def get_Ld(self) -> float:
        """获取d轴电感，如果Ld未设置则使用Lq。"""
        if self.Ld is not None:
            return self.Ld
        if self.Lq is not None:
            return self.Lq
        raise ValueError("Ld和Lq均未设置")

    def get_Lq(self) -> float:
        """获取q轴电感，如果Lq未设置则使用Ld。"""
        if self.Lq is not None:
            return self.Lq
        if self.Ld is not None:
            return self.Ld
        raise ValueError("Ld和Lq均未设置")

    def get_Kt(self) -> float:
        """获取转矩常数 Kt = 1.5 × p × Psi_f。"""
        if self.Psi_f is None:
            raise ValueError("Psi_f未设置")
        if self.p is None:
            raise ValueError("极对数p未设置")
        return 1.5 * self.p * self.Psi_f

    def can_tune_current_loop(self) -> bool:
        """检查是否可以整定电流环。"""
        return self.Rs is not None and (self.Ld is not None or self.Lq is not None)

    def can_tune_speed_loop(self) -> bool:
        """检查是否可以整定速度环。"""
        return (
            self.can_tune_current_loop()
            and self.Psi_f is not None
            and self.J is not None
            and self.p is not None
        )

    def check_completeness(self) -> dict[str, list[str]]:
        """检查参数完整性，返回缺失参数分类。"""
        missing: dict[str, list[str]] = {
            "电气参数": [],
            "机械参数": [],
            "额定参数": [],
        }

        if self.Rs is None:
            missing["电气参数"].append("Rs")
        if self.Ld is None:
            missing["电气参数"].append("Ld")
        if self.Lq is None:
            missing["电气参数"].append("Lq")
        if self.Psi_f is None:
            missing["电气参数"].append("Ψf")

        if self.J is None:
            missing["机械参数"].append("J")
        if self.p is None:
            missing["机械参数"].append("p")

        # 移除空列表
        return {k: v for k, v in missing.items() if v}


@dataclass
class PIParameters:
    """PI控制器参数。

    Attributes:
        Kp: 比例增益。
        Ki: 积分增益。
        loop_type: 环路类型。
        bandwidth: 带宽 (rad/s)。
        settling_time: 调节时间 (s)。
        overshoot: 超调量 (%)。
    """

    Kp: float
    Ki: float
    loop_type: ControlLoop
    bandwidth: Optional[float] = None
    settling_time: Optional[float] = None
    overshoot: Optional[float] = None


@dataclass
class TuningResult:
    """整定结果。

    Attributes:
        current_d: d轴电流环PI参数。
        current_q: q轴电流环PI参数。
        speed: 速度环PI参数。
        warnings: 警告信息列表。
        suggestions: 优化建议列表。
        tuning_guide: 调参指导列表。
    """

    current_d: Optional[PIParameters] = None
    current_q: Optional[PIParameters] = None
    speed: Optional[PIParameters] = None
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    tuning_guide: list[str] = field(default_factory=list)
