"""OpenAI兼容AI提供商。

支持OpenAI API格式，兼容国产大模型（通过配置base_url）。
"""

from typing import Generator, Optional

from src.ai.providers.base import (
    AIConfig,
    AIMessage,
    AIProvider,
    AIProviderError,
    ResponseFormat,
)


class OpenAIProvider(AIProvider):
    """OpenAI兼容AI提供商。

    支持OpenAI API格式，可通过配置base_url接入国产大模型
    （如通义千问、文心一言、DeepSeek等兼容接口）。

    Attributes:
        name: 提供商名称。
        api_key: API密钥。
        base_url: API基础URL。
    """

    # 国产大模型默认base_url映射
    PROVIDER_URLS: dict[str, str] = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "moonshot": "https://api.moonshot.cn/v1",
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
        timeout: float = 60.0,
    ) -> None:
        """初始化OpenAI兼容提供商。

        Args:
            api_key: API密钥。
            base_url: API基础URL，None则根据provider自动选择。
            provider: 提供商标识，用于自动选择base_url。
                支持: openai, deepseek, qwen, zhipu, moonshot。
                当base_url显式指定时此参数被忽略。
            timeout: 请求超时时间（秒），默认60秒。
        """
        if base_url is None:
            base_url = self.PROVIDER_URLS.get(
                provider, self.PROVIDER_URLS["openai"]
            )
        super().__init__(api_key=api_key, base_url=base_url)
        self._provider_name = provider
        self._timeout = timeout

    @property
    def name(self) -> str:
        """提供商名称。"""
        return self._provider_name

    def _build_request_params(
        self,
        messages: list[AIMessage],
        config: AIConfig,
        stream: bool = False,
    ) -> dict:
        """构建API请求参数。

        Args:
            messages: 对话消息列表。
            config: 调用配置。
            stream: 是否流式请求。

        Returns:
            请求参数字典。
        """
        params: dict = {
            "model": config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": stream,
        }

        if config.response_format == ResponseFormat.JSON:
            params["response_format"] = {"type": "json_object"}

        params.update(config.extra_params)
        return params

    def _create_client(self):
        """创建OpenAI客户端实例。

        Returns:
            OpenAI客户端。

        Raises:
            AIProviderError: 当openai包未安装时。
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise AIProviderError(
                "请安装openai包: pip install openai",
                provider=self.name,
            )
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self._get_timeout(),
        )

    def _get_timeout(self) -> float:
        """获取超时配置。

        Returns:
            超时时间（秒）。
        """
        return self._timeout

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
        if config is None:
            config = AIConfig()
        self.validate_config(config)

        try:
            client = self._create_client()
            params = self._build_request_params(messages, config, stream=False)
            response = client.chat.completions.create(**params)
            content = response.choices[0].message.content
            return content if content is not None else ""
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                f"API调用失败: {e}",
                provider=self.name,
            ) from e

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
        if config is None:
            config = AIConfig()
        self.validate_config(config)

        try:
            client = self._create_client()
            params = self._build_request_params(messages, config, stream=True)
            stream = client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                f"流式API调用失败: {e}",
                provider=self.name,
            ) from e
