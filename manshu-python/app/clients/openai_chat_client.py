"""
OpenAI Chat API 客户端 - 用于聊天对话
"""
from typing import List, Dict, Optional, AsyncIterator
from openai import AsyncOpenAI
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIChatClient:
    """OpenAI Chat API 客户端"""
    
    def __init__(self):
        """初始化OpenAI客户端"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_CHAT_MODEL
        self.temperature = settings.OPENAI_CHAT_TEMPERATURE
        self.max_tokens = settings.OPENAI_CHAT_MAX_TOKENS
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        流式调用 OpenAI Chat API
        
        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}]
            model: 模型名称（可选，默认使用配置的模型）
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            stream: 是否流式返回（默认True）
            
        Yields:
            str: 返回的内容块
        """
        try:
            # 构建请求参数
            request_params = {
                "model": model or self.model,
                "messages": messages,
                "stream": stream,
            }
            
            # 可选参数
            if temperature is not None:
                request_params["temperature"] = temperature
            elif self.temperature is not None:
                request_params["temperature"] = self.temperature
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            elif self.max_tokens is not None:
                request_params["max_tokens"] = self.max_tokens
            
            logger.debug(f"调用OpenAI Chat API: model={request_params['model']}, messages={len(messages)}条")
            
            # 流式调用
            stream_response = await self.client.chat.completions.create(**request_params)
            
            # 处理流式响应
            async for chunk in stream_response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                
                # 检查是否完成
                if chunk.choices and chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                    if finish_reason == "stop":
                        logger.debug("OpenAI 响应完成")
                    elif finish_reason == "length":
                        logger.warning("OpenAI 响应因长度限制被截断")
                    break
            
        except Exception as e:
            logger.error(f"OpenAI Chat API调用失败: {e}", exc_info=True)
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        非流式调用 OpenAI Chat API（返回完整响应）
        
        Args:
            messages: 消息列表
            model: 模型名称（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            
        Returns:
            str: 完整的响应内容
        """
        try:
            request_params = {
                "model": model or self.model,
                "messages": messages,
                "stream": False,
            }
            
            if temperature is not None:
                request_params["temperature"] = temperature
            elif self.temperature is not None:
                request_params["temperature"] = self.temperature
            
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            elif self.max_tokens is not None:
                request_params["max_tokens"] = self.max_tokens
            
            response = await self.client.chat.completions.create(**request_params)
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            
            return ""
            
        except Exception as e:
            logger.error(f"OpenAI Chat API调用失败: {e}", exc_info=True)
            raise


# 全局客户端实例
openai_chat_client = OpenAIChatClient()

