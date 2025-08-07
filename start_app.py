#!/usr/bin/env python3
"""直接启动应用的脚本"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 synonyms 库需要的环境变量
os.environ['SYNONYMS_DL_LICENSE'] = 'true'

def main():
    try:
        print("🚀 启动密码学工具集...")
        print("📍 当前包含功能:")
        print("   🔍 对角线提取工具")
        print("   📚 单词字典查询") 
        print("   🔍 中文同义词查询(Qwen驱动)")
        print("      - 🚀 统一处理算法：智能判断纯筛选或语义搜索模式")
        print("      - 🎯 二分查找优化：毫秒级韵母筛选，性能提升千倍")
        print("      - 🧠 Qwen3-Embedding：1024维语义向量，精准相似度计算")
        print("      - 🎵 押韵创作支持：23种声母+32种韵母筛选，诗词对仗工整")
        print("      - � 长度筛选支持：可设置最小/最大字符数，精确控制词汇长度")
        print("      - �📚 海量词库：25万+词汇覆盖，支持任意中文词汇")
        print("      - ✅ 高级验证修复：声母'g'等字符正确处理，筛选结果准确")
        print("   🇨🇳 中文汉字查询(增强版)")
        print("      - 偏旁按字数量排序，常用偏旁优先")
        print("      - 笔画数可选，笔画位置数字输入")
        print("      - 支持组合查询和多音字显示")
        print()
        
        # 直接导入并启动
        try:
            # 尝试直接导入（推荐方式）
            from gradio_interface import create_interface
        except ImportError as e1:
            # 如果失败，尝试包导入
            try:
                from mytools.gradio_interface import create_interface
            except ImportError as e2:
                print(f"❌ 模块导入失败: {e1},{e2}]")
                print("请确保在正确的目录下运行脚本")
                return
        
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
