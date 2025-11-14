"""
WebSocket 连接管理器 - 管理所有 WebSocket 连接和会话隔离
"""
from typing import Dict, Optional, Set
from fastapi import WebSocket
from app.models.user import User
import uuid
import asyncio
from datetime import datetime
from app.utils.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class WebSocketConnection:
    """单个 WebSocket 连接的封装"""
    
    def __init__(
        self,
        connection_id: str,
        websocket: WebSocket,
        user: User,
        conversation_id: str,
        created_at: datetime
    ):
        self.connection_id = connection_id
        self.websocket = websocket
        self.user = user
        self.conversation_id = conversation_id
        self.created_at = created_at
        self.last_activity = created_at
        self.last_ping_time: Optional[datetime] = None  # 最后一次发送ping的时间
        self.last_pong_time: Optional[datetime] = None  # 最后一次收到pong的时间
        self.is_active = True
        self.current_stop_token: Optional[str] = None
        self.pending_ping = False  # 是否有待响应的ping
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def is_idle(self, timeout_seconds: int) -> bool:
        """
        检查连接是否空闲（超过超时时间）
        
        Args:
            timeout_seconds: 超时时间（秒），0表示不超时
            
        Returns:
            是否空闲
        """
        if timeout_seconds <= 0:
            return False
        
        idle_seconds = (datetime.now() - self.last_activity).total_seconds()
        return idle_seconds > timeout_seconds
    
    def __repr__(self):
        return (
            f"<WebSocketConnection("
            f"id={self.connection_id}, "
            f"user_id={self.user.id}, "
            f"conversation_id={self.conversation_id}, "
            f"active={self.is_active}"
            f")>"
        )


class WebSocketConnectionManager:
    """
    WebSocket 连接管理器
    
    核心功能：
    1. 管理所有活跃的 WebSocket 连接
    2. 为每个连接分配独立的会话ID（连接级别隔离）
    3. 支持连接状态查询
    4. 异常断开检测和清理
    5. 基本消息路由（点对点）
    """
    
    def __init__(self):
        # 内存存储：连接ID -> WebSocketConnection
        self._connections: Dict[str, WebSocketConnection] = {}
        
        # 用户ID -> 连接ID集合（支持一个用户多个连接）
        self._user_connections: Dict[int, Set[str]] = {}
        
        # 会话ID -> 连接ID集合（一个会话可能被多个连接使用，但默认一对一）
        self._conversation_connections: Dict[str, Set[str]] = {}
        
        # 线程锁，保护并发访问
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        user: User,
        conversation_id: str
    ) -> str:
        """
        建立新的 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接对象
            user: 用户对象
            conversation_id: 会话ID（必填，由调用方验证和提供）
            
        Returns:
            连接ID
            
        Raises:
            ValueError: 如果超过连接数限制或会话ID无效
        """
        if not conversation_id:
            raise ValueError("会话ID不能为空")
        
        async with self._lock:
            # 检查单实例最大连接数
            if len(self._connections) >= settings.WEBSOCKET_MAX_CONNECTIONS_PER_INSTANCE:
                error_msg = (
                    f"达到单实例最大连接数限制: "
                    f"{settings.WEBSOCKET_MAX_CONNECTIONS_PER_INSTANCE}"
                )
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # 检查单用户最大连接数
            user_connections = self._user_connections.get(user.id, set())
            if len(user_connections) >= settings.WEBSOCKET_MAX_CONNECTIONS_PER_USER:
                error_msg = (
                    f"用户 {user.id} 达到最大连接数限制: "
                    f"{settings.WEBSOCKET_MAX_CONNECTIONS_PER_USER}"
                )
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            # 生成连接ID
            connection_id = f"ws_{uuid.uuid4().hex[:16]}"
            
            # 创建连接对象
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                user=user,
                conversation_id=conversation_id,
                created_at=datetime.now()
            )
            
            # 存储到内存
            self._connections[connection_id] = connection
            
            # 更新用户连接映射
            if user.id not in self._user_connections:
                self._user_connections[user.id] = set()
            self._user_connections[user.id].add(connection_id)
            
            # 更新会话连接映射
            if conversation_id not in self._conversation_connections:
                self._conversation_connections[conversation_id] = set()
            self._conversation_connections[conversation_id].add(connection_id)
            
            logger.info(
                f"WebSocket连接建立: connection_id={connection_id}, "
                f"user_id={user.id}, conversation_id={conversation_id}"
            )
            
            return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        断开连接并清理资源
        
        Args:
            connection_id: 连接ID
        """
        async with self._lock:
            if connection_id not in self._connections:
                logger.warning(f"尝试断开不存在的连接: {connection_id}")
                return
            
            connection = self._connections[connection_id]
            
            # 从用户连接映射中移除
            if connection.user.id in self._user_connections:
                self._user_connections[connection.user.id].discard(connection_id)
                if not self._user_connections[connection.user.id]:
                    del self._user_connections[connection.user.id]
            
            # 从会话连接映射中移除
            if connection.conversation_id in self._conversation_connections:
                self._conversation_connections[connection.conversation_id].discard(connection_id)
                if not self._conversation_connections[connection.conversation_id]:
                    del self._conversation_connections[connection.conversation_id]
            
            # 从内存中移除
            del self._connections[connection_id]
            
            logger.info(
                f"WebSocket连接断开: connection_id={connection_id}, "
                f"user_id={connection.user.id}"
            )
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        获取连接对象
        
        Args:
            connection_id: 连接ID
            
        Returns:
            连接对象，如果不存在则返回 None
        """
        return self._connections.get(connection_id)
    
    def get_conversation_id(self, connection_id: str) -> Optional[str]:
        """
        获取连接绑定的会话ID
        
        Args:
            connection_id: 连接ID
            
        Returns:
            会话ID，如果连接不存在则返回 None
        """
        connection = self.get_connection(connection_id)
        return connection.conversation_id if connection else None
    
    def get_user_connections(self, user_id: int) -> Set[str]:
        """
        获取用户的所有连接ID
        
        Args:
            user_id: 用户ID
            
        Returns:
            连接ID集合
        """
        return self._user_connections.get(user_id, set()).copy()
    
    def get_conversation_connections(self, conversation_id: str) -> Set[str]:
        """
        获取会话的所有连接ID
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            连接ID集合
        """
        return self._conversation_connections.get(conversation_id, set()).copy()
    
    async def send_to_connection(
        self,
        connection_id: str,
        message: dict
    ) -> bool:
        """
        向指定连接发送消息（点对点）
        
        Args:
            connection_id: 连接ID
            message: 消息字典
            
        Returns:
            是否发送成功
        """
        # 在锁内获取连接并检查状态
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection or not connection.is_active:
                logger.warning(f"尝试向无效连接发送消息: {connection_id}")
                return False
        
        # 在锁外发送消息（避免长时间持锁）
        try:
            await connection.websocket.send_json(message)
            # 更新活动时间（需要锁保护）
            async with self._lock:
                conn = self._connections.get(connection_id)
                if conn:
                    conn.update_activity()
            return True
        except Exception as e:
            logger.error(
                f"向连接发送消息失败: connection_id={connection_id}, "
                f"error={e}"
            )
            # 标记为不活跃（需要锁保护）
            async with self._lock:
                conn = self._connections.get(connection_id)
                if conn:
                    conn.is_active = False
            return False
    
    def get_statistics(self) -> dict:
        """
        获取连接统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_connections": len(self._connections),
            "total_users": len(self._user_connections),
            "total_conversations": len(self._conversation_connections),
            "connections_per_user": {
                user_id: len(conn_ids)
                for user_id, conn_ids in self._user_connections.items()
            }
        }
    
    async def send_heartbeat_ping(self, connection_id: str) -> bool:
        """
        向连接发送心跳ping消息
        
        Args:
            connection_id: 连接ID
            
        Returns:
            是否发送成功
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return False
        
        # 在锁内检查状态，避免并发修改
        async with self._lock:
            if not connection.is_active:
                return False
            
            # 如果已有待响应的ping，跳过
            if connection.pending_ping:
                return True
        
        # 在锁外发送消息（避免长时间持锁）
        try:
            ping_message = {
                "type": "ping",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            await asyncio.wait_for(
                connection.websocket.send_json(ping_message),
                timeout=1.0
            )
            # 更新状态（需要锁保护）
            async with self._lock:
                conn = self._connections.get(connection_id)
                if conn:
                    conn.last_ping_time = datetime.now()
                    conn.pending_ping = True
            return True
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(
                f"发送心跳ping失败: connection_id={connection_id}, error={e}"
            )
            # 标记为不活跃（需要锁保护）
            async with self._lock:
                conn = self._connections.get(connection_id)
                if conn:
                    conn.is_active = False
            return False
    
    async def handle_pong(self, connection_id: str):
        """
        处理客户端返回的pong响应
        
        Args:
            connection_id: 连接ID
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if connection:
                connection.last_pong_time = datetime.now()
                connection.pending_ping = False
                connection.update_activity()
    
    async def cleanup_inactive_connections(self):
        """
        清理不活跃的连接（心跳检测）
        
        检测策略：
        1. 检查连接是否空闲（超过IDLE_TIMEOUT）
        2. 发送ping检测连接是否响应
        3. 清理无响应的连接
        """
        if not self._connections:
            return
        
        now = datetime.now()
        inactive_connections = []
        ping_connections = []
        
        # 第一步：在锁内收集需要处理的连接ID（复制列表避免迭代时修改）
        async with self._lock:
            connection_ids = list(self._connections.keys())
        
        # 第二步：在锁外检查连接状态（避免长时间持锁）
        for connection_id in connection_ids:
            connection = self.get_connection(connection_id)
            if not connection:
                # 连接已被删除，跳过
                continue
            
            # 如果已经标记为不活跃，直接清理
            if not connection.is_active:
                inactive_connections.append(connection_id)
                continue
            
            # 检查空闲超时
            if settings.WEBSOCKET_IDLE_TIMEOUT > 0:
                if connection.is_idle(settings.WEBSOCKET_IDLE_TIMEOUT):
                    logger.debug(
                        f"连接空闲超时: connection_id={connection_id}, "
                        f"idle_seconds={(now - connection.last_activity).total_seconds():.1f}"
                    )
                    # 如果空闲超时，先尝试ping检测
                    ping_connections.append(connection_id)
                    continue
            
            # 检查pending ping是否超时（超过5秒未收到pong）
            if connection.pending_ping and connection.last_ping_time:
                ping_timeout = (now - connection.last_ping_time).total_seconds()
                if ping_timeout > 5.0:  # ping超时5秒
                    logger.warning(
                        f"心跳ping超时: connection_id={connection_id}, "
                        f"timeout={ping_timeout:.1f}s"
                    )
                    # 在锁内标记为不活跃
                    async with self._lock:
                        conn = self._connections.get(connection_id)
                        if conn:
                            conn.is_active = False
                    inactive_connections.append(connection_id)
                    continue
        
        # 第三步：对空闲连接发送ping检测（在锁外，避免阻塞）
        for connection_id in ping_connections:
            success = await self.send_heartbeat_ping(connection_id)
            if not success:
                inactive_connections.append(connection_id)
        
        # 第四步：清理不活跃连接（disconnect内部有锁保护）
        for connection_id in inactive_connections:
            await self.disconnect(connection_id)
        
        if inactive_connections:
            logger.info(
                f"心跳检测清理了 {len(inactive_connections)} 个不活跃连接"
            )


# 全局管理器实例
websocket_manager = WebSocketConnectionManager()

