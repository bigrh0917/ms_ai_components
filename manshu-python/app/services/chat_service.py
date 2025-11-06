"""
聊天服务 - 整合知识检索和LLM生成回答
"""
from typing import List, Dict, Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.search_service import search_service
from app.services.prompt_service import prompt_service
from app.services.conversation_service import conversation_service
from app.clients.openai_chat_client import openai_chat_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """聊天服务"""
    
    def __init__(self):
        self.search_service = search_service
        self.prompt_service = prompt_service
        self.chat_client = openai_chat_client
        self.conversation_service = conversation_service
    
    def _format_search_results(self, results: List[Dict]) -> tuple[str, List[Dict]]:
        """
        格式化检索结果为上下文和来源信息
        
        Args:
            results: 检索结果列表
            
        Returns:
            (context_str, sources_list): 上下文字符串和来源列表
        """
        if not results:
            return "未找到相关参考信息。", []
        
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            # 提取文本内容（限制长度）
            text_content = result.get('text_content', '')
            if len(text_content) > 300:
                text_content = text_content[:300] + "..."
            
            context_parts.append(
                f"[文档{i}]\n"
                f"文件: {result.get('file_name', '未知文件')}\n"
                f"内容: {text_content}\n"
            )
            
            sources.append({
                "index": i,
                "file_name": result.get('file_name', '未知文件'),
                "file_md5": result.get('file_md5'),
                "chunk_id": result.get('chunk_id'),
                "score": result.get('score', 0.0)
            })
        
        context_str = "\n".join(context_parts)
        return context_str, sources
    
    async def process_message(
        self,
        db: AsyncSession,
        user: User,
        message: str,
        conversation_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        处理用户消息，返回流式响应
        
        Args:
            db: 数据库会话
            user: 当前用户
            message: 用户消息
            conversation_id: 会话ID（可选，如果不提供则自动获取或创建）
            
        Yields:
            str: 响应内容块
        """
        try:
            # 1. 获取或创建会话ID
            if not conversation_id:
                conversation_id = await self.conversation_service.get_or_create_conversation(user.id)
            
            # 1.5. 检查会话是否已归档
            is_archived = await self.conversation_service.is_archived(conversation_id, db)
            if is_archived:
                yield "该会话已归档，无法继续对话。请创建新会话或使用其他会话。"
                return
            
            logger.info(f"处理用户消息: user_id={user.id}, conversation_id={conversation_id}")
            
            # 2. 知识库检索
            logger.info(f"开始知识库检索: {message[:50]}...")
            search_results = await self.search_service.hybrid_search(
                db=db,
                user=user,
                query_text=message,
                top_k=5
            )
            
            logger.info(f"检索完成，找到 {len(search_results)} 个相关文档")
            
            # 3. 处理检索结果
            context, sources = self._format_search_results(search_results)
            
            # 4. 获取对话历史（传入db以支持从MySQL查询已归档会话）
            history = await self.conversation_service.get_conversation_history(conversation_id, db=db)
            
            # 5. 构建Prompt
            prompt = self.prompt_service.build_rag_prompt(
                context=context,
                history=history,
                query=message,
                sources=sources
            )
            
            # 6. 构建LLM消息
            messages = [
                {"role": "system", "content": "你是派聪明，一个基于本地知识库的智能助手。请根据提供的参考信息回答问题，如果信息不足请明确说明。"},
                {"role": "user", "content": prompt}
            ]
            
            # 7. 保存用户消息（传入db以检查归档状态）
            await self.conversation_service.save_message(
                conversation_id, "user", message, db=db
            )
            
            # 8. 流式调用OpenAI Chat API
            logger.info("开始调用OpenAI Chat API（流式）")
            assistant_content = ""
            chunk_count = 0
            
            try:
                async for chunk in self.chat_client.stream_chat(messages):
                    assistant_content += chunk
                    chunk_count += 1
                    yield chunk
                
                logger.info(f"OpenAI响应完成，共 {chunk_count} 个chunk，总长度 {len(assistant_content)}")
                
            except Exception as e:
                error_type = type(e).__name__
                error_detail = str(e)
                logger.error(f"OpenAI API调用失败: {error_type}: {error_detail}", exc_info=True)
                
                # 根据错误类型提供更具体的错误消息
                if "rate_limit" in error_detail.lower() or "RateLimitError" in error_type:
                    error_msg = "AI服务请求过于频繁，请稍后重试。"
                elif "authentication" in error_detail.lower() or "AuthenticationError" in error_type:
                    error_msg = "AI服务认证失败，请联系管理员。"
                elif "timeout" in error_detail.lower() or "Timeout" in error_type:
                    error_msg = "AI服务响应超时，请稍后重试。"
                elif "connection" in error_detail.lower() or "Connection" in error_type:
                    error_msg = "无法连接到AI服务，请检查网络连接。"
                else:
                    error_msg = f"AI服务暂时不可用: {error_detail[:100]}（错误类型: {error_type}）"
                
                yield error_msg
                assistant_content = error_msg
            
            # 9. 保存助手回复（传入db以检查归档状态）
            if assistant_content:
                await self.conversation_service.save_message(
                    conversation_id, "assistant", assistant_content, db=db
                )
            
        except Exception as e:
            error_type = type(e).__name__
            error_detail = str(e)
            logger.error(f"处理用户消息失败: {error_type}: {error_detail}", exc_info=True)
            
            # 根据错误类型提供更具体的错误消息
            if "archived" in error_detail.lower():
                yield "该会话已归档，无法继续对话。请创建新会话。"
            elif "database" in error_detail.lower() or "Database" in error_type:
                yield "数据库操作失败，请稍后重试。如果问题持续，请联系管理员。"
            elif "embedding" in error_detail.lower() or "Embedding" in error_type:
                yield "文本向量化失败，请重试或联系管理员。"
            elif "search" in error_detail.lower() or "Search" in error_type:
                yield "知识库检索失败，请稍后重试。"
            else:
                yield f"处理消息时出错: {error_detail[:100]}（错误类型: {error_type}）"
    
    async def get_conversation_history(
        self,
        user_id: int,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID（可选，如果不提供则使用当前会话）
            
        Returns:
            对话历史列表
        """
        if not conversation_id:
            conversation_id = await self.conversation_service.get_current_conversation(user_id)
        
        if not conversation_id:
            return []
        
        return await self.conversation_service.get_conversation_history(conversation_id)
    
    async def create_new_conversation(self, user_id: int) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            新会话ID
        """
        return await self.conversation_service.create_conversation(user_id)
    
    async def clear_conversation(self, conversation_id: str) -> bool:
        """
        清空对话历史
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            是否成功
        """
        return await self.conversation_service.clear_conversation(conversation_id)


# 全局服务实例
chat_service = ChatService()

