"""
聊天路由 - WebSocket和REST API
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service
from app.services.websocket_manager import websocket_manager
from app.schemas.chat import (
    ConversationHistoryResponse,
    ConversationHistoryAdminResponse,
    ConversationListResponse,
    ConversationItem,
    MessageItem,
    MessageItemWithUser,
    WebSocketTokenResponse,
    WebSocketTokenData,
    ArchiveConversationResponse,
    ArchiveConversationData,
)
from app.clients.redis_client import redis_client
from app.clients.db_client import db_client
from app.core.config import settings
from app.utils import jwt_utils
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def verify_websocket_token(websocket: WebSocket, token: str) -> Optional[User]:
    """
    验证WebSocket连接的JWT Token
    
    Args:
        websocket: WebSocket连接
        token: JWT Token
        
    Returns:
        用户对象，如果验证失败则返回None
    """
    try:
        # 验证token
        if not await jwt_utils.validate_token(token):
            logger.warning("WebSocket Token验证失败")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token验证失败")
            return None
        
        # 提取用户名
        username = jwt_utils.extract_username(token)
        if not username:
            logger.warning("WebSocket Token中无法提取用户名")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token无效")
            return None
        
        # 查询用户（需要数据库连接）
        from sqlalchemy import select
        
        async for db in db_client.get_session():
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
                return None
            
            return user
            
    except Exception as e:
        logger.error(f"WebSocket Token验证异常: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="服务器错误")
        return None


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket聊天接口（使用连接管理器）
    
    客户端连接: ws://host/api/v1/chat?token={jwt_token}[&conversation_id={conversation_id}]
    其中token是JWT Token（通过查询参数传递）
    conversation_id是可选的，如果不提供则创建新会话
    
    消息格式:
    - 普通消息: 纯文本字符串 或 {"type": "message", "content": "..."}
    - 停止指令: {"type": "stop", "_internal_cmd_token": "..."}
    - 心跳响应: {"type": "pong"} (响应服务端的ping消息)
    
    响应格式:
    - 连接成功: {"type": "connected", "connection_id": "...", "conversation_id": "..."}
    - 心跳ping: {"type": "ping", "timestamp": ...} (服务端定期发送，客户端应回复pong)
    - 内容块: {"chunk": "..."}
    - 完成通知: {"type": "completion", "status": "finished", ...}
    - 停止确认: {"type": "stop", "message": "响应已停止", ...}
    - 错误: {"error": "..."}
    
    心跳机制:
    - 服务端会定期发送ping消息检测连接活跃度
    - 客户端收到ping后应回复pong消息
    - 如果连接空闲超过WEBSOCKET_IDLE_TIMEOUT秒，服务端会发送ping检测
    - 如果ping后5秒内未收到pong响应，连接将被自动断开
    """
    # 从查询参数获取token和可选的会话ID
    query_params = dict(websocket.query_params)
    token = query_params.get("token")
    specified_conversation_id = query_params.get("conversation_id")
    
    if not token:
        logger.warning("WebSocket连接缺少Token参数")
        try:
            await websocket.accept()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少Token参数")
        except:
            pass
        return
    
    logger.info(f"收到WebSocket连接请求，Token长度: {len(token)}")
    
    websocket_accepted = False
    try:
        await websocket.accept()
        websocket_accepted = True
        logger.info("WebSocket连接已接受")
    except Exception as e:
        logger.error(f"WebSocket accept失败: {e}", exc_info=True)
        return
    
    # 验证Token
    user = await verify_websocket_token(websocket, token)
    if not user:
        logger.warning("WebSocket Token验证失败，连接已关闭")
        if websocket_accepted:
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token验证失败")
            except:
                pass
        return
    
    # 确定要使用的会话ID
    conversation_id = None
    try:
        # 如果指定了会话ID，验证权限
        if specified_conversation_id:
            # 验证会话是否属于该用户
            async for db in db_client.get_session():
                is_owner = await conversation_service.verify_conversation_ownership(
                    specified_conversation_id,
                    user.id,
                    db=db
                )
                if not is_owner:
                    logger.warning(
                        f"用户 {user.id} 尝试访问不属于自己的会话: {specified_conversation_id}"
                    )
                    try:
                        await websocket.send_json({
                            "error": "无权访问该会话",
                            "type": "permission_denied"
                        })
                        await websocket.close(
                            code=status.WS_1008_POLICY_VIOLATION,
                            reason="无权访问该会话"
                        )
                    except:
                        pass
                    return
                conversation_id = specified_conversation_id
                break
        else:
            # 如果没有指定，创建新会话
            conversation_id = await conversation_service.create_conversation(user.id)
            logger.info(f"为用户 {user.id} 创建新会话: {conversation_id}")
    except Exception as e:
        logger.error(f"会话处理失败: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "error": "会话处理失败，请稍后重试",
                "type": "conversation_error"
            })
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="服务器错误"
            )
        except:
            pass
        return
    
    # 防御性检查：确保 conversation_id 不为空
    if not conversation_id:
        logger.error("会话ID为空，无法建立连接")
        try:
            await websocket.send_json({
                "error": "会话处理失败",
                "type": "conversation_error"
            })
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="服务器错误"
            )
        except:
            pass
        return
    
    # 使用连接管理器建立连接
    connection_id = None
    try:
        try:
            connection_id = await websocket_manager.connect(
                websocket=websocket,
                user=user,
                conversation_id=conversation_id
            )
        except ValueError as e:
            # 连接数限制错误
            logger.warning(f"连接数限制: {e}")
            await websocket.send_json({
                "error": "连接数已达到上限，请稍后再试",
                "type": "connection_limit"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="连接数限制")
            return
        
        logger.info(
            f"WebSocket连接建立: connection_id={connection_id}, "
            f"user_id={user.id}, conversation_id={conversation_id}"
        )
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "conversation_id": conversation_id,
            "timestamp": int(time.time() * 1000)
        })
        
        # 停止令牌（用于安全地停止响应）
        stop_token = None
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                
                # 获取连接对象并更新活动时间
                connection = websocket_manager.get_connection(connection_id)
                if connection:
                    connection.update_activity()
                
                # 解析消息（尝试JSON格式）
                message_data = None
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type")
                    
                    # 处理心跳pong响应
                    if message_type == "pong":
                        await websocket_manager.handle_pong(connection_id)
                        logger.debug(f"收到心跳pong响应: connection_id={connection_id}")
                        continue
                    
                    if message_type == "stop":
                        # 验证停止令牌
                        cmd_token = message_data.get("_internal_cmd_token")
                        if connection and cmd_token and cmd_token == connection.current_stop_token:
                            await websocket_manager.send_to_connection(connection_id, {
                                "type": "stop",
                                "message": "响应已停止",
                                "timestamp": int(time.time() * 1000),
                                "date": datetime.now().isoformat()
                            })
                            logger.info(f"用户 {user.id} 停止响应")
                            break
                        else:
                            logger.warning(f"无效的停止令牌: user_id={user.id}")
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass  # 普通文本消息
                
                # 处理普通文本消息
                user_message = data if isinstance(data, str) else (message_data.get("content", "") if message_data else "")
                
                if not user_message or not user_message.strip():
                    continue
                
                logger.info(
                    f"收到用户消息: connection_id={connection_id}, "
                    f"user_id={user.id}, message_length={len(user_message)}"
                )
                
                # 生成停止令牌（每次新请求都生成新的）
                stop_token = f"WSS_STOP_CMD_{uuid.uuid4().hex[:8]}"
                if connection:
                    connection.current_stop_token = stop_token
                
                await redis_client.set(
                    f"chat:stop_token:{stop_token}",
                    str(user.id),
                    expire=settings.CHAT_STOP_TOKEN_TTL
                )
                
                # 处理消息（流式返回，使用连接绑定的会话ID）
                try:
                    async for db in db_client.get_session():
                        async for chunk in chat_service.process_message(
                            db, user, user_message,
                            conversation_id=conversation_id  # 使用连接绑定的会话ID
                        ):
                            # 检查是否收到停止指令
                            try:
                                # 非阻塞检查停止令牌是否已被删除
                                token_exists = await redis_client.exists(f"chat:stop_token:{stop_token}")
                                if not token_exists:
                                    logger.info(
                                        f"检测到停止请求，中断响应: "
                                        f"connection_id={connection_id}, user_id={user.id}"
                                    )
                                    await websocket_manager.send_to_connection(connection_id, {
                                        "type": "stop",
                                        "message": "响应已停止",
                                        "timestamp": int(time.time() * 1000),
                                        "date": datetime.now().isoformat()
                                    })
                                    break
                            except:
                                pass
                            
                            # 发送内容块
                            await websocket_manager.send_to_connection(
                                connection_id,
                                {"chunk": chunk}
                            )
                        
                        # 发送完成通知
                        await websocket_manager.send_to_connection(connection_id, {
                            "type": "completion",
                            "status": "finished",
                            "message": "响应已完成",
                            "timestamp": int(time.time() * 1000),
                            "date": datetime.now().isoformat()
                        })
                        
                        # 清理停止令牌
                        await redis_client.delete(f"chat:stop_token:{stop_token}")
                        break  # 退出循环，因为我们只需要一个会话
                    
                except Exception as e:
                    logger.error(
                        f"处理消息失败: connection_id={connection_id}, error={e}",
                        exc_info=True
                    )
                    await websocket_manager.send_to_connection(connection_id, {
                        "error": "AI服务暂时不可用，请稍后重试"
                    })
        
        except WebSocketDisconnect:
            logger.info(
                f"WebSocket连接断开: connection_id={connection_id}, user_id={user.id}"
            )
        except Exception as e:
            logger.error(
                f"WebSocket处理错误: connection_id={connection_id}, error={e}",
                exc_info=True
            )
            try:
                await websocket_manager.send_to_connection(connection_id, {
                    "error": "服务器内部错误"
                })
            except:
                pass
        finally:
            # 清理停止令牌
            if stop_token:
                await redis_client.delete(f"chat:stop_token:{stop_token}")
    
    except Exception as e:
        logger.error(f"WebSocket连接管理错误: {e}", exc_info=True)
    finally:
        # 从连接管理器中移除连接
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.get("/chat/websocket/statistics")
async def get_websocket_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取 WebSocket 连接统计信息（管理员功能）
    
    返回当前活跃连接数、用户数、会话数等统计信息
    """
    # 检查是否为管理员（可选）
    # if current_user.role != UserRole.ADMIN:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="需要管理员权限"
    #     )
    
    statistics = websocket_manager.get_statistics()
    
    # 获取当前用户的连接信息
    user_connections = websocket_manager.get_user_connections(current_user.id)
    user_connection_details = []
    for conn_id in user_connections:
        conn = websocket_manager.get_connection(conn_id)
        if conn:
            user_connection_details.append({
                "connection_id": conn.connection_id,
                "conversation_id": conn.conversation_id,
                "created_at": conn.created_at.isoformat(),
                "last_activity": conn.last_activity.isoformat(),
                "is_active": conn.is_active
            })
    
    return {
        "code": 200,
        "message": "获取统计信息成功",
        "data": {
            **statistics,
            "current_user_connections": len(user_connections),
            "current_user_connection_details": user_connection_details
        }
    }


@router.get("/chat/websocket-token", response_model=WebSocketTokenResponse)
async def get_websocket_token(
    current_user: User = Depends(get_current_user)
):
    """
    获取WebSocket停止指令Token
    
    用于安全地停止正在进行的AI响应
    """
    # 生成停止令牌
    cmd_token = f"WSS_STOP_CMD_{uuid.uuid4().hex[:8]}"
    
    # 存储到Redis（短期有效）
    await redis_client.set(
        f"chat:stop_token:{cmd_token}",
        str(current_user.id),
        expire=settings.CHAT_STOP_TOKEN_TTL
    )
    
    return WebSocketTokenResponse(
        code=200,
        message="获取WebSocket停止指令Token成功",
        data=WebSocketTokenData(cmdToken=cmd_token)
    )


@router.get("/users/conversations", response_model=ConversationListResponse)
async def get_conversation_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的所有会话列表
    """
    try:
        # 获取当前会话ID
        current_conversation_id = await conversation_service.get_current_conversation(current_user.id)
        
        # 获取用户的所有会话ID列表
        conversation_ids = await conversation_service.get_user_conversations(current_user.id)
        
        # 如果没有会话列表，但存在当前会话，则添加当前会话
        if current_conversation_id and current_conversation_id not in conversation_ids:
            conversation_ids.append(current_conversation_id)
        
        # 构建会话列表
        conversations = []
        for conv_id in conversation_ids:
            # 检查是否已归档
            is_archived = await conversation_service.is_archived(conv_id, db)
            
            # 获取会话历史以获取消息数量和时间
            history = await conversation_service.get_conversation_history(conv_id, db=db)
            message_count = len(history)
            last_message_time = None
            if history:
                last_message_time = history[-1].get("timestamp")
            
            conversations.append(ConversationItem(
                conversation_id=conv_id,
                is_current=(conv_id == current_conversation_id),
                is_archived=is_archived,
                message_count=message_count,
                last_message_time=last_message_time
            ))
        
        # 按最后消息时间排序（最新的在前）
        conversations.sort(key=lambda x: x.last_message_time or "", reverse=True)
        
        return ConversationListResponse(
            code=200,
            message="获取会话列表成功",
            data=conversations
        )
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话列表失败"
        )


@router.get("/users/conversation", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: Optional[str] = Query(None, description="会话ID，如果不提供则返回当前会话"),
    start_date: Optional[str] = Query(None, description="开始日期时间"),
    end_date: Optional[str] = Query(None, description="结束日期时间"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的对话历史
    
    查询参数:
    - conversation_id: 会话ID（可选，如果不提供则返回当前会话）
    - start_date: 开始日期时间（可选）
    - end_date: 结束日期时间（可选）
    
    日期格式支持:
    - yyyy-MM-dd
    - yyyy-MM-ddTHH:mm
    - yyyy-MM-ddTHH:mm:ss
    """
    try:
        # 如果没有提供会话ID，则使用当前会话
        if not conversation_id:
            conversation_id = await conversation_service.get_current_conversation(current_user.id)
        
        if not conversation_id:
            return ConversationHistoryResponse(
                code=200,
                message="获取对话历史成功",
                data=[]
            )
        
        # 获取对话历史（传入db以支持从MySQL查询已归档会话）
        history = await conversation_service.get_conversation_history(conversation_id, db=db)
        
        # 过滤日期范围（如果提供）
        if start_date or end_date:
            filtered_history = []
            for msg in history:
                msg_timestamp = msg.get("timestamp", "")
                if msg_timestamp:
                    # 简单的日期过滤（可以根据需要完善）
                    if start_date and msg_timestamp < start_date:
                        continue
                    if end_date and msg_timestamp > end_date:
                        continue
                filtered_history.append(msg)
            history = filtered_history
        
        # 转换为响应格式
        messages = [
            MessageItem(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", datetime.now().isoformat())
            )
            for msg in history
        ]
        
        return ConversationHistoryResponse(
            code=200,
            message="获取对话历史成功",
            data=messages
        )
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话历史失败"
        )


@router.get("/admin/conversation", response_model=ConversationHistoryAdminResponse)
async def get_admin_conversation_history(
    userid: Optional[int] = Query(None, description="目标用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期时间"),
    end_date: Optional[str] = Query(None, description="结束日期时间"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员接口：获取对话历史（可查询指定用户）
    
    需要管理员权限
    """
    from app.models.user import UserRole
    
    # 检查管理员权限
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    try:
        # 如果指定了用户ID，查询该用户；否则查询所有用户（简化实现，实际可能需要分页）
        if userid:
            # 查询指定用户
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == userid))
            target_user = result.scalar_one_or_none()
            
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在"
                )
            
            conversation_id = await conversation_service.get_current_conversation(userid)
            if conversation_id:
                history = await conversation_service.get_conversation_history(conversation_id)
                
                messages = [
                    MessageItemWithUser(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        timestamp=msg.get("timestamp", datetime.now().isoformat()),
                        username=target_user.username
                    )
                    for msg in history
                ]
            else:
                messages = []
        else:
            # 查询所有用户（简化实现，实际可能需要分页和更复杂的逻辑）
            messages = []
            # TODO: 实现查询所有用户的对话历史
        
        return ConversationHistoryAdminResponse(
            code=200,
            message="获取对话历史成功",
            data=messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取管理员对话历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话历史失败"
        )


@router.post("/conversations/{conversation_id}/archive", response_model=ArchiveConversationResponse)
async def archive_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    归档会话：将Redis中的会话历史保存到MySQL，并从Redis删除
    
    归档后的会话变为只读模式，无法再添加新消息
    
    响应格式:
    {
        "code": 200,
        "message": "会话归档成功",
        "data": {
            "conversation_id": "...",
            "archived_at": "2025-01-26T10:30:15"
        }
    }
    """
    try:
        # 检查会话是否存在（从Redis或MySQL）
        history = await conversation_service.get_conversation_history(conversation_id, db=db)
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或已为空"
            )
        
        # 检查是否已归档
        is_archived = await conversation_service.is_archived(conversation_id, db)
        if is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="会话已经归档"
            )
        
        # 权限验证：只能归档自己的会话
        # 如果会话在Redis中存在（有历史记录），说明是活跃会话，允许归档
        # 如果会话不在Redis中，说明可能已过期或被删除，拒绝归档
        # 注意：这里简化处理，假设只有当前用户的活跃会话才会在Redis中
        # 实际可以通过在Redis中存储user_id来更严格地验证
        
        # 检查是否是当前用户的会话（通过检查当前会话ID）
        current_conversation_id = await conversation_service.get_current_conversation(current_user.id)
        if conversation_id != current_conversation_id:
            # 如果不是当前会话，检查是否在已归档记录中属于当前用户
            from app.models.chat import ConversationArchive
            from sqlalchemy import select
            
            result = await db.execute(
                select(ConversationArchive).where(
                    ConversationArchive.conversation_id == conversation_id,
                    ConversationArchive.user_id == current_user.id
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权归档此会话"
                )
        
        # 执行归档
        success = await conversation_service.archive_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="归档失败"
            )
        
        # 获取归档时间
        from app.models.chat import ConversationArchive
        from sqlalchemy import select
        
        result = await db.execute(
            select(ConversationArchive).where(
                ConversationArchive.conversation_id == conversation_id
            )
        )
        archive = result.scalar_one_or_none()
        
        return ArchiveConversationResponse(
            code=200,
            message="会话归档成功",
            data=ArchiveConversationData(
                conversation_id=conversation_id,
                archived_at=archive.archived_at.isoformat() if archive else datetime.now().isoformat()
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"归档会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"归档失败: {str(e)}"
        )

