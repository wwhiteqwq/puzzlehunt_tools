#!/usr/bin/env python3
"""
拼音工具模块
支持从中文词汇中提取拼音信息，以及高级汉字筛选功能
包括：声母、韵母、声调、笔画数、部首、特定笔画等
"""

import re
from typing import List, Tuple, Set, Dict, Any, Optional

# 全局缓存搜索器实例
_pinyin_searcher = None

def _get_pinyin_searcher():
    """获取拼音搜索器实例（单例模式）"""
    global _pinyin_searcher
    if _pinyin_searcher is None:
        try:
            from pinyin_searcher import PinyinSearcher
            _pinyin_searcher = PinyinSearcher()
        except Exception as e:
            print(f"初始化拼音搜索器失败: {e}")
            _pinyin_searcher = False
    return _pinyin_searcher

def get_pinyin_for_char(char: str) -> List[str]:
    """
    获取单个汉字的拼音（包括多音字）
    返回该字的所有读音列表
    """
    try:
        searcher = _get_pinyin_searcher()
        if not searcher:
            return []
        
        # 在词典中查找该字
        for word_info in searcher.words_data:
            if word_info.get('word') == char:
                # 优先使用pinyin_list（包含多音字），否则使用pinyin
                pinyin_list = word_info.get('pinyin_list', [])
                if pinyin_list:
                    return pinyin_list
                elif word_info.get('pinyin'):
                    return [word_info.get('pinyin')]
        
        return []
        
    except Exception as e:
        print(f"获取字符'{char}'拼音失败: {e}")
        return []

def split_initial_final(pinyin: str) -> Tuple[str, str]:
    """
    分离拼音的声母和韵母
    参考PinyinSearcher的实现，增强处理各种拼音格式
    """
    if not pinyin:
        return '', ''
    
    # 清理拼音：移除音调数字和特殊符号，转换为标准格式
    pinyin_clean = pinyin.lower().strip()
    
    # 跳过非拼音格式（如括号内容）
    if any(char in pinyin_clean for char in ['(', ')', '（', '）', '·', '，']):
        return '', ''
    
    # 移除音调符号，转换为基本字母
    tone_map = {
        'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
        'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
        'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
        'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
        'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
        'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v', 'ü': 'v',
        'ń': 'n', 'ň': 'n', 'ǹ': 'n',
        'ɡ': 'g'  # 处理特殊的g字符
    }
    
    for accented, base in tone_map.items():
        pinyin_clean = pinyin_clean.replace(accented, base)
    
    # 移除数字音调
    pinyin_clean = re.sub(r'[0-9]', '', pinyin_clean)
    
    # 标准声母列表（与PinyinSearcher保持一致）
    standard_initials = {
        'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
        'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
    }
    
    # 按长度排序，优先匹配较长的声母
    sorted_initials = sorted(standard_initials, key=len, reverse=True)
    
    for initial in sorted_initials:
        if pinyin_clean.startswith(initial):
            final = pinyin_clean[len(initial):]
            return initial, final
    
    # 如果没有匹配的声母，整个拼音作为韵母
    return '', pinyin_clean

def get_word_finals(word: str) -> List[str]:
    """
    获取词汇中每个字的韵母
    返回韵母列表（去重，排除无效韵母）
    """
    finals = []
    
    for char in word:
        pinyin_list = get_pinyin_for_char(char)
        for pinyin in pinyin_list:
            initial, final = split_initial_final(pinyin)
            # 只添加有效的韵母（不为空且为标准韵母）
            if final and final not in finals and len(final) <= 6:  # 排除过长的无效数据
                finals.append(final)
    
    return finals

def get_word_pinyin(word: str) -> List[List[str]]:
    """
    获取词汇中每个字的完整拼音
    返回每个字符对应的拼音列表的列表
    """
    result = []
    for char in word:
        pinyins = get_pinyin_for_char(char)
        if not pinyins:
            pinyins = ['']
        result.append(pinyins)
    return result

def get_available_finals() -> List[str]:
    """
    获取所有可用的韵母列表（与汉字搜索保持一致）
    """
    # 标准中文韵母（与汉字搜索界面保持一致）
    finals = [
        # 单韵母
        "a", "o", "e", "i", "u", "v",
        # 复韵母
        "ai", "ei", "ui", "ao", "ou", "iu", 
        "ie", "ue", "ve", "er", 
        # 前鼻韵母
        "an", "en", "in", "un", "vn", 
        # 后鼻韵母
        "ang", "eng", "ing", "ong",
        # 复合韵母
        "ia", "iao", "ian", "iang", "iong", 
        "ua", "uo", "uai", "uan", "uang"
    ]
    return finals  # 保持原有顺序


def filter_words_by_advanced_criteria(
    words: List[str], 
    character_position: int = 0,  # 字符位置（0表示第一个字）
    initial: Optional[str] = None,       # 声母
    final: Optional[str] = None,         # 韵母
    tone: Optional[str] = None,          # 声调
    stroke_count: Optional[int] = None,  # 笔画数
    radical: Optional[str] = None,       # 部首
    contains_stroke: Optional[str] = None,  # 包含特定笔画
    stroke_position: Optional[int] = None   # 特定位置的笔画
) -> List[str]:
    """
    根据高级条件筛选词汇中特定位置的字符
    
    Args:
        words: 候选词汇列表
        character_position: 要筛选的字符位置（0=第一个字，1=第二个字...）
        initial: 声母要求
        final: 韵母要求 
        tone: 声调要求（1-4）
        stroke_count: 笔画数要求
        radical: 部首要求
        contains_stroke: 必须包含的笔画名称
        stroke_position: 特定位置的笔画（与contains_stroke配合使用）
    
    Returns:
        筛选后的词汇列表
    """
    if not words:
        return []
    
    searcher = _get_pinyin_searcher()
    if not searcher:
        return words
    
    filtered_words = []
    
    for word in words:
        if character_position >= len(word):
            continue  # 跳过字符数不足的词汇
        
        char = word[character_position]
        
        # 获取字符的详细信息
        char_info = _get_char_info(char, searcher)
        if not char_info:
            continue
        
        # 检查声母
        if initial and not _check_initial(char_info, initial):
            continue
        
        # 检查韵母
        if final and not _check_final(char_info, final):
            continue
        
        # 检查声调
        if tone and not _check_tone(char_info, tone):
            continue
        
        # 检查笔画数
        if stroke_count is not None and not _check_stroke_count(char_info, stroke_count):
            continue
        
        # 检查部首
        if radical and not _check_radical(char_info, radical):
            continue
        
        # 检查特定笔画
        if contains_stroke and not _check_contains_stroke(char_info, contains_stroke, stroke_position):
            continue
        
        filtered_words.append(word)
    
    return filtered_words


def _get_char_info(char: str, searcher) -> Optional[Dict[str, Any]]:
    """获取字符的详细信息"""
    try:
        # 在数据中查找字符信息
        for word_data in searcher.words_data:
            if word_data and word_data.get('word') == char:
                return word_data
        return None
    except Exception:
        return None


def _check_initial(char_info: Dict[str, Any], required_initial: str) -> bool:
    """检查声母"""
    try:
        pinyin = char_info.get('pinyin', '')
        if not pinyin:
            return False
        
        initial, _ = split_initial_final(pinyin)
        return initial == required_initial
    except Exception:
        return False


def _check_final(char_info: Dict[str, Any], required_final: str) -> bool:
    """检查韵母（支持ue↔ve兼容性）"""
    try:
        pinyin = char_info.get('pinyin', '')
        if not pinyin:
            return False
        
        _, final = split_initial_final(pinyin)
        
        # 标准化韵母比较：处理ue↔ve兼容性
        def normalize_final(f):
            """标准化韵母格式，支持ue↔ve双向转换"""
            if not f:
                return ''
            # 处理ue↔ve转换：都统一为ue进行比较
            if f == 've':
                return 'ue'
            return f
        
        actual_normalized = normalize_final(final)
        required_normalized = normalize_final(required_final)
        
        return actual_normalized == required_normalized
    except Exception:
        return False


def _check_tone(char_info: Dict[str, Any], required_tone: str) -> bool:
    """检查声调"""
    try:
        pinyin = char_info.get('pinyin', '')
        if not pinyin:
            return False
        
        # 提取声调（音调符号对应的数字）
        tone_map = {
            'ā': '1', 'á': '2', 'ǎ': '3', 'à': '4',
            'ē': '1', 'é': '2', 'ě': '3', 'è': '4',
            'ī': '1', 'í': '2', 'ǐ': '3', 'ì': '4',
            'ō': '1', 'ó': '2', 'ǒ': '3', 'ò': '4',
            'ū': '1', 'ú': '2', 'ǔ': '3', 'ù': '4',
            'ǖ': '1', 'ǘ': '2', 'ǚ': '3', 'ǜ': '4'
        }
        
        for accented, tone_num in tone_map.items():
            if accented in pinyin and tone_num == required_tone:
                return True
        
        # 检查数字声调
        if required_tone in pinyin:
            return True
        
        return False
    except Exception:
        return False


def _check_stroke_count(char_info: Dict[str, Any], required_count: int) -> bool:
    """检查笔画数"""
    try:
        stroke_count = char_info.get('stroke', 0)
        return stroke_count == required_count
    except Exception:
        return False


def _check_radical(char_info: Dict[str, Any], required_radical: str) -> bool:
    """检查部首"""
    try:
        radical = char_info.get('radical', '')
        return radical == required_radical
    except Exception:
        return False


def _check_contains_stroke(char_info: Dict[str, Any], required_stroke: str, position: Optional[int] = None) -> bool:
    """检查是否包含特定笔画或特定位置的笔画"""
    try:
        stroke_order = char_info.get('order_simple', [])  # 使用order_simple而不是order
        if not stroke_order:
            return False
        
        if position is not None:
            # 检查特定位置的笔画（位置从1开始）
            array_index = position - 1
            if 0 <= array_index < len(stroke_order):
                return stroke_order[array_index] == required_stroke
            return False
        else:
            # 检查是否包含该笔画
            return required_stroke in stroke_order
    except Exception:
        return False


def get_available_initials() -> List[str]:
    """获取所有可用的声母"""
    searcher = _get_pinyin_searcher()
    if not searcher:
        return []
    
    try:
        return sorted(list(searcher.initials))
    except Exception:
        return ['b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w']


def get_available_tones() -> List[str]:
    """获取所有可用的声调"""
    return ['1', '2', '3', '4']


def get_available_strokes() -> List[str]:
    """获取所有可用的笔画名称"""
    searcher = _get_pinyin_searcher()
    if not searcher:
        return []
    
    try:
        return searcher.get_available_stroke_names()[1:]  # 去掉空字符串
    except Exception:
        return []


def get_available_radicals() -> List[str]:
    """获取所有可用的部首"""
    searcher = _get_pinyin_searcher()
    if not searcher:
        return []
    
    try:
        return searcher.get_available_radicals()
    except Exception:
        return []


def filter_words_by_character_finals(words: List[str], character_finals: List[str]) -> List[str]:
    """
    按每个字的韵母筛选词汇列表
    character_finals: 每个字位置对应的韵母要求，空字符串表示不限制
    例如: ["ao", ""] 表示第一个字韵母必须是"ao"，第二个字不限制
    """
    if not character_finals or all(not final for final in character_finals):
        return words
    
    filtered_words = []
    for word in words:
        if len(word) != len(character_finals):
            continue  # 跳过字数不匹配的词汇
        
        match = True
        for i, char in enumerate(word):
            if i >= len(character_finals):
                break
            
            required_final = character_finals[i]
            if not required_final:  # 空字符串表示不限制
                continue
            
            # 获取该字的所有韵母
            char_finals = []
            pinyin_list = get_pinyin_for_char(char)
            for pinyin in pinyin_list:
                initial, final = split_initial_final(pinyin)
                if final and len(final) <= 6:  # 排除无效韵母
                    char_finals.append(final)
            
            # 检查是否包含要求的韵母
            if required_final not in char_finals:
                match = False
                break
        
        if match:
            filtered_words.append(word)
    
    return filtered_words

def test_pinyin_tools():
    """测试拼音工具功能"""
    test_words = ["高兴", "学习", "美丽", "工作"]
    
    print("🧪 测试拼音工具功能")
    print("=" * 50)
    
    for word in test_words:
        print(f"\n词汇: {word}")
        
        # 获取每个字的拼音
        for char in word:
            pinyin_list = get_pinyin_for_char(char)
            print(f"  {char}: {pinyin_list}")
            
            # 显示韵母分析
            for pinyin in pinyin_list:
                initial, final = split_initial_final(pinyin)
                print(f"    {pinyin} -> 声母:{initial or '无'}, 韵母:{final}")
        
        # 获取词汇的所有韵母
        finals = get_word_finals(word)
        print(f"词汇韵母: {finals}")
    
    # 测试按每个字的韵母筛选
    print(f"\n测试按每个字的韵母筛选:")
    test_list = ["高兴", "高度", "低调", "高远", "美丽"]
    
    print(f"原词汇: {test_list}")
    
    # 第一个字韵母是"ao"，第二个字不限制
    filtered = filter_words_by_character_finals(test_list, ["ao", ""])
    print(f"第一个字韵母是'ao'的词: {filtered}")
    
    # 第一个字不限制，第二个字韵母是"i"
    filtered = filter_words_by_character_finals(test_list, ["", "i"])
    print(f"第二个字韵母是'i'的词: {filtered}")
    
    # 两个字都有特定韵母要求
    filtered = filter_words_by_character_finals(test_list, ["ao", "ao"])
    print(f"两个字都是'ao'韵母的词: {filtered}")
    
    # 显示筛选详情
    print(f"\n筛选详情:")
    for word in test_list:
        char_finals = []
        for char in word:
            char_pinyin = get_pinyin_for_char(char)
            char_final_list = []
            for pinyin in char_pinyin:
                initial, final = split_initial_final(pinyin)
                if final:
                    char_final_list.append(final)
            char_finals.append(char_final_list)
        print(f"  {word}: {char_finals}")

if __name__ == "__main__":
    test_pinyin_tools()
