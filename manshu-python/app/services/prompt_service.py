"""
Prompt 服务 - 管理 Prompt 模板和构建
"""
from typing import List, Dict, Optional
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptService:
    """Prompt 模板管理服务"""
    
    def __init__(self):
        """初始化Prompt模板"""
        self.templates = {
            "knowledge_qa": {
                "template": """你是派聪明，一个基于本地知识库的智能助手。

当回答问题时，请遵循以下规则：
1. 优先基于提供的参考信息回答
2. 如果参考信息不足，清楚地表明
3. 回答要简洁、准确、客观
4. 引用来源时使用[文档X]格式

参考信息：
{context}

文档来源：
{sources}

对话历史：
{history}

用户问题：{query}

请用中文回答，并引用相关文档来源。""",
                "variables": ["context", "history", "query", "sources"],
                "max_tokens": 4000
            },
            "simple_qa": {
                "template": """你是派聪明，一个智能助手。

对话历史：
{history}

用户问题：{query}

请用中文回答。""",
                "variables": ["history", "query"],
                "max_tokens": 2000
            }
        }
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """
        获取模板配置
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板配置，如果不存在返回None
        """
        return self.templates.get(template_name)
    
    def build_prompt(
        self,
        template_name: str,
        context: str = "",
        history: List[Dict] = None,
        query: str = "",
        sources: List[Dict] = None
    ) -> str:
        """
        构建Prompt
        
        Args:
            template_name: 模板名称
            context: 检索到的上下文信息
            history: 对话历史列表
            query: 用户问题
            sources: 文档来源列表
            
        Returns:
            构建好的Prompt字符串
        """
        template_config = self.get_template(template_name)
        if not template_config:
            logger.warning(f"模板 {template_name} 不存在，使用默认模板")
            template_config = self.templates["knowledge_qa"]
        
        template_str = template_config["template"]
        history = history or []
        sources = sources or []
        
        # 格式化历史记录（只取最近5轮）
        history_str = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in history[-5:]
        ]) if history else "无"
        
        # 格式化来源信息
        sources_str = "\n".join([
            f"[文档{i+1}] {source.get('file_name', '未知文件')}"
            for i, source in enumerate(sources)
        ]) if sources else "无"
        
        # 构建参数字典
        params = {
            "context": context or "未找到相关参考信息。",
            "history": history_str,
            "query": query,
            "sources": sources_str
        }
        
        # 根据模板需要的变量进行替换
        try:
            prompt = template_str.format(**params)
            logger.debug(f"构建Prompt成功: 模板={template_name}, 上下文长度={len(context)}")
            return prompt
        except KeyError as e:
            logger.error(f"构建Prompt失败: 缺少变量 {e}")
            # 使用简单格式作为fallback
            return f"用户问题：{query}\n\n请回答。"
    
    def build_rag_prompt(
        self,
        context: str,
        history: List[Dict],
        query: str,
        sources: List[Dict]
    ) -> str:
        """
        构建RAG Prompt（便捷方法）
        
        Args:
            context: 检索到的上下文
            history: 对话历史
            query: 用户问题
            sources: 文档来源
            
        Returns:
            Prompt字符串
        """
        return self.build_prompt(
            template_name="knowledge_qa",
            context=context,
            history=history,
            query=query,
            sources=sources
        )
    
    def format_history_for_llm(self, history: List[Dict]) -> List[Dict[str, str]]:
        """
        将对话历史格式化为LLM需要的格式
        
        Args:
            history: 对话历史列表（包含role, content, timestamp）
            
        Returns:
            LLM格式的消息列表
        """
        messages = []
        for msg in history:
            if msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg.get("content", "")
                })
        return messages


# 全局服务实例
prompt_service = PromptService()

