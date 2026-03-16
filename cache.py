"""
缓存模块 - 负责管理交易哈希的缓存
"""
import json
from pathlib import Path
from typing import Set


class CacheManager:
    """缓存管理类"""
    
    def __init__(self, cache_dir: str = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径，默认为项目根目录下的 cache 文件夹
        """
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent / "cache"
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_file(self, wallet: str) -> Path:
        """获取钱包对应的缓存文件路径"""
        short_addr = wallet[:10] + "..." + wallet[-6:]
        return self._cache_dir / f"seen_hashes_{short_addr}.json"
    
    def load_seen_hashes(self, wallet: str) -> Set[str]:
        """
        加载指定钱包的已保存的 transactionHash
        
        Args:
            wallet: 钱包地址
            
        Returns:
            已见交易哈希集合
        """
        cache_path = self._get_cache_file(wallet)
        if not cache_path.exists():
            return set()
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("hashes", []))
        except Exception as e:
            print(f"[{wallet[:10]}...] 加载缓存失败: {e}")
            return set()
    
    def save_seen_hashes(self, wallet: str, hashes: Set[str]) -> None:
        """
        保存指定钱包的已见 transactionHash
        
        Args:
            wallet: 钱包地址
            hashes: 交易哈希集合
        """
        cache_path = self._get_cache_file(wallet)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"wallet": wallet, "hashes": list(hashes)}, 
                    f, 
                    ensure_ascii=False, 
                    indent=2
                )
        except Exception as e:
            print(f"[{wallet[:10]}...] 保存缓存失败: {e}")


cache_manager = CacheManager()
