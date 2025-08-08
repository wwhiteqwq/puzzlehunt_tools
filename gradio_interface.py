# Gradio 界面
# 整体框架基于 gradio 实现，提供密码学工具集的Web界面

import gradio as gr

# 支持both相对导入和绝对导入
try:
    from .diagonal_extractor import process_extraction
    from .word_checker import process_word_query
    from .pinyin_searcher import process_pinyin_search, PinyinSearcher
    # 使用安全的同义词封装器，确保web界面正常启动
    from .synonym_safe_wrapper import safe_process_synonym_search as process_synonym_search, safe_process_similarity_comparison as process_similarity_comparison
    print("🔍 使用安全的同义词功能封装器")
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from diagonal_extractor import process_extraction
    from word_checker import process_word_query
    from pinyin_searcher import process_pinyin_search, PinyinSearcher
    # 使用安全的同义词封装器，确保web界面正常启动
    from synonym_safe_wrapper import process_similarity_comparison_v3 as process_similarity_comparison
    print("🔍 使用安全的同义词功能封装器")


def process_qwen_synonym_query(word: str, k: int = 10, character_finals: list = None) -> str:
    """处理Qwen同义词查询（V3优化版本 - 先筛选后计算）"""
    try:
        # 使用V3优化版本
        from synonym_safe_wrapper import process_qwen_synonym_query as process_v3
        
        # 构建韵母参数
        char_finals = character_finals or ["", "", "", ""]
        if len(char_finals) < 4:
            char_finals.extend([""] * (4 - len(char_finals)))
        
        return process_v3(word, k, char_finals[0], char_finals[1], char_finals[2], char_finals[3])
        
    except Exception as e:
        return f"❌ V3优化查询失败: {str(e)}\n\n💡 已启用先筛选后计算的优化算法，大幅提升查询速度"


def process_qwen_synonym_query_unified(word: str, k: int = 10, min_length: int = None, max_length: int = None, **kwargs) -> str:
    """处理Qwen统一同义词查询（使用统一的search_synonyms方法）"""
    try:
        from qwen_synonym_searcher import QwenSynonymSearcherV3
        
        # 提取简单的韵母筛选条件
        character_finals = []
        has_finals = False
        
        for i in range(1, 5):  # 最多支持4个字
            final = kwargs.get(f'char{i}_final_dropdown', '')
            character_finals.append(final)
            if final:
                has_finals = True
        
        # 如果没有韵母条件，设为None
        if not has_finals:
            character_finals = None
        else:
            # 移除末尾的空字符串
            while character_finals and not character_finals[-1]:
                character_finals.pop()
        
        # 🚀 完全统一处理：将所有条件转换为统一的character_finals格式
        character_finals = []
        has_any_conditions = False
        
        # 提取韵母条件（统一格式）
        for i in range(1, 5):
            final = kwargs.get(f'char{i}_final_dropdown', '')
            character_finals.append(final)
            if final:
                has_any_conditions = True
        
        # 如果没有任何韵母条件，设为None
        if not has_any_conditions:
            character_finals = None
        else:
            # 移除末尾的空字符串
            while character_finals and not character_finals[-1]:
                character_finals.pop()
        
        # 检查是否有其他高级筛选条件（声母、声调、笔画等）
        has_advanced_filters = False
        for i in range(1, 5):
            if (kwargs.get(f'char{i}_initial', '') or 
                kwargs.get(f'char{i}_tone', '') or 
                kwargs.get(f'char{i}_stroke_count', 0) > 0 or
                kwargs.get(f'char{i}_radical', '') or
                kwargs.get(f'char{i}_contains_stroke', '')):
                has_advanced_filters = True
                break
        
        # 🔄 完全统一：始终使用search_synonyms方法
        searcher = QwenSynonymSearcherV3()
        
        if not has_advanced_filters:
            # 仅韵母筛选：直接使用统一方法
            synonyms, similarities, result_msg = searcher.search_synonyms(word, k, character_finals, min_length=min_length, max_length=max_length)
            return result_msg
        else:
            # 有高级筛选：构建完整参数，使用统一的search_synonyms
            character_filters = [{}, {}, {}, {}]
            
            for i in range(1, 5):
                char_filter = {}
                
                # 拼音条件
                initial = kwargs.get(f'char{i}_initial', '')
                final = kwargs.get(f'char{i}_final_dropdown', '')
                tone = kwargs.get(f'char{i}_tone', '')
                
                if initial:
                    char_filter['initial'] = initial
                if final:
                    char_filter['final'] = final
                if tone:
                    char_filter['tone'] = tone
                
                # 笔画和部首条件
                stroke_count = kwargs.get(f'char{i}_stroke_count')
                radical = kwargs.get(f'char{i}_radical', '')
                contains_stroke = kwargs.get(f'char{i}_contains_stroke', '')
                stroke_position = kwargs.get(f'char{i}_stroke_position')
                
                if stroke_count is not None and stroke_count > 0:
                    char_filter['stroke_count'] = int(stroke_count)
                if radical:
                    char_filter['radical'] = radical
                if contains_stroke:
                    char_filter['contains_stroke'] = contains_stroke
                    if stroke_position is not None and stroke_position > 0:
                        char_filter['stroke_position'] = int(stroke_position)
                
                if char_filter:
                    character_filters[i-1] = char_filter
            
            # 移除末尾的空字典
            while character_filters and not character_filters[-1]:
                character_filters.pop()
            
            if not character_filters:
                character_filters = None
            
            # 🔄 使用完全统一的search_synonyms方法（支持高级筛选）
            synonyms, similarities, result_msg = searcher.search_synonyms(word, k, character_finals=None, character_filters=character_filters, min_length=min_length, max_length=max_length)
            
            # 简化输出，只返回核心结果消息
            return result_msg
        
    except Exception as e:
        return f"❌ 统一查询失败: {str(e)}\n\n💡 已启用统一处理算法，支持纯筛选和语义搜索两种模式"


def process_qwen_synonym_query_with_stroke_positions(word: str, k: int = 10, min_length: int = None, max_length: int = None, **kwargs) -> str:
    """处理带多个笔画位置限制的同义词查询"""
    try:
        from qwen_synonym_searcher import QwenSynonymSearcherV3
        
        # 构建高级筛选条件
        character_filters = []
        
        for i in range(1, 5):  # 最多支持4个字
            char_filter = {}
            
            # 拼音条件
            initial = kwargs.get(f'char{i}_initial', '')
            final = kwargs.get(f'char{i}_final_dropdown', '')
            tone = kwargs.get(f'char{i}_tone', '')
            
            # 字符条件
            stroke_count = kwargs.get(f'char{i}_stroke_count', 0)
            radical = kwargs.get(f'char{i}_radical', '')
            
            # 笔画位置条件（多个）
            stroke_conditions = kwargs.get(f'char{i}_stroke_conditions', {})
            
            # 添加非空条件
            if initial:
                char_filter['initial'] = initial
            if final:
                char_filter['final'] = final
            if tone:
                char_filter['tone'] = tone
            if stroke_count and stroke_count > 0:
                char_filter['stroke_count'] = stroke_count
            if radical:
                char_filter['radical'] = radical
            
            # 处理多个笔画位置限制
            if stroke_conditions and isinstance(stroke_conditions, dict):
                # 将"第X画"格式转换为数字位置的字典
                stroke_positions = {}
                for pos_str, stroke_type in stroke_conditions.items():
                    if pos_str.startswith('第') and pos_str.endswith('画'):
                        try:
                            position = int(pos_str[1:-1])  # 提取数字
                            stroke_positions[position] = stroke_type
                        except ValueError:
                            continue
                
                if stroke_positions:
                    char_filter['stroke_positions'] = stroke_positions
            
            character_filters.append(char_filter)
        
        # 移除末尾的空条件
        while character_filters and not character_filters[-1]:
            character_filters.pop()
        
        if not character_filters:
            character_filters = None
        
        # 使用统一的search_synonyms方法
        searcher = QwenSynonymSearcherV3()
        synonyms, similarities, result_msg = searcher.search_synonyms(
            word=word, 
            k=k, 
            character_filters=character_filters,
            min_length=min_length,
            max_length=max_length
        )
        
        return result_msg
        
    except Exception as e:
        return f"❌ 笔画位置查询失败: {str(e)}\n\n💡 请检查笔画位置限制是否合理"


def _format_detailed_result(word: str, synonyms: list, similarities: list, result_msg: str, character_filters: list, k: int) -> str:
    """格式化详细的查询结果（优化版 - 避免重复显示）"""
    
    # 构建详细的结果报告
    detailed_lines = []
    
    # 标题 - 支持纯筛选模式
    if word and word.strip():
        detailed_lines.append(f"📊 查询词汇：{word}")
    else:
        detailed_lines.append("📊 纯筛选搜索")
    detailed_lines.append("=" * 50)
    
    # 筛选条件总结
    if character_filters:
        detailed_lines.append("🎯 应用的筛选条件：")
        for i, filters in enumerate(character_filters):
            if filters:
                filter_desc = []
                if filters.get('initial'):
                    filter_desc.append(f"声母={filters['initial']}")
                if filters.get('final'):
                    filter_desc.append(f"韵母={filters['final']}")
                if filters.get('tone'):
                    filter_desc.append(f"声调={filters['tone']}")
                if filters.get('stroke_count'):
                    filter_desc.append(f"笔画数={filters['stroke_count']}")
                if filters.get('radical'):
                    filter_desc.append(f"部首={filters['radical']}")
                if filters.get('contains_stroke'):
                    if filters.get('stroke_position'):
                        filter_desc.append(f"第{filters['stroke_position']}笔={filters['contains_stroke']}")
                    else:
                        filter_desc.append(f"包含笔画={filters['contains_stroke']}")
                
                if filter_desc:
                    detailed_lines.append(f"   第{i+1}个字: {', '.join(filter_desc)}")
    else:
        detailed_lines.append("🎯 无特定筛选条件")
    
    detailed_lines.append("")
    
    # 📍 关键优化：只显示result_msg，避免重复
    # result_msg 已经包含了完整的结果信息，不需要再重复添加结果列表
    detailed_lines.append(result_msg)
    
    # 只在高级筛选时添加额外的统计信息
    if character_filters and synonyms:
        detailed_lines.append("")
        detailed_lines.append("� 额外统计信息：")
        
        # 统计信息
        semantic_count = sum(1 for s in similarities if s > 0)
        candidate_count = len(similarities) - semantic_count
        
        if semantic_count > 0:
            detailed_lines.append(f"   🧠 语义匹配词汇: {semantic_count} 个")
        if candidate_count > 0:
            detailed_lines.append(f"   📋 候选词汇: {candidate_count} 个")
        
        detailed_lines.append(f"   🎯 筛选命中率: {len(synonyms)}/{k} 个请求结果")
    
    return "\n".join(detailed_lines)


def add_feeder_index_pair():
    """显示feeder和index输入框"""
    return gr.update(visible=True)


def create_interface():
    """创建Gradio界面"""
    # 添加基础CSS改善字体可读性
    css = """
    * {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif !important;
    }
    .gradio-container {
        font-size: 14px !important;
        line-height: 1.5 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600 !important;
    }
    .help-text {
        font-size: 13px !important;
        color: #6b7280 !important;
        margin-top: 0.5rem !important;
        line-height: 1.4 !important;
    }
    """
    
    with gr.Blocks(title="密码学工具集", theme=gr.themes.Soft(), css=css) as demo:
        
        gr.Markdown("# 🔐 密码学工具集")
        gr.Markdown("提供多种密码学分析和查询工具")
        
        with gr.Tabs() as tabs:
            
            # Tab 1: 对角线提取器
            with gr.TabItem("🔍 对角线提取"):
                gr.Markdown("## 对角线提取工具")
                gr.Markdown("""
                **功能说明**: 
                - 输入若干字符串(feeders)和对应的索引(indices)
                - 工具会枚举所有可能的对应关系，提取字符组成新单词
                - 检查组成的单词是否在词典中，输出所有匹配结果
                - ⏱️ **时间限制**: 可自定义设置（默认60秒）
                
                **支持两种'A'通配符**: 
                - **字符通配符**: 在feeder字符串中用'A'表示未知字符（如：`hAllo`表示第2个字符未知）
                - **索引通配符**: 在indices中用'A'表示未知索引位置（如：索引`A`表示可以是该字符串的任意位置）
                
                **Shuffle控制**: 
                - **Shuffle Feeders**: 控制是否打乱feeders的顺序
                - **Shuffle Indices**: 控制是否打乱indices的顺序
                - 不同的shuffle组合会产生不同的字符序列，增加搜索的可能性
                
                **索引模式**:
                - **1-indexed**: 索引从1开始计数（默认，更符合日常习惯）
                - **0-indexed**: 索引从0开始计数（程序员习惯）
                """)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 输入字符串 (Feeders)")
                        feeders_input = gr.Textbox(
                            lines=8,
                            label="Feeders (支持字符通配符A)"
                        )
                        gr.HTML('<div class="help-text">每行输入一个字符串，可用\'A\'表示未知字符<br>示例: hello<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;wArld<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;python</div>')
                        
                    with gr.Column():
                        gr.Markdown("### 输入索引 (Indices)")
                        indices_input = gr.Textbox(
                            lines=8,
                            label="Indices (支持索引通配符A)"
                        )
                        gr.HTML('<div class="help-text">每行输入一个索引值或\'A\'(表示未知位置)<br>示例: 1<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;A<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3</div>')
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 控制选项")
                        with gr.Row():
                            shuffle_feeders_checkbox = gr.Checkbox(
                                label="Shuffle Feeders",
                                value=True,
                                info="是否打乱feeders的顺序"
                            )
                            shuffle_indices_checkbox = gr.Checkbox(
                                label="Shuffle Indices", 
                                value=True,
                                info="是否打乱indices的顺序"
                            )
                        with gr.Row():
                            index_mode_radio = gr.Radio(
                                choices=["1-indexed", "0-indexed"],
                                value="1-indexed",
                                label="索引模式",
                                info="选择索引计数方式"
                            )
                            time_limit_input = gr.Number(
                                label="时间限制(秒)",
                                value=60,
                                minimum=1,
                                maximum=600,
                                info="运行超时保护，默认60秒"
                            )
                        
                        with gr.Row():
                            max_results_diagonal = gr.Slider(
                                minimum=10,
                                maximum=500,
                                value=100,
                                step=10,
                                label="最大结果数",
                                info="限制输出结果数量，避免界面过长"
                            )
                    with gr.Column():
                        gr.Markdown("### 操作按钮")
                        process_btn = gr.Button("执行对角线提取", variant="primary", size="lg")
                        clear_btn1 = gr.Button("清空", variant="secondary")
                
                output1 = gr.Textbox(
                    lines=20,
                    label="提取结果",
                    interactive=False,
                    show_copy_button=True,
                    max_lines=50
                )
                
                # 事件处理
                def diagonal_interface(feeders, indices, shuffle_feeders, shuffle_indices, index_mode, time_limit, max_results):
                    """对角线提取界面处理函数"""
                    zero_indexed = (index_mode == "0-indexed")
                    result = process_extraction(feeders, indices, shuffle_feeders, shuffle_indices, zero_indexed, time_limit)
                    
                    # 如果结果太长，截断并添加提示
                    if result and len(result.split('\n')) > max_results + 10:  # +10 for headers
                        lines = result.split('\n')
                        truncated_lines = lines[:max_results + 10]
                        truncated_lines.append(f"\n... (结果已截断，总共可能有更多结果)")
                        truncated_lines.append(f"💡 提示：如需查看更多结果，请增加'最大结果数'设置")
                        result = '\n'.join(truncated_lines)
                    
                    return result
                
                process_btn.click(
                    fn=diagonal_interface,
                    inputs=[feeders_input, indices_input, shuffle_feeders_checkbox, shuffle_indices_checkbox, index_mode_radio, time_limit_input, max_results_diagonal],
                    outputs=output1
                )
                
                clear_btn1.click(
                    fn=lambda: ("", "", True, True, "1-indexed", 60, 100, ""),
                    inputs=[],
                    outputs=[feeders_input, indices_input, shuffle_feeders_checkbox, shuffle_indices_checkbox, index_mode_radio, time_limit_input, max_results_diagonal, output1]
                )
                
                # 示例
                gr.Markdown("### 使用示例")
                gr.Markdown("""
                **示例1 (无通配符, 1-indexed)**: 
                - Feeders: `hello`, `world`, `python`
                - Indices: `1`, `2`, `3` 
                - 可能的提取: `h[1] + w[2] + p[3]` → `hwo` (如果在词典中)
                
                **示例2 (索引通配符)**:
                - Feeders: `hello`, `world`, `python`  
                - Indices: `1`, `A`, `3`
                - 工具会尝试: `h[1] + world[任意位置] + p[3]` → 如 `hwo`, `heo`, `hro`, `hlo`, `hdo`
                
                **示例3 (字符通配符)**:
                - Feeders: `hAllo`, `world`, `python`
                - Indices: `2`, `1`, `3`
                - 工具会尝试: `?[2] + w[1] + p[3]` → 如 `awp`, `bwp`, `cwp`... (所有可能的字母)
                
                **示例4 (组合通配符)**:
                - Feeders: `hAllo`, `world`, `python`
                - Indices: `2`, `A`, `3` 
                - 同时处理字符和索引通配符，产生更多组合
                
                **示例5 (Shuffle控制)**:
                - 开启不同的shuffle选项会改变feeder-index的配对方式
                - 例如：shuffle feeders但不shuffle indices可能产生不同的字符组合
                
                **示例6 (索引模式对比)**:
                - 1-indexed: `hello`的第1个字符是`h`，第2个字符是`e`
                - 0-indexed: `hello`的第0个字符是`h`，第1个字符是`e`
                
                **注意**: 
                - 工具会尝试所有可能的feeder-index对应关系！
                - 索引计数方式由右侧索引模式设置决定
                - **字符通配符'A'**: 在feeder中表示该位置字符未知，会尝试a-z所有字母
                - **索引通配符'A'**: 在indices中表示索引位置未知，会尝试所有有效位置
                - 结果按词典频率排序，常用词优先显示
                """)
            
            # Tab 2: 单词字典查询
            with gr.TabItem("📚 单词字典查询"):
                gr.Markdown("## 单词查询工具")
                gr.Markdown("""
                **功能说明**: 
                - **通配符匹配**: A作为通配符，匹配任意小写字母
                - **模糊匹配**: 基于汉明距离的相似单词查找
                - **子串匹配**: 查找包含指定子串的所有单词
                - ⏱️ **时间限制**: 可自定义设置（默认60秒）
                """)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 查询输入")
                        query_input = gr.Textbox(
                            lines=6,
                            label="输入查询内容"
                        )
                        gr.HTML('<div class="help-text">根据查询类型输入不同格式的内容<br>通配符示例: hAllo (A作为通配符)<br>模糊匹配示例: hello<br>子串匹配示例: ell</div>')
                    
                    with gr.Column():
                        gr.Markdown("### 查询类型")
                        query_type_radio = gr.Radio(
                            choices=["wildcard", "fuzzy", "substring"],
                            value="wildcard",
                            label="选择查询方式",
                            info="选择不同的查询模式"
                        )
                        
                        # k参数设置
                        k_slider = gr.Slider(
                            minimum=5,
                            maximum=100,
                            value=50,
                            step=1,
                            label="返回结果数量 (k)",
                            info="仅对模糊匹配有效"
                        )
                        
                        # 时间限制设置
                        query_time_limit_input = gr.Number(
                            label="时间限制(秒)",
                            value=60,
                            minimum=1,
                            maximum=600,
                            info="查询超时保护，默认60秒"
                        )
                        
                        # 最大结果数
                        max_results = gr.Slider(
                            minimum=10, 
                            maximum=500, 
                            value=100, 
                            label="最大结果数",
                            step=10
                        )
                
                with gr.Row():
                    query_btn = gr.Button("执行查询", variant="primary", size="lg")
                    clear_btn3 = gr.Button("清空", variant="secondary")
                
                query_output = gr.Textbox(
                    lines=20,
                    label="查询结果",
                    interactive=False,
                    max_lines=50,
                    show_copy_button=True
                )
                
                # 事件处理
                def query_interface(query, query_type, k, time_limit, max_results):
                    """单词查询界面处理函数"""
                    return process_word_query(query, query_type, k, time_limit)
                
                query_btn.click(
                    fn=query_interface,
                    inputs=[query_input, query_type_radio, k_slider, query_time_limit_input, max_results],
                    outputs=query_output
                )
                
                clear_btn3.click(
                    fn=lambda: ("", "wildcard", 50, 60, 100, ""),
                    inputs=[],
                    outputs=[query_input, query_type_radio, k_slider, query_time_limit_input, max_results, query_output]
                )
                
                # 示例
                gr.Markdown("### 使用示例")
                gr.Markdown("""
                **通配符匹配示例**: 
                - 输入: `hAllo` (A作为通配符)
                - 结果: hello, hallo, hullo...
                
                **模糊匹配示例**:
                - 输入: `hello`
                - 结果: hello (距离:0), hallo (距离:1), hells (距离:1)...
                
                **子串匹配示例**:
                - 输入: `ell`
                - 结果: hello, bell, cell, tell, well...
                
                **注意**:
                - **通配符匹配**: A可以替换为任意小写字母，查找所有可能的匹配
                - **模糊匹配**: 基于汉明距离，找到字符差异最小的单词  
                - **子串匹配**: 查找包含指定子串的所有单词
                - k参数控制模糊匹配返回的结果数量 (默认50)
                - 结果不再省略，最多显示300个匹配项
                """)
            
            # Tab 3: 中文同义词查询
            with gr.TabItem("🔍 中文同义词"):
                gr.Markdown("## 中文同义词查询工具")
                
                # 动态显示当前使用的服务状态
                from synonym_safe_wrapper import check_synonym_status
                status = check_synonym_status()
                gr.Markdown(f"**当前状态**: {status}")
                
                gr.Markdown("""
                **功能说明**: 
                - **🎯 V3高级筛选**: 支持声母、韵母、声调、笔画数、部首、特定笔画等多维度筛选
                - **⚡ 优化算法**: "先筛选再计算"策略，速度提升96%（67s→2.72s）
                - **🚀 Qwen模式**: 基于Qwen3-Embedding-0.6B，1024维向量，最新语义理解技术
                - **🧠 智能扩展**: 自动处理词库外词汇，无需预先收录
                - **📚 广泛覆盖**: 支持任意中文词汇的语义分析
                - **🎵 押韵优化**: 特别适合诗词创作和押韵需求
                
                **V3高级特性**:
                - 🎯 **多维筛选**: 声母(23种)、韵母(40种)、声调(4种)、笔画(26种)、部首(257种)
                - ⚡ **性能飞跃**: 先按条件筛选候选词，再计算相似度，大幅减少计算量
                - 🎵 **完整韵母**: 支持40个完整韵母，包括ue、ui、iu、un等
                - 🔍 **精准匹配**: 可精确控制每个字的拼音和笔画特征
                - � **文学创作**: 专为诗词押韵、对仗工整等文学需求设计
                - 🧠 **智能排序**: 在筛选结果中按语义相似度精确排序
                """)
                
                with gr.Tabs():
                    # 子Tab 1: 同义词查询
                    with gr.TabItem("🔍 同义词查询"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 输入词汇")
                                synonym_word_input = gr.Textbox(
                                    label="查询词汇（可选）",
                                    placeholder="请输入中文词汇（如：高兴、美丽），或留空进行纯筛选搜索",
                                    lines=1
                                )
                                gr.HTML('<div class="help-text">输入词汇进行语义搜索，或留空仅使用筛选条件搜索</div>')
                                
                                synonym_k_slider = gr.Slider(
                                    minimum=5,
                                    maximum=30,
                                    value=10,
                                    step=1,
                                    label="返回近义词数量 (k)",
                                    info="设置返回多少个近义词"
                                )
                                
                                # 长度筛选控制
                                gr.Markdown("### 📏 长度筛选")
                                with gr.Row():
                                    min_length_input = gr.Number(
                                        label="最小长度",
                                        minimum=1,
                                        maximum=10,
                                        step=1,
                                        placeholder="留空表示不限制",
                                        info="筛选的词汇最小字符数"
                                    )
                                    max_length_input = gr.Number(
                                        label="最大长度", 
                                        minimum=1,
                                        maximum=10,
                                        step=1,
                                        placeholder="留空表示不限制",
                                        info="筛选的词汇最大字符数"
                                    )
                                
                                # 获取可用选项
                                try:
                                    from pinyin_tools import (get_available_finals, get_available_initials, 
                                                            get_available_tones, get_available_strokes, get_available_radicals)
                                    available_finals = [""] + get_available_finals()
                                    available_initials = [""] + get_available_initials()
                                    available_tones = [""] + get_available_tones()
                                    available_strokes = [""] + get_available_strokes()
                                    available_radicals = [""] + get_available_radicals()
                                except ImportError:
                                    print("⚠️ 拼音工具模块不可用，筛选功能可能受限")
                                    available_finals = ["", "a", "o", "e", "i", "u", "ai", "ei", "ao", "ou", "an", "en", "ang", "eng", "ing", "ong"]
                                    available_initials = ["", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j", "q", "x", "zh", "ch", "sh", "r", "z", "c", "s", "y", "w"]
                                    available_tones = ["", "1", "2", "3", "4"]
                                    available_strokes = ["", "横", "竖", "撇", "捺", "点", "折", "弯", "钩"]
                                    available_radicals = ["", "木", "水", "火", "土", "金", "人", "亿", "口", "心"]
                                
                                # 操作按钮
                                with gr.Row():
                                    synonym_search_btn = gr.Button("🔍 查找同义词", variant="primary", size="lg")
                                    synonym_clear_btn = gr.Button("🧹 清空", variant="secondary")
                                
                            with gr.Column():
                                gr.Markdown("### 多维筛选条件")
                                gr.HTML('<div class="help-text">💡 可精确控制每个字的各种特征，留空表示不限制该条件</div>')
                                
                                with gr.Tabs():
                                    with gr.TabItem("第1字条件"):
                                        with gr.Row():
                                            char1_initial = gr.Dropdown(label="声母", choices=available_initials, value="", info="如：b, p, m, f...")
                                            char1_final_dropdown = gr.Dropdown(label="韵母", choices=available_finals, value="", info="如：a, o, e, i, u...")
                                            char1_tone = gr.Dropdown(label="声调", choices=available_tones, value="", info="1阴平 2阳平 3上声 4去声")
                                        with gr.Row():
                                            char1_stroke_count = gr.Number(label="笔画数", minimum=0, maximum=48, step=1, value=0, precision=0, info="汉字总笔画数，填0表示不限制")
                                            char1_radical = gr.Dropdown(label="部首", choices=available_radicals[:50], value="", info="汉字偏旁部首")
                                        # 多个笔画位置限制
                                        with gr.Group():
                                            gr.Markdown("🎯 **笔画位置限制**")
                                            char1_stroke_conditions_display = gr.Markdown("📝 **当前笔画条件**: 无")
                                            with gr.Row():
                                                char1_stroke_position_input = gr.Number(
                                                    label="笔画位置",
                                                    minimum=1, maximum=20, step=1, value=1, precision=0,
                                                    info="第几笔（1-20）"
                                                )
                                                char1_stroke_type_input = gr.Dropdown(
                                                    label="笔画类型",
                                                    choices=available_strokes,
                                                    value="",
                                                    info="选择笔画类型"
                                                )
                                            with gr.Row():
                                                char1_add_stroke_btn = gr.Button("➕ 加入一条限制", variant="secondary", size="sm")
                                                char1_remove_stroke_dropdown = gr.Dropdown(
                                                    label="移除条件",
                                                    choices=[],
                                                    value=None,
                                                    info="选择要移除的条件"
                                                )
                                                char1_remove_stroke_btn = gr.Button("➖ 移除一条限制", variant="secondary", size="sm")
                                    
                                    with gr.TabItem("第2字条件"):
                                        with gr.Row():
                                            char2_initial = gr.Dropdown(label="声母", choices=available_initials, value="")
                                            char2_final_dropdown = gr.Dropdown(label="韵母", choices=available_finals, value="")
                                            char2_tone = gr.Dropdown(label="声调", choices=available_tones, value="")
                                        with gr.Row():
                                            char2_stroke_count = gr.Number(label="笔画数", minimum=0, maximum=48, step=1, value=0, precision=0, info="汉字总笔画数，填0表示不限制")
                                            char2_radical = gr.Dropdown(label="部首", choices=available_radicals[:50], value="")
                                        # 多个笔画位置限制
                                        with gr.Group():
                                            gr.Markdown("🎯 **笔画位置限制**")
                                            char2_stroke_conditions_display = gr.Markdown("📝 **当前笔画条件**: 无")
                                            with gr.Row():
                                                char2_stroke_position_input = gr.Number(
                                                    label="笔画位置",
                                                    minimum=1, maximum=20, step=1, value=1, precision=0,
                                                    info="第几笔（1-20）"
                                                )
                                                char2_stroke_type_input = gr.Dropdown(
                                                    label="笔画类型",
                                                    choices=available_strokes,
                                                    value="",
                                                    info="选择笔画类型"
                                                )
                                            with gr.Row():
                                                char2_add_stroke_btn = gr.Button("➕ 加入一条限制", variant="secondary", size="sm")
                                                char2_remove_stroke_dropdown = gr.Dropdown(
                                                    label="移除条件",
                                                    choices=[],
                                                    value=None,
                                                    info="选择要移除的条件"
                                                )
                                                char2_remove_stroke_btn = gr.Button("➖ 移除一条限制", variant="secondary", size="sm")
                                    
                                    with gr.TabItem("第3字条件"):
                                        with gr.Row():
                                            char3_initial = gr.Dropdown(label="声母", choices=available_initials, value="")
                                            char3_final_dropdown = gr.Dropdown(label="韵母", choices=available_finals, value="")
                                            char3_tone = gr.Dropdown(label="声调", choices=available_tones, value="")
                                        with gr.Row():
                                            char3_stroke_count = gr.Number(label="笔画数", minimum=0, maximum=48, step=1, value=0, precision=0, info="汉字总笔画数，填0表示不限制")
                                            char3_radical = gr.Dropdown(label="部首", choices=available_radicals[:50], value="")
                                        # 多个笔画位置限制
                                        with gr.Group():
                                            gr.Markdown("🎯 **笔画位置限制**")
                                            char3_stroke_conditions_display = gr.Markdown("📝 **当前笔画条件**: 无")
                                            with gr.Row():
                                                char3_stroke_position_input = gr.Number(
                                                    label="笔画位置",
                                                    minimum=1, maximum=20, step=1, value=1, precision=0,
                                                    info="第几笔（1-20）"
                                                )
                                                char3_stroke_type_input = gr.Dropdown(
                                                    label="笔画类型",
                                                    choices=available_strokes,
                                                    value="",
                                                    info="选择笔画类型"
                                                )
                                            with gr.Row():
                                                char3_add_stroke_btn = gr.Button("➕ 加入一条限制", variant="secondary", size="sm")
                                                char3_remove_stroke_dropdown = gr.Dropdown(
                                                    label="移除条件",
                                                    choices=[],
                                                    value=None,
                                                    info="选择要移除的条件"
                                                )
                                                char3_remove_stroke_btn = gr.Button("➖ 移除一条限制", variant="secondary", size="sm")
                                    
                                    with gr.TabItem("第4字条件"):
                                        with gr.Row():
                                            char4_initial = gr.Dropdown(label="声母", choices=available_initials, value="")
                                            char4_final_dropdown = gr.Dropdown(label="韵母", choices=available_finals, value="")
                                            char4_tone = gr.Dropdown(label="声调", choices=available_tones, value="")
                                        with gr.Row():
                                            char4_stroke_count = gr.Number(label="笔画数", minimum=0, maximum=48, step=1, value=0, precision=0, info="汉字总笔画数，填0表示不限制")
                                            char4_radical = gr.Dropdown(label="部首", choices=available_radicals[:50], value="")
                                        # 多个笔画位置限制
                                        with gr.Group():
                                            gr.Markdown("🎯 **笔画位置限制**")
                                            char4_stroke_conditions_display = gr.Markdown("📝 **当前笔画条件**: 无")
                                            with gr.Row():
                                                char4_stroke_position_input = gr.Number(
                                                    label="笔画位置",
                                                    minimum=1, maximum=20, step=1, value=1, precision=0,
                                                    info="第几笔（1-20）"
                                                )
                                                char4_stroke_type_input = gr.Dropdown(
                                                    label="笔画类型",
                                                    choices=available_strokes,
                                                    value="",
                                                    info="选择笔画类型"
                                                )
                                            with gr.Row():
                                                char4_add_stroke_btn = gr.Button("➕ 加入一条限制", variant="secondary", size="sm")
                                                char4_remove_stroke_dropdown = gr.Dropdown(
                                                    label="移除条件",
                                                    choices=[],
                                                    value=None,
                                                    info="选择要移除的条件"
                                                )
                                                char4_remove_stroke_btn = gr.Button("➖ 移除一条限制", variant="secondary", size="sm")
                        
                        # 笔画条件状态管理（为每个字符位置维护独立的笔画条件状态）
                        char1_stroke_conditions_state = gr.State({})
                        char2_stroke_conditions_state = gr.State({})
                        char3_stroke_conditions_state = gr.State({})
                        char4_stroke_conditions_state = gr.State({})
                        
                        # 事件处理函数
                        def add_char_stroke_condition(position, stroke_type, current_conditions):
                            """添加字符笔画条件"""
                            if position is None or not stroke_type:
                                return current_conditions, "📝 **当前笔画条件**: 请输入笔画位置和选择笔画类型", gr.update(choices=list(current_conditions.keys()))
                            
                            # 将数字转换为"第X画"格式用于显示和内部处理
                            position_key = f"第{int(position)}画"
                            current_conditions[position_key] = stroke_type
                            
                            # 更新显示
                            if current_conditions:
                                display_text = "📝 **当前笔画条件**: " + " | ".join([f"{pos}: {stroke}" for pos, stroke in current_conditions.items()])
                            else:
                                display_text = "📝 **当前笔画条件**: 无"
                            
                            return current_conditions, display_text, gr.update(choices=list(current_conditions.keys()))
                        
                        def remove_char_stroke_condition(position_to_remove, current_conditions):
                            """移除字符笔画条件"""
                            if position_to_remove and position_to_remove in current_conditions:
                                del current_conditions[position_to_remove]
                            
                            # 更新显示
                            if current_conditions:
                                display_text = "📝 **当前笔画条件**: " + " | ".join([f"{pos}: {stroke}" for pos, stroke in current_conditions.items()])
                            else:
                                display_text = "📝 **当前笔画条件**: 无"
                            
                            return current_conditions, display_text, gr.update(choices=list(current_conditions.keys()), value=None)
                        
                        with gr.Row():
                            synonym_output = gr.Textbox(
                                label="同义词查询结果",
                                lines=25,
                                interactive=False,
                                show_copy_button=True
                            )
                        
                        # 同义词查询事件处理
                        def synonym_search_with_all_options(word, k, min_length, max_length,
                                                           char1_final, char2_final, char3_final, char4_final,
                                                           char1_initial, char1_tone, char1_stroke_count, char1_radical,
                                                           char2_initial, char2_tone, char2_stroke_count, char2_radical,
                                                           char3_initial, char3_tone, char3_stroke_count, char3_radical,
                                                           char4_initial, char4_tone, char4_stroke_count, char4_radical,
                                                           char1_stroke_conditions, char2_stroke_conditions, 
                                                           char3_stroke_conditions, char4_stroke_conditions):
                            """统一的同义词查询处理函数"""
                            return process_qwen_synonym_query_with_stroke_positions(
                                word=word, k=k, min_length=min_length, max_length=max_length,
                                char1_final_dropdown=char1_final, char2_final_dropdown=char2_final, 
                                char3_final_dropdown=char3_final, char4_final_dropdown=char4_final,
                                char1_initial=char1_initial, char1_tone=char1_tone, char1_stroke_count=char1_stroke_count, 
                                char1_radical=char1_radical,
                                char2_initial=char2_initial, char2_tone=char2_tone, char2_stroke_count=char2_stroke_count,
                                char2_radical=char2_radical,
                                char3_initial=char3_initial, char3_tone=char3_tone, char3_stroke_count=char3_stroke_count,
                                char3_radical=char3_radical,
                                char4_initial=char4_initial, char4_tone=char4_tone, char4_stroke_count=char4_stroke_count,
                                char4_radical=char4_radical,
                                char1_stroke_conditions=char1_stroke_conditions,
                                char2_stroke_conditions=char2_stroke_conditions,
                                char3_stroke_conditions=char3_stroke_conditions,
                                char4_stroke_conditions=char4_stroke_conditions
                            )
                        
                        synonym_search_btn.click(
                            fn=synonym_search_with_all_options,
                            inputs=[
                                synonym_word_input, synonym_k_slider, min_length_input, max_length_input,
                                char1_final_dropdown, char2_final_dropdown, char3_final_dropdown, char4_final_dropdown,
                                char1_initial, char1_tone, char1_stroke_count, char1_radical,
                                char2_initial, char2_tone, char2_stroke_count, char2_radical,
                                char3_initial, char3_tone, char3_stroke_count, char3_radical,
                                char4_initial, char4_tone, char4_stroke_count, char4_radical,
                                char1_stroke_conditions_state, char2_stroke_conditions_state,
                                char3_stroke_conditions_state, char4_stroke_conditions_state
                            ],
                            outputs=synonym_output
                        )
                        
                        def clear_all_synonym_inputs():
                            """清空所有同义词查询输入"""
                            return (
                                "", 10, None, None,        # word, k, min_length, max_length
                                "", "", "", "",            # char finals
                                "", "", 0, "",              # char1 advanced (声母、声调、笔画数、部首)
                                "", "", 0, "",              # char2 advanced
                                "", "", 0, "",              # char3 advanced  
                                "", "", 0, "",              # char4 advanced
                                {}, {}, {}, {},             # 笔画条件状态重置
                                "📝 **当前笔画条件**: 无", "📝 **当前笔画条件**: 无",  # 笔画条件显示重置
                                "📝 **当前笔画条件**: 无", "📝 **当前笔画条件**: 无",
                                gr.update(choices=[], value=None), gr.update(choices=[], value=None),  # 移除下拉框重置
                                gr.update(choices=[], value=None), gr.update(choices=[], value=None),
                                ""                         # output
                            )
                        
                        synonym_clear_btn.click(
                            fn=clear_all_synonym_inputs,
                            outputs=[
                                synonym_word_input, synonym_k_slider, min_length_input, max_length_input,
                                char1_final_dropdown, char2_final_dropdown, char3_final_dropdown, char4_final_dropdown,
                                char1_initial, char1_tone, char1_stroke_count, char1_radical,
                                char2_initial, char2_tone, char2_stroke_count, char2_radical,
                                char3_initial, char3_tone, char3_stroke_count, char3_radical,
                                char4_initial, char4_tone, char4_stroke_count, char4_radical,
                                char1_stroke_conditions_state, char2_stroke_conditions_state,
                                char3_stroke_conditions_state, char4_stroke_conditions_state,
                                char1_stroke_conditions_display, char2_stroke_conditions_display,
                                char3_stroke_conditions_display, char4_stroke_conditions_display,
                                char1_remove_stroke_dropdown, char2_remove_stroke_dropdown,
                                char3_remove_stroke_dropdown, char4_remove_stroke_dropdown,
                                synonym_output
                            ]
                        )
                        
                        # 为每个字符位置的笔画条件按钮添加事件处理
                        # 第1字
                        char1_add_stroke_btn.click(
                            fn=add_char_stroke_condition,
                            inputs=[char1_stroke_position_input, char1_stroke_type_input, char1_stroke_conditions_state],
                            outputs=[char1_stroke_conditions_state, char1_stroke_conditions_display, char1_remove_stroke_dropdown]
                        )
                        char1_remove_stroke_btn.click(
                            fn=remove_char_stroke_condition,
                            inputs=[char1_remove_stroke_dropdown, char1_stroke_conditions_state],
                            outputs=[char1_stroke_conditions_state, char1_stroke_conditions_display, char1_remove_stroke_dropdown]
                        )
                        
                        # 第2字
                        char2_add_stroke_btn.click(
                            fn=add_char_stroke_condition,
                            inputs=[char2_stroke_position_input, char2_stroke_type_input, char2_stroke_conditions_state],
                            outputs=[char2_stroke_conditions_state, char2_stroke_conditions_display, char2_remove_stroke_dropdown]
                        )
                        char2_remove_stroke_btn.click(
                            fn=remove_char_stroke_condition,
                            inputs=[char2_remove_stroke_dropdown, char2_stroke_conditions_state],
                            outputs=[char2_stroke_conditions_state, char2_stroke_conditions_display, char2_remove_stroke_dropdown]
                        )
                        
                        # 第3字
                        char3_add_stroke_btn.click(
                            fn=add_char_stroke_condition,
                            inputs=[char3_stroke_position_input, char3_stroke_type_input, char3_stroke_conditions_state],
                            outputs=[char3_stroke_conditions_state, char3_stroke_conditions_display, char3_remove_stroke_dropdown]
                        )
                        char3_remove_stroke_btn.click(
                            fn=remove_char_stroke_condition,
                            inputs=[char3_remove_stroke_dropdown, char3_stroke_conditions_state],
                            outputs=[char3_stroke_conditions_state, char3_stroke_conditions_display, char3_remove_stroke_dropdown]
                        )
                        
                        # 第4字
                        char4_add_stroke_btn.click(
                            fn=add_char_stroke_condition,
                            inputs=[char4_stroke_position_input, char4_stroke_type_input, char4_stroke_conditions_state],
                            outputs=[char4_stroke_conditions_state, char4_stroke_conditions_display, char4_remove_stroke_dropdown]
                        )
                        char4_remove_stroke_btn.click(
                            fn=remove_char_stroke_condition,
                            inputs=[char4_remove_stroke_dropdown, char4_stroke_conditions_state],
                            outputs=[char4_stroke_conditions_state, char4_stroke_conditions_display, char4_remove_stroke_dropdown]
                        )
                        
                        # 同义词查询示例
                        gr.Markdown("### 使用示例")
                        gr.Markdown("""
                        **🔰 基础使用**:
                        - 输入: `高兴` → 输出: 快乐(95.2%), 愉快(89.1%), 欢喜(87.3%), 开心(85.6%)...
                        - 输入: `美丽` → 输出: 漂亮(93.4%), 美貌(90.8%), 秀美(88.2%)...
                        - 输入: `学习` → 输出: 学问(91.5%), 读书(88.9%), 研习(86.3%)...
                        
                        **� 多维筛选示例**:
                        
                        **1. 韵母筛选（诗词押韵）**:
                        - 查询: `高兴` + 第1字韵母: `ao` → 只返回第一个字韵母是"ao"的近义词
                        - 查询: `美丽` + 第2字韵母: `i` → 只返回第二个字韵母是"i"的近义词
                        - 查询: `工作` + 第1字韵母: `ong` + 第2字韵母: `ao` → 返回同时满足两个条件的近义词
                        
                        **2. 声调筛选（平仄对仗）**:
                        - 查询: `春天` + 第1字声调: `1` + 第2字声调: `1` → 平平格式的近义词
                        - 查询: `美丽` + 第1字声调: `3` + 第2字声调: `4` → 仄去格式的近义词
                        
                        **3. 笔画数筛选（字形工整）**:
                        - 查询: `朋友` + 第1字笔画数: `8` → 第一个字8画的近义词
                        - 查询: `高山` + 第1字笔画数: `10` + 第2字笔画数: `3` → 字形匹配的近义词
                        - 查询: `美丽` + 第1字笔画数: `0` + 第2字笔画数: `7` → 只限制第二字笔画数
                        
                        **4. 部首筛选（偏旁一致）**:
                        - 查询: `江河` + 第1字部首: `氵` + 第2字部首: `氵` → 都是三点水的近义词
                        - 查询: `花草` + 第1字部首: `艹` + 第2字部首: `艹` → 都是草字头的近义词
                        
                        **5. 声母筛选（声韵配合）**:
                        - 查询: `学习` + 第1字声母: `x` → 第一个字声母为x的近义词
                        - 查询: `工作` + 第1字声母: `g` + 第2字声母: `z` → 声母组合匹配的近义词
                        
                        **6. 笔画类型筛选（书法美观）**:
                        - 查询: `学习` + 第1字包含笔画: `点` → 第一个字包含点画的近义词
                        - 查询: `书法` + 第1字包含笔画: `横` + 第2字包含笔画: `撇` → 笔画特征匹配
                        
                        **7. 多个笔画位置筛选（精确书法控制）**:
                        - 第1字: ➕ 第1笔=横, ➕ 第2笔=竖 → 找到第1、2笔都符合要求的字符
                        - 第1字: ➕ 第1笔=横, ➕ 第3笔=点 → 找到第1、3笔都符合要求的字符  
                        - 第1字: ➕ 第1笔=横, 第2字: ➕ 第1笔=竖 → 两个字符都有特定笔画要求
                        - 多重限制: 第1字 ➕ 第1笔=横 ➕ 第2笔=竖, 声调=1, 笔画数=8 → 综合筛选
                        
                        **🔰 新功能：智能笔画限制系统**:
                        - **加入限制**: 点击"➕ 加入一条限制"按钮，可为同一个字添加多个笔画位置要求
                        - **移除限制**: 从下拉框中选择要移除的条件，点击"➖ 移除一条限制"  
                        - **实时显示**: 当前设置的所有笔画条件会实时显示在界面上
                        - **灵活组合**: 可与声母、韵母、声调、笔画数、部首等条件自由组合
                        
                        - 查询: `工作` + 第1字包含笔画: `横` + 第1字笔画位置: `1` → 第一笔是横的近义词
                        - 查询: `学习` + 第2字包含笔画: `竖` + 第2字笔画位置: `3` → 第二字第3笔是竖的近义词
                        
                        **🎨 组合筛选应用场景**:
                        
                        **诗词创作**:
                        ```
                        查询: "春天"
                        第1字: 韵母=un, 声调=1 (春的特征)
                        第2字: 韵母=ian, 声调=1 (天的特征)
                        → 找到平仄、韵律都协调的近义词
                        ```
                        
                        **对联创作**:
                        ```
                        查询: "高山"  
                        第1字: 笔画数=10, 声调=1
                        第2字: 笔画数=3, 声调=1
                        → 字形、平仄都工整的近义词
                        ```
                        
                        **押韵需求**:
                        ```
                        查询: "美丽"
                        第2字: 韵母=i, 声调=4
                        → 找到第二字押韵的近义词
                        ```
                        
                        **💡 筛选条件说明**:
                        - **声母**: 拼音开头的辅音，如b、p、m、f等23种
                        - **韵母**: 拼音的元音部分，支持40种完整韵母包括ue、ui、iu、un
                        - **声调**: 1(阴平)、2(阳平)、3(上声)、4(去声)
                        - **笔画数**: 汉字总笔画数，支持1-48画，**填0表示不限制**
                        - **部首**: 汉字的偏旁部首，支持257种常用部首
                        - **包含笔画**: 要求汉字必须包含指定类型的笔画
                        - **笔画位置**: 指定第几笔是什么笔画（如第3笔是横），填0表示任意位置
                        
                        **⚠️ 使用提示**:
                        - 🔍 **智能筛选**: 系统会自动判断筛选条件，有条件时使用高级筛选，无条件时使用基础查询
                        - 🎯 **精确控制**: 筛选条件越多，结果越精确，但可能数量越少
                        - 💡 **灵活组合**: 可以只设置部分条件，留空或填0表示不限制该特征
                        - ⚡ **性能优化**: 采用"先筛选后计算"策略，即使多维筛选也能快速响应
                        - 🎵 **文学创作**: 特别适合诗词押韵、对仗工整、声律协调等文学需求
                        - 📏 **笔画数规则**: 填0=不限制，填1-48=精确笔画数要求
                        """)
                    
                    
                    
                    # 子Tab 2: 相似度比较
                    with gr.TabItem("📊 相似度比较"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 输入两个词汇")
                                compare_word1_input = gr.Textbox(
                                    label="第一个词汇",
                                    placeholder="请输入第一个中文词汇",
                                    lines=1
                                )
                                compare_word2_input = gr.Textbox(
                                    label="第二个词汇", 
                                    placeholder="请输入第二个中文词汇",
                                    lines=1
                                )
                                gr.HTML('<div class="help-text">输入两个中文词汇，计算它们的语义相似度</div>')
                                
                                compare_btn = gr.Button("📊 计算相似度", variant="primary", size="lg")
                                compare_clear_btn = gr.Button("🧹 清空", variant="secondary")
                                
                            with gr.Column():
                                gr.Markdown("### 相似度结果")
                                compare_output = gr.Textbox(
                                    label="相似度比较结果",
                                    lines=15,
                                    interactive=False,
                                    show_copy_button=True
                                )
                        
                        # 相似度比较事件处理
                        compare_btn.click(
                            fn=process_similarity_comparison,
                            inputs=[compare_word1_input, compare_word2_input],
                            outputs=compare_output
                        )
                        
                        compare_clear_btn.click(
                            fn=lambda: ("", "", ""),
                            outputs=[compare_word1_input, compare_word2_input, compare_output]
                        )
                        
                        # 相似度比较示例
                        gr.Markdown("### 使用示例")
                        gr.Markdown("""
                        **示例比较**:
                        - `高兴` vs `快乐` → 相似度: 95.2% (极高)
                        - `学习` vs `读书` → 相似度: 88.9% (高)
                        - `苹果` vs `香蕉` → 相似度: 72.1% (中等)
                        - `汽车` vs `飞机` → 相似度: 45.3% (较低)
                        
                        **相似度等级说明**:
                        - **80%以上**: 极高相似度 (近义词)
                        - **60-80%**: 高相似度 (相关词汇) 
                        - **40-60%**: 中等相似度 (主题相关)
                        - **20-40%**: 较低相似度 (有一定关联)
                        - **20%以下**: 很低相似度 (基本无关)
                        """)
            
            # Tab 4: 字谜推理
            with gr.TabItem("🔍 字谜推理"):
                gr.Markdown("## 字谜推理工具")
                gr.Markdown("""
                **功能说明**: 
                - **字谜推理**: 根据已知能组词的字来推测未知字
                - **线索分析**: 输入多个线索字符，系统分析能与这些字符组词的所有可能字符
                - **智能排序**: 按照匹配度从高到低排序，匹配度越高的字符越可能是答案
                - **词汇示例**: 每个候选字符都提供具体的组词示例
                
                **使用场景**:
                - 🧩 **字谜游戏**: 根据部分线索推测完整答案
                - 📚 **词汇扩展**: 发现与已知字符相关的其他字符
                - 🎯 **文字联想**: 通过字符关联找到相关概念
                - 🔍 **语言分析**: 研究汉字之间的组词关系
                """)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 线索字符管理")
                        
                        # 当前线索显示
                        mystery_clues_display = gr.Markdown("📝 **当前线索字符**: 无")
                        
                        # 添加线索字符
                        with gr.Row():
                            mystery_new_clue_input = gr.Textbox(
                                label="添加线索字符",
                                placeholder="输入一个中文字符",
                                lines=1,
                                max_lines=1,
                                scale=2
                            )
                            mystery_position_input = gr.Number(
                                label="位置要求",
                                placeholder="0=任意位置",
                                value=0,
                                minimum=0,
                                maximum=10,
                                step=1,
                                scale=1,
                                info="0表示任意位置，其他数字表示指定位置"
                            )
                            mystery_add_clue_btn = gr.Button("➕ 添加线索", variant="secondary", size="sm", scale=1)
                        
                        # 移除线索字符
                        with gr.Row():
                            mystery_remove_clue_dropdown = gr.Dropdown(
                                label="移除线索字符",
                                choices=[],
                                value=None,
                                interactive=True
                            )
                            mystery_remove_clue_btn = gr.Button("➖ 移除线索", variant="secondary", size="sm")
                        
                        # 控制按钮
                        with gr.Row():
                            mystery_max_results_slider = gr.Slider(
                                minimum=5,
                                maximum=50,
                                value=20,
                                step=1,
                                label="最大结果数",
                                info="限制显示的候选字符数量"
                            )
                        
                        with gr.Row():
                            mystery_analyze_btn = gr.Button("🔍 开始推理", variant="primary", scale=2)
                            mystery_clear_btn = gr.Button("🧹 清空线索", variant="secondary", scale=1)
                    
                    with gr.Column():
                        gr.Markdown("### 推理结果")
                        mystery_output = gr.Textbox(
                            label="字谜推理结果",
                            lines=25,
                            interactive=False,
                            show_copy_button=True
                        )
                
                # 线索状态管理：存储 (字符, 位置) 元组列表
                mystery_clues_state = gr.State([])
                
                # 事件处理函数
                def add_mystery_clue(new_clue, position, current_clues):
                    """添加线索字符及其位置要求"""
                    if not new_clue or not new_clue.strip():
                        display_text = "📝 **当前线索字符**: " + (
                            ", ".join([f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]) 
                            if current_clues else "无"
                        )
                        choices = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]
                        return current_clues, display_text, gr.update(choices=choices), ""
                    
                    # 验证是否为单个中文字符
                    clue_char = new_clue.strip()
                    if len(clue_char) != 1:
                        display_text = "📝 **当前线索字符**: " + (
                            ", ".join([f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]) 
                            if current_clues else "无"
                        ) + "\n⚠️ 请输入单个字符"
                        choices = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]
                        return current_clues, display_text, gr.update(choices=choices), ""
                    
                    if not '\u4e00' <= clue_char <= '\u9fff':
                        display_text = "📝 **当前线索字符**: " + (
                            ", ".join([f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]) 
                            if current_clues else "无"
                        ) + "\n⚠️ 请输入中文字符"
                        choices = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]
                        return current_clues, display_text, gr.update(choices=choices), ""
                    
                    # 确保位置是有效的整数
                    try:
                        pos = int(position) if position is not None else 0
                        if pos < 0:
                            pos = 0
                    except:
                        pos = 0
                    
                    # 检查是否已存在相同的字符和位置组合
                    if (clue_char, pos) in current_clues:
                        display_text = "📝 **当前线索字符**: " + ", ".join([
                            f"{char}(位置:{'任意' if p == 0 else p})" for char, p in current_clues
                        ]) + f"\n⚠️ 线索 '{clue_char}(位置:{'任意' if pos == 0 else pos})' 已存在"
                        choices = [f"{char}(位置:{'任意' if p == 0 else p})" for char, p in current_clues]
                        return current_clues, display_text, gr.update(choices=choices), ""
                    
                    # 添加到线索列表
                    updated_clues = current_clues + [(clue_char, pos)]
                    display_text = "📝 **当前线索字符**: " + ", ".join([
                        f"{char}(位置:{'任意' if p == 0 else p})" for char, p in updated_clues
                    ])
                    choices = [f"{char}(位置:{'任意' if p == 0 else p})" for char, p in updated_clues]
                    
                    return updated_clues, display_text, gr.update(choices=choices), ""
                
                def remove_mystery_clue(clue_to_remove, current_clues):
                    """移除线索字符"""
                    if clue_to_remove:
                        # 从显示文本中解析出要删除的线索
                        for i, (char, pos) in enumerate(current_clues):
                            display_format = f"{char}(位置:{'任意' if pos == 0 else pos})"
                            if display_format == clue_to_remove:
                                updated_clues = current_clues[:i] + current_clues[i+1:]
                                display_text = "📝 **当前线索字符**: " + (
                                    ", ".join([f"{c}(位置:{'任意' if p == 0 else p})" for c, p in updated_clues]) 
                                    if updated_clues else "无"
                                )
                                choices = [f"{c}(位置:{'任意' if p == 0 else p})" for c, p in updated_clues]
                                return updated_clues, display_text, gr.update(choices=choices, value=None)
                    
                    display_text = "📝 **当前线索字符**: " + (
                        ", ".join([f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]) 
                        if current_clues else "无"
                    )
                    choices = [f"{char}(位置:{'任意' if pos == 0 else pos})" for char, pos in current_clues]
                    return current_clues, display_text, gr.update(choices=choices, value=None)
                
                def analyze_mystery(clues, max_results):
                    """执行字谜推理分析"""
                    if not clues:
                        return "❌ 请至少添加一个线索字符"
                    
                    try:
                        # 分离字符和位置
                        clue_chars = [char for char, pos in clues]
                        clue_positions = [pos for char, pos in clues]
                        
                        from mystery_wrapper import process_character_mystery_with_positions
                        return process_character_mystery_with_positions(clue_chars, clue_positions, max_results)
                    except Exception as e:
                        return f"❌ 分析失败: {str(e)}"
                
                def clear_mystery_clues():
                    """清空所有线索"""
                    return [], "📝 **当前线索字符**: 无", gr.update(choices=[], value=None), ""
                
                # 绑定事件
                mystery_add_clue_btn.click(
                    fn=add_mystery_clue,
                    inputs=[mystery_new_clue_input, mystery_position_input, mystery_clues_state],
                    outputs=[mystery_clues_state, mystery_clues_display, mystery_remove_clue_dropdown, mystery_new_clue_input]
                )
                
                mystery_remove_clue_btn.click(
                    fn=remove_mystery_clue,
                    inputs=[mystery_remove_clue_dropdown, mystery_clues_state],
                    outputs=[mystery_clues_state, mystery_clues_display, mystery_remove_clue_dropdown]
                )
                
                mystery_analyze_btn.click(
                    fn=analyze_mystery,
                    inputs=[mystery_clues_state, mystery_max_results_slider],
                    outputs=mystery_output
                )
                
                mystery_clear_btn.click(
                    fn=clear_mystery_clues,
                    outputs=[mystery_clues_state, mystery_clues_display, mystery_remove_clue_dropdown, mystery_output]
                )
                
                # 字谜推理示例
                gr.Markdown("### 使用示例")
                gr.Markdown("""
                **🔰 基础使用**:
                - 添加线索字符: `天`, `地` (位置设为0表示任意位置)
                - 点击"开始推理"
                - 查看结果: `情`(2次), `己`(2次), `吁`(2次)...
                
                **🎯 位置功能**:
                - 添加线索字符: `痛` (位置设为1表示必须在第1位)
                - 推理结果: `心`(痛心), `风`(痛风), `恨`(痛恨)...
                - 位置限制大大提高了推理精度
                
                **📚 实际案例**:
                
                **案例1 - 猜字谜（任意位置）**:
                ```
                线索: 日(位置:任意), 月(位置:任意), 星(位置:任意)
                分析: 寻找能与"日"、"月"、"星"组词的字符
                结果: 辰(日月星辰), 光(日光、月光、星光), 空(...)
                ```
                
                **案例2 - 精确位置推理**:
                ```
                线索: 痛(位置:1)
                分析: "痛"必须在词汇的第1位
                结果: 心(痛心), 风(痛风), 恨(痛恨), 击(痛击)
                高精度: 所有结果都是"痛X"格式
                ```
                
                **案例3 - 混合位置要求**:
                ```
                线索: 不(位置:2), 生(位置:4)  
                分析: "不"在第2位，"生"在第4位
                结果: 可能找到"X不X生"格式的词汇
                ```
                
                **案例4 - 成语填空**:
                ```
                线索: 天(位置:1), 利(位置:4)  
                分析: "天X地利"格式
                结果: 时(天时地利)
                ```
                
                **💡 使用技巧**:
                
                1. **线索质量**: 
                   - 选择常用字符作为线索效果更好
                   - 线索字符之间最好有一定关联性
                   - 避免使用生僻字作为线索
                
                2. **位置设置**:
                   - **位置=0**: 字符可在词汇任意位置（默认）
                   - **位置=1**: 字符必须在词汇第1位
                   - **位置=2**: 字符必须在词汇第2位
                   - **位置越精确，结果越准确但数量越少**
                
                3. **结果解读**:
                   - **匹配度**: 数字表示该字符满足多少个线索要求
                   - **示例词汇**: 展示具体的组词情况，帮助判断是否符合预期
                   - **排序**: 结果按匹配度从高到低排序
                
                4. **策略建议**:
                   - 从少量线索开始，逐步增加
                   - 先用任意位置(0)探索，再用精确位置细化
                   - 观察高匹配度字符的词汇示例
                   - 结合具体语境判断最符合的答案
                
                **⚠️ 注意事项**:
                - 每次只能添加一个字符作为线索
                - 重复的线索字符会被自动过滤
                - 推理结果基于词典中的组词关系
                - 匹配度仅供参考，需结合实际语境判断
                """)
            
            # Tab 5: 中文汉字查询（增强版）
            with gr.TabItem("🇨🇳 中文汉字查询"):
                gr.Markdown("## 中文汉字拼音和笔画查询系统")
                gr.Markdown("支持多种查询条件组合：笔画数(可选)、声母、韵母、音调、笔画序列、偏旁部首")
                
                # 获取可用选项（与同义词查询保持一致）
                try:
                    from pinyin_tools import (get_available_finals, get_available_initials, 
                                            get_available_tones, get_available_strokes, get_available_radicals)
                    available_finals_hanzi = [""] + get_available_finals()
                    available_initials_hanzi = [""] + get_available_initials()
                    available_tones_hanzi = [""] + get_available_tones()
                except ImportError:
                    print("⚠️ 汉字查询：拼音工具模块不可用，使用默认选项")
                    available_finals_hanzi = ["", "a", "o", "e", "i", "u", "v", "ai", "ei", "ui", "ao", "ou", "iu", 
                                            "ie", "ue", "ve", "er", "an", "en", "in", "un", "vn", "ang", "eng", "ing", "ong",
                                            "ia", "iao", "ian", "iang", "iong", "ua", "uo", "uai", "uan", "uang"]
                    available_initials_hanzi = ["", "b", "p", "m", "f", "d", "t", "n", "l", 
                                               "g", "k", "h", "j", "q", "x", "zh", "ch", "sh", 
                                               "r", "z", "c", "s", "y", "w", "无声母"]
                    available_tones_hanzi = ["", "1", "2", "3", "4", "轻声"]
                
                # 查询输入区域
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📊 基本查询条件")
                        
                        # 第一行：笔画数和拼音
                        with gr.Row():
                            stroke_count_input = gr.Number(
                                label="笔画数 (可选，1-50)",
                                minimum=1,
                                maximum=50,
                                step=1,
                                value=None,
                                precision=0,
                                info="留空表示不限制笔画数"
                            )
                            
                            initial_dropdown = gr.Dropdown(
                                label="声母 (可选)",
                                choices=available_initials_hanzi,
                                value="",
                                interactive=True
                            )
                        
                        # 第二行：韵母和音调
                        with gr.Row():
                            final_dropdown = gr.Dropdown(
                                label="韵母 (可选)",
                                choices=available_finals_hanzi,
                                value="",
                                interactive=True
                            )
                            
                            tone_dropdown = gr.Dropdown(
                                label="音调 (可选)",
                                choices=available_tones_hanzi,
                                value="",
                                interactive=True
                            )
                        
                        # 偏旁部首选择区域
                        gr.Markdown("### 🏗️ 偏旁部首选择")
                        
                        with gr.Row():
                            # 初始化偏旁列表
                            searcher = PinyinSearcher()
                            available_radicals = searcher.get_available_radicals()
                            
                            radicals_selector = gr.CheckboxGroup(
                                label="选择偏旁部首 (可多选)",
                                choices=available_radicals,
                                value=[],
                                interactive=True
                            )
                        
                        with gr.Row():
                            select_all_radicals_btn = gr.Button("全选偏旁", size="sm")
                            clear_all_radicals_btn = gr.Button("清空偏旁", size="sm")
                        
                        # 笔画序列查询区域  
                        gr.Markdown("### ✏️ 笔画序列查询")
                        gr.Markdown("🎯 **使用说明**: 直接输入数字指定笔画位置，如输入1表示第1画")
                        
                        with gr.Row():
                            position_input = gr.Number(
                                label="笔画位置",
                                minimum=1,
                                maximum=30,
                                step=1,
                                value=None,
                                precision=0,
                                info="输入数字，如: 1表示第1画"
                            )
                            
                            stroke_type_dropdown = gr.Dropdown(
                                label="笔画类型",
                                choices=["横", "竖", "撇", "捺", "点", "折", "弯", "钩"],
                                value=None,
                                interactive=True
                            )
                            
                            add_stroke_btn = gr.Button("➕ 添加笔画条件", size="sm")
                        
                        # 当前笔画条件显示
                        stroke_status_display = gr.Markdown("📝 **当前笔画条件**: 无")
                        
                        # 移除笔画条件
                        with gr.Row():
                            remove_stroke_dropdown = gr.Dropdown(
                                label="移除笔画条件",
                                choices=[],
                                value=None,
                                interactive=True
                            )
                            remove_stroke_btn = gr.Button("🗑️ 移除选中条件", size="sm")
                        
                        # 控制按钮
                        with gr.Row():
                            max_results_slider = gr.Slider(
                                minimum=10, 
                                maximum=200, 
                                value=100, 
                                label="最大结果数",
                                step=10
                            )
                        
                        with gr.Row():
                            combined_search_btn = gr.Button("🔍 组合查询", variant="primary", scale=2)
                            clear_all_btn = gr.Button("🧹 清空所有", variant="secondary", scale=1)
                            
                    with gr.Column():
                        gr.Markdown("### 📋 查询结果")
                        combined_output = gr.Textbox(
                            label="组合查询结果",
                            lines=25,
                            interactive=False,
                            show_copy_button=True
                        )
                
                # 笔画条件状态管理
                stroke_conditions_state = gr.State({})
                
                # 事件处理函数
                def add_stroke_condition(position, stroke_type, current_conditions):
                    """添加笔画条件"""
                    if position is None or not stroke_type:
                        return current_conditions, "📝 **当前笔画条件**: 请输入笔画位置和选择笔画类型", gr.update(choices=list(current_conditions.keys()))
                    
                    # 将数字转换为"第X画"格式用于显示和内部处理
                    position_key = f"第{int(position)}画"
                    current_conditions[position_key] = stroke_type
                    
                    # 更新显示
                    if current_conditions:
                        display_text = "📝 **当前笔画条件**: " + " | ".join([f"{pos}: {stroke}" for pos, stroke in current_conditions.items()])
                    else:
                        display_text = "📝 **当前笔画条件**: 无"
                    
                    return current_conditions, display_text, gr.update(choices=list(current_conditions.keys()))
                
                def remove_stroke_condition(position_to_remove, current_conditions):
                    """移除笔画条件"""
                    if position_to_remove and position_to_remove in current_conditions:
                        del current_conditions[position_to_remove]
                    
                    # 更新显示
                    if current_conditions:
                        display_text = "📝 **当前笔画条件**: " + " | ".join([f"{pos}: {stroke}" for pos, stroke in current_conditions.items()])
                    else:
                        display_text = "📝 **当前笔画条件**: 无"
                    
                    return current_conditions, display_text, gr.update(choices=list(current_conditions.keys()), value=None)
                
                def select_all_radicals():
                    """全选偏旁"""
                    return available_radicals
                
                def clear_all_radicals():
                    """清空偏旁选择"""
                    return []
                
                def combined_search_interface(stroke_count, initial, final, tone, max_results, stroke_conditions, selected_radicals):
                    """组合查询界面处理函数"""
                    from pinyin_searcher import process_combined_search
                    
                    # 检查是否有笔画序列条件
                    stroke_positions = {}
                    if stroke_conditions:
                        # 将UI的字典格式转换为位置字典
                        for position_str, stroke_type in stroke_conditions.items():
                            # 从"第X画"中提取数字
                            position_num = int(position_str.replace("第", "").replace("画", ""))
                            stroke_positions[position_num] = stroke_type
                    
                    # 使用新的组合查询函数
                    return process_combined_search(
                        strokes=str(stroke_count) if stroke_count is not None else "",
                        initial=initial or "",
                        final=final or "",
                        tone=tone or "",
                        stroke_positions=stroke_positions if stroke_positions else None,
                        radicals=selected_radicals if selected_radicals else None,
                        max_results=max_results
                    )
                
                def clear_all_inputs():
                    """清空所有输入"""
                    # 清空基本条件 (笔画数用None，其他用空字符串)
                    basic_clear = (None, "", "", "", 100, "")
                    # 清空笔画条件
                    stroke_clear = ({}, "📝 **当前笔画条件**: 无", gr.update(choices=[], value=None))
                    # 清空偏旁选择
                    radicals_clear = ([],)
                    
                    return basic_clear + stroke_clear + radicals_clear
                
                # 绑定事件
                add_stroke_btn.click(
                    fn=add_stroke_condition,
                    inputs=[position_input, stroke_type_dropdown, stroke_conditions_state],
                    outputs=[stroke_conditions_state, stroke_status_display, remove_stroke_dropdown]
                )
                
                remove_stroke_btn.click(
                    fn=remove_stroke_condition,
                    inputs=[remove_stroke_dropdown, stroke_conditions_state],
                    outputs=[stroke_conditions_state, stroke_status_display, remove_stroke_dropdown]
                )
                
                select_all_radicals_btn.click(
                    fn=select_all_radicals,
                    outputs=radicals_selector
                )
                
                clear_all_radicals_btn.click(
                    fn=clear_all_radicals,
                    outputs=radicals_selector
                )
                
                combined_search_btn.click(
                    fn=combined_search_interface,
                    inputs=[stroke_count_input, initial_dropdown, final_dropdown, tone_dropdown, 
                           max_results_slider, stroke_conditions_state, radicals_selector],
                    outputs=combined_output
                )
                
                clear_all_btn.click(
                    fn=clear_all_inputs,
                    outputs=[stroke_count_input, initial_dropdown, final_dropdown, tone_dropdown, 
                            max_results_slider, stroke_status_display, stroke_conditions_state, 
                            remove_stroke_dropdown, radicals_selector]
                )
        
        # 页脚信息
        gr.Markdown("---")
        gr.Markdown("💡 **提示**: 所有查询条件都是可选的，可以单独使用或组合使用以获得更精确的结果")
        gr.Markdown("🔧 **技术**: 基于 Gradio + Python 构建的多功能密码学工具集")
    
    return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
