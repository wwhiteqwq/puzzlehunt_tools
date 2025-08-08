#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词库预处理模块 - 简化版（无emoji）
将词库数据预处理成(词语,读音)配对，存储到本地以提高查询效率
"""

import json
import os
import pickle
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class VocabularyPreprocessor:
    """词库预处理器"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存文件路径
        self.word_pinyin_cache = self.cache_dir / "word_pinyin_pairs.pkl"
        self.character_info_cache = self.cache_dir / "character_info.pkl"
        
        # 数据存储
        self.word_pinyin_pairs: Dict[str, List[str]] = {}
        self.character_info: Dict[str, Dict] = {}
        
        # 高效查询索引（预处理后构建）
        self.words_by_initial: Dict[str, List[str]] = {}  # 按声母索引
        self.words_by_final: Dict[str, List[str]] = {}    # 按韵母索引
        self.words_by_length: Dict[int, List[str]] = {}   # 按长度索引
        self.words_by_stroke_count: Dict[int, List[str]] = {}  # 按笔画数索引
        self.words_by_radical: Dict[str, List[str]] = {}  # 按部首索引
        self.words_by_tone: Dict[str, List[str]] = {}     # 按声调索引
        self.sorted_words_by_pinyin: List[Tuple[str, str]] = []  # (word, pinyin) 按拼音排序
        self.sorted_words_by_reversed_pinyin: List[Tuple[str, str]] = []  # 按反向拼音排序
        self.sorted_words_by_stroke_count: List[Tuple[str, int]] = []  # (word, total_strokes) 按笔画数排序
        self.sorted_words_by_radical: List[Tuple[str, str]] = []  # (word, radical) 按部首排序
        
        # 自动预处理词库数据
        self.preprocess_vocabulary()
    
    def preprocess_vocabulary(self, force_rebuild: bool = False) -> bool:
        """
        预处理词库数据
        
        Args:
            force_rebuild: 是否强制重建缓存
            
        Returns:
            是否成功预处理
        """
        
        # 检查缓存是否存在且不强制重建
        if not force_rebuild and self._load_from_cache():
            print(f"[OK] 从缓存加载: {len(self.word_pinyin_pairs)} 个词汇, {len(self.character_info)} 个字符")
            return True
        
        print("[INFO] 开始预处理词库数据...")
        
        # 先处理字符数据，再处理词库数据
        success = self._process_character_data() and self._process_ci_data() and self._generate_word_pinyins()
        
        if success:
            # 构建高效查询索引
            self._build_query_indexes()
            # 保存到缓存
            self._save_to_cache()
            print(f"[OK] 预处理完成: {len(self.word_pinyin_pairs)} 个词汇, {len(self.character_info)} 个字符")
            return True
        else:
            print("[ERROR] 预处理失败")
            return False
    
    def _process_ci_data(self) -> bool:
        """处理词库数据(ci.json)"""
        try:
            ci_path = Path("chinese/chinese-xinhua/data/ci.json")
            if not ci_path.exists():
                print(f"[WARNING] 未找到词库文件: {ci_path}")
                return False
            
            print(f"[INFO] 处理词库文件: {ci_path}")
            
            with open(ci_path, 'r', encoding='utf-8') as f:
                ci_data = json.load(f)
            
            processed_count = 0
            
            for item in ci_data:
                word = item.get('ci', '').strip()
                if not word or len(word) < 2:
                    continue
                
                # 对于ci.json，我们需要使用字符信息来生成拼音
                # 暂时先收集所有词汇，稍后使用字符信息生成拼音
                self.word_pinyin_pairs[word] = []  # 先占位，稍后填充拼音
                processed_count += 1
            
            print(f"   处理词汇: {processed_count} 个")
            return True
            
        except Exception as e:
            print(f"[ERROR] 处理词库数据失败: {e}")
            return False
    
    def _process_character_data(self) -> bool:
        """处理字符数据"""
        try:
            # 尝试从拼音搜索器获取字符信息
            from chinese.src.pinyin_searcher import PinyinSearcher
            
            searcher = PinyinSearcher()
            
            processed_count = 0
            
            for word_data in searcher.words_data:
                if not word_data or not word_data.get('word'):
                    continue
                
                char = word_data.get('word')
                if len(char) == 1:  # 只处理单字符
                    stroke_str = word_data.get('strokes', '0')
                    try:
                        stroke_int = int(stroke_str)
                    except (ValueError, TypeError):
                        stroke_int = 0
                    
                    self.character_info[char] = {
                        'pinyin': word_data.get('pinyin', ''),
                        'pinyin_list': word_data.get('pinyin_list', []),
                        'strokes': stroke_int,  # 统一使用strokes字段名
                        'radical': word_data.get('radicals', ''),  # 修正字段名：radical -> radicals
                        'order_simple': word_data.get('order_simple', [])
                    }
                    processed_count += 1
                    
                    # 调试信息：显示前几个字符的处理结果
                    if processed_count <= 5:
                        print(f"   调试 - 字符{char}: strokes='{stroke_str}' -> strokes={stroke_int}")
            
            print(f"   处理字符: {processed_count} 个")
            return True
            
        except Exception as e:
            print(f"[ERROR] 处理字符数据失败: {e}")
            return False
    
    def _generate_word_pinyins(self) -> bool:
        """根据字符信息生成词汇拼音"""
        try:
            print("[INFO] 生成词汇拼音...")
            
            generated_count = 0
            
            for word in list(self.word_pinyin_pairs.keys()):
                pinyins = []
                
                # 为每个字符获取拼音
                for char in word:
                    char_info = self.character_info.get(char)
                    if char_info:
                        char_pinyin = char_info.get('pinyin', '')
                        if char_pinyin:
                            pinyins.append(char_pinyin)
                        elif char_info.get('pinyin_list'):
                            # 使用第一个拼音
                            pinyins.append(char_info['pinyin_list'][0])
                    else:
                        # 字符信息不存在，跳过这个词
                        pinyins = []
                        break
                
                if pinyins and len(pinyins) == len(word):
                    # 组合成完整的词汇拼音
                    word_pinyin = ' '.join(pinyins)
                    self.word_pinyin_pairs[word] = [word_pinyin]
                    generated_count += 1
                else:
                    # 无法生成完整拼音，移除这个词
                    del self.word_pinyin_pairs[word]
            
            print(f"   生成拼音: {generated_count} 个")
            return True
            
        except Exception as e:
            print(f"[ERROR] 生成词汇拼音失败: {e}")
            return False
    
    def _build_query_indexes(self):
        """构建高效查询索引"""
        print("[INFO] 构建查询索引...")
        
        # 清空所有索引
        self.words_by_initial.clear()
        self.words_by_final.clear()
        self.words_by_length.clear()
        self.words_by_stroke_count.clear()
        self.words_by_radical.clear()
        self.words_by_tone.clear()
        
        # 拼音排序列表
        pinyin_word_pairs = []
        reversed_pinyin_word_pairs = []
        
        for word, pinyins in self.word_pinyin_pairs.items():
            if not pinyins:
                continue
                
            # 使用第一个拼音进行索引
            pinyin = pinyins[0]
            
            # 按长度索引
            word_len = len(word)
            if word_len not in self.words_by_length:
                self.words_by_length[word_len] = []
            self.words_by_length[word_len].append(word)
            
            # 按笔画数索引（第一个字的笔画数）
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                stroke_count = char_info.get('strokes', 0)  # 使用strokes字段
                if stroke_count > 0:
                    if stroke_count not in self.words_by_stroke_count:
                        self.words_by_stroke_count[stroke_count] = []
                    self.words_by_stroke_count[stroke_count].append(word)
            
            # 按部首索引（第一个字的部首）
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                radical = char_info.get('radical', '')
                if radical:
                    if radical not in self.words_by_radical:
                        self.words_by_radical[radical] = []
                    self.words_by_radical[radical].append(word)
            
            # 解析拼音获取声母、韵母、声调
            pinyin_parts = pinyin.split()
            if not pinyin_parts:
                continue
            
            # 第一个字的声母、韵母、声调用于快速筛选
            first_pinyin = pinyin_parts[0].strip()
            if first_pinyin:
                # 提取声母和韵母
                initial, final = self._extract_initial_final(first_pinyin)
                
                # 按声母索引
                if initial and initial not in self.words_by_initial:
                    self.words_by_initial[initial] = []
                if initial:
                    self.words_by_initial[initial].append(word)
                
                # 按韵母索引
                if final and final not in self.words_by_final:
                    self.words_by_final[final] = []
                if final:
                    self.words_by_final[final].append(word)
                
                # 按声调索引（第一个字的声调）
                tone = self._extract_tone(first_pinyin)
                if tone:
                    if tone not in self.words_by_tone:
                        self.words_by_tone[tone] = []
                    self.words_by_tone[tone].append(word)
            
            # 为二分查找准备排序数据
            pinyin_word_pairs.append((word, pinyin))
            
            # 构建反向拼音：每个字符位置反转，但保持字符顺序
            reversed_pinyin = self._build_reversed_pinyin(pinyin_parts)
            reversed_pinyin_word_pairs.append((word, reversed_pinyin))
        
        # 按拼音排序（用于声母二分查找）
        self.sorted_words_by_pinyin = sorted(pinyin_word_pairs, key=lambda x: x[1])
        
        # 按反向拼音排序（用于韵母二分查找）
        self.sorted_words_by_reversed_pinyin = sorted(reversed_pinyin_word_pairs, key=lambda x: x[1])
        
        # 预计算笔画数排序数据
        print("[INFO] 预计算笔画数排序...")
        stroke_word_pairs = []
        for word in self.word_pinyin_pairs:
            total_strokes = 0
            for char in word:
                char_info = self.character_info.get(char, {})
                total_strokes += char_info.get('strokes', 0)  # 使用strokes字段
            stroke_word_pairs.append((word, total_strokes))
        
        # 按总笔画数排序
        self.sorted_words_by_stroke_count = sorted(stroke_word_pairs, key=lambda x: x[1])
        
        # 预计算部首排序数据
        print("[INFO] 预计算部首排序...")
        radical_word_pairs = []
        for word in self.word_pinyin_pairs:
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                radical = char_info.get('radical', '')
                radical_word_pairs.append((word, radical))
        
        # 按首字部首排序
        self.sorted_words_by_radical = sorted(radical_word_pairs, key=lambda x: x[1])
        
        print(f"   声母索引: {len(self.words_by_initial)} 种")
        print(f"   韵母索引: {len(self.words_by_final)} 种") 
        print(f"   长度索引: {len(self.words_by_length)} 种")
        print(f"   笔画索引: {len(self.words_by_stroke_count)} 种")
        print(f"   部首索引: {len(self.words_by_radical)} 种")
        print(f"   声调索引: {len(self.words_by_tone)} 种")
        print(f"   拼音排序: {len(self.sorted_words_by_pinyin)} 个词")
        print(f"   笔画排序: {len(self.sorted_words_by_stroke_count)} 个词")
        print(f"   部首排序: {len(self.sorted_words_by_radical)} 个词")
    
    def _extract_initial_final(self, pinyin: str) -> Tuple[str, str]:
        """从拼音中提取声母和韵母（与pinyin_tools.py保持一致）"""
        # 标准声母列表（与pinyin_tools.py一致，包含Unicode字符ɡ）
        initials = ['zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 
                   'ɡ', 'k', 'h', 'j', 'q', 'x', 'z', 'c', 's', 'r', 'y', 'w']
        
        # 去除音调标记，但保留ɡ字符，并标准化ü为v
        import unicodedata
        clean_pinyin = ''.join(c for c in unicodedata.normalize('NFD', pinyin) 
                              if unicodedata.category(c) != 'Mn' and (c.isalpha() or c == 'ɡ'))
        clean_pinyin = clean_pinyin.lower()
        
        # 标准化：ü -> v（与汉字搜索保持一致）
        clean_pinyin = clean_pinyin.replace('ü', 'v')
        
        # 查找声母
        initial = ""
        for init in sorted(initials, key=len, reverse=True):  # 长的优先匹配
            if clean_pinyin.startswith(init):
                initial = init
                break
        
        # 剩余部分为韵母
        final = clean_pinyin[len(initial):] if initial else clean_pinyin
        
        # 标准化韵母：确保与汉字搜索的韵母格式一致
        final_mappings = {
            'uei': 'ui',  # uei -> ui
            'iou': 'iu',  # iou -> iu
            'ue': 've',   # ue -> ve (界面输入ue，存储为ve)
        }
        if final in final_mappings:
            final = final_mappings[final]
        
        return initial, final
    
    def _extract_tone(self, pinyin: str) -> str:
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
        
        # 检查声调符号
        for char in pinyin:
            if char in tone_map:
                return tone_map[char]
        
        # 检查数字声调（如xue2）
        import re
        tone_match = re.search(r'(\d)$', pinyin)
        if tone_match:
            return tone_match.group(1)
        
        return '5'  # 轻声或无声调
    
    def _save_to_cache(self):
        """保存到缓存文件"""
        try:
            with open(self.word_pinyin_cache, 'wb') as f:
                pickle.dump(self.word_pinyin_pairs, f)
            
            with open(self.character_info_cache, 'wb') as f:
                pickle.dump(self.character_info, f)
            
            # 保存索引数据
            index_cache = self.cache_dir / "query_indexes.pkl"
            index_data = {
                'words_by_initial': self.words_by_initial,
                'words_by_final': self.words_by_final,
                'words_by_length': self.words_by_length,
                'words_by_stroke_count': self.words_by_stroke_count,
                'words_by_radical': self.words_by_radical,
                'words_by_tone': self.words_by_tone,
                'sorted_words_by_pinyin': self.sorted_words_by_pinyin,
                'sorted_words_by_reversed_pinyin': self.sorted_words_by_reversed_pinyin,
                'sorted_words_by_stroke_count': self.sorted_words_by_stroke_count,
                'sorted_words_by_radical': self.sorted_words_by_radical
            }
            with open(index_cache, 'wb') as f:
                pickle.dump(index_data, f)
            
            print(f"[OK] 缓存已保存到: {self.cache_dir}")
            
        except Exception as e:
            print(f"[ERROR] 保存缓存失败: {e}")
    
    def _load_from_cache(self) -> bool:
        """从缓存文件加载"""
        try:
            index_cache = self.cache_dir / "query_indexes.pkl"
            
            if not self.word_pinyin_cache.exists() or not self.character_info_cache.exists() or not index_cache.exists():
                return False
            
            with open(self.word_pinyin_cache, 'rb') as f:
                self.word_pinyin_pairs = pickle.load(f)
            
            with open(self.character_info_cache, 'rb') as f:
                self.character_info = pickle.load(f)
            
            # 加载索引数据
            with open(index_cache, 'rb') as f:
                index_data = pickle.load(f)
                self.words_by_initial = index_data.get('words_by_initial', {})
                self.words_by_final = index_data.get('words_by_final', {})
                self.words_by_length = index_data.get('words_by_length', {})
                self.words_by_stroke_count = index_data.get('words_by_stroke_count', {})
                self.words_by_radical = index_data.get('words_by_radical', {})
                self.words_by_tone = index_data.get('words_by_tone', {})
                self.sorted_words_by_pinyin = index_data.get('sorted_words_by_pinyin', [])
                self.sorted_words_by_reversed_pinyin = index_data.get('sorted_words_by_reversed_pinyin', [])
                self.sorted_words_by_stroke_count = index_data.get('sorted_words_by_stroke_count', [])
                self.sorted_words_by_radical = index_data.get('sorted_words_by_radical', [])
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 加载缓存失败: {e}")
            return False
    
    def get_word_pinyin(self, word: str) -> List[str]:
        """获取词汇的拼音列表"""
        return self.word_pinyin_pairs.get(word, [])
    
    def get_character_info(self, char: str) -> Optional[Dict]:
        """获取字符信息"""
        return self.character_info.get(char)
    
    def get_all_words(self) -> List[str]:
        """获取所有词汇"""
        return list(self.word_pinyin_pairs.keys())
    
    def filter_words_by_stroke_count_fast(self, stroke_count: int) -> List[str]:
        """按笔画数快速筛选词汇（第一个字的笔画数）"""
        return self.words_by_stroke_count.get(stroke_count, [])
    
    def filter_words_by_radical_fast(self, radical: str) -> List[str]:
        """按部首快速筛选词汇（第一个字的部首）"""
        return self.words_by_radical.get(radical, [])
    
    def filter_words_by_tone_fast(self, tone: str) -> List[str]:
        """按声调快速筛选词汇（第一个字的声调）"""
        return self.words_by_tone.get(tone, [])
    
    def filter_words_by_length(self, min_length: int = 2, max_length: int = 10) -> List[str]:
        """按长度筛选词汇"""
        result = []
        for length in range(min_length, max_length + 1):
            result.extend(self.words_by_length.get(length, []))
        return result
    
    def filter_words_by_initial_fast(self, initial: str) -> List[str]:
        """快速按声母筛选词汇"""
        return self.words_by_initial.get(initial, [])
    
    def filter_words_by_final_fast(self, final: str) -> List[str]:
        """快速按韵母筛选词汇（使用真正的二分搜索）"""
        # 优先尝试索引查找（最快）
        if final in self.words_by_final:
            return self.words_by_final[final]
        
        # 标准化查找：将标准韵母转换为Unicode格式
        final_mappings = {
            'ang': 'anɡ',
            'eng': 'enɡ', 
            'ing': 'inɡ',
            'ong': 'onɡ',
            'iang': 'ianɡ',
            'uang': 'uanɡ',
            'ueng': 'uenɡ',
            'iong': 'ionɡ',
            'ue': 've',  # 用户输入ue，查找存储的ve
            've': 've'   # 用户输入ve，查找存储的ve（直接匹配）
        }
        
        unicode_final = final_mappings.get(final, final)
        if unicode_final in self.words_by_final:
            return self.words_by_final[unicode_final]
        
        # 使用二分搜索在reverse拼音中查找韵母
        print(f"   使用二分搜索查找韵母: {final}")
        return self._binary_search_by_final(final)
    
    def filter_words_by_character_finals_fast(self, character_finals: List[str]) -> List[str]:
        """
        快速按多个字符位置的韵母筛选词汇
        
        Args:
            character_finals: 每个字符位置的韵母要求
            
        Returns:
            符合条件的词汇列表
        """
        if not character_finals:
            return self.get_all_words()
        
        # 找到第一个非空韵母条件进行初步筛选
        initial_candidates = None
        first_filter_pos = -1
        
        for i, final in enumerate(character_finals):
            if final and final.strip():
                initial_candidates = self.filter_words_by_final_fast(final.strip())
                first_filter_pos = i
                break
        
        if initial_candidates is None:
            return self.get_all_words()
        
        # 对初步筛选结果进行逐字符验证
        result = []
        for word in initial_candidates:
            if len(word) != len(character_finals):
                continue
                
            pinyins = self.get_word_pinyin(word)
            if not pinyins:
                continue
                
            # 解析词汇的每个字符拼音
            pinyin_parts = pinyins[0].split()
            if len(pinyin_parts) != len(character_finals):
                continue
            
            # 检查每个位置的韵母是否匹配
            match = True
            for j, (required_final, char_pinyin) in enumerate(zip(character_finals, pinyin_parts)):
                if required_final and required_final.strip():
                    _, actual_final = self._extract_initial_final(char_pinyin)
                    if actual_final != required_final.strip():
                        match = False
                        break
            
            if match:
                result.append(word)
        
        return result
    
    def _binary_search_by_final(self, final: str) -> List[str]:
        """
        使用二分搜索在反向拼音中查找韵母
        这是真正的二分搜索实现，查找效率O(log n)
        """
        import bisect
        
        if not self.sorted_words_by_reversed_pinyin or not final:
            return []
        
        print(f"     在{len(self.sorted_words_by_reversed_pinyin)}个反向拼音中二分查找韵母'{final}'")
        
        # 标准化目标韵母
        normalized_final = self._normalize_final(final)
        
        # 提取反向拼音列表用于二分查找
        reversed_pinyins = [item[1] for item in self.sorted_words_by_reversed_pinyin]
        
        # 二分查找第一个匹配的位置
        # 查找以韵母开头的反向拼音
        left = bisect.bisect_left(reversed_pinyins, normalized_final)
        
        # 查找最后一个匹配的位置
        # 使用字符递增技巧找到范围结束
        if normalized_final:
            next_char = normalized_final[:-1] + chr(ord(normalized_final[-1]) + 1)
        else:
            next_char = 'z'
        right = bisect.bisect_left(reversed_pinyins, next_char)
        
        result = []
        
        # 在二分查找范围内验证匹配
        for i in range(left, right):
            if i >= len(self.sorted_words_by_reversed_pinyin):
                break
                
            word, reversed_pinyin = self.sorted_words_by_reversed_pinyin[i]
            
            # 检查反向拼音是否以韵母开头
            if reversed_pinyin.startswith(normalized_final):
                # 进一步验证：检查实际韵母
                pinyins = self.get_word_pinyin(word)
                if pinyins:
                    pinyin_parts = pinyins[0].split()
                    if pinyin_parts:
                        # 检查第一个字符的韵母
                        _, actual_final = self._extract_initial_final(pinyin_parts[0])
                        if self._normalize_final(actual_final) == normalized_final:
                            result.append(word)
            elif not reversed_pinyin.startswith(normalized_final[:1]):
                # 如果连第一个字符都不匹配，可以提前退出
                break
        
        print(f"     二分搜索结果: {len(result)} 个匹配词汇")
        return result
    
    def _normalize_final(self, final: str) -> str:
        """标准化韵母格式以支持灵活匹配"""
        if not final:
            return ''
        # 处理Unicode ɡ字符
        normalized = final.replace('ɡ', 'g')
        # 处理ue <-> ve双向转换
        if normalized == 've':
            normalized = 'ue'
        return normalized
    
    def _build_reversed_pinyin(self, pinyin_parts: List[str]) -> str:
        """
        构建用于韵母二分查找的反向拼音字符串
        
        例如：['gao', 'xing'] -> 'ao_ing'
        这样韵母在前面，便于韵母的二分查找
        
        Args:
            pinyin_parts: 词汇的各字符拼音列表
            
        Returns:
            反向拼音字符串，韵母在前
        """
        reversed_parts = []
        
        for pinyin in pinyin_parts:
            if pinyin:
                initial, final = self._extract_initial_final(pinyin.strip())
                # 构建：韵母_声母的格式，便于韵母查找
                if final:
                    if initial:
                        reversed_parts.append(f"{final}_{initial}")
                    else:
                        reversed_parts.append(final)
                else:
                    # 如果没有韵母，保持原拼音
                    reversed_parts.append(pinyin.strip())
        
        return ' '.join(reversed_parts)
    
    def binary_search_by_stroke_count(self, stroke_count: int) -> List[str]:
        """
        使用二分搜索按笔画数快速查找词汇
        
        Args:
            stroke_count: 目标笔画数（总笔画数）
            
        Returns:
            匹配的词汇列表
        """
        import bisect
        
        if not self.sorted_words_by_stroke_count:
            print("[WARNING] 笔画排序数据不存在，回退到慢速查找")
            return self.filter_words_by_stroke_count_fast(stroke_count)
        
        print(f"   使用二分搜索查找总笔画数为{stroke_count}的词汇")
        
        # 提取笔画数列表用于二分查找
        stroke_counts = [item[1] for item in self.sorted_words_by_stroke_count]
        
        # 二分查找第一个匹配的位置
        left = bisect.bisect_left(stroke_counts, stroke_count)
        
        # 二分查找最后一个匹配的位置
        right = bisect.bisect_right(stroke_counts, stroke_count)
        
        # 提取匹配的词汇
        result = []
        for i in range(left, right):
            if i < len(self.sorted_words_by_stroke_count):
                word, actual_strokes = self.sorted_words_by_stroke_count[i]
                if actual_strokes == stroke_count:
                    result.append(word)
        
        print(f"   二分搜索结果: {len(result)} 个匹配词汇")
        return result
    
    def binary_search_by_character_stroke_count(self, character_position: int, stroke_count: int) -> List[str]:
        """
        使用二分搜索查找指定位置字符有指定笔画数的词汇
        
        Args:
            character_position: 字符位置（0开始）
            stroke_count: 字符笔画数
            
        Returns:
            匹配的词汇列表
        """
        print(f"   二分搜索第{character_position+1}个字有{stroke_count}画的词汇")
        
        # 对于字符级别的筛选，我们需要遍历但可以优化
        # 首先尝试从已排序的数据中快速筛选
        if character_position == 0:
            # 第一个字的笔画数，可以直接使用索引
            return self.filter_words_by_stroke_count_fast(stroke_count)
        
        # 对于非第一个字符，需要逐个检查，但可以并行化
        matching_words = []
        total_checked = 0
        
        for word in self.word_pinyin_pairs:
            total_checked += 1
            if total_checked % 50000 == 0:
                print(f"     已检查 {total_checked} 个词汇...")
            
            if len(word) <= character_position:
                continue
                
            char = word[character_position]
            char_info = self.character_info.get(char, {})
            if char_info.get('strokes', 0) == stroke_count:  # 使用strokes字段
                matching_words.append(word)
        
        print(f"   找到 {len(matching_words)} 个匹配的词汇")
        return matching_words
    
    def binary_search_by_radical(self, radical: str) -> List[str]:
        """
        使用二分搜索按部首查找词汇
        
        Args:
            radical: 目标部首
            
        Returns:
            匹配的词汇列表
        """
        import bisect
        
        if not self.sorted_words_by_radical:
            print("[WARNING] 部首排序数据不存在，回退到索引查找")
            return self.filter_words_by_radical_fast(radical)
        
        print(f"   使用二分搜索查找部首为'{radical}'的词汇")
        
        # 提取部首列表用于二分查找
        radicals = [item[1] for item in self.sorted_words_by_radical]
        
        # 二分查找第一个匹配的位置
        left = bisect.bisect_left(radicals, radical)
        
        # 二分查找最后一个匹配的位置
        right = bisect.bisect_right(radicals, radical)
        
        # 提取匹配的词汇
        result = []
        for i in range(left, right):
            if i < len(self.sorted_words_by_radical):
                word, actual_radical = self.sorted_words_by_radical[i]
                if actual_radical == radical:
                    result.append(word)
        
        print(f"   二分搜索结果: {len(result)} 个匹配词汇")
        return result
        """
        使用二分查找按拼音前缀快速筛选
        
        Args:
            prefix: 拼音前缀
            reverse: 是否使用反向拼音（用于韵母查找）
            
        Returns:
            匹配的词汇列表
        """
        import bisect
        
        target_list = self.sorted_words_by_reversed_pinyin if reverse else self.sorted_words_by_pinyin
        
        if not target_list or not prefix:
            return []
        
        # 提取拼音值列表用于二分查找
        pinyin_values = [item[1] for item in target_list]
        
        # 查找第一个匹配的位置
        left = bisect.bisect_left(pinyin_values, prefix)
        
        # 查找最后一个匹配的位置
        prefix_next = prefix[:-1] + chr(ord(prefix[-1]) + 1) if prefix else ''
        right = bisect.bisect_left(pinyin_values, prefix_next)
        
        # 提取匹配的词汇
        result = []
        for i in range(left, right):
            if i < len(target_list) and target_list[i][1].startswith(prefix):
                result.append(target_list[i][0])
        
        return result
    
    def get_words_sorted_by_pinyin(self) -> List[str]:
        """获取按拼音排序的词汇列表"""
        if not self.sorted_words_by_pinyin:
            # 构建按拼音排序的词汇列表
            word_pinyin_list = []
            for word in self.word_pinyin_pairs:
                pinyins = self.get_word_pinyin(word)
                if pinyins:
                    # 使用首个拼音作为排序键
                    pinyin_key = pinyins[0] if isinstance(pinyins[0], str) else str(pinyins[0])
                    word_pinyin_list.append((word, pinyin_key))
            
            # 按拼音排序
            word_pinyin_list.sort(key=lambda x: x[1])
            self.sorted_words_by_pinyin = word_pinyin_list
        
        return [item[0] for item in self.sorted_words_by_pinyin]
    
    def get_words_sorted_by_stroke_count(self) -> List[str]:
        """获取按笔画数排序的词汇列表（使用预计算缓存）"""
        if self.sorted_words_by_stroke_count:
            # 使用预计算的排序数据，直接返回词汇列表
            return [item[0] for item in self.sorted_words_by_stroke_count]
        
        # 兜底：如果缓存数据不存在，则实时计算（但会很慢）
        print("[WARNING] 笔画排序缓存不存在，实时计算中...")
        word_stroke_list = []
        for word in self.word_pinyin_pairs:
            total_strokes = 0
            for char in word:
                char_info = self.character_info.get(char, {})
                total_strokes += char_info.get('strokes', 0)  # 修正：stroke -> strokes
            word_stroke_list.append((word, total_strokes))
        
        # 按总笔画数排序
        word_stroke_list.sort(key=lambda x: x[1])
        return [item[0] for item in word_stroke_list]
    
    def get_words_sorted_by_radical(self) -> List[str]:
        """获取按部首排序的词汇列表（使用预计算缓存）"""
        if self.sorted_words_by_radical:
            # 使用预计算的排序数据，直接返回词汇列表
            return [item[0] for item in self.sorted_words_by_radical]
        
        # 兜底：如果缓存数据不存在，则实时计算（但会很慢）
        print("[WARNING] 部首排序缓存不存在，实时计算中...")
        word_radical_list = []
        for word in self.word_pinyin_pairs:
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                radical = char_info.get('radical', '')
                word_radical_list.append((word, radical))
        
        # 按首字部首排序
        word_radical_list.sort(key=lambda x: x[1])
        return [item[0] for item in word_radical_list]
    
    def filter_words_by_stroke_count_fast(self, stroke_count: int) -> List[str]:
        """快速筛选指定笔画数的词汇（首字）"""
        if stroke_count in self.words_by_stroke_count:
            return self.words_by_stroke_count[stroke_count]
        
        # 如果索引中没有，实时计算
        matching_words = []
        for word in self.word_pinyin_pairs:
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                if char_info.get('strokes', 0) == stroke_count:  # 使用strokes字段
                    matching_words.append(word)
        
        return matching_words
    
    def filter_words_by_radical_fast(self, radical: str) -> List[str]:
        """快速筛选指定部首的词汇（首字）"""
        if radical in self.words_by_radical:
            return self.words_by_radical[radical]
        
        # 如果索引中没有，实时计算
        matching_words = []
        for word in self.word_pinyin_pairs:
            if word:
                first_char = word[0]
                char_info = self.character_info.get(first_char, {})
                if char_info.get('radical', '') == radical:
                    matching_words.append(word)
        
        return matching_words
    
    def filter_words_by_tone_fast(self, tone: str) -> List[str]:
        """快速筛选指定声调的词汇（首字）"""
        if tone in self.words_by_tone:
            return self.words_by_tone[tone]
        
        # 如果索引中没有，实时计算
        matching_words = []
        for word in self.word_pinyin_pairs:
            pinyins = self.get_word_pinyin(word)
            if pinyins and len(pinyins) > 0:
                first_pinyin = pinyins[0]
                word_tone = self._extract_tone_from_pinyin(first_pinyin)
                if word_tone == tone:
                    matching_words.append(word)
        
        return matching_words
    
    def _extract_tone_from_pinyin(self, pinyin: str) -> str:
        """从拼音中提取声调"""
        if not pinyin:
            return '5'
        
        # 处理字符串格式的拼音列表
        if isinstance(pinyin, str) and pinyin.startswith('[') and pinyin.endswith(']'):
            try:
                import ast
                pinyin_list = ast.literal_eval(pinyin)
                if isinstance(pinyin_list, list) and pinyin_list:
                    pinyin = pinyin_list[0]
            except:
                pinyin = pinyin.strip("[]'\"")
        
        # 声调符号映射
        tone_map = {
            'ā': '1', 'á': '2', 'ǎ': '3', 'à': '4',
            'ē': '1', 'é': '2', 'ě': '3', 'è': '4',
            'ī': '1', 'í': '2', 'ǐ': '3', 'ì': '4',
            'ō': '1', 'ó': '2', 'ǒ': '3', 'ò': '4',
            'ū': '1', 'ú': '2', 'ǔ': '3', 'ù': '4',
            'ǖ': '1', 'ǘ': '2', 'ǚ': '3', 'ǜ': '4',
            'ń': '2', 'ň': '3', 'ǹ': '4',
            'ḿ': '2'
        }
        
        # 清理拼音字符串
        clean_pinyin = str(pinyin).strip()
        
        for char in clean_pinyin:
            if char in tone_map:
                return tone_map[char]
        
        # 如果没有找到声调符号，检查是否有数字声调
        import re
        tone_match = re.search(r'(\d)$', clean_pinyin)
        if tone_match:
            return tone_match.group(1)
        
        return '5'  # 轻声或无声调
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            'total_words': len(self.word_pinyin_pairs),
            'total_characters': len(self.character_info),
            'avg_word_length': sum(len(word) for word in self.word_pinyin_pairs) / len(self.word_pinyin_pairs) if self.word_pinyin_pairs else 0
        }

def main():
    """主函数 - 执行预处理"""
    print("[INFO] 词库预处理工具")
    print("=" * 50)
    
    preprocessor = VocabularyPreprocessor()
    
    # 执行预处理
    success = preprocessor.preprocess_vocabulary(force_rebuild=True)
    
    if success:
        # 显示统计信息
        stats = preprocessor.get_stats()
        print(f"\n[STATS] 统计信息:")
        print(f"   词汇总数: {stats['total_words']:,}")
        print(f"   字符总数: {stats['total_characters']:,}")
        print(f"   平均词长: {stats['avg_word_length']:.1f}")
        
        # 显示一些样例
        all_words = preprocessor.get_all_words()
        if all_words:
            print(f"\n[SAMPLE] 词汇样例:")
            for word in all_words[:10]:
                pinyins = preprocessor.get_word_pinyin(word)
                print(f"   {word}: {pinyins}")
        
        print(f"\n[OK] 预处理完成！缓存文件已保存到 cache/ 目录")
        print(f"[INFO] 使用预处理后的数据可以大幅提升查询效率")
    
    else:
        print(f"\n[ERROR] 预处理失败，请检查数据文件是否存在")

if __name__ == '__main__':
    main()
