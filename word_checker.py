#!/usr/bin/env python3
"""
单词查询工具
功能：通配符匹配、模糊匹配（汉明距离）、子串匹配
"""

import os
import time
from typing import List, Tuple, Set, Dict
from collections import defaultdict

class WordChecker:
    """单词检查器"""
    
    def __init__(self, dict_file=None):
        """初始化单词检查器"""
        if dict_file is None:
            # 自动寻找词典文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dict_file = os.path.join(current_dir, "dict_large.txt")
        
        self.dict_file = dict_file
        self.word_set = set()
        self.word_list = []
        # 分层索引：基于前N个字符的索引
        self.prefix_index = defaultdict(list)  # 前2字符索引
        self.suffix_index = defaultdict(list)  # 后2字符索引
        self.char_index = defaultdict(set)     # 单字符索引
        self.load_dictionary()
        
        # 时间阈值设置 (秒)
        self.TIME_LIMIT = 60  # 60秒时间限制（1分钟）
        self.start_time = None
    
    def load_dictionary(self) -> None:
        """加载词典文件并构建索引"""
        if not os.path.exists(self.dict_file):
            print(f"❌ 词典文件不存在: {self.dict_file}")
            return
        
        try:
            with open(self.dict_file, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    if word and word.isalpha():
                        self.word_set.add(word)
                        self.word_list.append(word)
                        self._build_indexes(word)
            
            print(f"✅ 词典加载成功: {len(self.word_set)} 个单词")
            print(f"🔧 索引构建完成: 前缀索引 {len(self.prefix_index)} 项, "
                  f"后缀索引 {len(self.suffix_index)} 项, "
                  f"字符索引 {len(self.char_index)} 项")
            
        except Exception as e:
            print(f"❌ 加载词典失败: {e}")
    
    def _build_indexes(self, word: str) -> None:
        """为单词构建多层索引"""
        word_len = len(word)
        
        # 前缀索引 (前2字符)
        if word_len >= 2:
            prefix = word[:2]
            self.prefix_index[prefix].append(word)
        
        # 后缀索引 (后2字符)
        if word_len >= 2:
            suffix = word[-2:]
            self.suffix_index[suffix].append(word)
        
        # 字符索引 (每个字符)
        for char in set(word):  # 使用set避免重复字符
            self.char_index[char].add(word)
    
    def wildcard_match(self, pattern: str, max_results: int = 300) -> List[str]:
        """通配符匹配：A作为通配符，可以匹配任意小写字母"""
        if not pattern:
            return []
        
        # 开始计时
        self.start_time = time.time()
        
        pattern = pattern.lower()
        matching_words = []
        
        for word in self.word_list:
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                print(f"⚠️ 通配符匹配超时 ({self.TIME_LIMIT}秒)，已找到 {len(matching_words)} 个结果")
                break
                
            if len(word) == len(pattern):
                # 检查是否匹配（A可以匹配任意字母）
                match = True
                for i, (p_char, w_char) in enumerate(zip(pattern, word)):
                    if p_char != 'a' and p_char != w_char:  # A是通配符
                        match = False
                        break
                
                if match:
                    matching_words.append(word)
                    if len(matching_words) >= max_results:
                        break
        
        return matching_words
    
    def hamming_distance(self, s1: str, s2: str) -> int:
        """计算两个等长字符串的汉明距离"""
        if len(s1) != len(s2):
            return float('inf')
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))
    
    def fuzzy_match(self, target: str, k: int = 50, max_distance: int = 3) -> List[Tuple[str, int]]:
        """模糊匹配：找到汉明距离小的前k个字符串"""
        if not target:
            return []
        
        # 开始计时
        self.start_time = time.time()
        
        target = target.lower()
        target_len = len(target)
        
        # 找到所有相同长度的单词及其汉明距离
        candidates = []
        for word in self.word_list:
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                print(f"⚠️ 模糊匹配超时 ({self.TIME_LIMIT}秒)，已找到 {len(candidates)} 个结果")
                break
                
            if len(word) == target_len:
                distance = self.hamming_distance(target, word)
                if distance <= max_distance:
                    candidates.append((word, distance))
        
        # 按汉明距离排序，取前k个
        candidates.sort(key=lambda x: x[1])
        return candidates[:k]
    
    def substring_match(self, substring: str, max_results: int = 300) -> List[str]:
        """子串匹配：找到所有包含指定子串的单词 (智能优化版本)"""
        if not substring:
            return []
        
        # 开始计时
        self.start_time = time.time()
        
        substring = substring.lower()
        sub_len = len(substring)
        
        # 策略选择：只对长子串和大量结果需求进行复杂优化
        if sub_len >= 5 and max_results >= 100:
            # 长子串：使用字符预筛选
            return self._hybrid_search(substring, max_results)
        else:
            # 短子串：直接线性搜索（避免优化开销）
            return self._linear_search(substring, max_results)
    
    def _linear_search(self, substring: str, max_results: int) -> List[str]:
        """线性搜索：原始的直接扫描方法"""
        matching_words = []
        for word in self.word_list:
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                print(f"⚠️ 子串匹配超时 ({self.TIME_LIMIT}秒)，已找到 {len(matching_words)} 个结果")
                break
                
            if substring in word:
                matching_words.append(word)
                if len(matching_words) >= max_results:
                    break
        return matching_words
    
    def _hybrid_search(self, substring: str, max_results: int) -> List[str]:
        """混合搜索：预筛选 + 验证（优化版）"""
        substring_chars = set(substring)
        
        # 找到最稀有的字符来缩小搜索范围
        char_counts = [(char, len(self.char_index.get(char, set()))) 
                      for char in substring_chars]
        char_counts.sort(key=lambda x: x[1])  # 按词汇数量排序
        
        if not char_counts:
            return []
        
        # 使用最稀有字符的词汇集合作为候选
        rarest_char = char_counts[0][0]
        candidates = self.char_index.get(rarest_char, set())
        
        # 验证候选词汇
        matching_words = []
        for word in candidates:
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                print(f"⚠️ 子串匹配超时 ({self.TIME_LIMIT}秒)，已找到 {len(matching_words)} 个结果")
                break
                
            if substring in word:
                matching_words.append(word)
                if len(matching_words) >= max_results:
                    break
        
        return matching_words


def process_word_query(query_text: str, query_type: str = "wildcard", k: int = 50, time_limit=None) -> str:
    """处理单词查询请求"""
    checker = WordChecker()
    
    # 设置时间限制
    if time_limit is not None:
        try:
            # 验证时间限制是否为有效的正整数
            time_limit_value = int(time_limit)
            if time_limit_value > 0:
                checker.TIME_LIMIT = time_limit_value
            else:
                checker.TIME_LIMIT = 60  # 默认60秒
        except (ValueError, TypeError):
            checker.TIME_LIMIT = 60  # 默认60秒
    else:
        checker.TIME_LIMIT = 60  # 默认60秒
    
    if not checker.word_set:
        return "❌ 词典未加载成功，无法进行查询"
    
    if not query_text.strip():
        return "❌ 请输入要查询的内容"
    
    lines = [line.strip() for line in query_text.split('\n') if line.strip()]
    results = []
    
    if query_type == "wildcard":
        # 通配符匹配
        results.append("🔍 通配符匹配查询结果 (A作为通配符):\n")
        
        for pattern in lines[:5]:  # 限制查询数量
            matches = checker.wildcard_match(pattern, 300)
            if matches:
                results.append(f"📝 匹配模式 '{pattern}' 的单词 ({len(matches)} 个):")
                results.append(f"   {', '.join(matches)}")  # 显示所有结果
            else:
                results.append(f"❌ 未找到匹配模式 '{pattern}' 的单词")
            results.append("")
    
    elif query_type == "fuzzy":
        # 模糊匹配（汉明距离）
        results.append(f"🔍 模糊匹配查询结果 (汉明距离，k={k}):\n")
        
        for target in lines[:5]:  # 限制查询数量
            matches = checker.fuzzy_match(target, k, 3)
            if matches:
                results.append(f"📝 与 '{target}' 相似的单词:")
                for word, distance in matches:
                    results.append(f"   {word} (距离: {distance})")
            else:
                results.append(f"❌ 未找到与 '{target}' 相似的单词")
            results.append("")
    
    elif query_type == "substring":
        # 子串匹配
        results.append("🔍 子串匹配查询结果:\n")
        
        for substring in lines[:5]:  # 限制查询数量
            matches = checker.substring_match(substring, 300)
            if matches:
                results.append(f"📝 包含子串 '{substring}' 的单词 ({len(matches)} 个):")
                results.append(f"   {', '.join(matches)}")  # 显示所有结果
            else:
                results.append(f"❌ 未找到包含子串 '{substring}' 的单词")
            results.append("")
    
    return '\n'.join(results)


def main():
    """主函数 - 命令行测试"""
    print("🔍 单词查询工具")
    print("=" * 50)
    
    checker = WordChecker()
    
    if not checker.word_set:
        print("❌ 无法加载词典，程序退出")
        return
    
    print(f"📊 词典统计: {len(checker.word_set):,} 个单词\n")
    
    # 交互式查询
    while True:
        print("请选择查询类型:")
        print("1. 通配符匹配 (A作为通配符，如: hAllo)")
        print("2. 模糊匹配 (汉明距离，如: hello)")
        print("3. 子串匹配 (查找包含子串的单词，如: ell)")
        print("4. 退出")
        
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '4':
            print("👋 再见!")
            break
        
        if choice not in ['1', '2', '3']:
            print("❌ 无效选择，请重试")
            continue
        
        query = input("请输入查询内容: ").strip()
        if not query:
            print("❌ 查询内容不能为空")
            continue
        
        k = 50
        if choice == '2':
            k_input = input(f"请输入返回结果数量k (默认{k}): ").strip()
            if k_input.isdigit():
                k = int(k_input)
        
        query_types = {'1': 'wildcard', '2': 'fuzzy', '3': 'substring'}
        result = process_word_query(query, query_types[choice], k)
        
        print("\n" + "="*60)
        print(result)
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
