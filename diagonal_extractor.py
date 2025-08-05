# 对角线提取工具（修正版）
# 功能：给定若干字符串(feeders)和索引(indices)，枚举所有可能的对应关系，
# 提取每个字符串在对应索引位置的字符，组成新字符串，检查是否在词典中

import itertools
import os
import time
from typing import List, Tuple, Set, Dict


class DiagonalExtractor:
    def __init__(self, dict_file=None):
        self.dictionary_list = self.load_dictionary_ordered(dict_file)
        self.dictionary = set(self.dictionary_list)  # 为兼容性保留set版本
        self.feeders = []
        self.indices = []
        
        # 时间阈值设置 (秒)
        self.TIME_LIMIT = 60  # 60秒时间限制（1分钟）
        self.start_time = None
    
    def load_dictionary_ordered(self, dict_file: str = None) -> List[str]:
        """加载词典文件，保持顺序（按频率排序）"""
        if dict_file is None:
            # 自动寻找词典文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dict_file = os.path.join(current_dir, "dict_large.txt")
        
        dictionary = []
        if os.path.exists(dict_file):
            try:
                with open(dict_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if word:
                            dictionary.append(word)
                print(f"对角线提取工具已加载词典文件: {dict_file}，共 {len(dictionary)} 个单词")
            except Exception as e:
                print(f"加载词典文件失败: {e}")
        else:
            print(f"词典文件 {dict_file} 不存在")
        return dictionary
    
    def extract_diagonal(self, feeders: List[str], indices, allow_wildcards: bool = True, 
                        shuffle_feeders: bool = True, shuffle_indices: bool = True, 
                        zero_indexed: bool = False) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
        """
        对角线提取主函数（修正版）
        参数:
        - feeders: 字符串列表，可包含'A'表示未知字符
        - indices: 索引列表，可以是数字或'A'表示未知索引位置
        - allow_wildcards: 是否允许通配符'A'
        - shuffle_feeders: 是否shuffle feeders的顺序
        - shuffle_indices: 是否shuffle indices的顺序
        - zero_indexed: True=0-based索引, False=1-based索引（默认）
        返回: [(提取的字符串, [(feeder, index_str, extracted_char), ...]), ...]
        """
        # 开始计时
        self.start_time = time.time()
        
        if len(feeders) != len(indices):
            return []
        
        n = len(feeders)
        results = []
        seen_combinations = set()  # 防止重复结果
        
        # 根据参数决定是否需要排列
        if shuffle_feeders and shuffle_indices:
            # 两者都shuffle：标准的n!排列
            permutations = list(itertools.permutations(range(n)))
        elif shuffle_feeders and not shuffle_indices:
            # 只shuffle feeders：保持indices顺序，排列feeders
            permutations = list(itertools.permutations(range(n)))
            # 但使用排列后的feeder顺序对应原始的indices顺序
        elif not shuffle_feeders and shuffle_indices:
            # 只shuffle indices：保持feeders顺序，排列indices
            # 这相当于对indices进行排列，但保持feeders的顺序
            permutations = [(tuple(range(n)),)]  # 只有一种feeder排列
        else:
            # 两者都不shuffle：只有一种组合
            permutations = [(tuple(range(n)),)]
        
        # 处理不同的shuffle模式
        if shuffle_feeders and shuffle_indices:
            # 双shuffle模式：同时排列feeders和indices
            for feeders_perm in permutations:
                # 检查时间限制
                if time.time() - self.start_time > self.TIME_LIMIT:
                    print(f"⚠️ 对角线提取超时 ({self.TIME_LIMIT}秒)，已找到 {len(results)} 个结果")
                    break
                for indices_perm in permutations:
                    # 检查时间限制
                    if time.time() - self.start_time > self.TIME_LIMIT:
                        print(f"⚠️ 对角线提取超时 ({self.TIME_LIMIT}秒)，已找到 {len(results)} 个结果")
                        break
                    self._process_single_combination(feeders, indices, feeders_perm, indices_perm, 
                                                   results, seen_combinations, allow_wildcards, zero_indexed)
        elif not shuffle_feeders and shuffle_indices:
            # 只shuffle indices
            indices_permutations = list(itertools.permutations(range(n)))
            for indices_perm in indices_permutations:
                # 检查时间限制
                if time.time() - self.start_time > self.TIME_LIMIT:
                    print(f"⚠️ 对角线提取超时 ({self.TIME_LIMIT}秒)，已找到 {len(results)} 个结果")
                    break
                self._process_single_combination(feeders, indices, list(range(n)), indices_perm, 
                                               results, seen_combinations, allow_wildcards, zero_indexed)
        elif shuffle_feeders and not shuffle_indices:
            # 只shuffle feeders
            for feeders_perm in permutations:
                # 检查时间限制
                if time.time() - self.start_time > self.TIME_LIMIT:
                    print(f"⚠️ 对角线提取超时 ({self.TIME_LIMIT}秒)，已找到 {len(results)} 个结果")
                    break
                self._process_single_combination(feeders, indices, feeders_perm, list(range(n)), 
                                               results, seen_combinations, allow_wildcards, zero_indexed)
        else:
            # 两者都不shuffle：只有一种组合
            self._process_single_combination(feeders, indices, list(range(n)), list(range(n)), 
                                           results, seen_combinations, allow_wildcards, zero_indexed)
        
        # 按词典中的频率排序（保持词典原有顺序）
        def get_dict_priority(item):
            word = item[0]
            try:
                return self.dictionary_list.index(word)
            except ValueError:
                return len(self.dictionary_list)
        
        results.sort(key=get_dict_priority)
        return results
    
    def _process_single_combination(self, feeders: List[str], indices, feeder_perm, indices_perm, 
                                   results: List, seen_combinations: Set, allow_wildcards: bool, zero_indexed: bool = False) -> None:
        """处理单个feeder-index组合"""
        try:
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                return
                
            extracted_chars = []
            mapping = []
            has_wildcards = False
            
            for i in range(len(feeders)):
                feeder_idx = feeder_perm[i]
                index_idx = indices_perm[i]
                
                feeder = feeders[feeder_idx]
                index_input = indices[index_idx]
                
                # 处理索引中的'A'（索引通配符）
                if isinstance(index_input, str) and index_input.upper() == 'A':
                    if allow_wildcards:
                        # 索引通配符：尝试feeder的所有可能位置
                        extracted_chars.append('?index')  # 索引通配符占位符
                        mapping.append((feeder, 'A', '?index'))
                        has_wildcards = True
                    else:
                        return  # 不允许通配符时跳过
                else:
                    try:
                        index = int(index_input)
                        # 根据索引模式进行转换
                        if not zero_indexed:
                            index = index - 1  # 1-based转换为0-based
                        
                        # 检查索引是否在有效范围内
                        if 0 <= index < len(feeder):
                            char = feeder[index]
                            # 检查feeder中的字符通配符（只有大写A才是通配符）
                            if char == 'A':
                                # 字符通配符
                                extracted_chars.append('?char')  # 字符通配符占位符
                                mapping.append((feeder, str(int(index_input)), '?char'))
                                has_wildcards = True
                            else:
                                # 普通字符
                                extracted_chars.append(char)
                                mapping.append((feeder, str(int(index_input)), char))
                        else:
                            # 索引超出范围，跳过这个排列
                            return
                    except (ValueError, TypeError):
                        # 无效的索引输入，跳过
                        return
            
            # 所有字符都成功提取
            if has_wildcards:
                # 有通配符的情况，处理所有可能的替换
                self._handle_wildcards(extracted_chars, mapping, results, seen_combinations, feeders, zero_indexed)
            else:
                # 无通配符的情况
                extracted_string = ''.join(extracted_chars).lower()
                
                # 检查是否在词典中且未重复
                if extracted_string in self.dictionary:
                    combination_key = (extracted_string, tuple(sorted(mapping)))
                    if combination_key not in seen_combinations:
                        seen_combinations.add(combination_key)
                        results.append((extracted_string, mapping))
        
        except Exception as e:
            pass
    
    def _handle_wildcards(self, extracted_chars: List[str], mapping: List[Tuple[str, str, str]], 
                         results: List, seen_combinations: Set, feeders: List[str], zero_indexed: bool = False) -> None:
        """处理包含通配符的情况"""
        # 找到所有通配符位置
        char_wildcard_positions = [i for i, char in enumerate(extracted_chars) if char == '?char']
        index_wildcard_positions = [i for i, char in enumerate(extracted_chars) if char == '?index']
        
        if not char_wildcard_positions and not index_wildcard_positions:
            return
        
        # 优先处理索引通配符，再处理字符通配符
        if index_wildcard_positions:
            self._handle_index_wildcards(extracted_chars, mapping, results, seen_combinations, 
                                        feeders, index_wildcard_positions, zero_indexed)
        elif char_wildcard_positions:
            # 只有字符通配符的情况
            self._handle_char_wildcards(extracted_chars, mapping, results, seen_combinations, 
                                       char_wildcard_positions)
    
    def _handle_index_wildcards(self, extracted_chars: List[str], mapping: List[Tuple[str, str, str]],
                               results: List, seen_combinations: Set, feeders: List[str],
                               index_wildcard_positions: List[int], zero_indexed: bool = False) -> None:
        """处理索引通配符"""
        # 为每个索引通配符生成所有可能的索引值
        index_wildcards_info = []
        for pos in index_wildcard_positions:
            feeder, _, _ = mapping[pos]
            # 根据索引模式生成可能的索引
            if zero_indexed:
                # 0-based: 0到字符串长度-1
                possible_indices = list(range(0, len(feeder)))
            else:
                # 1-based: 1到字符串长度
                possible_indices = list(range(1, len(feeder) + 1))
            index_wildcards_info.append((pos, feeder, possible_indices))
        
        # 生成所有索引组合
        if index_wildcards_info:
            import itertools
            index_combinations = itertools.product(*[info[2] for info in index_wildcards_info])
            
            for index_combo in index_combinations:
                # 检查时间限制
                if time.time() - self.start_time > self.TIME_LIMIT:
                    return
                    
                test_chars = extracted_chars.copy()
                test_mapping = mapping.copy()
                
                # 替换索引通配符
                for i, (pos, feeder, _) in enumerate(index_wildcards_info):
                    new_index = index_combo[i]
                    # 根据索引模式转换为实际的数组索引
                    if zero_indexed:
                        actual_index = new_index  # 0-based直接使用
                    else:
                        actual_index = new_index - 1  # 1-based需要减1转换为0-based
                    
                    char_at_index = feeder[actual_index]
                    
                    # 检查该位置的字符是否是字符通配符（只有大写A才是通配符）
                    if char_at_index == 'A':
                        # 索引通配符指向了字符通配符，需要进一步处理
                        test_chars[pos] = '?char'
                        test_mapping[pos] = (feeder, f"A→{new_index}", '?char')
                    else:
                        # 索引通配符指向了普通字符，直接使用
                        test_chars[pos] = char_at_index
                        test_mapping[pos] = (feeder, f"A→{new_index}", char_at_index)
                
                # 检查是否还有字符通配符需要处理
                remaining_char_wildcards = [i for i, char in enumerate(test_chars) if char == '?char']
                if remaining_char_wildcards:
                    # 继续处理字符通配符
                    self._handle_char_wildcards(test_chars, test_mapping, results, seen_combinations,
                                               remaining_char_wildcards)
                else:
                    # 没有剩余的字符通配符，检查结果
                    test_string = ''.join(test_chars).lower()
                    if test_string in self.dictionary:
                        combination_key = (test_string, tuple(sorted(test_mapping)))
                        if combination_key not in seen_combinations:
                            seen_combinations.add(combination_key)
                            results.append((test_string, test_mapping))
    
    def _handle_char_wildcards(self, extracted_chars: List[str], mapping: List[Tuple[str, str, str]],
                              results: List, seen_combinations: Set, char_wildcard_positions: List[int]) -> None:
        """处理字符通配符"""
        import string
        import itertools
        letters = string.ascii_lowercase
        
        # 为每个字符通配符尝试所有字母
        for combo in itertools.product(letters, repeat=len(char_wildcard_positions)):
            # 检查时间限制
            if time.time() - self.start_time > self.TIME_LIMIT:
                return
                
            test_chars = extracted_chars.copy()
            test_mapping = mapping.copy()
            
            # 替换字符通配符
            for i, letter in enumerate(combo):
                pos = char_wildcard_positions[i]
                test_chars[pos] = letter
                # 更新映射中的字符信息
                feeder, index_str, _ = test_mapping[pos]
                # 如果index_str包含索引推导，在后面添加字符推导
                if '→' in index_str:
                    test_mapping[pos] = (feeder, index_str + f"[A→{letter}]", letter)
                else:
                    # 纯字符通配符
                    test_mapping[pos] = (feeder, index_str + f"[A→{letter}]", letter)
            
            test_string = ''.join(test_chars).lower()
            
            # 检查是否在词典中且未重复
            if test_string in self.dictionary:
                combination_key = (test_string, tuple(sorted(test_mapping)))
                if combination_key not in seen_combinations:
                    seen_combinations.add(combination_key)
                    results.append((test_string, test_mapping))


def process_extraction(feeders_text, indices_text, shuffle_feeders=True, shuffle_indices=True, zero_indexed=False, time_limit=None):
    """处理提取请求（修正版，支持两种'A'通配符、shuffle控制和索引模式）"""
    # 创建全局提取器实例
    extractor = DiagonalExtractor()
    
    # 设置时间限制
    if time_limit is not None:
        try:
            # 验证时间限制是否为有效的正整数
            time_limit_value = int(time_limit)
            if time_limit_value > 0:
                extractor.TIME_LIMIT = time_limit_value
            else:
                extractor.TIME_LIMIT = 60  # 默认60秒
        except (ValueError, TypeError):
            extractor.TIME_LIMIT = 60  # 默认60秒
    else:
        extractor.TIME_LIMIT = 60  # 默认60秒
    
    try:
        # 解析输入
        feeders = [line.strip() for line in feeders_text.split('\n') if line.strip()]
        indices_lines = [line.strip() for line in indices_text.split('\n') if line.strip()]
        indices = []
        
        for line in indices_lines:
            line = line.strip()
            if line.upper() == 'A':
                indices.append('A')  # 保持'A'作为字符串（索引通配符）
            else:
                try:
                    indices.append(int(line))
                except ValueError:
                    return f"错误: '{line}' 不是有效的整数索引或'A'"
        
        if len(feeders) != len(indices):
            return f"错误: feeders数量({len(feeders)})与indices数量({len(indices)})不匹配"
        
        if not feeders:
            return "请输入至少一个feeder和对应的index"
        
        # 检查是否有通配符
        has_index_wildcards = any(isinstance(idx, str) and idx.upper() == 'A' for idx in indices)
        has_char_wildcards = any('A' in feeder for feeder in feeders)
        
        # 执行对角线提取
        results = extractor.extract_diagonal(feeders, indices, allow_wildcards=True, 
                                           shuffle_feeders=shuffle_feeders, shuffle_indices=shuffle_indices,
                                           zero_indexed=zero_indexed)
        
        if not results:
            wildcard_info = ""
            if has_index_wildcards and has_char_wildcards:
                wildcard_info = "（注意：使用了索引通配符和字符通配符）"
            elif has_index_wildcards:
                wildcard_info = "（注意：使用了索引通配符'A'，会尝试所有可能的位置）"
            elif has_char_wildcards:
                wildcard_info = "（注意：feeder中包含字符通配符'A'，会尝试所有可能的字母）"
            
            return f"未找到匹配的词典单词{wildcard_info}"
        
        # 格式化输出
        output_lines = []
        
        # 添加shuffle模式信息
        shuffle_info = ""
        if shuffle_feeders and shuffle_indices:
            shuffle_info = " (shuffle: feeders & indices)"
        elif shuffle_feeders and not shuffle_indices:
            shuffle_info = " (shuffle: feeders only)"
        elif not shuffle_feeders and shuffle_indices:
            shuffle_info = " (shuffle: indices only)"
        else:
            shuffle_info = " (no shuffle)"
        
        # 添加索引模式信息
        index_mode = " (0-indexed)" if zero_indexed else " (1-indexed)"
        
        wildcard_info = ""
        if has_index_wildcards and has_char_wildcards:
            wildcard_info = " (包含索引和字符通配符推导)"
        elif has_index_wildcards:
            wildcard_info = " (包含索引通配符推导)"
        elif has_char_wildcards:
            wildcard_info = " (包含字符通配符推导)"
        
        output_lines.append(f"找到 {len(results)} 个匹配的单词{shuffle_info}{index_mode}{wildcard_info}:\n")
        
        for i, (word, mapping) in enumerate(results, 1):
            output_lines.append(f"{i}. 单词: '{word}'")
            output_lines.append("   提取路径:")
            for feeder, index_info, char in mapping:
                if '→' in index_info and '[A→' in index_info:
                    # 同时有索引和字符通配符
                    output_lines.append(f"     '{feeder}'[{index_info}] → '{char}'")
                elif '→' in index_info:
                    # 索引通配符推导
                    output_lines.append(f"     '{feeder}'[{index_info}] → '{char}' (索引推导)")
                elif '[A→' in index_info:
                    # 字符通配符推导
                    output_lines.append(f"     '{feeder}'[{index_info}] → '{char}' (字符推导)")
                else:
                    # 正常情况
                    output_lines.append(f"     '{feeder}'[{index_info}] → '{char}'")
            output_lines.append("")
        
        # 添加使用提示
        if (has_index_wildcards or has_char_wildcards) and len(results) > 10:
            output_lines.append("提示: 使用通配符产生了较多结果，结果已按词典频率排序。")
        
        return '\n'.join(output_lines)
        
    except Exception as e:
        return f"处理过程中发生错误: {str(e)}"
