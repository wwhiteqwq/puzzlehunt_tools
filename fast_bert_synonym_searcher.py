#!/usr/bin/env python3
"""
基于预计算BERT embeddings的高速同义词搜索器
"""

from typing import List, Tuple, Optional
import re
from bert_embedding_manager import BertEmbeddingManager

class FastBertSynonymSearcher:
    """基于预计算embeddings的快速同义词搜索器"""
    
    def __init__(self):
        """初始化快速同义词搜索器"""
        self.embedding_manager = BertEmbeddingManager()
        self.initialized = False
        
        print("🔍 初始化快速BERT同义词搜索器...")
        
        # 尝试加载预计算的embeddings
        if self.embedding_manager.load_embeddings():
            self.initialized = True
            print("✅ 预计算embeddings加载成功，进入高速模式")
        else:
            print("⚠️ 未找到预计算embeddings，请先运行 compute_bert_embeddings.py")
            print("💡 或者使用实时BERT服务模式")
    
    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return bool(chinese_pattern.search(text))
    
    def get_synonyms(self, word: str, k: int = 10) -> Tuple[List[str], List[float], str]:
        """获取指定词汇的 k 个近义词"""
        if not self.initialized:
            return [], [], "❌ 预计算embeddings未加载，请先运行 compute_bert_embeddings.py"
        
        if not word or not word.strip():
            return [], [], "❌ 请输入有效的词汇"
        
        word = word.strip()
        
        # 验证输入是否为中文
        if not self._is_chinese(word):
            return [], [], f"⚠️ 输入'{word}'不是中文词汇，建议使用中文"
        
        try:
            # 使用预计算的embeddings查找相似词
            similar_words = self.embedding_manager.find_similar_words(word, k)
            
            if not similar_words:
                return [], [], f"❌ 词汇'{word}'在预计算词库中未找到"
            
            # 分离词汇和相似度
            synonym_words = [item[0] for item in similar_words]
            similarity_scores = [round(item[1] * 100, 2) for item in similar_words]
            
            status = f"✅ 找到 {len(synonym_words)} 个近义词 (高速BERT查询)"
            return synonym_words, similarity_scores, status
            
        except Exception as e:
            return [], [], f"❌ 查询出错: {str(e)}"
    
    def compare_similarity(self, word1: str, word2: str) -> str:
        """比较两个词汇的相似度"""
        if not self.initialized:
            return "❌ 预计算embeddings未加载，请先运行 compute_bert_embeddings.py"
        
        if not word1 or not word2 or not word1.strip() or not word2.strip():
            return "❌ 请输入两个有效的词汇进行比较"
        
        word1, word2 = word1.strip(), word2.strip()
        
        # 验证输入是否为中文
        if not self._is_chinese(word1) or not self._is_chinese(word2):
            return "⚠️ 输入的词汇不是中文，建议使用中文词汇"
        
        try:
            # 使用预计算的embeddings计算相似度
            similarity = self.embedding_manager.compare_words(word1, word2)
            
            if similarity is None:
                missing_words = []
                if self.embedding_manager.get_embedding(word1) is None:
                    missing_words.append(word1)
                if self.embedding_manager.get_embedding(word2) is None:
                    missing_words.append(word2)
                return f"❌ 词汇{missing_words}在预计算词库中未找到"
            
            # 转换为百分比
            similarity_percent = round(similarity * 100, 2)
            
            # 生成评价
            if similarity_percent >= 80:
                level = "极高"
            elif similarity_percent >= 60:
                level = "高"
            elif similarity_percent >= 40:
                level = "中等"
            elif similarity_percent >= 20:
                level = "较低"
            else:
                level = "很低"
            
            return f"✅ '{word1}' 与 '{word2}' 的相似度: {similarity_percent}% ({level}) [高速BERT计算]"
            
        except Exception as e:
            return f"❌ 相似度计算出错: {str(e)}"
    
    def search_words_by_pattern(self, pattern: str, limit: int = 20) -> List[str]:
        """按模式搜索词汇"""
        if not self.initialized:
            return []
        
        return self.embedding_manager.search_words(pattern, limit)
    
    def get_embedding_stats(self) -> dict:
        """获取embedding统计信息"""
        if not self.initialized:
            return {}
        
        return self.embedding_manager.get_stats()

def process_synonym_search(word: str, k: int = 10) -> str:
    """处理同义词查询的主函数"""
    searcher = FastBertSynonymSearcher()
    
    if not searcher.initialized:
        return f"""❌ 高速BERT同义词功能不可用

🔍 查询词汇: {word}

🔧 需要预计算embeddings，请按以下步骤操作：

1. 📊 运行embedding计算脚本：
   python compute_bert_embeddings.py

2. ⏳ 等待计算完成（可能需要几小时）

3. 🔄 重新访问此页面

📚 高速模式优势：
• 预计算26万+中文词汇的BERT embeddings
• 毫秒级查询响应，无需等待实时计算
• 支持大规模词库的语义搜索
• 更稳定的服务，不依赖实时BERT服务器

💡 提示: 计算过程可能较长，但一次计算永久使用"""
    
    synonym_words, similarities, status = searcher.get_synonyms(word, k)
    
    if not synonym_words:
        return status
    
    # 获取统计信息
    stats = searcher.get_embedding_stats()
    
    # 格式化输出
    result_lines = [
        f"🔍 查询词汇: {word}",
        f"📊 {status}",
        f"📚 词库规模: {stats.get('total_words', 'N/A')} 个词汇",
        "",
        "📝 近义词列表 (高速BERT查询):",
        "=" * 50
    ]
    
    for i, (syn_word, similarity) in enumerate(zip(synonym_words, similarities), 1):
        result_lines.append(f"{i:2d}. {syn_word:<15} (相似度: {similarity:5.1f}%)")
    
    result_lines.extend([
        "=" * 50,
        f"💡 提示: 基于预计算的BERT embeddings，查询速度极快",
        f"🧠 词库: 中文新华词典 + BERT深度学习模型",
        f"📈 内存使用: {stats.get('memory_usage_mb', 'N/A'):.1f} MB"
    ])
    
    return "\n".join(result_lines)

def process_similarity_comparison(word1: str, word2: str) -> str:
    """处理两个词汇相似度比较的主函数"""
    searcher = FastBertSynonymSearcher()
    
    if not searcher.initialized:
        return f"""❌ 高速BERT相似度计算功能不可用

🔍 比较词汇: '{word1}' vs '{word2}'

🔧 需要预计算embeddings，请运行：
python compute_bert_embeddings.py

📚 高速模式说明:
• 基于26万+词汇的预计算BERT embeddings
• 毫秒级相似度计算
• 无需等待实时BERT服务响应
• 支持离线使用

💡 相似度等级:
• 80%以上: 极高相似度（近义词）
• 60-80%: 高相似度（相关词汇）  
• 40-60%: 中等相似度（主题相关）
• 20-40%: 较低相似度（有一定关联）
• 20%以下: 很低相似度（基本无关）"""
    
    result = searcher.compare_similarity(word1, word2)
    stats = searcher.get_embedding_stats()
    
    # 添加额外信息
    result_lines = [
        "🔍 词汇相似度比较 (高速BERT)",
        "=" * 35,
        result,
        "",
        "🧠 计算方法: 预计算BERT embeddings + 余弦相似度",
        f"📚 词库规模: {stats.get('total_words', 'N/A')} 个词汇",
        f"📈 向量维度: {stats.get('vector_dimension', 'N/A')}",
        "",
        "💡 说明:",
        "• 基于预计算embeddings，查询速度极快",
        "• 使用完整的中文新华词典词库",
        "• BERT深度学习模型提供准确的语义理解"
    ]
    
    return "\n".join(result_lines)

if __name__ == "__main__":
    # 测试快速BERT同义词功能
    print("🧪 测试高速BERT同义词功能...")
    
    test_words = ["高兴", "美丽", "学习"]
    for word in test_words:
        print(f"\n测试词汇: {word}")
        result = process_synonym_search(word, 5)
        print(result)
    
    print("\n测试相似度比较...")
    result = process_similarity_comparison("高兴", "快乐")
    print(result)
