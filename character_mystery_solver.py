#!/usr/bin/env python3
"""
字谜推理器 - 根据已知能组词的字来推测未知字
"""

import json
import os
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple

class CharacterWordAnalyzer:
    """字谜推理分析器"""
    
    def __init__(self):
        self.char_words_dict = {}  # 字典：字 -> 包含该字的所有词汇列表
        self.word_chars_dict = {}  # 字典：词汇 -> 包含的字符列表  
        self.is_loaded = False
        
    def load_data(self):
        """加载ci.json数据并预处理"""
        if self.is_loaded:
            return
            
        print("🔄 加载字词关系数据...")
        
        # 尝试加载ci.json
        ci_path = os.path.join(os.path.dirname(__file__), "ci.json")
        if not os.path.exists(ci_path):
            print(f"❌ 找不到ci.json文件: {ci_path}")
            return
            
        try:
            with open(ci_path, 'r', encoding='utf-8') as f:
                ci_data = json.load(f)
            
            print(f"📖 加载了 {len(ci_data)} 个词条")
            
            # 预处理数据
            self.char_words_dict = defaultdict(set)
            self.word_chars_dict = {}
            
            for item in ci_data:
                word = item.get('ci', '').strip()
                if not word or len(word) < 2:  # 过滤单字和空词
                    continue
                    
                # 清理词汇（去掉标点和注释）
                cleaned_word = self._clean_word(word)
                if not cleaned_word or len(cleaned_word) < 2:
                    continue
                
                # 存储词汇包含的字符
                chars_in_word = list(cleaned_word)
                self.word_chars_dict[cleaned_word] = chars_in_word
                
                # 为每个字符记录包含它的词汇
                for char in chars_in_word:
                    if self._is_chinese_char(char):
                        self.char_words_dict[char].add(cleaned_word)
            
            # 转换为普通字典（便于使用）
            self.char_words_dict = {char: list(words) for char, words in self.char_words_dict.items()}
            
            print(f"✅ 处理完成：{len(self.char_words_dict)} 个字符，{len(self.word_chars_dict)} 个词汇")
            self.is_loaded = True
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            
    def _clean_word(self, word: str) -> str:
        """清理词汇，去掉标点和注释"""
        # 移除常见的标点和注释符号
        import re
        # 去掉括号内容
        word = re.sub(r'[（(].*?[）)]', '', word)
        # 去掉其他标点
        word = re.sub(r'[，。、；：！？""''『』「」〔〕【】《》〈〉]', '', word)
        return word.strip()
    
    def _is_chinese_char(self, char: str) -> bool:
        """判断是否为中文字符"""
        return '\u4e00' <= char <= '\u9fff'
    
    def analyze_character_clues(self, clue_chars: List[str], clue_positions: List[int] = None) -> List[Tuple[str, int, List[str]]]:
        """
        根据线索字符分析可能的目标字符
        
        Args:
            clue_chars: 线索字符列表，表示"这些字可以与目标字组成词语"
            clue_positions: 线索字符的位置要求列表，0表示任意位置，其他数字表示必须在指定位置(1-based)
            
        Returns:
            List[Tuple[str, int, List[str]]]: (候选字符, 匹配数量, 示例词汇列表)
        """
        if not self.is_loaded:
            self.load_data()

        if not self.is_loaded:
            return []

        # 如果没有提供位置信息，默认都是任意位置
        if clue_positions is None:
            clue_positions = [0] * len(clue_chars)
        
        # 确保线索字符和位置列表长度一致
        if len(clue_chars) != len(clue_positions):
            print("❌ 线索字符和位置列表长度不一致")
            return []

        # 过滤有效的线索字符
        valid_clues = []
        valid_positions = []
        for char, pos in zip(clue_chars, clue_positions):
            if char in self.char_words_dict:
                valid_clues.append(char)
                valid_positions.append(pos)

        if not valid_clues:
            return []

        print(f"🔍 分析线索字符: {[(char, pos) for char, pos in zip(valid_clues, valid_positions)]}")

        # 统计每个字符与线索字符的共现次数
        candidate_counter = Counter()
        candidate_examples = defaultdict(set)  # 存储示例词汇

        # 对每个线索字符分别分析
        for clue_char, required_position in zip(valid_clues, valid_positions):
            words_with_clue = self.char_words_dict.get(clue_char, [])
            print(f"   字符 '{clue_char}' (位置要求: {'任意' if required_position == 0 else required_position}) 出现在 {len(words_with_clue)} 个词汇中")
            
            # 筛选符合位置要求的词汇
            valid_words = []
            for word in words_with_clue:
                chars_in_word = self.word_chars_dict.get(word, [])
                if required_position == 0:
                    # 任意位置都可以
                    valid_words.append(word)
                else:
                    # 检查线索字符是否在指定位置
                    if (required_position <= len(chars_in_word) and 
                        chars_in_word[required_position - 1] == clue_char):
                        valid_words.append(word)
            
            print(f"      符合位置要求的词汇: {len(valid_words)} 个")
            
            # 从符合条件的词汇中提取所有字符并去重
            chars_from_this_clue = set()
            for word in valid_words:
                chars_in_word = self.word_chars_dict.get(word, [])
                chars_from_this_clue.update(chars_in_word)
                # 记录示例词汇
                for char in chars_in_word:
                    if char not in valid_clues and self._is_chinese_char(char):
                        candidate_examples[char].add(word)
            
            # 对该线索字符的去重字符集，每个字符计数器 +1
            for char in chars_from_this_clue:
                if char not in valid_clues and self._is_chinese_char(char):  # 排除线索字符本身，只考虑中文字符
                    candidate_counter[char] += 1
            
            print(f"      从该线索提取到 {len(chars_from_this_clue)} 个不重复字符")        # 整理结果
        results = []
        for char, count in candidate_counter.most_common():
            example_words = list(candidate_examples[char])[:5]  # 最多显示5个示例
            results.append((char, count, example_words))
        
        print(f"✅ 找到 {len(results)} 个候选字符")
        return results
    
    def get_character_words(self, char: str) -> List[str]:
        """获取包含指定字符的所有词汇"""
        if not self.is_loaded:
            self.load_data()
        
        return self.char_words_dict.get(char, [])
    
    def get_statistics(self) -> Dict[str, int]:
        """获取数据统计信息"""
        if not self.is_loaded:
            self.load_data()
        
        return {
            'total_characters': len(self.char_words_dict),
            'total_words': len(self.word_chars_dict),
            'avg_words_per_char': sum(len(words) for words in self.char_words_dict.values()) / len(self.char_words_dict) if self.char_words_dict else 0
        }


# 全局分析器实例
_analyzer = None

def get_analyzer() -> CharacterWordAnalyzer:
    """获取全局分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = CharacterWordAnalyzer()
    return _analyzer


def process_character_mystery(clue_chars: List[str], max_results: int = 20) -> str:
    """
    处理字谜推理请求
    
    Args:
        clue_chars: 线索字符列表
        max_results: 最大返回结果数
        
    Returns:
        格式化的分析结果
    """
    try:
        analyzer = get_analyzer()
        
        if not clue_chars:
            return "❌ 请至少提供一个线索字符"
        
        # 去重并过滤
        unique_clues = list(set(char.strip() for char in clue_chars if char.strip()))
        
        if not unique_clues:
            return "❌ 请提供有效的中文字符作为线索"
        
        # 分析
        results = analyzer.analyze_character_clues(unique_clues)
        
        if not results:
            return f"❌ 没有找到与线索字符 {unique_clues} 相关的候选字符"
        
        # 格式化输出
        output_lines = []
        output_lines.append(f"🔍 字谜推理分析")
        output_lines.append(f"📝 线索字符: {', '.join(unique_clues)}")
        output_lines.append("=" * 50)
        
        for i, (char, count, examples) in enumerate(results[:max_results], 1):
            output_lines.append(f"{i:2d}. 字符: {char} (匹配度: {count})")
            output_lines.append(f"    示例词汇: {' | '.join(examples[:3])}")
            if len(examples) > 3:
                output_lines.append(f"    更多词汇: {' | '.join(examples[3:5])}")
            output_lines.append("")
        
        # 添加统计信息
        stats = analyzer.get_statistics()
        output_lines.append("📊 数据统计:")
        output_lines.append(f"   总字符数: {stats['total_characters']:,}")
        output_lines.append(f"   总词汇数: {stats['total_words']:,}")
        output_lines.append(f"   平均每字词汇数: {stats['avg_words_per_char']:.1f}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"❌ 分析失败: {str(e)}"


def process_character_mystery_with_positions(clue_chars: List[str], clue_positions: List[int] = None, max_results: int = 20) -> str:
    """
    处理带位置要求的字谜推理请求
    
    Args:
        clue_chars: 线索字符列表
        clue_positions: 位置要求列表，0表示任意位置，其他数字表示指定位置(1-based)
        max_results: 最大返回结果数
        
    Returns:
        格式化的分析结果
    """
    try:
        analyzer = get_analyzer()
        
        if not clue_chars:
            return "❌ 请至少提供一个线索字符"
        
        # 去重并过滤
        unique_clues = list(set(char.strip() for char in clue_chars if char.strip()))
        
        if not unique_clues:
            return "❌ 请提供有效的中文字符作为线索"
        
        # 如果没有提供位置，默认都是任意位置
        if clue_positions is None:
            clue_positions = [0] * len(unique_clues)
        
        # 分析
        results = analyzer.analyze_character_clues(unique_clues, clue_positions)
        
        if not results:
            clue_info = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in zip(unique_clues, clue_positions)]
            return f"❌ 没有找到与线索 {clue_info} 相关的候选字符"
        
        # 限制结果数量
        limited_results = results[:max_results]
        
        # 格式化输出
        output_lines = []
        clue_info = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in zip(unique_clues, clue_positions)]
        output_lines.append(f"🔍 字谜推理结果 (线索: {', '.join(clue_info)})")
        output_lines.append("=" * 60)
        output_lines.append("")
        
        for i, (char, match_count, example_words) in enumerate(limited_results, 1):
            output_lines.append(f"**{i:2d}. {char}** (匹配度: {match_count})")
            
            # 显示示例词汇
            if example_words:
                examples = example_words[:5]  # 显示前5个例子
                output_lines.append(f"    📚 示例: {', '.join(examples)}")
                if len(example_words) > 5:
                    output_lines.append(f"    💡 共{len(example_words)}个相关词汇")
            else:
                output_lines.append(f"    📚 示例: 无")
            output_lines.append("")
        
        # 添加统计信息
        stats = analyzer.get_statistics()
        output_lines.append("📊 数据统计:")
        output_lines.append(f"   总字符数: {stats['total_characters']:,}")
        output_lines.append(f"   总词汇数: {stats['total_words']:,}")
        output_lines.append(f"   候选字符数: {len(results):,}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"❌ 分析失败: {str(e)}"


if __name__ == "__main__":
    # 测试代码
    print("🧪 测试字谜推理器 - 基础功能")
    
    # 基础测试用例
    test_clues = ["天", "地"]
    result = process_character_mystery(test_clues)
    print(result)
    
    print("\n" + "="*60 + "\n")
    
    print("🧪 测试字谜推理器 - 位置功能")
    
    # 位置测试用例：痛在第1位
    test_clues_pos = ["痛"]
    test_positions = [1]  # 痛必须在第1位
    result_pos = process_character_mystery_with_positions(test_clues_pos, test_positions, 10)
    print(result_pos)
