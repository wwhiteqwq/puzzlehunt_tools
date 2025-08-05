# 带缺拼音查汉字功能
# 基于新华字典数据，支持通过笔画数、声母、韵母等条件查询汉字

import json
import re
import os
from typing import List, Dict, Optional, Set, Tuple


class PinyinSearcher:
    """拼音查汉字工具类"""
    
    def __init__(self):
        """初始化拼音查汉字工具"""
        self.words_data = []
        self.initials = set()  # 声母集合
        self.finals = set()    # 韵母集合
        self.tones = set()     # 音调集合
        self._load_data()
        
    def _load_data(self):
        """加载新华字典数据"""
        # 获取数据文件路径，优先使用包含笔顺信息的新词典
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(current_dir, "word-new.json")        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.words_data = json.load(f)
            # 处理多音字数据
            self._process_multiple_pronunciations()
            self._analyze_pinyin_components()
            
            # 检查是否加载了包含笔顺信息的数据
            has_stroke_order = any(word.get('order') is not None for word in self.words_data[:10])
            stroke_info = "（包含笔顺信息）" if has_stroke_order else "（不含笔顺信息）"
            
            print(f"成功加载 {len(self.words_data)} 个汉字数据 {stroke_info}")
        except FileNotFoundError:
            print(f"警告：找不到字典文件 {data_file}")
            self.words_data = []
        except Exception as e:
            print(f"加载字典数据时出错：{e}")
            self.words_data = []
    
    def _process_multiple_pronunciations(self):
        """处理多音字数据，从more字段中提取额外的读音"""
        for word_info in self.words_data:
            word = word_info.get('word', '')
            more = word_info.get('more', '')
            base_pinyin = word_info.get('pinyin', '')
            
            # 收集所有读音，以列表形式存储
            all_pronunciations = []
            if base_pinyin:
                all_pronunciations.append(base_pinyin)
            
            if more and word:
                # 在more字段中查找格式如"字1"、"字2"等的多音字标记
                pronunciations = self._extract_pronunciations_from_more(word, more)
                all_pronunciations.extend(pronunciations)
            
            # 去重并更新拼音字段为列表
            word_info['pinyin_list'] = list(set(all_pronunciations)) if all_pronunciations else [base_pinyin] if base_pinyin else []
    
    def _extract_pronunciations_from_more(self, word: str, more: str) -> List[str]:
        """从more字段中提取多音字的读音"""
        pronunciations = []
        
        # 查找格式如"字1\n读音"、"字2\n读音"的模式
        pattern = re.compile(rf'{re.escape(word)}(\d+)\n([^\n\s]+)', re.MULTILINE)
        matches = pattern.findall(more)
        
        for match in matches:
            pronunciation = match[1].strip()
            if pronunciation:
                pronunciations.append(pronunciation)
        
        return pronunciations
    
    def _analyze_pinyin_components(self):
        """分析拼音数据，提取声母、韵母、音调"""
        # 标准声母列表（固定）
        standard_initials = {
            'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
            'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
        }
        
        # 标准韵母列表（固定）
        standard_finals = {
            'a', 'o', 'e', 'i', 'u', 'v', 'er', 
            'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
            'iao', 'iou', 'uai', 'uei', 
            'an', 'ian', 'uan', 'van', 
            'en', 'in', 'uen', 'vn', 
            'ang', 'iang', 'uang', 
            'eng', 'ing', 'ueng', 
            'ong', 'iong'
        }
        
        # 从数据中收集拼音并分析（只保留符合标准的）
        for word_info in self.words_data:
            # 使用新的拼音列表
            pinyin_list = word_info.get('pinyin_list', [])
            if not pinyin_list:
                continue
                
            for pinyin in pinyin_list:
                if not pinyin:
                    continue
                    
                # 处理多个拼音（用逗号分隔）
                pinyins = [p.strip() for p in pinyin.split(',')]
                
                for py in pinyins:
                    if not py:
                        continue
                        
                    # 验证拼音是否符合标准并分析
                    if self._is_valid_pinyin(py, standard_initials, standard_finals):
                        self._parse_single_pinyin(py, standard_initials, standard_finals)
        
        # 使用标准列表（固定不变）
        self.initials = [''] + sorted(list(standard_initials))  # 空字符串表示"不限制"
        self.finals = [''] + sorted(list(standard_finals))
        self.tones = ['', '1', '2', '3', '4', '5']  # 空字符串表示"不限制"，5表示轻声
    
    def _is_valid_pinyin(self, pinyin: str, standard_initials: set, standard_finals: set) -> bool:
        """验证拼音是否符合标准声母韵母组合"""
        if not pinyin:
            return False
        
        # 去除音调获取基础拼音
        base_pinyin = self._remove_tone_marks(pinyin)
        
        # 分离声母和韵母
        initial, final = self._split_initial_final(base_pinyin, standard_initials)
        
        # 检查韵母是否在标准列表中
        if final and final not in standard_finals:
            return False
        
        # 检查声母是否在标准列表中（如果有声母的话）
        if initial and initial not in standard_initials:
            return False
        
        return True
    
    def _parse_single_pinyin(self, pinyin: str, standard_initials: Set[str], standard_finals: Set[str]):
        """解析单个拼音，提取声母、韵母、音调"""
        if not pinyin:
            return
            
        # 去除音调符号，提取音调
        tone = self._extract_tone(pinyin)
        if tone:
            self.tones.add(tone)
        
        # 注意：不再动态添加声母韵母，因为我们使用固定的标准列表
    
    def _extract_tone(self, pinyin: str) -> str:
        """从拼音中提取音调"""
        # 音调符号映射
        tone_marks = {
            'ā': '1', 'á': '2', 'ǎ': '3', 'à': '4',
            'ē': '1', 'é': '2', 'ě': '3', 'è': '4',
            'ī': '1', 'í': '2', 'ǐ': '3', 'ì': '4',
            'ō': '1', 'ó': '2', 'ǒ': '3', 'ò': '4',
            'ū': '1', 'ú': '2', 'ǔ': '3', 'ù': '4',
            'ǖ': '1', 'ǘ': '2', 'ǚ': '3', 'ǜ': '4',
            'ü': '5', 'v': '5'  # 这些通常表示轻声或无调
        }
        
        # 检查数字音调
        if pinyin and pinyin[-1].isdigit():
            return pinyin[-1]
        
        # 检查音调符号
        for char in pinyin:
            if char in tone_marks:
                return tone_marks[char]
        
        return '5'  # 默认轻声
    
    def _remove_tone_marks(self, pinyin: str) -> str:
        """去除拼音中的音调符号"""
        # 音调符号到基本字母的映射
        tone_map = {
            'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
            'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
            'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
            'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
            'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
            'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v',
            'ü': 'v', 'ɡ': 'g'  # 特殊的g字符
        }
        
        result = ''
        for char in pinyin:
            if char in tone_map:
                result += tone_map[char]
            elif char.isdigit() and char in '12345':
                continue  # 跳过数字音调
            else:
                result += char
                
        return result.lower()
    
    def _split_initial_final(self, pinyin: str, known_initials: Set[str]) -> Tuple[str, str]:
        """分离声母和韵母"""
        if not pinyin:
            return '', ''
        
        # 按长度排序，优先匹配较长的声母
        sorted_initials = sorted(known_initials, key=len, reverse=True)
        
        for initial in sorted_initials:
            if pinyin.startswith(initial):
                final = pinyin[len(initial):]
                return initial, final
        
        # 如果没有匹配的声母，整个拼音作为韵母
        return '', pinyin
    
    def get_available_options(self) -> Dict[str, List[str]]:
        """获取可用的查询选项"""
        return {
            'initials': self.initials,
            'finals': self.finals,
            'tones': self.tones,
            'stroke_names': self.get_available_stroke_names(),
            'radicals': self.get_available_radicals()
        }
    
    def search_characters(self, strokes: Optional[str] = None, initial: Optional[str] = None, 
                         final: Optional[str] = None, tone: Optional[str] = None, 
                         stroke_name: Optional[str] = None, radicals: Optional[List[str]] = None, 
                         max_results: int = 100) -> Tuple[List[Dict], int]:
        """
        根据条件搜索汉字
        
        Args:
            strokes: 笔画数
            initial: 声母
            final: 韵母
            tone: 音调
            stroke_name: 笔画名称（如：横、竖、撇、捺等）
            radicals: 偏旁部首列表
            max_results: 最大结果数
            
        Returns:
            (匹配的汉字列表, 总结果数)
        """
        if not self.words_data:
            return [], 0
        
        # 检查是否至少提供了一个查询条件
        if not any([strokes, initial, final, tone, stroke_name, radicals]):
            return [], 0
        
        results = []
        stroke_count = None
        
        # 处理笔画数
        if strokes and strokes.strip():
            try:
                stroke_count = int(strokes.strip())
            except ValueError:
                stroke_count = None
        
        # 清理查询条件
        initial = initial.strip() if initial else ''
        final = final.strip() if final else ''
        tone = tone.strip() if tone else ''
        stroke_name = stroke_name.strip() if stroke_name else ''
        
        # 先收集所有符合条件的结果
        for word_info in self.words_data:
            if self._matches_criteria(word_info, stroke_count, initial, final, tone, stroke_name, radicals):
                results.append(word_info)
        
        # 记录总结果数
        total_count = len(results)
        
        # 按释义长度从长到短排序（释义长的字通常更常用）
        results.sort(key=lambda x: len(x.get('explanation', '')), reverse=True)
        
        # 最后限制结果数量
        limited_results = results[:max_results]
        
        # 返回结果和总数信息
        return limited_results, total_count
    
    def _matches_criteria(self, word_info: Dict, stroke_count: Optional[int], 
                         initial: str, final: str, tone: str, stroke_name: str = '', 
                         radicals: Optional[List[str]] = None) -> bool:
        """检查汉字是否匹配查询条件"""
        # 检查笔画数
        if stroke_count is not None:
            try:
                word_strokes = int(word_info.get('strokes', '0'))
                if word_strokes != stroke_count:
                    return False
            except ValueError:
                if stroke_count > 0:  # 如果指定了笔画数但汉字数据无效，则不匹配
                    return False
        
        # 检查笔画名称
        if stroke_name:
            if not self._matches_stroke_name(word_info, stroke_name):
                return False
        
        # 检查偏旁部首
        if radicals:
            word_radical = word_info.get('radicals', '').strip()
            if not word_radical or word_radical not in radicals:
                return False
        
        # 如果没有拼音条件，只要其他条件匹配就返回True
        if not any([initial, final, tone]):
            return True
        
        # 检查拼音条件 - 必须有至少一个读音满足所有拼音条件
        pinyin_list = word_info.get('pinyin_list', [])
        if not pinyin_list:
            return False  # 如果有拼音条件但字没有拼音数据，则不匹配
        
        # 处理多个拼音读音
        for pinyin in pinyin_list:
            if not pinyin:
                continue
                
            # 处理逗号分隔的拼音
            pinyins = [p.strip() for p in pinyin.split(',')]
            
            for py in pinyins:
                # 只处理符合标准的拼音
                standard_initials = {
                    'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                    'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
                }
                standard_finals = {
                    'a', 'o', 'e', 'i', 'u', 'v', 'er', 
                    'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
                    'iao', 'iou', 'uai', 'uei', 
                    'an', 'ian', 'uan', 'van', 
                    'en', 'in', 'uen', 'vn', 
                    'ang', 'iang', 'uang', 
                    'eng', 'ing', 'ueng', 
                    'ong', 'iong'
                }
                
                if self._is_valid_pinyin(py, standard_initials, standard_finals) and self._pinyin_matches(py, initial, final, tone):
                    return True
        
        return False
    
    def _pinyin_matches(self, pinyin: str, target_initial: str, 
                       target_final: str, target_tone: str) -> bool:
        """检查单个拼音是否匹配条件"""
        if not pinyin:
            return False
        
        # 提取音调
        extracted_tone = self._extract_tone(pinyin)
        
        # 检查音调
        if target_tone and extracted_tone != target_tone:
            return False
        
        # 去除音调获取基础拼音
        base_pinyin = self._remove_tone_marks(pinyin)
        
        # 分离声母和韵母
        standard_initials = {
            'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
            'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
        }
        
        extracted_initial, extracted_final = self._split_initial_final(base_pinyin, standard_initials)
        
        # 检查声母
        if target_initial and extracted_initial != target_initial:
            return False
        
        # 检查韵母
        if target_final and extracted_final != target_final:
            return False
        
        return True

    def search_by_stroke_positions(self, stroke_positions: Dict[int, str], max_results: int = 50) -> Tuple[List[Dict], int]:
        """
        按指定位置的笔画查找汉字
        
        Args:
            stroke_positions: 笔画位置字典，如 {1: "横", 3: "竖", 7: "撇"} 表示第1画是横，第3画是竖，第7画是撇
            max_results: 最大结果数
            
        Returns:
            (匹配的汉字列表, 总结果数)
        """
        if not self.words_data or not stroke_positions:
            return [], 0
        
        results = []
        
        for word_info in self.words_data:
            if self._matches_stroke_positions(word_info, stroke_positions):
                results.append(word_info)
        
        # 记录总结果数
        total_count = len(results)
        
        # 按笔画数从少到多排序，笔画数相同的按释义长度排序
        results.sort(key=lambda x: (
            len(x.get('order_simple', [])), 
            -len(x.get('explanation', ''))
        ))
        
        # 限制结果数量
        limited_results = results[:max_results]
        
        return limited_results, total_count
    
    def _matches_stroke_positions(self, word_info: Dict, stroke_positions: Dict[int, str]) -> bool:
        """检查汉字是否匹配指定位置的笔画"""
        order_simple = word_info.get('order_simple', [])
        if not order_simple:
            return False
        
        # 检查每个指定位置的笔画是否匹配
        for position, expected_stroke in stroke_positions.items():
            # 位置从1开始，转换为数组索引（从0开始）
            array_index = position - 1
            
            # 检查位置是否超出笔画总数
            if array_index >= len(order_simple):
                return False
            
            # 检查该位置的笔画是否匹配
            if order_simple[array_index] != expected_stroke:
                return False
        
        return True

    def search_by_stroke_sequence(self, stroke_sequence: List[str], max_results: int = 50) -> Tuple[List[Dict], int]:
        """
        按笔画顺序查找汉字
        
        Args:
            stroke_sequence: 笔画序列，如 ["横", "竖", "撇"]
            max_results: 最大结果数
            
        Returns:
            (匹配的汉字列表, 总结果数)
        """
        if not self.words_data or not stroke_sequence:
            return [], 0
        
        results = []
        
        # 过滤掉空的笔画
        stroke_sequence = [stroke for stroke in stroke_sequence if stroke and stroke.strip()]
        if not stroke_sequence:
            return [], 0
        
        for word_info in self.words_data:
            if self._matches_stroke_sequence(word_info, stroke_sequence):
                results.append(word_info)
        
        # 记录总结果数
        total_count = len(results)
        
        # 按笔画数从少到多排序，笔画数相同的按释义长度排序
        results.sort(key=lambda x: (
            len(x.get('order_simple', [])), 
            -len(x.get('explanation', ''))
        ))
        
        # 限制结果数量
        limited_results = results[:max_results]
        
        return limited_results, total_count
    
    def _matches_stroke_sequence(self, word_info: Dict, stroke_sequence: List[str]) -> bool:
        """检查汉字是否匹配指定的笔画序列"""
        order_simple = word_info.get('order_simple', [])
        if not order_simple:
            return False
        
        # 检查笔画序列长度
        if len(stroke_sequence) > len(order_simple):
            return False
        
        # 检查每个位置的笔画是否匹配
        for i, expected_stroke in enumerate(stroke_sequence):
            if i >= len(order_simple) or order_simple[i] != expected_stroke:
                return False
        
        return True
    
    def _matches_stroke_name(self, word_info: Dict, stroke_name: str) -> bool:
        """检查汉字是否包含指定的笔画名称"""
        if not stroke_name:
            return True
        
        # 获取简化笔画名称列表
        order_simple = word_info.get('order_simple', [])
        if not order_simple:
            return False
        
        # 检查是否包含指定的笔画名称
        return stroke_name in order_simple
    
    def get_available_stroke_names(self) -> List[str]:
        """获取数据中所有可用的笔画名称"""
        stroke_names = set()
        
        for word_info in self.words_data:
            order_simple = word_info.get('order_simple', [])
            if order_simple:
                stroke_names.update(order_simple)
        
        # 按常见笔画顺序排序
        common_strokes = ['横', '竖', '撇', '捺', '点', '提', '横折', '竖钩', '横钩', '撇点']
        result = []
        
        # 先添加常见笔画
        for stroke in common_strokes:
            if stroke in stroke_names:
                result.append(stroke)
                stroke_names.remove(stroke)
        
        # 再添加其他笔画（按字母顺序）
        result.extend(sorted(stroke_names))
        
        return [''] + result  # 空字符串表示"不限制"
    
    def get_available_radicals(self) -> List[str]:
        """获取数据中所有可用的偏旁部首，按字数量降序排列"""
        radical_count = {}
        
        # 统计每个偏旁对应的字数量
        for word_info in self.words_data:
            radical = word_info.get('radicals', '').strip()
            if radical:
                radical_count[radical] = radical_count.get(radical, 0) + 1
        
        # 按字数量降序排序
        sorted_radicals = sorted(radical_count.items(), key=lambda x: x[1], reverse=True)
        
        # 返回带数量的偏旁列表，方便用户看到使用频率
        return [f"{radical} ({count}字)" for radical, count in sorted_radicals]
    
    def get_available_radicals_simple(self) -> List[str]:
        """获取简单的偏旁列表（不带数量显示）"""
        radical_count = {}
        
        # 统计每个偏旁对应的字数量
        for word_info in self.words_data:
            radical = word_info.get('radicals', '').strip()
            if radical:
                radical_count[radical] = radical_count.get(radical, 0) + 1
        
        # 按字数量降序排序
        sorted_radicals = sorted(radical_count.items(), key=lambda x: x[1], reverse=True)
        
        # 只返回偏旁列表（不包含数量）
        return [radical for radical, count in sorted_radicals]


def _is_valid_standard_pinyin(pinyin: str, standard_initials: set, standard_finals: set) -> bool:
    """验证拼音是否符合标准声母韵母组合（独立函数版本）"""
    if not pinyin:
        return False
    
    # 去除音调获取基础拼音
    tone_map = {
        'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
        'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
        'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
        'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
        'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
        'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v',
        'ü': 'v', 'ɡ': 'g'
    }
    
    base_pinyin = ''
    for char in pinyin:
        if char in tone_map:
            base_pinyin += tone_map[char]
        elif char.isdigit() and char in '12345':
            continue
        else:
            base_pinyin += char
    base_pinyin = base_pinyin.lower()
    
    # 分离声母和韵母
    sorted_initials = sorted(standard_initials, key=len, reverse=True)
    initial = ''
    final = base_pinyin
    
    for init in sorted_initials:
        if base_pinyin.startswith(init):
            initial = init
            final = base_pinyin[len(init):]
            break
    
    # 检查韵母是否在标准列表中
    if final and final not in standard_finals:
        return False
    
    # 检查声母是否在标准列表中（如果有声母的话）
    if initial and initial not in standard_initials:
        return False
    
    return True


def process_stroke_positions_search(stroke_positions: Dict[int, str], max_results: int = 50) -> str:
    """
    处理指定位置笔画查汉字请求
    
    Args:
        stroke_positions: 笔画位置字典，如 {1: "横", 3: "竖", 7: "撇"}
        max_results: 最大结果数
        
    Returns:
        查询结果字符串
    """
    try:
        searcher = PinyinSearcher()
        
        if not stroke_positions:
            return "❌ 请至少指定一个笔画位置"
        
        results, total_count = searcher.search_by_stroke_positions(stroke_positions, max_results)
        
        if not results:
            # 生成条件描述
            conditions = []
            for pos in sorted(stroke_positions.keys()):
                conditions.append(f"第{pos}画={stroke_positions[pos]}")
            condition_str = ", ".join(conditions)
            return f"❌ 未找到符合条件 [{condition_str}] 的汉字"
        
        # 格式化输出结果
        conditions = []
        for pos in sorted(stroke_positions.keys()):
            conditions.append(f"第{pos}画={stroke_positions[pos]}")
        condition_str = ", ".join(conditions)
        
        if total_count > len(results):
            output_lines = [f"🔍 找到 {total_count} 个符合条件 [{condition_str}] 的汉字，显示前 {len(results)} 个:\n"]
        else:
            output_lines = [f"🔍 找到 {len(results)} 个符合条件 [{condition_str}] 的汉字:\n"]
        
        # 添加查询条件说明
        output_lines.append(f"📋 查询条件: {condition_str}\n")
        
        # 格式化汉字结果
        output_lines.append("📝 查询结果:")
        for i, word_info in enumerate(results, 1):
            word = word_info.get('word', '?')
            
            # 获取拼音信息
            pinyin_list = word_info.get('pinyin_list', [])
            if not pinyin_list:
                pinyin_list = [word_info.get('pinyin', '无')]
            
            # 过滤并合并所有符合标准的读音显示
            standard_initials = {
                'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
            }
            standard_finals = {
                'a', 'o', 'e', 'i', 'u', 'v', 'er', 
                'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
                'iao', 'iou', 'uai', 'uei', 
                'an', 'ian', 'uan', 'van', 
                'en', 'in', 'vn', 
                'ang', 'iang', 'uang', 
                'eng', 'ing', 
                'ong', 'iong'
            }
            
            all_pinyins = []
            for p in pinyin_list:
                if p:
                    for py in [py.strip() for py in p.split(',')]:
                        if _is_valid_standard_pinyin(py, standard_initials, standard_finals):
                            all_pinyins.append(py)
            
            # 去重但保持顺序，显示多音字的所有读音
            seen = set()
            unique_pinyins = []
            for py in all_pinyins:
                if py not in seen:
                    seen.add(py)
                    unique_pinyins.append(py)
            
            # 如果有多个读音，用特殊格式标记多音字
            if len(unique_pinyins) > 1:
                pinyin_display = f"[多音字] {' / '.join(unique_pinyins)}"
            elif unique_pinyins:
                pinyin_display = unique_pinyins[0]
            else:
                pinyin_display = '无'
            
            strokes_info = word_info.get('strokes', '?')
            radical = word_info.get('radicals', '?')
            
            # 获取笔顺信息并高亮匹配的位置
            order_simple = word_info.get('order_simple', [])
            stroke_order_display = ''
            if order_simple:
                # 创建高亮显示的笔顺
                highlighted_strokes = []
                for idx, stroke in enumerate(order_simple):
                    position = idx + 1  # 转换为1开始的位置
                    if position in stroke_positions:
                        highlighted_strokes.append(f"[{stroke}]")  # 高亮匹配的笔画
                    else:
                        highlighted_strokes.append(stroke)
                
                if len(order_simple) <= 10:
                    stroke_order_display = f", 笔顺: {'→'.join(highlighted_strokes)}"
                else:
                    # 对于长笔顺，显示前几画和匹配的位置
                    display_strokes = highlighted_strokes[:8]
                    stroke_order_display = f", 笔顺: {'→'.join(display_strokes)}→...共{len(order_simple)}笔"
            
            explanation = word_info.get('explanation', '')
            if explanation:
                explanation = ' '.join(line.strip() for line in explanation.split('\n') if line.strip())
                if len(explanation) > 200:
                    explanation = explanation[:200] + '...'
            else:
                explanation = '无释义'
            
            output_lines.append(f"  {i:2d}. {word} ({pinyin_display}, {strokes_info}笔, 部首:{radical}{stroke_order_display})")
            output_lines.append(f"     {explanation}")
        
        return '\n'.join(output_lines)
    
    except Exception as e:
        return f"❌ 查询出错: {str(e)}"


def process_stroke_sequence_search(stroke_sequence: List[str], max_results: int = 50) -> str:
    """
    处理笔画序列查汉字请求
    
    Args:
        stroke_sequence: 笔画序列，如 ["横", "竖", "撇"]
        max_results: 最大结果数
        
    Returns:
        查询结果字符串
    """
    try:
        searcher = PinyinSearcher()
        
        # 过滤空值
        filtered_sequence = [stroke for stroke in stroke_sequence if stroke and stroke.strip()]
        
        if not filtered_sequence:
            return "❌ 请至少指定一个笔画"
        
        results, total_count = searcher.search_by_stroke_sequence(filtered_sequence, max_results)
        
        if not results:
            sequence_str = "→".join(filtered_sequence)
            return f"❌ 未找到以 [{sequence_str}] 开头的汉字"
        
        # 格式化输出结果
        sequence_str = "→".join(filtered_sequence)
        if total_count > len(results):
            output_lines = [f"🔍 找到 {total_count} 个以 [{sequence_str}] 开头的汉字，显示前 {len(results)} 个:\n"]
        else:
            output_lines = [f"🔍 找到 {len(results)} 个以 [{sequence_str}] 开头的汉字:\n"]
        
        # 添加查询条件说明
        output_lines.append(f"📋 查询条件: 前{len(filtered_sequence)}画为 {sequence_str}\n")
        
        # 格式化汉字结果
        output_lines.append("📝 查询结果:")
        for i, word_info in enumerate(results, 1):
            word = word_info.get('word', '?')
            
            # 获取拼音信息
            pinyin_list = word_info.get('pinyin_list', [])
            if not pinyin_list:
                pinyin_list = [word_info.get('pinyin', '无')]
            
            # 过滤并合并所有符合标准的读音显示
            standard_initials = {
                'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
            }
            standard_finals = {
                'a', 'o', 'e', 'i', 'u', 'v', 'er', 
                'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
                'iao', 'iou', 'uai', 'uei', 
                'an', 'ian', 'uan', 'van', 
                'en', 'in', 'vn', 
                'ang', 'iang', 'uang', 
                'eng', 'ing', 
                'ong', 'iong'
            }
            
            all_pinyins = []
            for p in pinyin_list:
                if p:
                    for py in [py.strip() for py in p.split(',')]:
                        if _is_valid_standard_pinyin(py, standard_initials, standard_finals):
                            all_pinyins.append(py)
            
            # 去重但保持顺序，显示多音字的所有读音
            seen = set()
            unique_pinyins = []
            for py in all_pinyins:
                if py not in seen:
                    seen.add(py)
                    unique_pinyins.append(py)
            
            # 如果有多个读音，用特殊格式标记多音字
            if len(unique_pinyins) > 1:
                pinyin_display = f"[多音字] {' / '.join(unique_pinyins)}"
            elif unique_pinyins:
                pinyin_display = unique_pinyins[0]
            else:
                pinyin_display = '无'
            
            strokes_info = word_info.get('strokes', '?')
            radical = word_info.get('radicals', '?')
            
            # 获取完整笔顺信息
            order_simple = word_info.get('order_simple', [])
            stroke_order_display = ''
            if order_simple:
                # 高亮匹配的部分
                matched_part = "→".join(order_simple[:len(filtered_sequence)])
                remaining_part = "→".join(order_simple[len(filtered_sequence):]) if len(order_simple) > len(filtered_sequence) else ""
                
                if remaining_part:
                    stroke_order_display = f", 笔顺: [{matched_part}]→{remaining_part}"
                else:
                    stroke_order_display = f", 笔顺: [{matched_part}]"
            
            explanation = word_info.get('explanation', '')
            if explanation:
                # 删除空行，合并多行为一行，用空格分隔
                explanation = ' '.join(line.strip() for line in explanation.split('\n') if line.strip())
                # 如果释义太长则截断
                if len(explanation) > 200:
                    explanation = explanation[:200] + "..."
            else:
                explanation = "无释义"
            
            # 添加字与字之间的分割线（除了第一个字）
            if i > 1:
                output_lines.append("     " + "─" * 60)
            
            output_lines.append(
                f"{i:3d}. {word} ({pinyin_display}, {strokes_info}笔, 部首:{radical}{stroke_order_display})"
            )
            output_lines.append(f"     释义: {explanation}")
        
        if total_count > len(results):
            output_lines.append(f"\n💡 共找到 {total_count} 个结果，已显示前 {len(results)} 个最匹配的汉字")
            output_lines.append(f"   如需查看更多结果，请调整最大结果数")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"❌ 查询时发生错误: {str(e)}"


def process_combined_search(strokes: str = "", initial: str = "", final: str = "", tone: str = "", 
                          stroke_positions: Dict[int, str] = None, radicals: List[str] = None, 
                          max_results: int = 50) -> str:
    """
    处理组合查询：同时支持拼音条件、笔画位置条件和偏旁条件
    
    Args:
        strokes: 笔画数
        initial: 声母
        final: 韵母
        tone: 音调
        stroke_positions: 笔画位置字典，如 {1: "横", 3: "竖", 7: "撇"}
        radicals: 偏旁部首列表
        max_results: 最大结果数
        
    Returns:
        查询结果字符串
    """
    try:
        searcher = PinyinSearcher()
        
        # 检查是否至少提供了一个查询条件
        has_pinyin_conditions = any([
            strokes and strokes.strip(), 
            initial and initial.strip(), 
            final and final.strip(), 
            tone and tone.strip()
        ])
        
        has_stroke_positions = stroke_positions and len(stroke_positions) > 0
        has_radicals = radicals and len(radicals) > 0
        
        if not has_pinyin_conditions and not has_stroke_positions and not has_radicals:
            return "❌ 请至少提供一个查询条件（拼音信息、笔画位置或偏旁部首）"
        
        # 收集所有符合条件的结果
        all_results = []
        
        # 处理偏旁列表，去除数量信息
        clean_radicals = None
        if radicals:
            clean_radicals = []
            for radical in radicals:
                # 如果偏旁包含数量信息（格式如"口 (542字)"），提取纯偏旁名称
                if ' (' in radical and radical.endswith('字)'):
                    clean_radical = radical.split(' (')[0]
                    clean_radicals.append(clean_radical)
                else:
                    # 否则直接使用原偏旁名称
                    clean_radicals.append(radical)
        
        # 先通过拼音条件或偏旁条件筛选
        if has_pinyin_conditions or has_radicals:
            pinyin_results, _ = searcher.search_characters(strokes, initial, final, tone, "", clean_radicals, max_results * 2)
            all_results = pinyin_results
        else:
            # 如果没有拼音条件和偏旁条件，获取所有汉字
            all_results = searcher.words_data
        
        # 再通过笔画位置条件筛选
        if has_stroke_positions:
            filtered_results = []
            for word_info in all_results:
                if searcher._matches_stroke_positions(word_info, stroke_positions):
                    filtered_results.append(word_info)
            all_results = filtered_results
        
        if not all_results:
            # 生成条件描述
            conditions = []
            if strokes and strokes.strip():
                conditions.append(f"笔画数: {strokes}")
            if initial and initial.strip():
                conditions.append(f"声母: {initial}")
            if final and final.strip():
                conditions.append(f"韵母: {final}")
            if tone and tone.strip():
                tone_names = {'1': '一声', '2': '二声', '3': '三声', '4': '四声', '5': '轻声'}
                tone_name = tone_names.get(tone, f"{tone}声")
                conditions.append(f"音调: {tone_name}")
            if has_radicals:
                # 显示时也使用清理后的偏旁名称
                display_radicals = [r.split(' (')[0] if ' (' in r and r.endswith('字)') else r for r in radicals]
                conditions.append(f"偏旁: {', '.join(display_radicals)}")
            if has_stroke_positions:
                stroke_conds = []
                for pos in sorted(stroke_positions.keys()):
                    stroke_conds.append(f"第{pos}画={stroke_positions[pos]}")
                conditions.append(", ".join(stroke_conds))
            
            condition_str = " | ".join(conditions)
            return f"❌ 未找到符合条件 [{condition_str}] 的汉字"
        
        # 记录总结果数
        total_count = len(all_results)
        
        # 按笔画数从少到多排序，笔画数相同的按释义长度排序
        all_results.sort(key=lambda x: (
            int(x.get('strokes', '0')) if x.get('strokes', '0').isdigit() else 999,
            -len(x.get('explanation', ''))
        ))
        
        # 限制结果数量
        limited_results = all_results[:max_results]
        
        # 格式化输出结果
        conditions = []
        if strokes and strokes.strip():
            conditions.append(f"笔画数: {strokes}")
        if initial and initial.strip():
            conditions.append(f"声母: {initial}")
        if final and final.strip():
            conditions.append(f"韵母: {final}")
        if tone and tone.strip():
            tone_names = {'1': '一声', '2': '二声', '3': '三声', '4': '四声', '5': '轻声'}
            tone_name = tone_names.get(tone, f"{tone}声")
            conditions.append(f"音调: {tone_name}")
        if has_radicals:
            conditions.append(f"偏旁: {', '.join(radicals)}")
        if has_stroke_positions:
            stroke_conds = []
            for pos in sorted(stroke_positions.keys()):
                stroke_conds.append(f"第{pos}画={stroke_positions[pos]}")
            conditions.append(", ".join(stroke_conds))
        
        condition_str = " | ".join(conditions)
        
        if total_count > len(limited_results):
            output_lines = [f"🔍 找到 {total_count} 个符合条件 [{condition_str}] 的汉字，显示前 {len(limited_results)} 个:\n"]
        else:
            output_lines = [f"🔍 找到 {len(limited_results)} 个符合条件 [{condition_str}] 的汉字:\n"]
        
        # 添加查询条件说明
        output_lines.append(f"📋 查询条件: {condition_str}\n")
        
        # 格式化汉字结果
        output_lines.append("📝 查询结果:")
        for i, word_info in enumerate(limited_results, 1):
            word = word_info.get('word', '?')
            
            # 获取拼音信息
            pinyin_list = word_info.get('pinyin_list', [])
            if not pinyin_list:
                pinyin_list = [word_info.get('pinyin', '无')]
            
            # 过滤并合并所有符合标准的读音显示
            standard_initials = {
                'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
            }
            standard_finals = {
                'a', 'o', 'e', 'i', 'u', 'v', 'er', 
                'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
                'iao', 'iou', 'uai', 'uei', 
                'an', 'ian', 'uan', 'van', 
                'en', 'in', 'vn', 
                'ang', 'iang', 'uang', 
                'eng', 'ing', 
                'ong', 'iong'
            }
            
            all_pinyins = []
            for p in pinyin_list:
                if p:
                    for py in [py.strip() for py in p.split(',')]:
                        if _is_valid_standard_pinyin(py, standard_initials, standard_finals):
                            all_pinyins.append(py)
            
            # 去重但保持顺序，显示多音字的所有读音
            seen = set()
            unique_pinyins = []
            for py in all_pinyins:
                if py not in seen:
                    seen.add(py)
                    unique_pinyins.append(py)
            
            # 如果有多个读音，用特殊格式标记多音字
            if len(unique_pinyins) > 1:
                pinyin_display = f"[多音字] {' / '.join(unique_pinyins)}"
            elif unique_pinyins:
                pinyin_display = unique_pinyins[0]
            else:
                pinyin_display = '无'
            
            strokes_info = word_info.get('strokes', '?')
            radical = word_info.get('radicals', '?')
            
            # 获取笔顺信息并高亮匹配的位置
            order_simple = word_info.get('order_simple', [])
            stroke_order_display = ''
            if order_simple:
                # 创建高亮显示的笔顺
                highlighted_strokes = []
                for idx, stroke in enumerate(order_simple):
                    position = idx + 1  # 转换为1开始的位置
                    if has_stroke_positions and position in stroke_positions:
                        highlighted_strokes.append(f"[{stroke}]")  # 高亮匹配的笔画
                    else:
                        highlighted_strokes.append(stroke)
                
                if len(order_simple) <= 10:
                    stroke_order_display = f", 笔顺: {'→'.join(highlighted_strokes)}"
                else:
                    # 对于长笔顺，显示前几画和匹配的位置
                    display_strokes = highlighted_strokes[:8]
                    stroke_order_display = f", 笔顺: {'→'.join(display_strokes)}→...共{len(order_simple)}笔"
            
            explanation = word_info.get('explanation', '')
            if explanation:
                explanation = ' '.join(line.strip() for line in explanation.split('\n') if line.strip())
                if len(explanation) > 200:
                    explanation = explanation[:200] + '...'
            else:
                explanation = '无释义'
            
            output_lines.append(f"  {i:2d}. {word} ({pinyin_display}, {strokes_info}笔, 部首:{radical}{stroke_order_display})")
            output_lines.append(f"     {explanation}")
        
        return '\n'.join(output_lines)
    
    except Exception as e:
        return f"❌ 查询出错: {str(e)}"


def process_pinyin_search(strokes: str, initial: str, final: str, tone: str, 
                         stroke_name: str = '', max_results: int = 100) -> str:
    """
    处理拼音查汉字请求
    
    Args:
        strokes: 笔画数
        initial: 声母
        final: 韵母
        tone: 音调
        stroke_name: 笔画名称
        max_results: 最大结果数
        
    Returns:
        查询结果字符串
    """
    try:
        searcher = PinyinSearcher()
        
        # 检查是否至少提供了一个查询条件
        if not any([strokes and strokes.strip(), 
                   initial and initial.strip(), 
                   final and final.strip(), 
                   tone and tone.strip(),
                   stroke_name and stroke_name.strip()]):
            return "❌ 请至少提供一个查询条件（笔画数、声母、韵母、音调或笔画名称）"
        
        results, total_count = searcher.search_characters(strokes, initial, final, tone, stroke_name, max_results)
        
        if not results:
            return "❌ 未找到符合条件的汉字"
        
        # 格式化输出结果
        if total_count > len(results):
            output_lines = [f"🔍 找到 {total_count} 个符合条件的汉字，显示前 {len(results)} 个:\n"]
        else:
            output_lines = [f"🔍 找到 {len(results)} 个符合条件的汉字:\n"]
        
        # 添加查询条件说明
        conditions = []
        if strokes and strokes.strip():
            conditions.append(f"笔画数: {strokes}")
        if initial and initial.strip():
            conditions.append(f"声母: {initial}")
        if final and final.strip():
            conditions.append(f"韵母: {final}")
        if tone and tone.strip():
            tone_names = {'1': '一声', '2': '二声', '3': '三声', '4': '四声', '5': '轻声'}
            tone_name = tone_names.get(tone, f"{tone}声")
            conditions.append(f"音调: {tone_name}")
        if stroke_name and stroke_name.strip():
            conditions.append(f"包含笔画: {stroke_name}")
        
        if conditions:
            output_lines.append(f"📋 查询条件: {' | '.join(conditions)}\n")
        
        # 格式化汉字结果
        output_lines.append("📝 查询结果:")
        for i, word_info in enumerate(results, 1):
            word = word_info.get('word', '?')
            # 使用拼音列表，如果没有则回退到原始pinyin字段
            pinyin_list = word_info.get('pinyin_list', [])
            if not pinyin_list:
                pinyin_list = [word_info.get('pinyin', '无')]
            
            # 过滤并合并所有符合标准的读音显示
            standard_initials = {
                'b', 'p', 'm', 'f', 'z', 'c', 's', 'd', 't', 'n', 'l', 
                'zh', 'ch', 'sh', 'r', 'j', 'q', 'x', 'h', 'k', 'g', 'y', 'w'
            }
            standard_finals = {
                'a', 'o', 'e', 'i', 'u', 'v', 'er', 
                'ai', 'ei', 'ao', 'ou', 'ia', 'ie', 'ua', 'uo', 've', 
                'iao', 'iou', 'uai', 'uei', 
                'an', 'ian', 'uan', 'van', 
                'en', 'in', 'vn', 
                'ang', 'iang', 'uang', 
                'eng', 'ing', 
                'ong', 'iong'
            }
            
            all_pinyins = []
            for p in pinyin_list:
                if p:
                    for py in [py.strip() for py in p.split(',')]:
                        # 简单验证：去除音调后检查是否符合标准
                        if _is_valid_standard_pinyin(py, standard_initials, standard_finals):
                            all_pinyins.append(py)
            
            # 去重但保持顺序，显示多音字的所有读音
            seen = set()
            unique_pinyins = []
            for py in all_pinyins:
                if py not in seen:
                    seen.add(py)
                    unique_pinyins.append(py)
            
            # 如果有多个读音，用特殊格式标记多音字
            if len(unique_pinyins) > 1:
                pinyin_display = f"[多音字] {' / '.join(unique_pinyins)}"
            elif unique_pinyins:
                pinyin_display = unique_pinyins[0]
            else:
                pinyin_display = '无'
            
            strokes_info = word_info.get('strokes', '?')
            radical = word_info.get('radicals', '?')
            
            # 获取笔顺信息
            order_simple = word_info.get('order_simple', [])
            stroke_order_display = ''
            if order_simple:
                if len(order_simple) <= 10:
                    stroke_order_display = f", 笔顺: {'→'.join(order_simple)}"
                else:
                    stroke_order_display = f", 笔顺: {'→'.join(order_simple[:8])}→...共{len(order_simple)}笔"
            
            explanation = word_info.get('explanation', '')
            if explanation:
                # 删除空行，合并多行为一行，用空格分隔
                explanation = ' '.join(line.strip() for line in explanation.split('\n') if line.strip())
                # 如果释义太长则截断
                if len(explanation) > 200:
                    explanation = explanation[:200] + "..."
            else:
                explanation = "无释义"
            
            # 添加字与字之间的分割线（除了第一个字）
            if i > 1:
                output_lines.append("     " + "─" * 60)
            
            output_lines.append(
                f"{i:3d}. {word} ({pinyin_display}, {strokes_info}笔, 部首:{radical}{stroke_order_display})"
            )
            output_lines.append(f"     释义: {explanation}")
        
        if total_count > len(results):
            output_lines.append(f"\n💡 共找到 {total_count} 个结果，已显示前 {len(results)} 个最相关的汉字")
            output_lines.append(f"   如需查看更多结果，请调整最大结果数或细化查询条件")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"❌ 查询时发生错误: {str(e)}"


# 测试代码
if __name__ == "__main__":
    # 测试功能
    searcher = PinyinSearcher()
    
    # 测试1: 查询3笔画的字
    print("=== 测试1: 查询3笔画的字 ===")
    result = process_pinyin_search("3", "", "", "", "", 10)
    print(result)
    
    print("\n=== 测试2: 查询声母为'zh'的字 ===")
    result = process_pinyin_search("", "zh", "", "", "", 10)
    print(result)
    
    print("\n=== 测试3: 查询韵母为'ang'四声的字 ===")
    result = process_pinyin_search("", "", "ang", "4", "", 10)
    print(result)
    
    print("\n=== 测试4: 查询包含'横'笔画的字 ===")
    result = process_pinyin_search("", "", "", "", "横", 10)
    print(result)
    
    print("\n=== 测试5: 查询3笔画且包含'撇'的字 ===")
    result = process_pinyin_search("3", "", "", "", "撇", 10)
    print(result)
    
    # 显示可用的笔画名称
    print("\n=== 可用的笔画名称 ===")
    stroke_names = searcher.get_available_stroke_names()
    print(f"共有 {len(stroke_names)-1} 种笔画: {', '.join(stroke_names[1:15])}..." if len(stroke_names) > 15 else f"笔画: {', '.join(stroke_names[1:])}")
