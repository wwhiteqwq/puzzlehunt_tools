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
        self.sorted_words_by_pinyin: List[Tuple[str, str]] = []  # (word, pinyin) 按拼音排序
        self.sorted_words_by_reversed_pinyin: List[Tuple[str, str]] = []  # 按反向拼音排序
        
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
            ci_path = Path("ci.json")
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
            from pinyin_searcher import PinyinSearcher
            
            searcher = PinyinSearcher()
            
            processed_count = 0
            
            for word_data in searcher.words_data:
                if not word_data or not word_data.get('word'):
                    continue
                
                char = word_data.get('word')
                if len(char) == 1:  # 只处理单字符
                    self.character_info[char] = {
                        'pinyin': word_data.get('pinyin', ''),
                        'pinyin_list': word_data.get('pinyin_list', []),
                        'stroke': word_data.get('stroke', 0),
                        'radical': word_data.get('radical', ''),
                        'order_simple': word_data.get('order_simple', [])
                    }
                    processed_count += 1
            
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
        
        # 按声母索引
        self.words_by_initial.clear()
        # 按韵母索引  
        self.words_by_final.clear()
        # 按长度索引
        self.words_by_length.clear()
        
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
            
            # 解析拼音获取声母和韵母
            pinyin_parts = pinyin.split()
            if not pinyin_parts:
                continue
            
            # 第一个字的声母和韵母用于快速筛选
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
            
            # 为二分查找准备排序数据
            pinyin_word_pairs.append((word, pinyin))
            reversed_pinyin_word_pairs.append((word, pinyin[::-1]))  # 反向拼音
        
        # 按拼音排序（用于声母二分查找）
        self.sorted_words_by_pinyin = sorted(pinyin_word_pairs, key=lambda x: x[1])
        
        # 按反向拼音排序（用于韵母二分查找）
        self.sorted_words_by_reversed_pinyin = sorted(reversed_pinyin_word_pairs, key=lambda x: x[1])
        
        print(f"   声母索引: {len(self.words_by_initial)} 种")
        print(f"   韵母索引: {len(self.words_by_final)} 种")
        print(f"   长度索引: {len(self.words_by_length)} 种")
        print(f"   拼音排序: {len(self.sorted_words_by_pinyin)} 个词")
    
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
                'sorted_words_by_pinyin': self.sorted_words_by_pinyin,
                'sorted_words_by_reversed_pinyin': self.sorted_words_by_reversed_pinyin
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
                self.sorted_words_by_pinyin = index_data.get('sorted_words_by_pinyin', [])
                self.sorted_words_by_reversed_pinyin = index_data.get('sorted_words_by_reversed_pinyin', [])
            
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
        """快速按韵母筛选词汇（支持标准化查找）"""
        # 直接查找
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
        return self.words_by_final.get(unicode_final, [])
    
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
    
    def binary_search_by_pinyin_prefix(self, prefix: str, reverse: bool = False) -> List[str]:
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
