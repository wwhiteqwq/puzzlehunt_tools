#!/usr/bin/env python3
"""
Qwen Embedding客户端
支持通过HTTP API调用Qwen embedding服务
"""

import requests
import numpy as np
from typing import List, Dict, Any, Optional
import json

class QwenEmbeddingClient:
    """Qwen embedding服务客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """初始化Qwen客户端"""
        self.base_url = base_url
        self.embed_url = f"{base_url}/embed"
        self.available = False
        self._test_connection()
    
    def _test_connection(self):
        """测试连接"""
        try:
            # 测试健康检查端点
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                self.available = True
                print("✅ Qwen embedding服务连接成功")
            else:
                print(f"⚠️ Qwen服务响应异常: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Qwen embedding服务连接失败: {e}")
            print("💡 请确保:")
            print("   1. Docker容器已启动")
            print("   2. 服务运行在 http://localhost:8080")
            print("   3. 网络连接正常")
    
    def encode(self, texts: List[str]) -> Optional[np.ndarray]:
        """编码文本为向量"""
        if not self.available:
            return None
        
        try:
            # 准备请求数据
            payload = {
                "inputs": texts,
                "truncate": True
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # 发送请求
            response = requests.post(
                self.embed_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # 解析响应
                result = response.json()
                
                # 提取embeddings
                if isinstance(result, list):
                    # 直接是embeddings列表
                    embeddings = np.array(result)
                elif isinstance(result, dict) and 'embeddings' in result:
                    # 包含embeddings字段
                    embeddings = np.array(result['embeddings'])
                else:
                    print(f"⚠️ 未知的响应格式: {type(result)}")
                    return None
                
                return embeddings
            else:
                print(f"❌ Qwen服务请求失败: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Qwen编码失败: {e}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            info_url = f"{self.base_url}/info"
            response = requests.get(info_url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

def test_qwen_client():
    """测试Qwen客户端"""
    print("🧪 测试Qwen embedding客户端")
    print("=" * 50)
    
    client = QwenEmbeddingClient()
    
    if not client.available:
        print("❌ Qwen服务不可用")
        return
    
    # 获取模型信息
    model_info = client.get_model_info()
    print(f"📊 模型信息: {model_info}")
    
    # 测试编码
    test_texts = ["测试文本", "高兴", "美丽"]
    print(f"\n🔍 测试编码: {test_texts}")
    
    embeddings = client.encode(test_texts)
    
    if embeddings is not None:
        print(f"✅ 编码成功!")
        print(f"   形状: {embeddings.shape}")
        print(f"   数据类型: {embeddings.dtype}")
        print(f"   第一个向量前5维: {embeddings[0][:5]}")
    else:
        print("❌ 编码失败")

if __name__ == "__main__":
    test_qwen_client()
