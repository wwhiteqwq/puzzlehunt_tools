#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen同义词搜索器 V3版本 - 优化版
先按韵母筛选，再计算相似度，大幅提升查询速度
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import re
from qwen_embedding_client import QwenEmbeddingClient
from pinyin_tools import (
    get_word_pinyin, filter_words_by_character_finals, 
    filter_words_by_advanced_criteria, get_available_initials, 
    get_available_finals, get_available_tones, get_available_strokes, 
    get_available_radicals
)
from vocabulary_preprocessor import VocabularyPreprocessor
import json
import os

class QwenSynonymSearcherV3:
    """Qwen同义词搜索器V3 - 先筛选再计算版本"""
    
    def __init__(self, qwen_client=None):
        """初始化搜索器"""
        print("🚀 初始化QwenSynonymSearcherV3...")
        
        # 初始化Qwen客户端（可选）
        if qwen_client:
            self.qwen_client = qwen_client
            self.qwen_available = qwen_client.available
        else:
            try:
                self.qwen_client = QwenEmbeddingClient()
                if self.qwen_client.available:
                    print("✅ Qwen embedding服务连接成功")
                    self.qwen_available = True
                else:
                    print("⚠️ Qwen embedding服务不可用，切换到离线模式")
                    self.qwen_available = False
            except Exception as e:
                print(f"⚠️ Qwen客户端初始化失败: {e}")
                print("🔧 切换到离线模式（仅支持筛选功能）")
                self.qwen_client = None
                self.qwen_available = False
        
        # 初始化词库预处理器
        print("🔄 初始化词库预处理器...")
        self.vocab_preprocessor = VocabularyPreprocessor()
        
        # 加载预处理的词库数据
        if self.vocab_preprocessor.preprocess_vocabulary():
            self.candidate_words = self.vocab_preprocessor.get_all_words()
            print(f"✅ 已加载预处理词库: {len(self.candidate_words)} 个词汇")
        else:
            # 备用方法加载候选词库
            print("⚠️ 预处理失败，使用备用方法加载候选词...")
            self.candidate_words = self._load_candidate_words()
            if self.candidate_words:
                print(f"📚 已加载候选词库: {len(self.candidate_words)} 个词汇")
            else:
                print("⚠️ 未找到候选词库数据")
        
        # 尝试加载大词库（如果可用）
        self.large_vocabulary = self._load_large_vocabulary()
        if self.large_vocabulary:
            print(f"📖 已加载大词库: {len(self.large_vocabulary)} 个词汇")
        
        # 初始化离线筛选器（备用）
        try:
            from offline_character_filter import OfflineCharacterFilter
            self.offline_filter = OfflineCharacterFilter()
            print("✅ 离线筛选器已就绪")
        except Exception as e:
            print(f"⚠️ 离线筛选器初始化失败: {e}")
            self.offline_filter = None
    
    def get_word_pinyin_fast(self, word: str) -> List[str]:
        """
        快速获取词汇拼音（使用预处理的数据）
        
        Args:
            word: 词汇
            
        Returns:
            拼音列表
        """
        if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
            pinyins = self.vocab_preprocessor.get_word_pinyin(word)
            if pinyins:
                return pinyins
        
        # 备用方法：使用原始函数
        return get_word_pinyin(word)
    
    def _load_candidate_words(self) -> List[str]:
        """加载基础候选词库 - 仅从实际数据源加载，不编造"""
        try:
            # 尝试从ci.json加载词汇
            import os
            import json
            
            ci_path = os.path.join(os.path.dirname(__file__), "ci.json")
            if os.path.exists(ci_path):
                with open(ci_path, 'r', encoding='utf-8') as f:
                    ci_data = json.load(f)
                    words = [item.get('ci', '').strip() for item in ci_data if item.get('ci') and len(item.get('ci', '').strip()) >= 2]
                    return words[:500]  # 限制为前500个作为基础词库
            
            print("⚠️ 未找到ci.json词库文件")
            return []
            
        except Exception as e:
            print(f"⚠️ 加载候选词库失败: {e}")
            return []
    
    def _load_large_vocabulary(self) -> Optional[List[str]]:
        """尝试加载大词库（ci.json）"""
        try:
            ci_path = "ci.json"
            if os.path.exists(ci_path):
                with open(ci_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                words = []
                seen = set()
                for item in data:
                    word = item.get('ci', '').strip()
                    if word and len(word) >= 2 and word not in seen:
                        words.append(word)
                        seen.add(word)
                return words
        except Exception as e:
            print(f"⚠️ 加载大词库失败: {e}")
        return None
    
    def _is_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return bool(chinese_pattern.search(text))
    
    def search_synonyms(self, word: str, k: int = 10, character_finals: Optional[List[str]] = None, 
                       character_filters: Optional[List[Dict[str, Any]]] = None, 
                       min_length: Optional[int] = None, max_length: Optional[int] = None) -> Tuple[List[str], List[float], str]:
        """
        同义词查询 - 完全统一处理版本
        步骤：1.二分查找获取候选词 → 2.验证所有条件 → 3.根据是否有查询词决定是否相似度排序
        
        Args:
            word: 查询词汇（可以为空，表示纯筛选）
            k: 返回结果数量
            character_finals: 每个字符位置的韵母要求，空字符串表示无要求（简单模式）
            character_filters: 高级筛选条件，每个位置的详细筛选参数（高级模式）
            min_length: 最小词长限制（可选）
            max_length: 最大词长限制（可选）
        """
        try:
            # 判断是否有查询词
            has_query_word = bool(word and word.strip())
            
            if has_query_word:
                word = word.strip()
                if not self._is_chinese(word):
                    return [], [], "⚠️ 输入的词汇不是中文"
                print(f"🔍 开始查询: {word}")
            else:
                # 检查是否有任何筛选条件（韵母、高级筛选、长度筛选）
                has_any_filter = False
                if character_finals and any(f for f in character_finals):
                    has_any_filter = True
                if character_filters and any(f for f in character_filters):
                    has_any_filter = True
                if min_length is not None or max_length is not None:
                    has_any_filter = True
                    
                if not has_any_filter:
                    return [], [], "❌ 请输入查询词汇或设置筛选条件"
                print("🔍 启动纯筛选模式（无查询词）")
            
            # 步骤1: 统一筛选候选词
            print("⚡ 步骤1: 高效筛选候选词...")
            
            # 🔄 统一筛选逻辑：支持简单韵母筛选、高级筛选和纯长度筛选
            if character_filters:
                # 高级筛选模式
                eligible_words = self._filter_candidates_by_advanced_criteria(word, character_filters)
            elif character_finals and any(f for f in character_finals):
                # 简单韵母筛选模式
                eligible_words = self._filter_candidates_by_finals(word, character_finals)
            else:
                # 纯长度筛选模式（无其他筛选条件）
                eligible_words = self._filter_candidates_by_length_only(word)
            
            # 📏 应用长度筛选
            if min_length is not None or max_length is not None:
                eligible_words = self._filter_by_length(eligible_words, min_length, max_length)
                print(f"📏 长度筛选后: {len(eligible_words)} 个候选词")
            
            if not eligible_words:
                if character_finals and any(f for f in character_finals):
                    return [], [], "🎵 没有找到符合韵母条件的词汇"
                elif character_filters:
                    return [], [], "🎯 没有找到符合筛选条件的词汇"
                else:
                    return [], [], "❌ 没有找到候选词汇"
            
            print(f"✅ 筛选出 {len(eligible_words)} 个候选词")
            
            # 步骤2: 统一排序决策
            if has_query_word and self.qwen_available:
                # 有查询词且服务可用：计算相似度并排序
                print("🧠 步骤2: 计算相似度并排序...")
                synonyms, similarities = self._compute_similarities_and_sort(word, eligible_words, k)
                
                if not synonyms:
                    return [], [], "❌ 相似度计算失败"
                
                result_msg = self._build_unified_result_message(word, synonyms, similarities, character_finals, character_filters, sorted=True, min_length=min_length, max_length=max_length)
                return synonyms, similarities, result_msg
            
            else:
                # 无查询词或服务不可用：直接返回筛选结果
                if has_query_word:
                    print("⚠️ Qwen服务不可用，返回筛选结果（无排序）")
                else:
                    print("📋 返回筛选结果（纯筛选模式）")
                
                final_results = eligible_words[:k]
                zero_similarities = [0.0] * len(final_results)
                result_msg = self._build_unified_result_message(word, final_results, zero_similarities, character_finals, character_filters, sorted=False, min_length=min_length, max_length=max_length)
                return final_results, zero_similarities, result_msg
            
        except Exception as e:
            error_msg = f"❌ 查询失败: {str(e)}"
            print(error_msg)
            return [], [], error_msg
    
    def _compute_similarities_and_sort(self, query_word: str, candidates: List[str], k: int) -> Tuple[List[str], List[float]]:
        """
        计算相似度并排序，返回前k个结果
        优化版本：直接计算并排序，避免中间步骤
        """
        
        if not candidates:
            return [], []
        
        try:
            # 限制候选词数量以提高效率
            max_candidates = 1000
            if len(candidates) > max_candidates:
                print(f"📊 候选词过多 ({len(candidates)}个)，限制为前{max_candidates}个")
                candidates = candidates[:max_candidates]
            
            print(f"🧠 计算 {len(candidates)} 个候选词的相似度...")
            
            # 计算相似度
            similarities = self._compute_batch_similarities_optimized(query_word, candidates)
            
            if not similarities:
                print("❌ 相似度计算失败")
                return [], []
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 返回前k个结果
            top_k = similarities[:k]
            synonyms = [pair[0] for pair in top_k]
            sim_scores = [pair[1] for pair in top_k]
            
            print(f"✅ 排序完成，返回前{len(synonyms)}个结果")
            return synonyms, sim_scores
            
        except Exception as e:
            print(f"❌ 相似度计算失败: {e}")
            return [], []
    
    def _compute_batch_similarities_optimized(self, query_word: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """优化的批量相似度计算"""
        try:
            # 准备编码词汇列表（查询词 + 候选词）
            words_to_encode = [query_word] + candidates
            
            # 分批编码以避免超过API限制
            batch_size = 25  # 保守的批次大小
            all_embeddings = []
            
            total_batches = (len(words_to_encode) + batch_size - 1) // batch_size
            
            for i in range(0, len(words_to_encode), batch_size):
                batch = words_to_encode[i:i + batch_size]
                print(f"   编码批次 {i//batch_size + 1}/{total_batches}: {len(batch)} 个词")
                
                batch_embeddings = self.qwen_client.encode(batch)
                
                if batch_embeddings is None:
                    print(f"❌ 批次编码失败")
                    continue
                
                all_embeddings.extend(batch_embeddings)
            
            if len(all_embeddings) != len(words_to_encode):
                print(f"⚠️ 编码数量不匹配: {len(all_embeddings)} vs {len(words_to_encode)}")
                return []
            
            # 计算相似度
            query_embedding = all_embeddings[0]
            candidate_embeddings = all_embeddings[1:]
            
            similarities = []
            for i, candidate in enumerate(candidates):
                if i < len(candidate_embeddings):
                    candidate_embedding = candidate_embeddings[i]
                    # 计算余弦相似度
                    similarity = np.dot(query_embedding, candidate_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
                    )
                    similarities.append((candidate, float(similarity)))
            
            return similarities
            
        except Exception as e:
            print(f"❌ 批量相似度计算失败: {e}")
            return []
    
    def search_synonyms_advanced(
        self, 
        word: str, 
        k: int = 10,
        character_filters: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[str], List[float], str]:
        """
        高级同义词查询 - 支持声母、韵母、声调、笔画、部首等多重筛选
        
        Args:
            word: 查询词汇（可以为空，表示纯筛选模式）
            k: 返回结果数量
            character_filters: 每个字符位置的筛选条件列表
                格式: [
                    {  # 第一个字的条件
                        'initial': '声母',
                        'final': '韵母', 
                        'tone': '声调',
                        'stroke_count': 笔画数,
                        'radical': '部首',
                        'contains_stroke': '笔画名称',
                        'stroke_position': 笔画位置
                    },
                    {  # 第二个字的条件
                        ...
                    }
                ]
        
        Returns:
            (同义词列表, 相似度列表, 结果消息)
        """
        try:
            # 🚀 新增：支持纯筛选模式（查询词为空）
            if not word or not word.strip():
                if character_filters:
                    print("🔍 启动纯筛选模式（无需embedding服务）")
                    return self._pure_filter_search(character_filters, k)
                else:
                    return [], [], "❌ 请输入查询词汇或设置筛选条件"
            
            word = word.strip()
            if not self._is_chinese(word):
                return [], [], "⚠️ 输入的词汇不是中文"
            
            print(f"🔍 开始高级查询: {word}")
            
            # 步骤1: 按高级条件筛选候选词
            print("📝 步骤1: 按高级条件筛选候选词...")
            eligible_words = self._filter_candidates_by_advanced_criteria(word, character_filters)
            
            if not eligible_words:
                # 🚀 新机制：没有符合筛选条件的词时，直接返回前k个候选词（不进行语义排序）
                print("⚠️ 未找到符合筛选条件的词汇，返回前k个候选词")
                candidates = self._get_candidate_pool(word)
                # 移除查询词本身，取前k个
                top_candidates = [w for w in candidates if w != word][:k]
                
                # 返回空相似度分数（表示未进行语义计算）
                zero_similarities = [0.0] * len(top_candidates)
                result_msg = f"🎯 未找到符合筛选条件的词汇，显示前{len(top_candidates)}个候选词（未排序）"
                
                return top_candidates, zero_similarities, result_msg
            
            print(f"✅ 筛选出 {len(eligible_words)} 个候选词")
            
            # 检查是否需要语义相似度计算
            if not self.qwen_available:
                print("⚠️ Qwen服务不可用，跳过语义排序")
                # 直接返回筛选结果，不进行语义排序
                final_results = eligible_words[:k]
                zero_similarities = [0.0] * len(final_results)
                result_msg = self._build_advanced_result_message(word, final_results, zero_similarities, character_filters)
                return final_results, zero_similarities, result_msg
            
            # 步骤2: 对筛选后的词汇计算相似度并排序
            print("🧠 步骤2: 计算相似度并排序...")
            synonyms, similarities = self._compute_similarities(word, eligible_words, k)
            
            if not synonyms:
                return [], [], "❌ 相似度计算失败"
            
            # 构建结果消息
            result_msg = self._build_advanced_result_message(word, synonyms, similarities, character_filters)
            
            return synonyms, similarities, result_msg
            
        except Exception as e:
            error_msg = f"❌ 高级查询失败: {str(e)}"
            print(error_msg)
            return [], [], error_msg
    
    def _get_candidate_pool(self, query_word: str) -> List[str]:
        """获取候选词池（用于相似度计算）"""
        
        # 优先使用预处理的词汇库
        if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
            candidates = self.vocab_preprocessor.get_all_words()
            print(f"⚡ 使用预处理词库: {len(candidates)} 个候选词")
        elif self.large_vocabulary and len(self.large_vocabulary) > 1000:
            # 使用大词库
            candidates = self.large_vocabulary
            print(f"📖 使用大词库: {len(candidates)} 个候选词")
        else:
            candidates = self.candidate_words
            print(f"📚 使用基础词库: {len(candidates)} 个候选词")
        
        # 过滤掉查询词本身和单字词
        filtered = [w for w in candidates if w != query_word and len(w) >= 2]
        return filtered
    
    def _filter_candidates_by_finals(self, query_word: str, character_finals: Optional[List[str]]) -> List[str]:
        """按韵母条件筛选候选词（高效版 - 使用二分查找优化）"""
        
        # 判断是否有查询词
        has_query_word = bool(query_word and query_word.strip())
        
        # 如果没有韵母限制，返回基础词库（高质量词汇）
        if not character_finals or all(not f for f in character_finals):
            if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
                base_candidates = self.vocab_preprocessor.filter_words_by_length(2, 10)
                if has_query_word:
                    base_candidates = [w for w in base_candidates if w != query_word]
                print(f"⚡ 无韵母限制，使用预处理词库: {len(base_candidates)} 个候选词")
                return base_candidates[:1000]  # 限制数量
            else:
                # 备用方法
                candidates = self._get_candidate_pool(query_word if has_query_word else "")
                base_candidates = [w for w in self.candidate_words if len(w) >= 2]
                if has_query_word:
                    base_candidates = [w for w in base_candidates if w != query_word]
                if len(base_candidates) < 500 and len(candidates) > len(base_candidates):
                    additional = [w for w in candidates[:1000] if w not in base_candidates]
                    base_candidates.extend(additional)
                print(f"📚 无韵母限制，使用备用词库: {len(base_candidates)} 个候选词")
                return base_candidates
        
        print("⚡ 应用高效韵母筛选...")
        
        if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
            return self._efficient_filter_by_finals(query_word, character_finals)
        else:
            # 备用方法：使用原始筛选
            candidates = self._get_candidate_pool(query_word if has_query_word else "")
            filtered_words = filter_words_by_character_finals(candidates, character_finals)
            print(f"📚 备用筛选完成: {len(filtered_words)} 个候选词")
            return filtered_words
    
    def _filter_candidates_by_length_only(self, query_word: str) -> List[str]:
        """纯长度筛选（无其他条件时使用）"""
        if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
            # 获取基础词库（2-10字）
            base_candidates = self.vocab_preprocessor.filter_words_by_length(2, 10)
            # 移除查询词本身
            if query_word and query_word.strip():
                base_candidates = [w for w in base_candidates if w != query_word]
            print(f"⚡ 纯长度筛选，使用预处理词库: {len(base_candidates)} 个候选词")
            return base_candidates[:1000]  # 限制数量避免计算量过大
        else:
            # 备用方法
            candidates = [w for w in self.candidate_words if len(w) >= 2]
            if query_word and query_word.strip():
                candidates = [w for w in candidates if w != query_word]
            print(f"📚 纯长度筛选，使用备用词库: {len(candidates)} 个候选词")
            return candidates[:1000]
    
    def _efficient_filter_by_finals(self, query_word: str, character_finals: List[str]) -> List[str]:
        """
        高效的韵母筛选算法：
        1. 二分查找获取初始候选词
        2. 逐词验证所有条件
        """
        print(f"   目标韵母条件: {character_finals}")
        
        # 步骤1: 使用二分查找获取初始候选词集合
        initial_candidates = self._get_candidates_by_binary_search(character_finals)
        
        if not initial_candidates:
            print("   二分查找无结果")
            return []
        
        print(f"   二分查找结果: {len(initial_candidates)} 个候选词")
        
        # 步骤2: 逐词验证所有条件
        verified_candidates = self._verify_candidates_conditions(initial_candidates, character_finals)
        
        # 移除查询词本身（如果有查询词）
        if query_word and query_word.strip():
            verified_candidates = [w for w in verified_candidates if w != query_word]
        
        print(f"   验证完成: {len(verified_candidates)} 个符合条件的词")
        return verified_candidates
    
    def _get_candidates_by_binary_search(self, character_finals: List[str]) -> List[str]:
        """使用二分查找获取初始候选词集合"""
        
        # 找到第一个非空的韵母条件用于二分查找
        primary_final = None
        primary_position = -1
        
        for i, final in enumerate(character_finals):
            if final and final.strip():
                primary_final = final.strip()
                primary_position = i
                break
        
        if not primary_final:
            # 没有韵母条件，返回所有词汇
            return self.vocab_preprocessor.get_all_words()
        
        print(f"   使用第{primary_position+1}个字的韵母'{primary_final}'进行二分查找")
        
        # 使用预处理器的韵母索引快速获取候选词
        candidates = self.vocab_preprocessor.filter_words_by_final_fast(primary_final)
        
        # 如果候选词太少，尝试使用二分查找扩展
        if len(candidates) < 100:
            # 尝试按拼音前缀搜索（用于处理复合韵母）
            prefix_candidates = self.vocab_preprocessor.binary_search_by_pinyin_prefix(primary_final)
            # 合并结果并去重
            all_candidates = list(set(candidates + prefix_candidates))
            print(f"   扩展搜索: {len(candidates)} + {len(prefix_candidates)} = {len(all_candidates)} 个候选词")
            return all_candidates
        
        return candidates
    
    def _verify_candidates_conditions(self, candidates: List[str], character_finals: List[str]) -> List[str]:
        """逐词验证候选词是否满足所有韵母条件"""
        
        verified = []
        target_length = len(character_finals)
        
        # 导入 pinyin_tools 以获取实时拼音
        from pinyin_tools import get_word_finals
        
        # 限制候选词数量以提高性能
        max_candidates = 1000
        if len(candidates) > max_candidates:
            candidates = candidates[:max_candidates]
            print(f"   为提高性能，限制验证候选词为前{max_candidates}个")
        
        for word in candidates:
            # 检查词长是否匹配
            if len(word) != target_length:
                continue
            
            # 使用 pinyin_tools 获取实时韵母
            try:
                actual_finals = get_word_finals(word)
                
                # 过滤掉非拼音数据（如"説"等注释）
                clean_finals = []
                for final in actual_finals:
                    # 只保留包含拼音字符的韵母
                    if final and all(c.isalpha() or c in 'üɡ' for c in final):
                        clean_finals.append(final)
                
                # 检查清理后的韵母数量是否匹配
                if len(clean_finals) != target_length:
                    continue
                
                # 验证每个位置的韵母
                matches = True
                for i, (required_final, actual_final) in enumerate(zip(character_finals, clean_finals)):
                    if required_final and required_final.strip():
                        required = required_final.strip()
                        
                        # 标准化韵母比较：处理Unicode字符ɡ和ue↔ve转换
                        def normalize_final(final):
                            """标准化韵母格式，支持ue↔ve双向转换"""
                            if not final:
                                return ''
                            # 处理Unicode ɡ字符
                            normalized = final.replace('ɡ', 'g')
                            # 处理ue↔ve转换：都统一为ue进行比较
                            if normalized == 've':
                                normalized = 'ue'
                            return normalized
                        
                        if normalize_final(actual_final) != normalize_final(required):
                            matches = False
                            break
                
                if matches:
                    verified.append(word)
                    # 找到足够的词汇就停止（为了性能）
                    if len(verified) >= 100:
                        print(f"   已找到{len(verified)}个符合条件的词，停止验证以提高性能")
                        break
                        
            except Exception:
                # 如果拼音获取失败，跳过这个词
                continue
        
        return verified
    
    def _filter_candidates_by_advanced_criteria(self, query_word: str, character_filters: Optional[List[Dict[str, Any]]]) -> List[str]:
        """按高级条件筛选候选词（高效版 - 使用二分查找优化）"""
        
        # 如果没有筛选条件，返回基础词库
        if not character_filters:
            if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
                base_candidates = self.vocab_preprocessor.filter_words_by_length(2, 10)
                base_candidates = [w for w in base_candidates if w != query_word]
                print(f"⚡ 无筛选条件，使用预处理词库: {len(base_candidates)} 个候选词")
                return base_candidates[:1000]
            else:
                candidates = self._get_candidate_pool(query_word)
                base_candidates = [w for w in self.candidate_words if w != query_word and len(w) >= 2]
                if len(base_candidates) < 500 and len(candidates) > len(base_candidates):
                    additional = [w for w in candidates[:1000] if w not in base_candidates]
                    base_candidates.extend(additional)
                print(f"📚 无筛选条件，使用优选词库: {len(base_candidates)} 个候选词")
                return base_candidates
        
        print("⚡ 应用高效高级筛选...")
        
        if hasattr(self, 'vocab_preprocessor') and self.vocab_preprocessor:
            return self._efficient_advanced_filter(query_word, character_filters)
        else:
            # 备用方法：使用分层筛选
            candidates = self._get_candidate_pool(query_word)
            filtered_words = self._apply_layered_filtering(candidates, character_filters)
            print(f"📚 备用筛选完成: {len(filtered_words)} 个候选词")
            return filtered_words
    
    def _efficient_advanced_filter(self, query_word: str, character_filters: List[Dict[str, Any]]) -> List[str]:
        """
        高效的高级筛选算法：
        1. 二分查找获取初始候选词（基于声母/韵母）
        2. 逐词验证所有条件（声调、笔画、部首等）
        """
        print(f"   高级筛选条件: {len(character_filters)} 个字符位置")
        
        # 步骤1: 使用二分查找获取初始候选词集合
        initial_candidates = self._get_candidates_by_advanced_binary_search(character_filters)
        
        if not initial_candidates:
            print("   二分查找无结果")
            return []
        
        print(f"   二分查找结果: {len(initial_candidates)} 个候选词")
        
        # 步骤2: 逐词验证所有高级条件
        verified_candidates = self._verify_advanced_conditions(initial_candidates, character_filters)
        
        # 移除查询词本身
        verified_candidates = [w for w in verified_candidates if w != query_word]
        
        print(f"   高级验证完成: {len(verified_candidates)} 个符合条件的词")
        return verified_candidates
    
    def _get_candidates_by_advanced_binary_search(self, character_filters: List[Dict[str, Any]]) -> List[str]:
        """使用二分查找获取初始候选词集合（基于声母/韵母条件）"""
        
        # 寻找最容易用索引查找的条件（声母或韵母）
        best_filter = None
        best_position = -1
        best_type = None
        
        for i, filters in enumerate(character_filters):
            if not filters:
                continue
            
            # 优先使用韵母（通常更具选择性）
            if filters.get('final'):
                best_filter = filters['final']
                best_position = i
                best_type = 'final'
                break
            # 其次使用声母
            elif filters.get('initial'):
                best_filter = filters['initial']
                best_position = i
                best_type = 'initial'
        
        if not best_filter:
            # 没有声母/韵母条件，返回所有词汇
            print("   无声母/韵母条件，使用全词库")
            return self.vocab_preprocessor.get_all_words()
        
        print(f"   使用第{best_position+1}个字的{best_type}'{best_filter}'进行二分查找")
        
        # 使用索引快速获取候选词
        if best_type == 'final':
            candidates = self.vocab_preprocessor.filter_words_by_final_fast(best_filter)
        else:  # initial
            # 处理声母字符转换（g -> ɡ）
            search_initial = best_filter
            if search_initial == 'g':
                search_initial = 'ɡ'  # Unicode U+0261
            candidates = self.vocab_preprocessor.filter_words_by_initial_fast(search_initial)
        
        print(f"   二分查找结果: {len(candidates)} 个候选词")
        return candidates
    
    def _verify_advanced_conditions(self, candidates: List[str], character_filters: List[Dict[str, Any]]) -> List[str]:
        """逐词验证候选词是否满足所有高级条件"""
        
        verified = []
        
        # 计算实际有效的筛选条件数量（去除空条件）
        effective_filters = [f for f in character_filters if f]
        max_position = 0
        for i, f in enumerate(character_filters):
            if f:
                max_position = i + 1
        
        for word in candidates:
            # 词长必须至少包含有条件的位置
            if len(word) < max_position:
                continue
            
            # 验证每个字符位置的条件
            if self._verify_word_conditions(word, character_filters):
                verified.append(word)
        
        return verified
    
    def _filter_by_length(self, candidates: List[str], min_length: Optional[int], max_length: Optional[int]) -> List[str]:
        """按词汇长度筛选候选词"""
        if min_length is None and max_length is None:
            return candidates
        
        filtered = []
        for word in candidates:
            word_length = len(word)
            # 检查最小长度
            if min_length is not None and word_length < min_length:
                continue
            # 检查最大长度
            if max_length is not None and word_length > max_length:
                continue
            filtered.append(word)
        
        return filtered
    
    def _verify_word_conditions(self, word: str, character_filters: List[Dict[str, Any]]) -> bool:
        """验证单个词汇是否满足所有条件"""
        
        # 获取词汇拼音
        pinyins = self.vocab_preprocessor.get_word_pinyin(word)
        if not pinyins:
            return False
        
        # 处理拼音格式：如果是字符串表示的列表，需要解析
        pinyin_string = pinyins[0]
        if isinstance(pinyin_string, str) and pinyin_string.startswith('[') and pinyin_string.endswith(']'):
            # 解析字符串表示的列表，如"['xué']" -> "xué"
            import ast
            try:
                pinyin_list = ast.literal_eval(pinyin_string)
                if isinstance(pinyin_list, list) and len(pinyin_list) > 0:
                    pinyin_string = ' '.join(pinyin_list)
            except:
                # 如果解析失败，尝试简单的字符串处理
                pinyin_string = pinyin_string.strip("[]'\"").replace("'", "").replace('"', '')
        
        pinyin_parts = pinyin_string.split()
        
        # 逐字符验证（只验证有条件的位置）
        for i, filters in enumerate(character_filters):
            if not filters:  # 空条件，跳过
                continue
                
            # 检查词汇是否有足够的字符
            if i >= len(word) or i >= len(pinyin_parts):
                return False
            
            char = word[i]
            char_pinyin = pinyin_parts[i]
            
            # 验证拼音相关条件（声母、韵母、声调）
            if not self._verify_pinyin_conditions(char_pinyin, filters):
                return False
            
            # 验证字符相关条件（笔画、部首等）
            if not self._verify_character_conditions(char, filters):
                return False
        
        return True
    
    def _verify_pinyin_conditions(self, char_pinyin: str, filters: Dict[str, Any]) -> bool:
        """验证拼音相关条件（空值表示无限制）"""
        
        # 提取声母和韵母
        initial, final = self.vocab_preprocessor._extract_initial_final(char_pinyin)
        
        # 验证声母（空值或None表示无限制）
        required_initial = filters.get('initial')
        if required_initial and required_initial.strip():  # 有具体要求
            # 处理声母字符转换（g -> ɡ）
            search_initial = required_initial.strip()
            if search_initial == 'g':
                search_initial = 'ɡ'  # Unicode U+0261
            if initial != search_initial:
                return False
        
        # 验证韵母（空值或None表示无限制）
        required_final = filters.get('final')
        if required_final and required_final.strip():  # 有具体要求
            # 支持韵母标准化比较
            def normalize_final(f):
                if not f:
                    return ''
                # 处理Unicode ɡ字符
                normalized = f.replace('ɡ', 'g')
                # 处理ue <-> ve转换：统一为ue标准
                if normalized == 've':
                    normalized = 'ue'
                return normalized
            
            actual_normalized = normalize_final(final)
            required_normalized = normalize_final(required_final.strip())
            
            # 支持双向匹配：ue可以匹配ve，ve也可以匹配ue
            if actual_normalized != required_normalized and not (
                (actual_normalized == 'ue' and required_normalized == 've') or
                (actual_normalized == 've' and required_normalized == 'ue')
            ):
                return False
        
        # 验证声调（需要从原始拼音提取）
        required_tone = filters.get('tone')
        if required_tone and required_tone.strip():  # 有具体要求
            # 简单的声调提取（基于音调符号）
            tone = self._extract_tone(char_pinyin)
            if tone != filters['tone']:
                return False
        
        return True
    
    def _verify_character_conditions(self, char: str, filters: Dict[str, Any]) -> bool:
        """验证字符相关条件（笔画、部首等，空值表示无限制）"""
        
        # 获取字符信息
        char_info = self.vocab_preprocessor.get_character_info(char)
        if not char_info:
            # 如果没有字符信息，检查是否有必须验证的条件
            has_required_conditions = any([
                filters.get('stroke_count'),
                filters.get('radical') and filters.get('radical').strip(),
                filters.get('contains_stroke') and filters.get('contains_stroke').strip()
            ])
            return not has_required_conditions
        
        # 验证笔画数（0或None表示无限制）
        required_stroke = filters.get('stroke_count')
        if required_stroke and required_stroke > 0:  # 有具体要求
            actual_stroke = char_info.get('stroke', 0)
            if actual_stroke != required_stroke:
                return False
        
        # 验证部首（空值或None表示无限制）
        required_radical = filters.get('radical')
        if required_radical and required_radical.strip():  # 有具体要求
            actual_radical = char_info.get('radical', '')
            if actual_radical != required_radical.strip():
                return False
        
        # 验证笔画相关条件（空值表示无限制）
        required_stroke_char = filters.get('contains_stroke')
        if required_stroke_char and required_stroke_char.strip():  # 有具体要求
            order_simple = char_info.get('order_simple', [])
            if not self._verify_stroke_conditions(order_simple, filters):
                return False
        
        return True
    
    def _extract_tone(self, pinyin) -> str:
        """从拼音中提取声调"""
        # 声调符号映射
        tone_map = {
            'ā': '1', 'á': '2', 'ǎ': '3', 'à': '4',
            'ē': '1', 'é': '2', 'ě': '3', 'è': '4',
            'ī': '1', 'í': '2', 'ǐ': '3', 'ì': '4',
            'ō': '1', 'ó': '2', 'ǒ': '3', 'ò': '4',
            'ū': '1', 'ú': '2', 'ǔ': '3', 'ù': '4',
            'ǖ': '1', 'ǘ': '2', 'ǚ': '3', 'ǜ': '4',
            'ń': '2', 'ň': '3', 'ǹ': '4',
            'ḿ': '2', 'ň': '3', 'ǹ': '4'
        }
        
        # 处理不同的拼音格式
        if isinstance(pinyin, list) and pinyin:
            clean_pinyin = pinyin[0]  # 取第一个拼音
        elif isinstance(pinyin, str):
            # 如果是字符串表示的列表格式，如 "['xué']"
            if pinyin.startswith('[') and pinyin.endswith(']'):
                # 解析字符串表示的列表
                import ast
                try:
                    parsed = ast.literal_eval(pinyin)
                    if isinstance(parsed, list) and parsed:
                        clean_pinyin = parsed[0]
                    else:
                        clean_pinyin = pinyin.strip("[]'\"")
                except:
                    clean_pinyin = pinyin.strip("[]'\"")
            else:
                clean_pinyin = pinyin.strip()
        else:
            return '5'
        
        # 清理拼音字符串
        clean_pinyin = str(clean_pinyin).strip()
        
        for char in clean_pinyin:
            if char in tone_map:
                return tone_map[char]
        
        # 如果没有找到声调符号，检查是否有数字声调（如xue2）
        import re
        tone_match = re.search(r'(\d)$', clean_pinyin)
        if tone_match:
            return tone_match.group(1)
        
        return '5'  # 轻声或无声调
    
    def _verify_stroke_conditions(self, order_simple: List[str], filters: Dict[str, Any]) -> bool:
        """验证笔画相关条件"""
        
        contains_stroke = filters.get('contains_stroke')
        stroke_position = filters.get('stroke_position')
        
        if contains_stroke:
            if stroke_position:
                # 验证特定位置的笔画
                pos = int(stroke_position) - 1  # 转换为0索引
                if pos < 0 or pos >= len(order_simple) or order_simple[pos] != contains_stroke:
                    return False
            else:
                # 验证是否包含某种笔画
                if contains_stroke not in order_simple:
                    return False
        
        return True
    
    def _apply_layered_filtering(self, candidates: List[str], character_filters: List[Dict[str, Any]]) -> List[str]:
        """分层筛选策略：预筛选 → 逐步精化 → 最终优化"""
        
        # 第一层：预筛选 - 使用最严格的条件快速过滤
        print("🔍 第一层：预筛选阶段...")
        filtered_candidates = self._pre_filter_candidates(candidates, character_filters)
        
        if not filtered_candidates:
            print("❌ 预筛选后无结果")
            return []
        
        print(f"   预筛选完成: {len(candidates)} → {len(filtered_candidates)} 个候选词")
        
        # 第二层：渐进式筛选 - 逐个位置应用筛选条件
        print("🎯 第二层：渐进式筛选...")
        final_candidates = self._progressive_filtering(filtered_candidates, character_filters)
        
        if not final_candidates:
            print("❌ 渐进式筛选后无结果")
            return []
        
        print(f"   渐进式筛选完成: {len(filtered_candidates)} → {len(final_candidates)} 个候选词")
        
        return final_candidates
    
    def _pre_filter_candidates(self, candidates: List[str], character_filters: List[Dict[str, Any]]) -> List[str]:
        """预筛选：使用最严格的条件快速过滤"""
        
        # 统计筛选条件的严格程度
        strictness_scores = []
        for position, filters in enumerate(character_filters):
            if not filters:
                continue
            
            score = 0
            # 声调和声母/韵母组合最严格
            if filters.get('tone') and (filters.get('initial') or filters.get('final')):
                score += 10
            # 笔画数 + 部首组合严格
            elif filters.get('stroke_count') and filters.get('radical'):
                score += 8
            # 特定位置笔画很严格
            elif filters.get('stroke_position') and filters.get('contains_stroke'):
                score += 7
            # 单一条件
            elif any(filters.values()):
                score += 3
            
            strictness_scores.append((position, score, filters))
        
        # 按严格程度排序，优先使用最严格的条件
        strictness_scores.sort(key=lambda x: x[1], reverse=True)
        
        if not strictness_scores:
            return candidates
        
        # 使用最严格的条件进行预筛选
        position, score, filters = strictness_scores[0]
        print(f"   使用第{position+1}个字的条件进行预筛选 (严格度: {score})")
        
        filtered = filter_words_by_advanced_criteria(
            candidates,
            character_position=position,
            initial=filters.get('initial'),
            final=filters.get('final'), 
            tone=filters.get('tone'),
            stroke_count=filters.get('stroke_count'),
            radical=filters.get('radical'),
            contains_stroke=filters.get('contains_stroke'),
            stroke_position=filters.get('stroke_position')
        )
        
        return filtered
    
    def _progressive_filtering(self, candidates: List[str], character_filters: List[Dict[str, Any]]) -> List[str]:
        """渐进式筛选：逐个位置应用剩余的筛选条件"""
        
        filtered_words = candidates
        
        for position, filters in enumerate(character_filters):
            if not filters:
                continue
            
            print(f"     筛选第{position+1}个字: {filters}")
            
            before_count = len(filtered_words)
            filtered_words = filter_words_by_advanced_criteria(
                filtered_words,
                character_position=position,
                initial=filters.get('initial'),
                final=filters.get('final'), 
                tone=filters.get('tone'),
                stroke_count=filters.get('stroke_count'),
                radical=filters.get('radical'),
                contains_stroke=filters.get('contains_stroke'),
                stroke_position=filters.get('stroke_position')
            )
            
            after_count = len(filtered_words)
            print(f"     第{position+1}个字筛选: {before_count} → {after_count} 个候选词")
            
            # 如果筛选后没有结果，提前退出
            if not filtered_words:
                print(f"     ❌ 第{position+1}个字筛选后无结果，停止")
                break
        
        return filtered_words
    
    def _pure_filter_search(self, character_filters: List[Dict[str, Any]], k: int) -> Tuple[List[str], List[float], str]:
        """
        纯筛选搜索模式 - 不依赖embedding，只根据筛选条件筛选词汇
        """
        print("🔍 纯筛选模式：基于筛选条件搜索词汇...")
        
        try:
            # 获取候选词池，优先级：大词库 > 基础词库 > 离线筛选器
            candidates = None
            source_name = ""
            
            if self.large_vocabulary and len(self.large_vocabulary) > 1000:
                candidates = self.large_vocabulary
                source_name = f"大词库: {len(candidates)} 个候选词"
            elif self.candidate_words and len(self.candidate_words) > 0:
                candidates = self.candidate_words
                source_name = f"基础词库: {len(candidates)} 个候选词"
            elif self.offline_filter:
                # 使用离线筛选器
                print("📖 使用离线筛选器")
                return self.offline_filter.pure_filter_search(character_filters, k)
            else:
                return [], [], "❌ 没有可用的词库数据"
            
            print(f"📖 使用{source_name}")
            
            # 应用分层筛选
            filtered_words = self._apply_layered_filtering(candidates, character_filters)
            
            if not filtered_words:
                return [], [], "🎯 没有找到符合所有筛选条件的词汇"
            
            # 限制结果数量
            final_results = filtered_words[:k] if len(filtered_words) > k else filtered_words
            
            # 生成零相似度分数（因为没有参考词汇）
            zero_similarities = [0.0] * len(final_results)
            
            # 构建结果消息
            result_msg = self._build_pure_filter_result_message(final_results, character_filters, len(filtered_words))
            
            print(f"✅ 纯筛选完成，返回 {len(final_results)} 个结果")
            return final_results, zero_similarities, result_msg
            
        except Exception as e:
            error_msg = f"❌ 纯筛选搜索失败: {str(e)}"
            print(error_msg)
            return [], [], error_msg
    
    def _build_pure_filter_result_message(self, results: List[str], character_filters: List[Dict[str, Any]], total_matches: int) -> str:
        """构建纯筛选结果消息"""
        
        result_lines = ["🔍 纯筛选搜索结果"]
        result_lines.append(f"📊 搜索模式: 仅基于筛选条件（无embedding计算）")
        
        # 筛选条件信息
        if character_filters:
            condition_info = []
            for i, filters in enumerate(character_filters):
                if not filters:
                    continue
                
                char_conditions = []
                if filters.get('initial'):
                    char_conditions.append(f"声母={filters['initial']}")
                if filters.get('final'):
                    char_conditions.append(f"韵母={filters['final']}")
                if filters.get('tone'):
                    char_conditions.append(f"声调={filters['tone']}")
                if filters.get('stroke_count'):
                    char_conditions.append(f"笔画={filters['stroke_count']}")
                if filters.get('radical'):
                    char_conditions.append(f"部首={filters['radical']}")
                if filters.get('contains_stroke'):
                    if filters.get('stroke_position'):
                        char_conditions.append(f"第{filters['stroke_position']}笔={filters['contains_stroke']}")
                    else:
                        char_conditions.append(f"含笔画={filters['contains_stroke']}")
                
                if char_conditions:
                    condition_info.append(f"第{i+1}字({', '.join(char_conditions)})")
            
            if condition_info:
                result_lines.append(f"🎯 筛选条件: {'; '.join(condition_info)}")
        
        result_lines.append(f"📈 匹配统计: 共找到 {total_matches} 个符合条件的词汇")
        result_lines.append(f"📝 显示结果: 前 {len(results)} 个词汇")
        result_lines.append("")
        
        # 结果列表
        for i, word in enumerate(results, 1):
            result_lines.append(f"{i:2d}. {word} (筛选匹配)")
        
        return "\n".join(result_lines)
    
    def _compute_similarities(self, query_word: str, candidates: List[str], k: int) -> Tuple[List[str], List[float]]:
        """计算查询词与候选词的相似度（高效版）"""
        
        if not candidates:
            return [], []
        
        try:
            # 限制候选词数量以提高效率
            max_candidates = 1000  # 最大处理候选词数量
            if len(candidates) > max_candidates:
                print(f"📊 候选词过多 ({len(candidates)}个)，限制为前{max_candidates}个")
                candidates = candidates[:max_candidates]
            
            # 如果候选词较多，分批处理
            max_batch_candidates = 300  # 每批最大候选词数量
            
            if len(candidates) > max_batch_candidates:
                print(f"📊 分批处理 {len(candidates)} 个候选词...")
                
                all_similarities = []
                batch_size = max_batch_candidates
                
                for i in range(0, len(candidates), batch_size):
                    batch_candidates = candidates[i:i + batch_size]
                    print(f"🔄 处理批次 {i//batch_size + 1}/{(len(candidates) + batch_size - 1) // batch_size}")
                    
                    batch_similarities = self._compute_batch_similarities(query_word, batch_candidates)
                    all_similarities.extend(batch_similarities)
                
                # 按相似度排序，取top-k
                all_similarities.sort(key=lambda x: x[1], reverse=True)
                top_k = all_similarities[:k]
                
                synonyms = [pair[0] for pair in top_k]
                sim_scores = [pair[1] for pair in top_k]
                
                return synonyms, sim_scores
            else:
                # 候选词较少，直接处理
                print(f"🧠 直接计算 {len(candidates)} 个候选词的相似度")
                return self._compute_batch_similarities_with_topk(query_word, candidates, k)
            
        except Exception as e:
            print(f"❌ 相似度计算失败: {e}")
            return [], []
    
    def _compute_batch_similarities(self, query_word: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """计算一批候选词的相似度（优化版）"""
        try:
            # 限制单次编码的最大数量（Qwen API限制）
            max_batch_size = 30  # 查询词 + 候选词总数不超过32
            
            if len(candidates) > max_batch_size - 1:
                # 候选词太多，分批处理
                return self._compute_batch_similarities_fallback(query_word, candidates)
            
            # 准备编码词汇列表（查询词 + 候选词）
            words_to_encode = [query_word] + candidates
            
            # 批量编码
            embeddings = self.qwen_client.encode(words_to_encode)
            
            if embeddings is None or len(embeddings) != len(words_to_encode):
                raise Exception("编码失败或数量不匹配")
            
            # 分离查询词和候选词的向量
            query_embedding = embeddings[0]
            candidate_embeddings = embeddings[1:]
            
            # 计算相似度
            similarities = []
            for i, candidate in enumerate(candidates):
                if i < len(candidate_embeddings):
                    candidate_embedding = candidate_embeddings[i]
                    # 计算余弦相似度
                    similarity = np.dot(query_embedding, candidate_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
                    )
                    similarities.append((candidate, float(similarity)))
            
            return similarities
            
        except Exception as e:
            print(f"❌ 批次相似度计算失败: {e}")
            # 降级处理：使用分批方法
            return self._compute_batch_similarities_fallback(query_word, candidates)
    
    def _compute_batch_similarities_fallback(self, query_word: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """备用的批次相似度计算方法"""
        # 准备编码词汇列表（查询词 + 候选词）
        words_to_encode = [query_word] + candidates
        
        # 分批编码以避免超过API限制
        batch_size = 20
        all_embeddings = []
        
        for i in range(0, len(words_to_encode), batch_size):
            batch = words_to_encode[i:i + batch_size]
            batch_embeddings = self.qwen_client.encode(batch)
            
            if batch_embeddings is None:
                print(f"❌ 批次编码失败")
                continue
            
            all_embeddings.extend(batch_embeddings)
        
        if len(all_embeddings) != len(words_to_encode):
            print(f"⚠️ 编码数量不匹配: {len(all_embeddings)} vs {len(words_to_encode)}")
            return []
        
        # 计算相似度
        query_embedding = all_embeddings[0]
        candidate_embeddings = all_embeddings[1:]
        
        similarities = []
        for i, candidate in enumerate(candidates):
            if i < len(candidate_embeddings):
                candidate_embedding = candidate_embeddings[i]
                # 计算余弦相似度
                similarity = np.dot(query_embedding, candidate_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
                )
                similarities.append((candidate, float(similarity)))
        
        return similarities
    
    def _compute_batch_similarities_with_topk(self, query_word: str, candidates: List[str], k: int) -> Tuple[List[str], List[float]]:
        """计算候选词相似度并直接返回top-k结果（避免递归调用）"""
        
        # 直接使用fallback方法，避免递归调用
        similarities = self._compute_batch_similarities_fallback(query_word, candidates)
        
        if not similarities:
            return [], []
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 返回top-k结果
        top_k = similarities[:k]
        synonyms = [pair[0] for pair in top_k]
        sim_scores = [pair[1] for pair in top_k]
        
        return synonyms, sim_scores
    
    def _build_unified_result_message(self, query_word: str, synonyms: List[str], similarities: List[float], 
                                    character_finals: Optional[List[str]], character_filters: Optional[List[Dict[str, Any]]], 
                                    sorted: bool = True, min_length: Optional[int] = None, max_length: Optional[int] = None) -> str:
        """构建统一的结果消息（支持简单和高级筛选）"""
        
        if not synonyms:
            return "❌ 未找到相似词汇"
        
        # 判断是否有查询词
        has_query_word = bool(query_word and query_word.strip())
        
        # 构建结果展示
        result_lines = []
        
        if has_query_word:
            result_lines.append(f"🔍 查询词汇: {query_word}")
        else:
            result_lines.append(f"🔍 纯筛选模式（无查询词）")
        
        if sorted and has_query_word:
            result_lines.append(f"📊 数据来源: Qwen3-Embedding-0.6B (1024维向量)")
            result_lines.append(f"⚡ 算法: 二分查找筛选 + 语义相似度排序")
        else:
            result_lines.append(f"📊 数据来源: 预处理词库索引")
            result_lines.append(f"⚡ 算法: 二分查找筛选（未排序）")
        
        # 筛选条件信息（统一格式）
        if character_filters:
            # 高级筛选模式
            filters_info = []
            for i, char_filter in enumerate(character_filters):
                if char_filter:
                    filter_parts = []
                    if char_filter.get('initial'):
                        filter_parts.append(f"声母={char_filter['initial']}")
                    if char_filter.get('final'):
                        filter_parts.append(f"韵母={char_filter['final']}")
                    if char_filter.get('tone'):
                        filter_parts.append(f"声调={char_filter['tone']}")
                    if char_filter.get('stroke_count'):
                        filter_parts.append(f"笔画={char_filter['stroke_count']}")
                    if char_filter.get('radical'):
                        filter_parts.append(f"部首={char_filter['radical']}")
                    if char_filter.get('contains_stroke'):
                        if char_filter.get('stroke_position'):
                            filter_parts.append(f"第{char_filter['stroke_position']}笔={char_filter['contains_stroke']}")
                        else:
                            filter_parts.append(f"含笔画={char_filter['contains_stroke']}")
                    
                    if filter_parts:
                        filters_info.append(f"第{i+1}字({', '.join(filter_parts)})")
            
            if filters_info:
                result_lines.append(f"🎯 高级筛选: {', '.join(filters_info)}")
        
        elif character_finals and any(f for f in character_finals):
            # 简单韵母筛选模式
            finals_info = []
            for i, final in enumerate(character_finals):
                if final:
                    finals_info.append(f"第{i+1}字='{final}'")
            if finals_info:
                result_lines.append(f"🎵 韵母筛选: {', '.join(finals_info)}")
        
        # 长度筛选信息
        if min_length is not None or max_length is not None:
            length_info = []
            if min_length is not None:
                length_info.append(f"最小长度={min_length}")
            if max_length is not None:
                length_info.append(f"最大长度={max_length}")
            result_lines.append(f"📏 长度筛选: {', '.join(length_info)}")
        
        if sorted and has_query_word:
            result_lines.append(f"📝 找到 {len(synonyms)} 个近义词（按相似度排序）:")
        else:
            result_lines.append(f"📝 找到 {len(synonyms)} 个匹配词（筛选结果）:")
        
        result_lines.append("")
        
        # 词汇列表
        for i, (synonym, similarity) in enumerate(zip(synonyms, similarities), 1):
            if sorted and has_query_word and similarity > 0:
                percentage = similarity * 100
                result_lines.append(f"{i:2d}. {synonym} ({percentage:.1f}%)")
            else:
                result_lines.append(f"{i:2d}. {synonym}")
        
        return "\n".join(result_lines)
    
    def _build_advanced_result_message(self, query_word: str, synonyms: List[str], similarities: List[float], character_filters: Optional[List[Dict[str, Any]]]) -> str:
        """构建高级搜索结果消息"""
        
        if not synonyms:
            return "❌ 未找到符合条件的相似词汇"
        
        # 构建结果展示
        result_lines = [f"🔍 查询词汇: {query_word}"]
        result_lines.append(f"📊 数据来源: Qwen3-Embedding-0.6B (1024维向量)")
        result_lines.append(f"🎯 算法: 语义相似度 + 高级汉字筛选")
        
        # 检查是否进行了语义排序
        semantic_count = sum(1 for s in similarities if s > 0)
        candidate_count = len(similarities) - semantic_count
        
        if semantic_count > 0 and candidate_count > 0:
            result_lines.append(f"📈 结果类型: {semantic_count}个语义排序词 + {candidate_count}个候选词")
        elif semantic_count > 0:
            result_lines.append(f"📈 结果类型: {semantic_count}个语义排序的同义词")
        elif candidate_count > 0:
            result_lines.append(f"📈 结果类型: {candidate_count}个候选词（未进行语义排序）")
        
        # 筛选条件信息
        if character_filters:
            condition_info = []
            for i, filters in enumerate(character_filters):
                if not filters:
                    continue
                
                char_conditions = []
                if filters.get('initial'):
                    char_conditions.append(f"声母={filters['initial']}")
                if filters.get('final'):
                    char_conditions.append(f"韵母={filters['final']}")
                if filters.get('tone'):
                    char_conditions.append(f"声调={filters['tone']}")
                if filters.get('stroke_count'):
                    char_conditions.append(f"笔画={filters['stroke_count']}")
                if filters.get('radical'):
                    char_conditions.append(f"部首={filters['radical']}")
                if filters.get('contains_stroke'):
                    if filters.get('stroke_position'):
                        char_conditions.append(f"第{filters['stroke_position']}笔={filters['contains_stroke']}")
                    else:
                        char_conditions.append(f"含笔画={filters['contains_stroke']}")
                
                if char_conditions:
                    condition_info.append(f"第{i+1}字({', '.join(char_conditions)})")
            
            if condition_info:
                result_lines.append(f"🎯 筛选条件: {'; '.join(condition_info)}")
        
        result_lines.append(f"📝 找到 {len(synonyms)} 个符合条件的近义词:")
        result_lines.append("")
        
        # 近义词列表
        for i, (synonym, similarity) in enumerate(zip(synonyms, similarities), 1):
            if similarity > 0:
                # 有语义相似度分数
                percentage = similarity * 100
                result_lines.append(f"{i:2d}. {synonym} ({percentage:.1f}%)")
            else:
                # 候选词（无语义分数）
                result_lines.append(f"{i:2d}. {synonym} (候选词)")
        
        return "\n".join(result_lines)

class QwenSynonymSearcherV2:
    """兼容性包装器 - 使用V3实现"""
    
    def __init__(self, qwen_client=None):
        self.searcher_v3 = QwenSynonymSearcherV3(qwen_client)
        self.qwen_available = self.searcher_v3.qwen_available
    
    def search_synonyms(self, word: str, k: int = 10, character_finals: Optional[List[str]] = None) -> Tuple[List[str], List[float], str]:
        return self.searcher_v3.search_synonyms(word, k, character_finals)

# 处理函数
def process_qwen_synonym_search_v3(word: str, k: int, char1_final: str, char2_final: str, char3_final: str, char4_final: str) -> str:
    """处理Qwen同义词查询V3"""
    try:
        searcher = QwenSynonymSearcherV3()
        
        # 构建韵母筛选条件
        character_finals = [char1_final, char2_final, char3_final, char4_final]
        # 移除末尾的空字符串
        while character_finals and not character_finals[-1]:
            character_finals.pop()
        
        synonyms, similarities, result_msg = searcher.search_synonyms(word, k, character_finals)
        return result_msg
        
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


def process_qwen_synonym_search_advanced(
    word: str, 
    k: int,
    char1_conditions: Dict[str, Any] = None,
    char2_conditions: Dict[str, Any] = None,
    char3_conditions: Dict[str, Any] = None,
    char4_conditions: Dict[str, Any] = None
) -> str:
    """处理Qwen高级同义词查询"""
    try:
        searcher = QwenSynonymSearcherV3()
        
        # 构建筛选条件
        character_filters = []
        for conditions in [char1_conditions, char2_conditions, char3_conditions, char4_conditions]:
            if conditions:
                # 过滤掉空值
                filtered_conditions = {k: v for k, v in conditions.items() if v}
                character_filters.append(filtered_conditions)
            else:
                character_filters.append({})
        
        # 移除末尾的空条件
        while character_filters and not character_filters[-1]:
            character_filters.pop()
        
        synonyms, similarities, result_msg = searcher.search_synonyms_advanced(word, k, character_filters)
        return result_msg
        
    except Exception as e:
        return f"❌ 高级查询失败: {str(e)}"


def get_available_search_options() -> Dict[str, List[str]]:
    """获取可用的搜索选项"""
    try:
        return {
            'initials': get_available_initials(),     # 声母
            'finals': get_available_finals(),         # 韵母
            'tones': get_available_tones(),           # 声调
            'strokes': get_available_strokes(),       # 笔画
            'radicals': get_available_radicals()      # 部首
        }
    except Exception as e:
        print(f"获取搜索选项失败: {e}")
        return {}

if __name__ == "__main__":
    # 测试
    searcher = QwenSynonymSearcherV3()
    result = searcher.search_synonyms("高兴", 5, ["ao", ""])
    print(result[2])
