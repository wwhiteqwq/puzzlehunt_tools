#!/usr/bin/env python3
"""直接启动应用的脚本"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        print("🚀 启动密码学工具集...")
        print("📍 当前包含功能:")
        print("   🔍 对角线提取工具")
        print("   📚 单词字典查询") 
        print("   🇨🇳 中文汉字查询(增强版)")
        print("      - 偏旁按字数量排序，常用偏旁优先")
        print("      - 笔画数可选，笔画位置数字输入")
        print("      - 支持组合查询和多音字显示")
        print()
        
        # 直接导入并启动
        try:
            from mytools.gradio_interface import create_interface
        except ImportError:
            # 如果相对导入失败，使用绝对导入
            from gradio_interface import create_interface
        
        print("✅ 创建界面...")
        demo = create_interface()
        
        print("🌐 启动Web服务器...")
        print("📍 访问地址: http://localhost:7860")
        print("🔄 Shuffle功能已启用!")
        
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            # share=True,
            inbrowser=True
        )
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔧 可能的解决方案:")
        print("1. 确保已安装gradio: pip install gradio")
        print("2. 检查文件路径是否正确")
        print("3. 查看上述错误信息")

if __name__ == "__main__":
    main()
