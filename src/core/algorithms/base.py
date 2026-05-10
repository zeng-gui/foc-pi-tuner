"""整定算法抽象基类。"""

from abc import ABC, abstractmethod
from src.core.models import MotorParameters, PIParameters


class TuningAlgorithm(ABC):
    """整定算法抽象基类。

    所有整定算法需实现此接口。
    """

    @abstractmethod
    def can_execute(self, params: MotorParameters) -> bool:
        """判断给定参数是否满足执行条件。"""

    @abstractmethod
    def execute_current_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
    ) -> tuple[PIParameters, PIParameters]:
        """执行电流环PI参数整定。"""

    @abstractmethod
    def execute_speed_loop(
        self,
        params: MotorParameters,
        bandwidth: float,
        damping: float = 0.707,
    ) -> PIParameters:
        """执行速度环PI参数整定。"""
