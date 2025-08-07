#!/usr/bin/env python3
"""
同义词查询安全封装器
确保即使synonyms库初始化失败，web界面也能正常启动
"""

def safe_process_synonym_search(word: str, k: int = 10, final_filter: str = "") -> str:
    """安全的同义词查询处理函数"""
    try:
        # 最优先：尝试使用Qwen同义词服务（最新最准确）
        from qwen_synonym_searcher import process_synonym_search as qwen_process_synonym_search
        from qwen_synonym_searcher import QwenSynonymSearcher
        
        # 检测Qwen服务是否可用
        qwen_searcher = QwenSynonymSearcher()
        if qwen_searcher.qwen_available:
            print("🚀 使用Qwen3-Embedding同义词服务（最新模型）")
            return qwen_process_synonym_search(word, k, final_filter)
        
        # 次优先：尝试使用预计算BERT embeddings（快速备用）
        from fast_bert_synonym_searcher import process_synonym_search as fast_bert_process_synonym_search
        from fast_bert_synonym_searcher import FastBertSynonymSearcher
        
        # 检测预计算embeddings是否可用
        fast_searcher = FastBertSynonymSearcher()
        if fast_searcher.initialized:
            print("⚡ Qwen不可用，使用高速BERT同义词服务（预计算embeddings）")
            return fast_bert_process_synonym_search(word, k)
        
        # 第三选择：尝试使用实时BERT服务
        from bert_synonym_searcher import process_synonym_search as bert_process_synonym_search
        from bert_synonym_searcher import BertSynonymSearcher
        
        bert_searcher = BertSynonymSearcher()
        if bert_searcher.bert_available:
            print("🧠 使用实时BERT同义词服务")
            return bert_process_synonym_search(word, k)
        
        # 备用：使用synonyms库
        print("⚠️ 所有AI模型服务不可用，尝试使用synonyms库")
        from synonym_searcher_fallback import process_synonym_search
        # 注意：传统synonyms库不支持韵母筛选，忽略final_filter参数
        return process_synonym_search(word, k)
            
    except ImportError as e:
        return f"""❌ 同义词模块未找到

🔍 查询词汇: {word}
❌ 导入错误: {str(e)}

🔧 请检查:
1. 确保相关Python文件存在
2. 安装必要的依赖包
3. 重启应用程序

💡 支持的方式（优先级顺序）:
• Qwen模式: 基于Qwen3-Embedding-0.6B最新模型（推荐）
• 高速BERT模式: 预计算embeddings
• 实时BERT模式: 在线BERT服务器
• 传统模式: synonyms词向量库"""
    except Exception as e:
        # 如果出现任何错误，返回友好的错误信息
        return f"""⏳ 同义词功能检测中...

🔍 查询词汇: {word}
⚠️ 当前状态: {str(e)}

🔧 建议尝试:
1. Qwen模式: 启动Docker容器
   命令: docker run --gpus all -p 8080:80 ghcr.io/huggingface/text-embeddings-inference:1.8 --model-id Qwen/Qwen3-Embedding-0.6B
2. 高速模式: 运行 python compute_bert_embeddings.py 预计算embeddings
3. 实时模式: 确保BERT服务器已启动
   命令: bert-serving-start -model_dir /path/to/bert_model
4. 传统模式: 确保synonyms库已正确安装
   命令: pip install synonyms -i https://mirrors.aliyun.com/pypi/simple
5. 检查网络连接和模型下载状态
6. 刷新页面重新尝试

💡 提示: 
• Qwen模式: 基于最新Qwen3-Embedding模型，1024维向量，语义理解最准确
• 高速模式: 预计算embeddings，毫秒级响应
• 实时模式: 实时计算，准确度高但响应较慢
• 传统模式: 快速词汇匹配，基础功能保证"""

def safe_process_similarity_comparison(word1: str, word2: str) -> str:
    """安全的相似度比较处理函数"""
    return process_similarity_comparison_v3(word1, word2)

def process_similarity_comparison(word1: str, word2: str) -> str:
    """处理相似度比较 - 兼容性函数，现在使用V3版本"""
    return process_similarity_comparison_v3(word1, word2)

def safe_process_similarity_comparison_v3(word1: str, word2: str) -> str:
    """安全的相似度比较处理函数 - V3版本的别名"""
    return process_similarity_comparison_v3(word1, word2)

def process_similarity_comparison_v3(word1: str, word2: str) -> str:
    """处理相似度比较 - V3版本"""
    try:
        from qwen_synonym_searcher_v3 import QwenSynonymSearcherV3
        searcher = QwenSynonymSearcherV3()
        
        if not searcher.qwen_available:
            return "❌ Qwen服务不可用，无法进行相似度比较"
        
        # 编码两个词汇
        embeddings = searcher.qwen_client.encode([word1, word2])
        if embeddings is None or len(embeddings) != 2:
            return "❌ 词汇编码失败"
        
        # 计算余弦相似度
        import numpy as np
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        percentage = similarity * 100
        
        # 相似度等级
        if percentage >= 90:
            level = "极高相似"
        elif percentage >= 80:
            level = "高度相似"
        elif percentage >= 70:
            level = "中等相似"
        elif percentage >= 60:
            level = "较低相似"
        else:
            level = "低相似"
        
        result = f"🔍 相似度分析\n\n"
        result += f"词汇1: {word1}\n"
        result += f"词汇2: {word2}\n\n"
        result += f"📊 相似度: {percentage:.2f}% ({level})\n"
        result += f"📚 数据来源: Qwen3-Embedding-0.6B"
        
        return result
        
    except Exception as e:
        return f"❌ 相似度比较失败: {str(e)}"
            
    except ImportError as e:
        return f"""❌ 相似度比较模块未找到

🔍 比较词汇: '{word1}' vs '{word2}'
❌ 导入错误: {str(e)}

🔧 请检查:
1. 确保相关Python文件存在
2. 安装必要的依赖包
3. 重启应用程序"""
    except Exception as e:
        # 如果出现任何错误，返回友好的错误信息
        return f"""⏳ 相似度计算功能检测中...

🔍 比较词汇: '{word1}' vs '{word2}'
⚠️ 当前状态: {str(e)}

🔧 建议尝试:
1. Qwen模式: 启动Docker容器
   命令: docker run --gpus all -p 8080:80 ghcr.io/huggingface/text-embeddings-inference:1.8 --model-id Qwen/Qwen3-Embedding-0.6B
2. 高速模式: 运行 python compute_bert_embeddings.py 预计算embeddings
3. 实时模式: 确保BERT服务器已启动
   命令: bert-serving-start -model_dir /path/to/bert_model
4. 传统模式: 等待synonyms库初始化完成
5. 检查网络连接状态
6. 刷新页面重新尝试

💡 提示: 
• Qwen模式: 基于Qwen3-Embedding-0.6B，1024维向量，语义理解最准确
• 高速BERT: 基于预计算embeddings，毫秒级响应
• 实时BERT: 基于深度学习的上下文语义理解
• 传统模式: 基于词向量的传统相似度计算
• 系统会自动选择最佳可用方式

📚 相似度等级说明:
• 80%以上: 极高相似度（近义词）
• 60-80%: 高相似度（相关词汇）
• 40-60%: 中等相似度（主题相关）
• 20-40%: 较低相似度（有一定关联）
• 20%以下: 很低相似度（基本无关）"""

def process_qwen_synonym_query(word: str, k: int, char1_final: str, char2_final: str, char3_final: str, char4_final: str) -> str:
    """处理Qwen同义词查询 - 使用V3优化版本"""
    try:
        from qwen_synonym_searcher_v2 import QwenSynonymSearcher
        
        searcher = QwenSynonymSearcher()
        if not searcher.qwen_available:
            return "❌ Qwen embedding服务不可用，请启动服务后重试"
        
        # 构建韵母筛选条件
        character_finals = [char1_final, char2_final, char3_final, char4_final]
        # 移除末尾的空字符串
        while character_finals and not character_finals[-1]:
            character_finals.pop()
        
        synonyms, similarities, status = searcher.get_synonyms(word, k, character_finals)
        
        if not synonyms:
            return status
        
        # 构建结果展示
        result_lines = [f"🔍 查询词汇: {word}"]
        result_lines.append(f"📊 数据来源: Qwen3-Embedding-0.6B (1024维向量)")
        result_lines.append(f"⚡ 优化算法: 先筛选后计算，速度大幅提升")
        
        # 韵母筛选信息
        if any(f for f in [char1_final, char2_final, char3_final, char4_final]):
            finals_info = []
            finals_list = [char1_final, char2_final, char3_final, char4_final]
            for i, final in enumerate(finals_list[:len(word)]):
                if final:
                    finals_info.append(f"第{i+1}字='{final}'")
            if finals_info:
                result_lines.append(f"🎵 韵母筛选: {', '.join(finals_info)}")
        
        result_lines.append(f"📝 找到 {len(synonyms)} 个近义词:")
        result_lines.append("")
        
        # 近义词列表
        for i, (synonym, similarity) in enumerate(zip(synonyms, similarities), 1):
            percentage = similarity * 100 if isinstance(similarity, (int, float)) else 0
            result_lines.append(f"{i:2d}. {synonym} ({percentage:.1f}%)")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"❌ Qwen查询失败: {str(e)}\n\n💡 请确保Qwen服务正在运行"

def check_synonym_status() -> str:
    """检查同义词功能状态"""
    try:
        # 检查Qwen服务状态（最优先）
        from qwen_synonym_searcher import QwenSynonymSearcher
        qwen_searcher = QwenSynonymSearcher()
        
        if qwen_searcher.qwen_available:
            return "✅ Qwen3-Embedding-0.6B服务已就绪（最新模型，1024维向量）"
        
        # 检查高速BERT服务状态（预计算embeddings）
        from fast_bert_synonym_searcher import FastBertSynonymSearcher
        fast_searcher = FastBertSynonymSearcher()
        
        if fast_searcher.initialized:
            stats = fast_searcher.get_embedding_stats()
            return f"✅ 高速BERT服务已就绪（{stats.get('total_words', 'N/A')}个词汇预计算完成）- Qwen不可用时的备用方案"
        
        # 检查实时BERT服务状态
        from bert_synonym_searcher import BertSynonymSearcher
        bert_searcher = BertSynonymSearcher()
        
        if bert_searcher.bert_available:
            return "✅ 实时BERT服务已连接，功能可用 - AI模型未完全就绪时的备用方案"
        
        # 检查synonyms库状态
        from synonym_searcher_fallback import SynonymSearcherFallback
        synonym_searcher = SynonymSearcherFallback()
        
        if synonym_searcher.initialized:
            return "✅ synonyms库已初始化，基础功能可用 - 所有AI服务不可用时的最后备用方案"
        else:
            return "⚠️ 正在初始化中：Qwen/BERT服务未连接，synonyms库加载中"
            
    except Exception as e:
        return f"❌ 同义词服务检测失败: {str(e)}"

if __name__ == "__main__":
    print("🧪 测试安全封装器...")
    print(check_synonym_status())
    print("\n测试同义词查询:")
    print(safe_process_synonym_search("高兴", 5))
    print("\n测试相似度比较:")
    print(safe_process_similarity_comparison("高兴", "快乐"))
