"""
测试 Kafka 文档处理服务
测试从发送消息到Kafka，到文档处理、向量化、索引的完整流程
"""

import asyncio
import sys
import hashlib
from pathlib import Path
from typing import Tuple

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.kafka_client import kafka_client
from app.clients.db_client import db_client
from app.clients.minio_client import minio_client
from app.clients.elasticsearch_client import es_client
from app.clients.redis_client import redis_client
from app.services.document_processor_service import document_processor_service
from app.services.search_service import search_service
from app.models.file import FileUpload, DocumentVector
from app.models.user import User
from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def print_info(msg: str):
    """打印信息"""
    print(f"ℹ️  {msg}")


def print_success(msg: str):
    """打印成功信息"""
    print(f"✅ {msg}")


def print_error(msg: str):
    """打印错误信息"""
    print(f"❌ {msg}")


def print_warning(msg: str):
    """打印警告信息"""
    print(f"⚠️  {msg}")


def calculate_file_md5(data: bytes) -> str:
    """计算文件MD5"""
    return hashlib.md5(data).hexdigest()


async def create_test_file_content() -> Tuple[bytes, str, str]:
    """
    创建测试文件内容
    
    Returns:
        (file_data, file_md5, file_name)
    """
    # 创建一个简单的Markdown测试文件
    test_content = """# 测试文档

这是一个用于测试Kafka文档处理服务的测试文档。

## 第一章：介绍

Kafka是一个分布式流处理平台，可以用于构建实时数据管道和流式应用。

## 第二章：特性

Kafka具有以下特性：
- 高吞吐量
- 可扩展性
- 持久性
- 容错性

## 第三章：使用场景

Kafka可以用于：
1. 日志聚合
2. 流式处理
3. 事件溯源
4. 消息队列

## 第四章：总结

通过Kafka，我们可以实现异步处理，提高系统的整体性能和可扩展性。
"""
    
    file_data = test_content.encode('utf-8')
    file_md5 = calculate_file_md5(file_data)
    file_name = "test_kafka_document.md"
    
    return file_data, file_md5, file_name


async def setup_test_data(db: AsyncSession, user: User, file_data: bytes, file_md5: str, file_name: str) -> Tuple[str, bool]:
    """
    设置测试数据：上传文件到MinIO，创建数据库记录
    
    Returns:
        (storage_path, success)
    """
    try:
        # 1. 检查文件记录是否已存在，如果存在则先删除
        print_info("检查是否已存在测试数据...")
        existing_result = await db.execute(
            select(FileUpload).where(
                FileUpload.file_md5 == file_md5,
                FileUpload.user_id == user.id
            )
        )
        existing_record = existing_result.scalar_one_or_none()
        
        if existing_record:
            print_warning(f"发现已存在的文件记录，将清理旧数据: file_md5={file_md5}")
            
            # 删除相关的向量记录
            vectors_result = await db.execute(
                select(DocumentVector).where(DocumentVector.file_md5 == file_md5)
            )
            vectors = vectors_result.scalars().all()
            for vec in vectors:
                await db.delete(vec)
            
            # 删除文件记录（级联删除会自动处理）
            await db.delete(existing_record)
            await db.commit()
            print_info("旧数据已清理")
        
        # 2. 上传文件到MinIO（如果已存在则覆盖）
        storage_path = minio_client.build_document_path(user.id, file_name)
        print_info(f"上传文件到MinIO: {storage_path}")
        
        success = minio_client.upload_bytes(
            bucket_name=settings.MINIO_DEFAULT_BUCKET,
            object_name=storage_path,
            data=file_data
        )
        
        if not success:
            print_error("文件上传到MinIO失败")
            return None, False
        
        print_success(f"文件已上传到MinIO: {storage_path}")
        
        # 3. 创建数据库记录
        print_info("创建文件数据库记录...")
        file_record = FileUpload(
            file_md5=file_md5,
            file_name=file_name,
            total_size=len(file_data),
            status=1,  # 已完成（已合并）
            user_id=user.id,
            org_tag=user.primary_org,
            is_public=False
        )
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        
        print_success(f"文件记录已创建: file_md5={file_md5}")
        return storage_path, True
        
    except Exception as e:
        print_error(f"设置测试数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None, False


async def test_send_kafka_message(file_md5: str, file_name: str, storage_path: str, user_id: int) -> bool:
    """
    测试发送Kafka消息
    
    Returns:
        是否发送成功
    """
    try:
        print_info("发送文档处理消息到Kafka...")
        
        kafka_message = {
            "file_md5": file_md5,
            "file_name": file_name,
            "storage_path": storage_path,
            "user_id": user_id,
            "org_tag": None,
            "is_public": False
        }
        
        print_info(f"消息内容: {kafka_message}")
        
        success = await kafka_client.send_message(
            topic="document_parse",
            value=kafka_message,
            key=file_md5
        )
        
        if success:
            print_success("消息已发送到Kafka")
            # 刷新生产者缓冲区，确保消息已发送
            await kafka_client.flush()
            print_info("生产者缓冲区已刷新")
        else:
            print_error("消息发送失败")
        
        return success
        
    except Exception as e:
        print_error(f"发送Kafka消息失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_document_processor_direct(file_md5: str, file_name: str, storage_path: str, user_id: int) -> bool:
    """
    直接测试文档处理服务（不使用Kafka消费者）
    
    Returns:
        是否处理成功
    """
    try:
        print_info("直接测试文档处理服务...")
        
        success = await document_processor_service.process_document(
            file_md5=file_md5,
            file_name=file_name,
            storage_path=storage_path,
            user_id=user_id,
            org_tag=None,
            is_public=False
        )
        
        if success:
            print_success("文档处理成功")
        else:
            print_error("文档处理失败")
        
        return success
        
    except Exception as e:
        print_error(f"文档处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_processing_result(file_md5: str) -> bool:
    """
    验证处理结果：检查数据库和Elasticsearch
    
    Returns:
        是否验证通过
    """
    try:
        print_info("验证处理结果...")
        
        # 使用新的数据库会话进行查询（因为文档处理使用了不同的会话）
        result = False
        async for db in db_client.get_session():
            try:
                # 1. 检查数据库中的向量记录
                print_info("检查数据库中的向量记录...")
                vectors_result = await db.execute(
                    select(DocumentVector).where(DocumentVector.file_md5 == file_md5)
                )
                vectors = vectors_result.scalars().all()
                
                if not vectors:
                    print_error("数据库中没有找到向量记录")
                    result = False
                    break
                
                print_success(f"数据库中找到 {len(vectors)} 个向量记录")
                for i, vec in enumerate(vectors[:3], 1):  # 只显示前3个
                    print_info(f"  向量 {i}: chunk_id={vec.chunk_id}, text_length={len(vec.text_content) if vec.text_content else 0}")
                
                # 2. 检查Elasticsearch索引
                print_info("检查Elasticsearch索引...")
                await es_client.refresh_index(search_service.INDEX_NAME)
                
                # 使用file_md5查询
                query = {
                    "bool": {
                        "must": [
                            {"term": {"file_md5": file_md5}}
                        ]
                    }
                }
                
                search_result = await es_client.search(
                    index=search_service.INDEX_NAME,
                    query=query,
                    size=10
                )
                
                if not search_result or 'hits' not in search_result:
                    print_error("Elasticsearch查询失败或没有结果")
                    result = False
                    break
                
                hits = search_result.get('hits', {}).get('hits', [])
                if not hits:
                    print_error("Elasticsearch中没有找到索引文档")
                    result = False
                    break
                
                print_success(f"Elasticsearch中找到 {len(hits)} 个索引文档")
                for i, hit in enumerate(hits[:3], 1):  # 只显示前3个
                    doc = hit.get('_source', {})
                    print_info(f"  文档 {i}: chunk_id={doc.get('chunk_id')}, file_name={doc.get('file_name')}")
                
                # 所有验证都通过
                result = True
                break
                
            except Exception as e:
                print_error(f"验证过程中出错: {e}")
                import traceback
                traceback.print_exc()
                result = False
                break
        
        return result
        
    except Exception as e:
        print_error(f"验证处理结果失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_test_data(db: AsyncSession, file_md5: str, storage_path: str, user_id: int):
    """清理测试数据"""
    try:
        print_info("清理测试数据...")
        
        # 1. 删除数据库中的向量记录
        vectors_result = await db.execute(
            select(DocumentVector).where(DocumentVector.file_md5 == file_md5)
        )
        vectors = vectors_result.scalars().all()
        for vec in vectors:
            await db.delete(vec)
        if vectors:
            print_info(f"数据库向量记录已删除 ({len(vectors)} 个)")
        
        # 2. 删除文件记录（级联删除会自动处理相关的向量记录）
        file_result = await db.execute(
            select(FileUpload).where(
                FileUpload.file_md5 == file_md5,
                FileUpload.user_id == user_id
            )
        )
        file_record = file_result.scalar_one_or_none()
        
        if file_record:
            await db.delete(file_record)
            await db.commit()
            print_info("数据库文件记录已删除")
        
        # 3. 删除MinIO文件
        if minio_client.file_exists(settings.MINIO_DEFAULT_BUCKET, storage_path):
            minio_client.delete_file(
                bucket_name=settings.MINIO_DEFAULT_BUCKET,
                object_name=storage_path
            )
            print_info("MinIO文件已删除")
        
        # 4. 删除Elasticsearch文档
        query = {
            "bool": {
                "must": [
                    {"term": {"file_md5": file_md5}}
                ]
            }
        }
        
        search_result = await es_client.search(
            index=search_service.INDEX_NAME,
            query=query,
            size=100
        )
        
        if search_result and 'hits' in search_result:
            hits = search_result['hits'].get('hits', [])
            for hit in hits:
                doc_id = hit['_id']
                await es_client.delete_document(
                    index=search_service.INDEX_NAME,
                    doc_id=doc_id
                )
            if hits:
                print_info(f"Elasticsearch文档已删除 ({len(hits)} 个)")
        
        print_success("测试数据清理完成")
        
    except Exception as e:
        print_warning(f"清理测试数据时出错: {e}")


async def get_or_create_test_user(db: AsyncSession) -> User:
    """获取或创建测试用户"""
    try:
        # 查找测试用户
        result = await db.execute(
            select(User).where(User.username == "test_user")
        )
        user = result.scalar_one_or_none()
        
        if user:
            print_info(f"找到测试用户: {user.username} (ID: {user.id})")
            return user
        
        # 创建测试用户（如果不存在）
        print_warning("测试用户不存在，请先运行 create_user.py 创建测试用户")
        raise ValueError("测试用户不存在")
        
    except Exception as e:
        print_error(f"获取测试用户失败: {e}")
        raise


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Kafka 文档处理服务测试")
    print("=" * 60)
    print("\n注意：")
    print("1. 请确保已启动所有服务（MySQL, Redis, MinIO, Elasticsearch, Kafka）")
    print("2. 请确保已创建测试用户 'test_user'")
    print("3. 请确保 MinIO 存储桶已创建")
    print("4. 请确保 Elasticsearch 索引已创建")
    print("\n" + "=" * 60)
    
    try:
        # 1. 连接所有服务
        print_info("\n步骤1: 连接所有服务...")
        
        db_client.connect()
        print_success("MySQL 连接成功")
        
        await redis_client.connect()
        print_success("Redis 连接成功")
        
        minio_client.connect()
        # 确保存储桶存在
        minio_client.ensure_bucket(settings.MINIO_DEFAULT_BUCKET)
        print_success("MinIO 连接成功")
        
        await es_client.connect()
        print_success("Elasticsearch 连接成功")
        
        await kafka_client.connect()
        print_success("Kafka 连接成功")
        
        # 检查Kafka健康状态
        kafka_health = await kafka_client.health_check()
        if not kafka_health:
            print_error("Kafka 健康检查失败")
            return False
        
        print_success("所有服务连接成功")
        
        # 2. 创建测试文件
        print_info("\n步骤2: 创建测试文件...")
        file_data, file_md5, file_name = await create_test_file_content()
        print_success(f"测试文件创建成功: {file_name} (MD5: {file_md5}, 大小: {len(file_data)} 字节)")
        
        # 3. 获取数据库会话并设置测试数据
        print_info("\n步骤3: 设置测试数据...")
        test_result = False
        async for db in db_client.get_session():
            try:
                # 获取测试用户
                user = await get_or_create_test_user(db)
                
                # 设置测试数据（上传文件到MinIO，创建数据库记录）
                storage_path, setup_success = await setup_test_data(db, user, file_data, file_md5, file_name)
                
                if not setup_success:
                    print_error("设置测试数据失败")
                    test_result = False
                    break
                
                # 4. 测试选项：直接处理或通过Kafka
                print_info("\n步骤4: 选择测试方式...")
                print("请选择测试方式：")
                print("1. 直接测试文档处理服务（不使用Kafka）")
                print("2. 通过Kafka发送消息测试（需要消费者运行）")
                
                # 默认使用Kafka测试（测试完整的异步流程）
                # 如果应用没有运行消费者，可以改为 "1" 使用直接测试
                test_mode = "2"  # 改为 "1" 可以跳过Kafka，直接测试文档处理服务
                
                if test_mode == "1":
                    # 直接测试文档处理服务
                    print_info("使用直接测试模式...")
                    process_success = await test_document_processor_direct(
                        file_md5=file_md5,
                        file_name=file_name,
                        storage_path=storage_path,
                        user_id=user.id
                    )
                else:
                    # 通过Kafka测试（在测试中启动消费者）
                    print_info("使用Kafka测试模式...")
                    print_info("将在测试中启动Kafka消费者...")
                    
                    # 启动Kafka消费者
                    kafka_consumer = None
                    kafka_consumer_task = None
                    
                    try:
                        print_info("创建Kafka消费者...")
                        kafka_consumer = await kafka_client.create_consumer(
                            topics=["document_parse"],
                            group_id="test_document_processor_group",  # 使用测试专用的group_id
                            auto_offset_reset='latest',  # 从最新消息开始消费
                            enable_auto_commit=True
                        )
                        
                        # 在后台启动消费者任务
                        async def consume_loop():
                            """消费者循环"""
                            try:
                                print_info("Kafka消费者已启动，监听 document_parse 主题")
                                await kafka_client.consume_messages(
                                    consumer=kafka_consumer,
                                    callback=document_processor_service.handle_kafka_message
                                )
                            except asyncio.CancelledError:
                                print_info("Kafka消费者任务已取消")
                            except Exception as e:
                                print_error(f"Kafka消费者异常: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        kafka_consumer_task = asyncio.create_task(consume_loop())
                        print_success("Kafka消费者已启动")
                        
                        # 等待消费者完全启动
                        await asyncio.sleep(1)
                        print_info("消费者已就绪，准备发送消息...")
                        
                        # 发送消息
                        msg_success = await test_send_kafka_message(
                            file_md5=file_md5,
                            file_name=file_name,
                            storage_path=storage_path,
                            user_id=user.id
                        )
                        
                        if msg_success:
                            print_info("消息已发送到Kafka，等待消费者处理...")
                            
                            # 等待一段时间让消费者处理消息（处理可能需要时间）
                            # 文档处理包括：下载、解析、向量化、索引，可能需要较长时间
                            print_info("等待20秒，让消费者处理消息（包括向量化）...")
                            for i in range(20):
                                await asyncio.sleep(1)
                                if (i + 1) % 5 == 0:  # 每5秒打印一次
                                    print_info(f"  等待中... {i+1}/20 秒")
                            
                            process_success = msg_success
                        else:
                            print_error("消息发送失败")
                            process_success = False
                        
                    except Exception as e:
                        print_error(f"启动Kafka消费者失败: {e}")
                        import traceback
                        traceback.print_exc()
                        process_success = False
                    
                    finally:
                        # 停止消费者
                        if kafka_consumer_task and not kafka_consumer_task.done():
                            print_info("正在停止Kafka消费者...")
                            kafka_consumer_task.cancel()
                            try:
                                await asyncio.wait_for(kafka_consumer_task, timeout=5.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                pass
                        
                        if kafka_consumer:
                            try:
                                await kafka_consumer.stop()
                                print_info("Kafka消费者已停止")
                            except Exception as e:
                                print_warning(f"停止Kafka消费者时出错: {e}")
                
                if not process_success:
                    if test_mode == "2":
                        print_error("Kafka消息发送成功，但文档未被处理")
                        print_error("可能的原因：")
                        print_error("  1. 应用未运行 - 消费者没有启动")
                        print_error("  2. 消费者启动失败 - 检查应用日志")
                        print_error("  3. 消费者在消息发送后启动 - 使用了'latest'偏移量")
                        print_error("建议：")
                        print_error("  - 确保应用正在运行: uvicorn app.main:app")
                        print_error("  - 检查应用日志中是否有'Kafka 消费者已启动'")
                        print_error("  - 或者使用模式1（直接测试）跳过Kafka")
                    else:
                        print_error("文档处理失败")
                    await cleanup_test_data(db, file_md5, storage_path, user.id)
                    test_result = False
                    break
                
                # 5. 验证处理结果（等待一小段时间确保数据已提交）
                print_info("\n步骤5: 验证处理结果...")
                if test_mode == "2":
                    # Kafka模式下，已经在上面等待了15秒
                    pass
                else:
                    await asyncio.sleep(0.5)  # 直接模式下等待一小段时间确保事务已提交
                
                verify_success = await verify_processing_result(file_md5)
                
                if verify_success:
                    print_success("验证通过！")
                else:
                    print_error("验证失败")
                    if test_mode == "2":
                        print_error("Kafka模式下验证失败的可能原因：")
                        print_error("  1. 应用未运行，消费者没有处理消息")
                        print_error("  2. 处理时间超过15秒（向量化需要时间）")
                        print_error("  3. 消费者处理消息时出错（检查应用日志）")
                        print_error("建议：检查应用日志查看详细错误信息")
                
                # 6. 清理测试数据（可选）
                print_info("\n步骤6: 清理测试数据...")
                cleanup_choice = "n"  # 可以改为输入
                if cleanup_choice.lower() == 'y':
                    await cleanup_test_data(db, file_md5, storage_path, user.id)
                else:
                    print_info("保留测试数据（可以手动清理）")
                
                print("\n" + "=" * 60)
                if verify_success:
                    print_success("Kafka 文档处理服务测试完成！")
                else:
                    print_warning("测试完成，但验证失败")
                print("=" * 60)
                
                test_result = verify_success
                break
                
            except Exception as e:
                print_error(f"测试过程中出错: {e}")
                import traceback
                traceback.print_exc()
                test_result = False
                break
        
        return test_result
        
    except Exception as e:
        print_error(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 关闭连接
        try:
            await kafka_client.close()
            await es_client.close()
            await redis_client.close()
            minio_client.close()
            await db_client.close()
        except:
            pass


if __name__ == "__main__":
    print("\n启动 Kafka 文档处理服务测试...\n")
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)

