"""
聊天相关 Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MessageItem(BaseModel):
    """消息项"""
    role: str = Field(..., description="角色: user 或 assistant")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳，ISO格式")


class MessageItemWithUser(MessageItem):
    """带用户名的消息项（管理员接口）"""
    username: Optional[str] = Field(None, description="用户名")


class ConversationHistoryResponse(BaseModel):
    """对话历史响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取对话历史成功", description="消息")
    data: List[MessageItem] = Field(..., description="对话历史列表")


class ConversationHistoryAdminResponse(BaseModel):
    """管理员对话历史响应（包含用户名）"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取对话历史成功", description="消息")
    data: List[MessageItemWithUser] = Field(..., description="对话历史列表")


class WebSocketTokenData(BaseModel):
    """WebSocket Token数据"""
    cmdToken: str = Field(..., description="停止指令Token")


class WebSocketTokenResponse(BaseModel):
    """WebSocket停止指令Token响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取WebSocket停止指令Token成功", description="消息")
    data: WebSocketTokenData = Field(..., description="Token数据")


class WebSocketMessage(BaseModel):
    """WebSocket消息格式"""
    type: Optional[str] = Field(None, description="消息类型: stop, completion等")
    chunk: Optional[str] = Field(None, description="内容块（流式响应）")
    error: Optional[str] = Field(None, description="错误信息")
    status: Optional[str] = Field(None, description="状态: finished等")
    message: Optional[str] = Field(None, description="消息")
    timestamp: Optional[int] = Field(None, description="时间戳（毫秒）")
    date: Optional[str] = Field(None, description="日期时间（ISO格式）")
    internal_cmd_token: Optional[str] = Field(None, alias="_internal_cmd_token", description="内部停止指令Token")
    
    class Config:
        populate_by_name = True  # 允许使用字段名或别名


class ConversationItem(BaseModel):
    """会话项"""
    conversation_id: str = Field(..., description="会话ID")
    is_current: bool = Field(False, description="是否为当前会话")
    is_archived: bool = Field(False, description="是否已归档")
    message_count: int = Field(0, description="消息数量")
    last_message_time: Optional[str] = Field(None, description="最后一条消息时间")


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取会话列表成功", description="消息")
    data: List[ConversationItem] = Field(..., description="会话列表")


class ConversationQueryParams(BaseModel):
    """对话历史查询参数"""
    start_date: Optional[str] = Field(None, description="开始日期时间，格式: yyyy-MM-ddTHH:mm:ss")
    end_date: Optional[str] = Field(None, description="结束日期时间，格式: yyyy-MM-ddTHH:mm:ss")
    userid: Optional[int] = Field(None, description="用户ID（仅管理员接口）")

