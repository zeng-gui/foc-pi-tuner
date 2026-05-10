"""应用配置管理模块。

支持从YAML文件和环境变量加载配置，环境变量优先级更高。
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """应用配置。

    Attributes:
        ai_provider: AI提供商名称。
        ai_api_key: API密钥。
        ai_base_url: API基础URL。
        ai_model: 模型名称。
        ai_temperature: 温度参数。
        ai_max_tokens: 最大token数。
        ai_timeout: 请求超时时间（秒）。
    """

    ai_provider: str = "deepseek"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "deepseek-v4-flash"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 2048
    ai_timeout: float = 60.0


def load_ai_config() -> Optional[dict]:
    """加载AI配置，优先使用环境变量。

    Returns:
        配置字典或None。
    """
    config_path = Path(__file__).parent.parent / "config" / "ai_config.yaml"

    # 从YAML加载基础配置
    yaml_config = {}
    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f) or {}

    ai_config = yaml_config.get("ai", {})

    # 环境变量覆盖（支持多个变量名）
    # 优先使用配置文件中的值，除非环境变量以 sk- 开头（有效的DeepSeek密钥格式）
    env_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("MIMO_API_KEY") or os.getenv("OPENAI_API_KEY")
    config_key = ai_config.get("api_key", "")

    # 如果环境变量是有效的DeepSeek密钥格式，优先使用；否则使用配置文件
    if env_key and env_key.startswith("sk-"):
        api_key = env_key
    elif config_key and not config_key.startswith("${"):
        api_key = config_key
    else:
        api_key = env_key or config_key

    if not api_key or api_key.startswith("${"):
        return None

    return {
        "provider": os.getenv("AI_PROVIDER", ai_config.get("provider", "deepseek")),
        "api_key": api_key,
        "base_url": os.getenv("AI_BASE_URL", ai_config.get("base_url", "")),
        "model": os.getenv("AI_MODEL", ai_config.get("model", "deepseek-v4-flash")),
        "temperature": float(os.getenv("AI_TEMPERATURE", ai_config.get("temperature", 0.7))),
        "max_tokens": int(os.getenv("AI_MAX_TOKENS", ai_config.get("max_tokens", 2048))),
        "timeout": float(os.getenv("AI_TIMEOUT", ai_config.get("timeout", 60.0))),
    }


def load_config() -> AppConfig:
    """加载应用配置。

    Returns:
        AppConfig实例。
    """
    ai_config = load_ai_config() or {}

    return AppConfig(
        ai_provider=ai_config.get("provider", "deepseek"),
        ai_api_key=ai_config.get("api_key", ""),
        ai_base_url=ai_config.get("base_url", ""),
        ai_model=ai_config.get("model", "deepseek-v4-flash"),
        ai_temperature=ai_config.get("temperature", 0.7),
        ai_max_tokens=ai_config.get("max_tokens", 2048),
        ai_timeout=ai_config.get("timeout", 60.0),
    )
