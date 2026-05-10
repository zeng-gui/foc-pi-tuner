"""整定API路由。

提供PI参数整定计算的REST API。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.models import MotorParameters, PIParameters, TuningMethod
from src.core.tuner import FOCPITuner

router = APIRouter(tags=["tune"])


class MotorParamsRequest(BaseModel):
    """电机参数请求模型。"""

    # 电气参数
    Rs: Optional[float] = Field(None, description="定子电阻 (Ω)")
    Ld: Optional[float] = Field(None, description="d轴电感 (H)")
    Lq: Optional[float] = Field(None, description="q轴电感 (H)")
    Psi_f: Optional[float] = Field(None, description="永磁体磁链 (Wb)")

    # 机械参数
    J: Optional[float] = Field(None, description="转动惯量 (kg·m²)")
    B: Optional[float] = Field(None, description="粘性摩擦系数 (N·m·s/rad)")
    p: Optional[int] = Field(None, description="极对数")

    # 额定参数
    Pn: Optional[float] = Field(None, description="额定功率 (W)")
    Tn: Optional[float] = Field(None, description="额定转矩 (N·m)")
    Nn: Optional[float] = Field(None, description="额定转速 (rpm)")
    In: Optional[float] = Field(None, description="额定电流 (A)")
    Vdc: Optional[float] = Field(None, description="母线电压 (V)")


class TuneRequest(BaseModel):
    """整定请求模型。"""

    motor_params: MotorParamsRequest
    method: str = Field("auto", description="整定方法: auto/bandwidth/pole_placement/ziegler_nichols")
    current_bw: Optional[float] = Field(None, description="电流环带宽 (rad/s)")
    speed_bw: Optional[float] = Field(None, description="速度环带宽 (rad/s)")
    damping: float = Field(0.707, description="阻尼比")


class PIParamsResponse(BaseModel):
    """PI参数响应模型。"""

    Kp: float
    Ki: float
    loop_type: str
    bandwidth: Optional[float] = None
    settling_time: Optional[float] = None
    overshoot: Optional[float] = None


class TuneResponse(BaseModel):
    """整定响应模型。"""

    current_d: Optional[PIParamsResponse] = None
    current_q: Optional[PIParamsResponse] = None
    speed: Optional[PIParamsResponse] = None
    warnings: list[str] = []
    suggestions: list[str] = []
    tuning_guide: list[str] = []


def _parse_method(method_str: str) -> TuningMethod:
    """解析整定方法字符串。"""
    method_map = {
        "auto": TuningMethod.AUTO,
        "bandwidth": TuningMethod.BANDWIDTH,
        "pole_placement": TuningMethod.POLE_PLACEMENT,
        "ziegler_nichols": TuningMethod.ZIEGLER_NICHOLS,
    }
    method = method_map.get(method_str.lower())
    if method is None:
        raise ValueError(f"未知整定方法: {method_str}")
    return method


def _pi_to_response(pi_params: PIParameters) -> PIParamsResponse:
    """将PIParameters转换为响应模型。

    Args:
        pi_params: PI参数对象。

    Returns:
        PIParamsResponse响应模型。
    """
    return PIParamsResponse(
        Kp=pi_params.Kp,
        Ki=pi_params.Ki,
        loop_type=pi_params.loop_type.name,
        bandwidth=pi_params.bandwidth,
        settling_time=pi_params.settling_time,
        overshoot=pi_params.overshoot,
    )


@router.post("/tune", response_model=TuneResponse)
async def tune_pi_params(request: TuneRequest):
    """执行PI参数整定。

    接收电机参数和整定配置，返回电流环和速度环的PI参数。
    """
    try:
        # 构建电机参数对象
        motor_params = MotorParameters(
            Rs=request.motor_params.Rs,
            Ld=request.motor_params.Ld,
            Lq=request.motor_params.Lq,
            Psi_f=request.motor_params.Psi_f,
            J=request.motor_params.J,
            B=request.motor_params.B,
            p=request.motor_params.p,
            Pn=request.motor_params.Pn,
            Tn=request.motor_params.Tn,
            Nn=request.motor_params.Nn,
            In=request.motor_params.In,
            Vdc=request.motor_params.Vdc,
        )

        # 解析整定方法
        method = _parse_method(request.method)

        # 创建整定器并执行
        tuner = FOCPITuner(motor_params, method)
        result = tuner.tune_all(
            current_bw=request.current_bw,
            speed_bw=request.speed_bw,
            damping=request.damping,
        )

        # 转换为响应格式
        response = TuneResponse(
            current_d=_pi_to_response(result.current_d) if result.current_d else None,
            current_q=_pi_to_response(result.current_q) if result.current_q else None,
            speed=_pi_to_response(result.speed) if result.speed else None,
            warnings=result.warnings,
            suggestions=result.suggestions,
            tuning_guide=result.tuning_guide,
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"整定计算失败: {e}")
