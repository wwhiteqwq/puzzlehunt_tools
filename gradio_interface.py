# Gradio 界面
# 整体框架基于 gradio 实现，提供密码学工具集的Web界面

import gradio as gr

# 支持both相对导入和绝对导入
try:
    from .diagonal_extractor import process_extraction
    from .word_checker import process_word_query
    from .pinyin_searcher import process_pinyin_search, PinyinSearcher
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from diagonal_extractor import process_extraction
    from word_checker import process_word_query
    from pinyin_searcher import process_pinyin_search, PinyinSearcher


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
            
            # Tab 3: 中文汉字查询（增强版）
            with gr.TabItem("🇨🇳 中文汉字查询"):
                gr.Markdown("## 中文汉字拼音和笔画查询系统")
                gr.Markdown("支持多种查询条件组合：笔画数(可选)、声母、韵母、音调、笔画序列、偏旁部首")
                
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
                                choices=["", "b", "p", "m", "f", "d", "t", "n", "l", 
                                        "g", "k", "h", "j", "q", "x", "zh", "ch", "sh", 
                                        "r", "z", "c", "s", "y", "w", "无声母"],
                                value="",
                                interactive=True
                            )
                        
                        # 第二行：韵母和音调
                        with gr.Row():
                            final_dropdown = gr.Dropdown(
                                label="韵母 (可选)",
                                choices=["", "a", "o", "e", "i", "u", "v", "ai", "ei", "ui", "ao", "ou", "iu", 
                                        "ie", "ve", "er", "an", "en", "in", "un", "vn", "ang", "eng", "ing", "ong",
                                        "ia", "iao", "ian", "iang", "iong", "ua", "uo", "uai", "uan", "uang"],
                                value="",
                                interactive=True
                            )
                            
                            tone_dropdown = gr.Dropdown(
                                label="音调 (可选)",
                                choices=["", "1", "2", "3", "4", "轻声"],
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
