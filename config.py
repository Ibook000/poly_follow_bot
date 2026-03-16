"""
配置模块 - 负责加载和管理配置
"""
import json
from pathlib import Path
from typing import Dict, Any, List


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，默认为 config.json
        """
        if config_path is None:
            config_path = Path(__file__).resolve().parent / "config.json"
        self._config = self._load_config(config_path)
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        if not config_path.exists():
            return {}
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    @property
    def wallets(self) -> List[str]:
        """获取监控的钱包列表"""
        return self._config.get("wallets", [])
    
    @property
    def discord_webhook_url(self) -> str:
        """获取Discord webhook URL"""
        return self._config.get("discord_webhook_url", "")
    
    @property
    def poll_interval(self) -> int:
        """获取轮询间隔（秒）"""
        return self._config.get("poll_interval", 10)
    
    @property
    def private_key(self) -> str:
        """获取私钥"""
        return self._config.get("private_key", "")
    
    @property
    def funder(self) -> str:
        """获取funder地址"""
        return self._config.get("funder", "")
    
    @property
    def signature_type(self) -> int:
        """获取签名类型"""
        return self._config.get("signature_type", 0)
    
    @property
    def tp(self) -> dict:
        return self._config.get("tp", {"enabled": False, "type": "price", "value": 0.99})
    @property
    def sl(self) -> dict:
        return self._config.get("sl", {"enabled": False, "type": "percent", "value": 0.5})

    @property
    def price_filter(self) -> dict:
        return self._config.get("price_filter", {"enabled": False, "min_price": 0, "max_price": 1})

    @property
    def no_duplicate(self) -> dict:
        return self._config.get("no_duplicate", {"enabled": False, "expire_seconds": 3600})


config = Config()
WALLETS = config.wallets
DISCORD_WEBHOOK_URL = config.discord_webhook_url
POLL_INTERVAL = config.poll_interval
PRIVATE_KEY = config.private_key
FUNDER = config.funder
SIGNATURE_TYPE = config.signature_type
