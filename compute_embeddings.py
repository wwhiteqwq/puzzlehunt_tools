#!/usr/bin/env python3
"""
使用Qwen Embedding计算ci.json词库中所有词汇的embedding并保存
"""

import json
import numpy as np
import os
from typing import Dict, List
import time
from qwen_embedding_client import QwenEmbeddingClient

def load_ci_data(file_path: str) -> List[str]:
    """加载ci.json数据，提取所有词汇"""
    print(f"📖 加载词库: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ 加载完成，共 {len(data)} 个词条")
    
    # 提取所有词汇
    words = []
    seen_words = set()  # 用于去重
    
    for item in data:
        word = item.get('ci', '').strip()
        if word and word not in seen_words:
            words.append(word)
            seen_words.add(word)
    
    print(f"📝 去重后共 {len(words)} 个不重复词汇")
    return words

def connect_qwen_service() -> QwenEmbeddingClient:
    """连接Qwen embedding服务"""
    print("🔍 连接Qwen embedding服务...")
    
    try:
        client = QwenEmbeddingClient()
        
        if client.available:
            # 测试编码功能
            test_vectors = client.encode(["测试"])
            if test_vectors is not None and len(test_vectors) > 0:
                print("✅ Qwen embedding服务连接成功")
                print(f"   向量维度: {test_vectors[0].shape}")
                print(f"   模型信息: {client.get_model_info()}")
                return client
            else:
                raise Exception("Qwen服务响应异常")
        else:
            raise Exception("Qwen服务不可用")
            
    except Exception as e:
        print(f"❌ Qwen embedding服务连接失败: {e}")
        print("💡 请确保:")
        print("   1. Docker容器已启动: docker run --gpus all -p 8080:80 ...")
        print("   2. 服务器地址为: http://localhost:8080")
        print("   3. 模型已完全加载")
        raise

def compute_embeddings_batch(words: List[str], client: QwenEmbeddingClient, batch_size: int = 100) -> Dict[str, np.ndarray]:
    """批量计算词汇的Qwen embeddings"""
    print(f"🧠 开始计算embeddings，批次大小: {batch_size}")
    
    embeddings = {}
    total_words = len(words)
    
    for i in range(0, total_words, batch_size):
        batch_words = words[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_words + batch_size - 1) // batch_size
        
        print(f"⏳ 处理批次 {batch_num}/{total_batches} ({len(batch_words)} 个词汇)")
        
        try:
            start_time = time.time()
            
            # 计算当前批次的embeddings
            vectors = client.encode(batch_words)
            
            if vectors is not None:
                # 保存结果
                for word, vector in zip(batch_words, vectors):
                    embeddings[word] = vector
                
                elapsed_time = time.time() - start_time
                print(f"   ✅ 完成，耗时: {elapsed_time:.2f}秒")
                
                # 显示进度
                progress = (i + len(batch_words)) / total_words * 100
                print(f"   📊 总进度: {progress:.1f}% ({i + len(batch_words)}/{total_words})")
            else:
                print(f"   ❌ 批次 {batch_num} 编码失败")
                print(f"   ⏭️ 跳过该批次，继续处理下一批次")
                continue
            
        except Exception as e:
            print(f"   ❌ 批次 {batch_num} 处理失败: {e}")
            print(f"   ⏭️ 跳过该批次，继续处理下一批次")
            continue
    
    print(f"🎉 embedding计算完成！成功处理 {len(embeddings)} 个词汇")
    return embeddings

def save_embeddings(embeddings: Dict[str, np.ndarray], output_dir: str):
    """保存embeddings到文件"""
    print(f"💾 保存embeddings到: {output_dir}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为numpy格式
    words = list(embeddings.keys())
    vectors = np.array([embeddings[word] for word in words])
    
    np.save(os.path.join(output_dir, 'words.npy'), words)
    np.save(os.path.join(output_dir, 'embeddings.npy'), vectors)
    
    # 保存词汇列表（便于人工查看）
    with open(os.path.join(output_dir, 'words.txt'), 'w', encoding='utf-8') as f:
        for i, word in enumerate(words):
            f.write(f"{i+1:6d}: {word}\n")
    
    # 保存元数据
    metadata = {
        'total_words': len(words),
        'vector_dimension': vectors.shape[1] if len(vectors) > 0 else 0,
        'creation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'source_file': 'ci.json',
        'model': 'Qwen3-Embedding-0.6B',
        'service_url': 'http://localhost:8080'
    }
    
    with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 保存完成:")
    print(f"   📄 words.npy: {len(words)} 个词汇名称")
    print(f"   🧠 embeddings.npy: {vectors.shape} 向量矩阵")
    print(f"   📝 words.txt: 词汇列表（便于查看）")
    print(f"   📊 metadata.json: 元数据信息")

def main():
    """主函数"""
    print("🚀 开始计算ci.json词库的Qwen embeddings")
    print("=" * 60)
    
    # 配置
    ci_file_path = 'chinese/chinese-xinhua/data/ci.json'
    output_dir = 'qwen_embeddings'  # 使用新的目录名
    batch_size = 20  # Qwen服务的最大批次32，我们设置更小以确保稳定
    
    try:
        # 1. 加载词汇数据
        words = load_ci_data(ci_file_path)
        
        # 2. 连接Qwen服务
        client = connect_qwen_service()
        
        # 3. 计算embeddings
        embeddings = compute_embeddings_batch(words, client, batch_size)
        
        # 4. 保存结果
        save_embeddings(embeddings, output_dir)
        
        print("\n🎉 任务完成！")
        print(f"📊 统计信息:")
        print(f"   总词汇数: {len(words)}")
        print(f"   成功处理: {len(embeddings)}")
        print(f"   成功率: {len(embeddings)/len(words)*100:.1f}%")
        
    except Exception as e:
        print(f"\n❌ 任务失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
