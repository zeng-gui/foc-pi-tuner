"""AI提供商抽象基类。

定义统一的AI模型调用接口，支持流式和非流式响应。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Generator, Optional


class ResponseFormat(Enum):
    """响应格式。"""

    TEXT = auto()   # 纯文本
    JSON = auto()   # JSON格式


@dataclass
class AIConfig:
    """AI调用配置。

    Attributes:
        model: 模型名称。
        temperature: 温度参数，控制随机性。
        max_tokens: 最大生成token数。
        top_p: 核采样参数。
        response_format: 期望的响应格式。
        timeout: 请求超时时间（秒）。
        extra_params: 额外的模型参数。
    """

    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    response_format: ResponseFormat = ResponseFormat.TEXT
    timeout: float = 60.0
    extra_params: dict = field(default_factory=dict)


@dataclass
class AIMessage:
    """AI对话消息。

    Attributes:
        role: 角色（system/user/assistant）。
        content: 消息内容。
    """

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        """转换为API所需的字典格式。"""
        return {"role": self.role, "content": self.content}


class AIProvider(ABC):
    """AI提供商抽象基类。

    定义统一的模型调用接口，所有具体提供商需实现此接口。

    Attributes:
        name: 提供商名称。
        api_key: API密钥。
        base_url: API基础URL。
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
    ) -> None:
        """初始化提供商。

        Args:
            api_key: API密钥。
            base_url: API基础URL，None则使用默认值。
        """
        self.api_key = api_key
        self.base_url = base_url

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商名称。"""

    @abstractmethod
    def chat(
        self,
        messages: list[AIMessage],
        config: Optional[AIConfig] = None,
    ) -> str:
        """非流式对话。

        Args:
            messages: 对话消息列表。
            config: 调用配置，None则使用默认配置。

        Returns:
            模型响应文本。

        Raises:
            AIProviderError: 调用失败时抛出。
        """

    @abstractmethod
    def stream_chat(
        self,
        messages: list[AIMessage],
        config: Optional[AIConfig] = None,
    ) -> Generator[str, None, None]:
        """流式对话。

        Args:
            messages: 对话消息列表。
            config: 调用配置，None则使用默认配置。

        Yields:
            模型响应的文本片段。

        Raises:
            AIProviderError: 调用失败时抛出。
        """

    def validate_config(self, config: AIConfig) -> None:
        """验证配置参数有效性。

        Args:
            config: 调用配置。

        Raises:
            ValueError: 配置参数无效时抛出。
        """
        if config.temperature < 0 or config.temperature > 2.0:
            raise ValueError(
                f"temperature应在0~2之间，当前值: {config.temperature}"
            )
        if config.max_tokens < 1:
            raise ValueError(
                f"max_tokens应大于0，当前值: {config.max_tokens}"
            )
        if config.top_p < 0 or config.top_p > 1.0:
            raise ValueError(
                f"top_p应在0~1之间，当前值: {config.top_p}"
            )


class AIProviderError(Exception):
    """AI提供商调用异常。

    Attributes:
        provider: 提供商名称。
        status_code: HTTP状态码（如有）。
        message: 错误描述。
    """

    def __init__(
        self,
        message: str,
        provider: str = "",
        status_code: Optional[int] = None,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)
