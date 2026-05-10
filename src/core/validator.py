"""参数验证模块。

验证电机参数的有效性和合理性。
"""

from dataclasses import dataclass, field
from src.core.models import MotorParameters


@dataclass
class ValidationResult:
    """验证结果。

    Attributes:
        is_valid: 是否有效。
        errors: 错误信息列表。
        warnings: 警告信息列表。
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ParamValidator:
    """电机参数验证器。"""

    def validate_all(self, params: MotorParameters) -> ValidationResult:
        """验证所有电机参数。

        Args:
            params: 电机参数对象。

        Returns:
            验证结果。
        """
        result = ValidationResult()

        # 验证电阻
        if params.Rs is not None:
            if params.Rs <= 0:
                result.errors.append("Rs必须大于0")
                result.is_valid = False
            elif params.Rs > 100:
                result.warnings.append("Rs值异常大，请确认单位是否为Ω")

        # 验证电感
        if params.Ld is not None:
            if params.Ld <= 0:
                result.errors.append("Ld必须大于0")
                result.is_valid = False
            elif params.Ld > 1:
                result.warnings.append("Ld值异常大，请确认单位是否为H")

        if params.Lq is not None:
            if params.Lq <= 0:
                result.errors.append("Lq必须大于0")
                result.is_valid = False
            elif params.Lq > 1:
                result.warnings.append("Lq值异常大，请确认单位是否为H")

        # 验证磁链
        if params.Psi_f is not None:
            if params.Psi_f <= 0:
                result.errors.append("Psi_f必须大于0")
                result.is_valid = False
            elif params.Psi_f > 10:
                result.warnings.append("Psi_f值异常大，请确认单位是否为Wb")

        # 验证转动惯量
        if params.J is not None:
            if params.J <= 0:
                result.errors.append("J必须大于0")
                result.is_valid = False

        # 验证极对数
        if params.p is not None:
            if params.p <= 0:
                result.errors.append("极对数p必须大于0")
                result.is_valid = False
            elif params.p > 100:
                result.warnings.append("极对数值异常大，请确认")

        return result
