"""
字谜推理器包装模块
为 Gradio 界面提供字谜推理功能的包装函数
"""

def process_character_mystery(clues, max_results=20):
    """
    处理字谜推理请求的包装函数
    
    Args:
        clues (list): 线索字符列表
        max_results (int): 最大结果数量
    
    Returns:
        str: 格式化的推理结果
    """
    try:
        from character_mystery_solver import get_analyzer
        
        # 使用全局分析器实例
        analyzer = get_analyzer()
        
        # 分析线索
        raw_results = analyzer.analyze_character_clues(clues)
        
        # 限制结果数量
        results = raw_results[:max_results] if max_results else raw_results
        
        if not results:
            return f"❌ 未找到与线索字符 {', '.join(clues)} 相关的字符"
        
        # 格式化输出
        output_lines = []
        output_lines.append(f"🔍 **字谜推理结果** (基于线索: {', '.join(clues)})")
        output_lines.append("=" * 50)
        output_lines.append("")
        
        for i, (char, match_count, example_words) in enumerate(results, 1):
            
            output_lines.append(f"**{i:2d}. 字符: {char}**")
            output_lines.append(f"    🎯 匹配度: {match_count} 次")
            
            # 显示示例词汇（限制数量避免过长）
            if example_words:
                shown_examples = example_words[:8]  # 最多显示8个示例
                examples_text = "、".join(shown_examples)
                if len(example_words) > 8:
                    examples_text += f"... (共{len(example_words)}个词)"
                output_lines.append(f"    📚 示例词汇: {examples_text}")
            else:
                output_lines.append(f"    📚 示例词汇: 无")
            
            output_lines.append("")
        
        # 添加统计信息
        output_lines.append("📊 **分析统计**")
        output_lines.append(f"- 线索字符数: {len(clues)}")
        output_lines.append(f"- 候选字符数: {len(results)}")
        output_lines.append(f"- 最高匹配度: {results[0][1] if results else 0}")
        output_lines.append(f"- 最低匹配度: {results[-1][1] if results else 0}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f"❌ 字谜推理失败:\n\n**错误信息**: {str(e)}\n\n**详细错误**:\n```\n{error_detail}\n```"


def process_character_mystery_with_positions(clues, positions, max_results=20):
    """
    处理带位置要求的字谜推理请求的包装函数
    
    Args:
        clues (list): 线索字符列表
        positions (list): 位置要求列表，0表示任意位置，其他数字表示指定位置(1-based)
        max_results (int): 最大结果数量
    
    Returns:
        str: 格式化的推理结果
    """
    try:
        from character_mystery_solver import get_analyzer
        
        # 使用全局分析器实例
        analyzer = get_analyzer()
        
        # 分析线索（带位置要求）
        raw_results = analyzer.analyze_character_clues(clues, positions)
        
        # 限制结果数量
        results = raw_results[:max_results] if max_results else raw_results
        
        if not results:
            clue_info = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in zip(clues, positions)]
            return f"❌ 未找到与线索 {', '.join(clue_info)} 相关的字符"
        
        # 格式化输出
        output_lines = []
        clue_info = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in zip(clues, positions)]
        output_lines.append(f"🔍 **字谜推理结果** (基于线索: {', '.join(clue_info)})")
        output_lines.append("=" * 50)
        output_lines.append("")
        
        for i, (char, match_count, example_words) in enumerate(results, 1):
            
            output_lines.append(f"**{i:2d}. 字符: {char}**")
            output_lines.append(f"    🎯 匹配度: {match_count} 次")
            
            # 显示示例词汇（限制数量避免过长）
            if example_words:
                shown_examples = example_words[:8]  # 最多显示8个示例
                examples_text = "、".join(shown_examples)
                if len(example_words) > 8:
                    examples_text += f"... (共{len(example_words)}个词)"
                output_lines.append(f"    📚 示例词汇: {examples_text}")
            else:
                output_lines.append(f"    📚 示例词汇: 无")
            
            output_lines.append("")
        
        # 添加统计信息
        output_lines.append("📊 **分析统计**")
        output_lines.append(f"- 线索字符数: {len(clues)} (带位置要求)")
        output_lines.append(f"- 候选字符数: {len(results)}")
        output_lines.append(f"- 最高匹配度: {results[0][1] if results else 0}")
        output_lines.append(f"- 最低匹配度: {results[-1][1] if results else 0}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f"❌ 字谜推理失败:\n\n**错误信息**: {str(e)}\n\n**详细错误**:\n```\n{error_detail}\n```"

def get_mystery_analyzer_status():
    """
    获取字谜分析器状态信息
    
    Returns:
        str: 状态信息
    """
    try:
        from character_mystery_solver import get_analyzer
        
        analyzer = get_analyzer()
        
        # 获取统计信息
        stats = analyzer.get_statistics()
        
        status_lines = []
        status_lines.append("🔍 **字谜推理器状态**")
        status_lines.append(f"- 字符数据: {stats['total_characters']:,} 个字符")
        status_lines.append(f"- 词汇数据: {stats['total_words']:,} 个词汇")
        status_lines.append(f"- 平均每字词汇数: {stats['avg_words_per_char']:.1f}")
        status_lines.append("- 数据来源: ci.json (实时加载)")
        status_lines.append("- 状态: ✅ 就绪")
        
        return "\n".join(status_lines)
            
    except Exception as e:
        return f"❌ 获取状态失败: {str(e)}"

if __name__ == "__main__":
    # 测试代码
    print("测试字谜推理器包装模块...")
    
    # 测试基本功能
    test_clues = ["天", "地"]
    result = process_character_mystery(test_clues, 10)
    print(result)
    
    print("\n" + "="*60 + "\n")
    
    # 测试位置功能
    print("测试位置功能...")
    test_clues_pos = ["痛"]
    test_positions = [1]  # 痛必须在第1位
    result_pos = process_character_mystery_with_positions(test_clues_pos, test_positions, 10)
    print(result_pos)
    
    print("\n" + "="*60 + "\n")
    
    # 测试状态获取
    status = get_mystery_analyzer_status()
    print(status)
