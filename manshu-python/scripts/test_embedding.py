"""
测试向量化服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.embedding_service import embedding_service
from app.core.config import settings
from app.utils.logger import setup_logging, get_logger

# 初始化日志
setup_logging()
logger = get_logger(__name__)


async def test_single_embedding():
    """测试单个文本向量化"""
    print("\n" + "=" * 60)
    print("测试 1: 单个文本向量化")
    print("=" * 60)
    
    test_text = "测试文本，人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。"
    print(f"测试文本: {test_text}")
    print(f"使用的模型: {settings.OPENAI_EMBEDDING_MODEL}")
    print(f"向量维度: {settings.OPENAI_EMBEDDING_DIMENSIONS}")
    
    try:
        vector = await embedding_service.embed_text(test_text)
        
        if vector:
            print(f"✅ 向量化成功！")
            print(f"   向量维度: {len(vector)}")
            print(f"   向量前5个值: {vector[:5]}")
            print(f"   向量后5个值: {vector[-5:]}")
            print(f"   向量范围: [{min(vector):.6f}, {max(vector):.6f}]")
            return True
        else:
            print(f"❌ 向量化失败")
            return False
            
    except Exception as e:
        print(f"❌ 向量化异常: {e}")
        logger.error(f"向量化异常: {e}", exc_info=True)
        return False


async def test_batch_embedding():
    """测试批量文本向量化"""
    print("\n" + "=" * 60)
    print("测试 2: 批量文本向量化")
    print("=" * 60)
    
    test_texts = [
        "测试文本1，用于验证批量向量化功能。",
        "测试文本2，包含不同的内容。",
        "测试文本3，比较简短。",
        "",  # 空文本测试
        "测试文本4，包含一些特殊字符：！@#￥%……&*（）",
        "测试文本5，是最后一个。"
    ]
    
    print(f"测试文本数量: {len(test_texts)}")
    print(f"文本列表:")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i}. {text[:30] + '...' if len(text) > 30 else text}")
    
    try:
        vectors = await embedding_service.embed_batch(test_texts, batch_size=3)
        
        success_count = sum(1 for v in vectors if v is not None)
        print(f"\n✅ 批量向量化完成！")
        print(f"   成功: {success_count}/{len(test_texts)}")
        print(f"   失败: {len(test_texts) - success_count}/{len(test_texts)}")
        
        # 显示每个向量的信息
        for i, vector in enumerate(vectors):
            if vector:
                print(f"   文本 {i+1}: 维度={len(vector)}, 范围=[{min(vector):.6f}, {max(vector):.6f}]")
            else:
                print(f"   文本 {i+1}: ❌ 向量化失败")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 批量向量化异常: {e}")
        logger.error(f"批量向量化异常: {e}", exc_info=True)
        return False


async def test_query_embedding():
    """测试查询文本向量化"""
    print("\n" + "=" * 60)
    print("测试 3: 查询文本向量化")
    print("=" * 60)
    
    query_texts = [
        "什么是人工智能？",
        "如何学习Python编程？",
        "RAG系统的工作原理",
    ]
    
    for query in query_texts:
        print(f"\n查询文本: {query}")
        try:
            vector = await embedding_service.embed_query(query)
            if vector:
                print(f"  ✅ 向量化成功，维度: {len(vector)}")
                print(f"     向量示例: {vector[:3]}...")
            else:
                print(f"  ❌ 向量化失败")
        except Exception as e:
            print(f"  ❌ 异常: {e}")


async def test_vector_similarity():
    """测试向量相似度计算"""
    print("\n" + "=" * 60)
    print("测试 4: 向量相似度计算")
    print("=" * 60)
    
    text1 = "人工智能是计算机科学的一个分支"
    text2 = "AI是计算机科学的重要领域"
    text3 = "今天天气很好，适合出去散步"
    
    try:
        vector1 = await embedding_service.embed_text(text1)
        vector2 = await embedding_service.embed_text(text2)
        vector3 = await embedding_service.embed_text(text3)
        
        if not all([vector1, vector2, vector3]):
            print("❌ 向量化失败，无法计算相似度")
            return False
        
        # 计算余弦相似度
        def cosine_similarity(v1, v2):
            dot_product = sum(a * b for a, b in zip(v1, v2))
            norm1 = sum(a * a for a in v1) ** 0.5
            norm2 = sum(b * b for b in v2) ** 0.5
            return dot_product / (norm1 * norm2)
        
        sim_12 = cosine_similarity(vector1, vector2)
        sim_13 = cosine_similarity(vector1, vector3)
        sim_23 = cosine_similarity(vector2, vector3)
        
        print(f"文本1: {text1}")
        print(f"文本2: {text2}")
        print(f"文本3: {text3}")
        print(f"\n相似度结果:")
        print(f"  文本1 vs 文本2 (相关): {sim_12:.4f}")
        print(f"  文本1 vs 文本3 (不相关): {sim_13:.4f}")
        print(f"  文本2 vs 文本3 (不相关): {sim_23:.4f}")
        
        # 验证：相关文本的相似度应该高于不相关的
        if sim_12 > sim_13 and sim_12 > sim_23:
            print(f"\n✅ 相似度计算正确（相关文本相似度更高）")
            return True
        else:
            print(f"\n⚠️  相似度计算可能有问题")
            return False
            
    except Exception as e:
        print(f"❌ 相似度计算异常: {e}")
        logger.error(f"相似度计算异常: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("向量化服务测试")
    print("=" * 60)
    print(f"OpenAI API Key: {settings.OPENAI_API_KEY[:10] + '...' if settings.OPENAI_API_KEY else '未配置'}")
    print(f"Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
    print(f"Vector Dimensions: {settings.OPENAI_EMBEDDING_DIMENSIONS}")
    
    # 检查配置
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key-here":
        print("\n❌ 错误: 请先在 .env 文件中配置 OPENAI_API_KEY")
        return
    
    results = []
    
    # 运行测试
    results.append(("单个文本向量化", await test_single_embedding()))
    results.append(("批量文本向量化", await test_batch_embedding()))
    await test_query_embedding()
    results.append(("向量相似度计算", await test_vector_similarity()))
    
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
        print("⚠️  部分测试失败，请检查配置和网络连接")


if __name__ == "__main__":
    asyncio.run(main())

