"""
测试 Elasticsearch 检索服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.search_service import search_service
from app.services.embedding_service import embedding_service
from app.clients.elasticsearch_client import es_client
from app.clients.db_client import db_client
from app.core.config import settings
from app.utils.logger import setup_logging, get_logger
from app.models.file import FileUpload, DocumentVector
from app.models.user import User
from sqlalchemy import select

# 初始化日志
setup_logging()
logger = get_logger(__name__)


async def test_index_creation():
    """测试索引创建"""
    print("\n" + "=" * 60)
    print("测试 1: Elasticsearch 索引创建")
    print("=" * 60)
    
    try:
        # 确保索引存在
        success = await search_service.ensure_index_exists()
        
        if success:
            print("✅ 索引创建/验证成功")
            
            # 检查索引是否存在
            exists = await es_client.index_exists(search_service.INDEX_NAME)
            print(f"   索引名称: {search_service.INDEX_NAME}")
            print(f"   索引存在: {exists}")
            
            # 获取索引mapping
            try:
                mapping = await es_client.client.indices.get_mapping(index=search_service.INDEX_NAME)
                print(f"   索引mapping: 已配置")
                
                # 检查向量字段
                properties = mapping[search_service.INDEX_NAME]["mappings"]["properties"]
                if "vector" in properties:
                    vector_config = properties["vector"]
                    print(f"   向量字段配置:")
                    print(f"     - 维度: {vector_config.get('dims', 'N/A')}")
                    print(f"     - 类型: {vector_config.get('type', 'N/A')}")
                    print(f"     - 相似度算法: {vector_config.get('similarity', 'N/A')}")
                
            except Exception as e:
                print(f"   ⚠️  获取mapping失败: {e}")
            
            return True
        else:
            print("❌ 索引创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 索引创建异常: {e}")
        logger.error(f"索引创建异常: {e}", exc_info=True)
        return False


async def test_index_document():
    """测试索引文档（添加测试数据）"""
    print("\n" + "=" * 60)
    print("测试 2: 索引文档到 Elasticsearch")
    print("=" * 60)
    
    try:
        # 确保索引存在
        await search_service.ensure_index_exists()
        
        # 准备测试数据
        # 注意：user_id=1 的文档（属于当前测试用户）
        #       user_id=999 的文档（不属于当前测试用户，用于测试权限过滤）
        test_docs = [
            {
                "file_md5": "test_file_001",
                "chunk_id": 0,
                "text_content": "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
                "vector": None,  # 需要向量化
                "user_id": 1,
                "org_tag": "DEFAULT",
                "is_public": True,
                "file_name": "test_ai_intro.txt",
                "model_version": settings.OPENAI_EMBEDDING_MODEL
            },
            {
                "file_md5": "test_file_001",
                "chunk_id": 1,
                "text_content": "机器学习是人工智能的一个子领域，它使计算机能够在没有明确编程的情况下学习和改进。",
                "vector": None,
                "user_id": 1,
                "org_tag": "DEFAULT",
                "is_public": True,
                "file_name": "test_ai_intro.txt",
                "model_version": settings.OPENAI_EMBEDDING_MODEL
            },
            {
                "file_md5": "test_file_002",
                "chunk_id": 0,
                "text_content": "Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。",
                "vector": None,
                "user_id": 1,
                "org_tag": "DEFAULT",
                "is_public": True,
                "file_name": "test_python.txt",
                "model_version": settings.OPENAI_EMBEDDING_MODEL
            },
            # 添加不属于 user_id=1 的文档（用于测试权限过滤）
            {
                "file_md5": "test_file_other_user",
                "chunk_id": 0,
                "text_content": "这是另一个用户（user_id=999）的私有文档，包含敏感信息，不应该被 user_id=1 检索到。",
                "vector": None,
                "user_id": 999,  # 不同的用户ID
                "org_tag": "PRIVATE_TAG",  # 不同的标签，且不是DEFAULT
                "is_public": False,  # 不是公开的
                "file_name": "test_other_user_private.txt",
                "model_version": settings.OPENAI_EMBEDDING_MODEL
            },
            {
                "file_md5": "test_file_other_user_public",
                "chunk_id": 0,
                "text_content": "这是另一个用户（user_id=999）的公开文档，虽然不属于user_id=1，但是公开的，应该可以被检索到。",
                "vector": None,
                "user_id": 999,  # 不同的用户ID
                "org_tag": "OTHER_TAG",  # 不同的标签
                "is_public": True,  # 但是公开的
                "file_name": "test_other_user_public.txt",
                "model_version": settings.OPENAI_EMBEDDING_MODEL
            }
        ]
        
        print(f"准备索引 {len(test_docs)} 个测试文档...")
        print(f"  - user_id=1 的文档: 3 个")
        print(f"  - user_id=999 的私有文档: 1 个（不应该被 user_id=1 检索到）")
        print(f"  - user_id=999 的公开文档: 1 个（可以被检索到，因为是公开的）")
        
        # 向量化文本
        texts = [doc["text_content"] for doc in test_docs]
        vectors = await embedding_service.embed_batch(texts)
        
        # 更新文档向量
        for i, vector in enumerate(vectors):
            if vector:
                test_docs[i]["vector"] = vector
        
        # 索引文档
        success_count = 0
        for doc in test_docs:
            if doc["vector"]:
                doc_id = f"{doc['file_md5']}_{doc['chunk_id']}"
                result = await es_client.index_document(
                    index=search_service.INDEX_NAME,
                    document=doc,
                    doc_id=doc_id
                )
                if result:
                    success_count += 1
                    print(f"  ✅ 索引文档: {doc_id} ({doc['file_name']})")
                else:
                    print(f"  ❌ 索引失败: {doc_id}")
            else:
                print(f"  ⚠️  跳过（向量化失败）: {doc['file_md5']}_{doc['chunk_id']}")
        
        # 刷新索引
        await es_client.refresh_index(search_service.INDEX_NAME)
        print(f"\n✅ 索引完成: {success_count}/{len(test_docs)}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 索引文档异常: {e}")
        logger.error(f"索引文档异常: {e}", exc_info=True)
        return False


async def test_hybrid_search():
    """测试混合检索（包含权限过滤验证）"""
    print("\n" + "=" * 60)
    print("测试 3: 混合检索（向量 + 全文）+ 权限过滤验证")
    print("=" * 60)
    print("\n说明：")
    print("  - 当前测试用户: user_id=1")
    print("  - 应该检索到: user_id=1 的文档 + 公开文档")
    print("  - 不应该检索到: user_id=999 的私有文档")
    print("-" * 60)
    
    try:
        # 确保索引存在并有数据
        await search_service.ensure_index_exists()
        
        # 测试查询
        test_queries = [
            "什么是人工智能？",
            "Python编程语言",
            "机器学习",
            "敏感信息",  # 这个查询应该匹配到 user_id=999 的私有文档，但该文档不应该被检索到
        ]
        
        all_tests_passed = True
        for query in test_queries:
            print(f"\n查询: {query}")
            print("-" * 60)
            
            # 向量化查询
            query_vector = await embedding_service.embed_query(query)
            if not query_vector:
                print(f"  ❌ 查询向量化失败")
                continue
            
            print(f"  查询向量维度: {len(query_vector)}")
            
            # 构建权限过滤（模拟 user_id=1 的权限）
            # 用户可以访问：1. 自己上传的文档 2. 公开的文档 3. DEFAULT标签的文档
            permission_filters = [
                {"term": {"user_id": 1}},  # 用户自己的文档
                {"term": {"is_public": True}},  # 公开文档
                {"term": {"org_tag": "DEFAULT"}}  # DEFAULT标签的文档
            ]
            
            # 构建混合查询
            es_query = search_service.build_hybrid_query(
                query_vector=query_vector,
                query_text=query,
                permission_filters=permission_filters
            )
            
            # 执行搜索
            result = await es_client.search(
                index=search_service.INDEX_NAME,
                query=es_query["query"],
                size=10  # 增加返回数量，确保能看到所有结果
            )
            
            if result:
                hits = result.get("hits", {}).get("hits", [])
                total = result.get("hits", {}).get("total", {}).get("value", 0)
                
                print(f"  找到 {total} 个结果（显示前 {len(hits)} 个）:")
                
                # 验证权限过滤是否生效
                found_unauthorized = False
                for i, hit in enumerate(hits, 1):
                    source = hit.get("_source", {})
                    score = hit.get("_score", 0.0)
                    user_id = source.get('user_id')
                    is_public = source.get('is_public', False)
                    org_tag = source.get('org_tag', '')
                    file_name = source.get('file_name', 'N/A')
                    
                    # 检查权限：如果不是 user_id=1，且不是公开的，且不是DEFAULT标签，则不应该被检索到
                    is_authorized = (
                        user_id == 1 or 
                        is_public or 
                        org_tag == "DEFAULT"
                    )
                    
                    if not is_authorized:
                        found_unauthorized = True
                        print(f"\n  ⚠️  结果 {i} [权限验证失败]:")
                    else:
                        print(f"\n  ✅ 结果 {i}:")
                    
                    print(f"    文件: {file_name}")
                    print(f"    用户ID: {user_id}")
                    print(f"    是否公开: {is_public}")
                    print(f"    组织标签: {org_tag}")
                    print(f"    分块ID: {source.get('chunk_id', 'N/A')}")
                    print(f"    分数: {score:.4f}")
                    print(f"    内容: {source.get('text_content', '')[:50]}...")
                
                # 统计结果
                user_own_docs = sum(1 for hit in hits if hit.get("_source", {}).get('user_id') == 1)
                public_docs = sum(1 for hit in hits if hit.get("_source", {}).get('is_public', False))
                other_user_private_docs = sum(1 for hit in hits 
                    if hit.get("_source", {}).get('user_id') == 999 
                    and not hit.get("_source", {}).get('is_public', False)
                    and hit.get("_source", {}).get('org_tag') != 'DEFAULT')
                
                print(f"\n  📊 检索结果统计:")
                print(f"     - 用户自己的文档 (user_id=1): {user_own_docs} 个")
                print(f"     - 公开文档: {public_docs} 个")
                print(f"     - 其他用户的私有文档: {other_user_private_docs} 个")
                
                if found_unauthorized:
                    print(f"\n  ❌ 权限过滤失败：检索到了不应该被访问的文档！")
                    print(f"     预期: 不应该检索到 user_id=999 的私有文档")
                    all_tests_passed = False
                else:
                    print(f"\n  ✅ 权限过滤正常：所有检索到的文档都是用户有权限访问的")
            else:
                print(f"  ⚠️  未找到结果")
        
        if not all_tests_passed:
            print(f"\n⚠️  部分查询的权限过滤测试失败")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ 混合检索异常: {e}")
        logger.error(f"混合检索异常: {e}", exc_info=True)
        return False


async def test_permission_filter():
    """测试权限过滤"""
    print("\n" + "=" * 60)
    print("测试 4: 权限过滤")
    print("=" * 60)
    
    try:
        # 构建不同的权限过滤条件
        test_cases = [
            {
                "name": "公开文档",
                "filters": [{"term": {"is_public": True}}]
            },
            {
                "name": "DEFAULT标签",
                "filters": [{"term": {"org_tag": "DEFAULT"}}]
            },
            {
                "name": "用户自己的文档",
                "filters": [{"term": {"user_id": 1}}]
            },
            {
                "name": "组合条件（公开 OR DEFAULT）",
                "filters": [
                    {
                        "bool": {
                            "should": [
                                {"term": {"is_public": True}},
                                {"term": {"org_tag": "DEFAULT"}}
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ]
            }
        ]
        
        for case in test_cases:
            print(f"\n测试: {case['name']}")
            
            # 构建查询
            query = {
                "query": {
                    "bool": {
                        "must": [{"match_all": {}}],
                        "filter": case["filters"]
                    }
                },
                "size": 5
            }
            
            result = await es_client.search(
                index=search_service.INDEX_NAME,
                query=query["query"],
                size=5
            )
            
            if result:
                total = result.get("hits", {}).get("total", {}).get("value", 0)
                print(f"  找到 {total} 个文档")
            else:
                print(f"  ⚠️  查询失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 权限过滤测试异常: {e}")
        logger.error(f"权限过滤测试异常: {e}", exc_info=True)
        return False


async def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)
    
    try:
        test_doc_ids = [
            "test_file_001_0",
            "test_file_001_1",
            "test_file_002_0",
            "test_file_other_user_0",  # 添加其他用户的文档ID
            "test_file_other_user_public_0"  # 添加其他用户的公开文档ID
        ]
        
        deleted_count = 0
        for doc_id in test_doc_ids:
            try:
                success = await es_client.delete_document(
                    index=search_service.INDEX_NAME,
                    doc_id=doc_id
                )
                if success:
                    deleted_count += 1
                    print(f"  ✅ 删除: {doc_id}")
            except Exception as e:
                print(f"  ⚠️  删除失败 {doc_id}: {e}")
        
        await es_client.refresh_index(search_service.INDEX_NAME)
        print(f"\n✅ 清理完成: 删除了 {deleted_count}/{len(test_doc_ids)} 个测试文档")
        
    except Exception as e:
        print(f"⚠️  清理异常: {e}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Elasticsearch 检索服务测试")
    print("=" * 60)
    print(f"Elasticsearch Host: {settings.ES_HOST}")
    print(f"索引名称: {search_service.INDEX_NAME}")
    print(f"向量维度: {search_service.VECTOR_DIMENSIONS}")
    
    # 检查配置
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key-here":
        print("\n❌ 错误: 请先在 .env 文件中配置 OPENAI_API_KEY")
        return
    
    try:
        # 连接数据库和ES
        db_client.connect()
        await es_client.connect()
        
        results = []
        
        # 运行测试
        results.append(("索引创建", await test_index_creation()))
        results.append(("索引文档", await test_index_document()))
        results.append(("混合检索", await test_hybrid_search()))
        results.append(("权限过滤", await test_permission_filter()))
        
        # 清理测试数据
        await cleanup_test_data()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        print(f"\n总计: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！")
        else:
            print("⚠️  部分测试失败，请检查配置和连接")
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        logger.error(f"测试异常: {e}", exc_info=True)
    finally:
        # 关闭连接
        await es_client.close()
        db_client.close()


if __name__ == "__main__":
    asyncio.run(main())

