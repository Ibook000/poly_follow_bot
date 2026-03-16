"""
API模块 - 负责与Polymarket API交互
"""
import requests
from typing import List, Dict, Any


class PolymarketAPI:
    """Polymarket API 交互类"""
    
    def __init__(self, base_url: str = "https://data-api.polymarket.com", timeout: int = 10):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self._base_url = base_url
        self._timeout = timeout
    
    def get_trades(self, wallet: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取钱包的交易记录
        
        Args:
            wallet: 钱包地址
            limit: 返回记录数量限制
            
        Returns:
            交易记录列表
        """
        try:
            response = requests.get(
                url=f"{self._base_url}/trades",
                params={"user": wallet, "limit": limit},
                timeout=self._timeout
            )
            
            if not response.ok:
                print(f"[{wallet[:10]}...] 请求失败: {response.status_code}")
                return []
            
            return response.json()
            
        except Exception as e:
            print(f"[{wallet[:10]}...] 请求异常: {e}")
            return []



api = PolymarketAPI()
