"""
Kafka 客户端
"""
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
from typing import Optional, List, Callable, Dict, Any
import json
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KafkaClient:
    """Kafka 异步客户端"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
    
    async def connect(self):
        """创建 Kafka 生产者连接"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type='gzip',
                max_batch_size=16384,
                max_request_size=1048576,
            )
            
            await self.producer.start()
            logger.info(f"Kafka 生产者初始化成功: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Kafka 生产者初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭 Kafka 客户端"""
        try:
            # 关闭生产者
            if self.producer:
                await self.producer.stop()
                logger.info("Kafka 生产者已关闭")
            
            # 关闭所有消费者
            for topic, consumer in self.consumers.items():
                await consumer.stop()
                logger.info(f"Kafka 消费者已关闭: {topic}")
            
            self.consumers.clear()
        except Exception as e:
            logger.error(f"关闭 Kafka 连接时出错: {e}")
    
    async def send_message(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[List[tuple]] = None
    ) -> bool:
        """
        发送消息到 Kafka
        
        Args:
            topic: 主题名称
            value: 消息内容（会自动序列化为 JSON）
            key: 消息键（可选）
            partition: 指定分区（可选）
            headers: 消息头（可选）
            
        Returns:
            bool: 是否发送成功
        """
        try:
            if not self.producer:
                logger.error("Kafka 生产者未初始化")
                return False
            
            # 发送消息
            await self.producer.send(
                topic=topic,
                value=value,
                key=key,
                partition=partition,
                headers=headers
            )
            
            logger.info(f"消息发送成功: topic={topic}, key={key}")
            return True
        except KafkaError as e:
            logger.error(f"Kafka 消息发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            return False
    
    async def send_message_sync(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[List[tuple]] = None
    ) -> Optional[Dict]:
        """
        同步发送消息到 Kafka（等待确认）
        
        Args:
            topic: 主题名称
            value: 消息内容
            key: 消息键（可选）
            partition: 指定分区（可选）
            headers: 消息头（可选）
            
        Returns:
            Optional[Dict]: 发送结果元数据，失败返回 None
        """
        try:
            if not self.producer:
                logger.error("Kafka 生产者未初始化")
                return None
            
            # 发送并等待确认
            metadata = await self.producer.send_and_wait(
                topic=topic,
                value=value,
                key=key,
                partition=partition,
                headers=headers
            )
            
            result = {
                "topic": metadata.topic,
                "partition": metadata.partition,
                "offset": metadata.offset,
                "timestamp": metadata.timestamp
            }
            
            logger.info(f"消息同步发送成功: {result}")
            return result
        except KafkaError as e:
            logger.error(f"Kafka 消息发送失败: {e}")
            return None
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            return None
    
    async def send_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]]
    ) -> int:
        """
        批量发送消息
        
        Args:
            topic: 主题名称
            messages: 消息列表，每条消息可包含 value, key, partition, headers
            
        Returns:
            int: 成功发送的消息数量
        """
        success_count = 0
        
        for msg in messages:
            success = await self.send_message(
                topic=topic,
                value=msg.get('value'),
                key=msg.get('key'),
                partition=msg.get('partition'),
                headers=msg.get('headers')
            )
            if success:
                success_count += 1
        
        logger.info(f"批量发送完成: 成功 {success_count}/{len(messages)}")
        return success_count
    
    async def create_consumer(
        self,
        topics: List[str],
        group_id: str,
        auto_offset_reset: str = 'latest',
        enable_auto_commit: bool = True
    ) -> AIOKafkaConsumer:
        """
        创建 Kafka 消费者
        
        Args:
            topics: 要订阅的主题列表
            group_id: 消费者组 ID
            auto_offset_reset: 偏移量重置策略（'earliest' 或 'latest'）
            enable_auto_commit: 是否自动提交偏移量
            
        Returns:
            AIOKafkaConsumer: 消费者实例
        """
        try:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=enable_auto_commit,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
            )
            
            await consumer.start()
            
            # 保存消费者引用
            consumer_key = f"{group_id}_{','.join(topics)}"
            self.consumers[consumer_key] = consumer
            
            logger.info(f"Kafka 消费者创建成功: topics={topics}, group_id={group_id}")
            return consumer
        except Exception as e:
            logger.error(f"创建 Kafka 消费者失败: {e}")
            raise
    
    async def consume_messages(
        self,
        consumer: AIOKafkaConsumer,
        callback: Callable,
        max_messages: Optional[int] = None
    ):
        """
        消费消息
        
        Args:
            consumer: 消费者实例
            callback: 消息处理回调函数
            max_messages: 最大消费消息数（可选，None 表示持续消费）
        """
        try:
            message_count = 0
            
            async for message in consumer:
                try:
                    # 调用回调函数处理消息
                    await callback(message)
                    
                    message_count += 1
                    
                    # 检查是否达到最大消息数
                    if max_messages and message_count >= max_messages:
                        logger.info(f"已达到最大消费消息数: {max_messages}")
                        break
                        
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    continue
        except Exception as e:
            logger.error(f"消费消息时出错: {e}")
            raise
    
    async def get_topic_partitions(self, topic: str) -> Optional[int]:
        """
        获取主题的分区数
        
        Args:
            topic: 主题名称
            
        Returns:
            Optional[int]: 分区数，失败返回 None
        """
        try:
            if not self.producer:
                return None
            
            partitions = await self.producer.partitions_for(topic)
            return len(partitions) if partitions else 0
        except Exception as e:
            logger.error(f"获取主题分区信息失败: {e}")
            return None
    
    async def flush(self):
        """刷新生产者缓冲区（确保所有消息已发送）"""
        try:
            if self.producer:
                await self.producer.flush()
                logger.info("Kafka 生产者缓冲区已刷新")
        except Exception as e:
            logger.error(f"刷新生产者缓冲区失败: {e}")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.producer:
                return False
            
            # 尝试获取集群元数据
            await self.producer.client.fetch_all_metadata()
            return True
        except Exception as e:
            logger.error(f"Kafka 健康检查失败: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取 Kafka 客户端状态"""
        if not self.producer:
            return {"error": "Kafka 生产者未初始化"}
        
        try:
            return {
                "状态": "已连接",
                "Bootstrap 服务器": settings.KAFKA_BOOTSTRAP_SERVERS,
                "生产者状态": "运行中" if self.producer else "未启动",
                "活跃消费者数": len(self.consumers),
                "消费者列表": list(self.consumers.keys())
            }
        except Exception as e:
            return {
                "状态": "连接失败",
                "错误": str(e)
            }


# 全局 Kafka 客户端实例
kafka_client = KafkaClient()

