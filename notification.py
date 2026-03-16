"""
通知模块 - 负责发送Discord通知
"""
import requests
from typing import Dict, Any, Optional


class NotificationManager:
    """通知管理类"""
    
    def __init__(self, webhook_url: str = ""):
        """
        初始化通知管理器
        
        Args:
            webhook_url: Discord webhook URL
        """
        self._webhook_url = webhook_url
        self._timeout = 10
    
    @property
    def is_configured(self) -> bool:
        """检查是否配置了webhook"""
        return bool(self._webhook_url)
    
    def send_trade_notification(
        self, 
        trade: Dict[str, Any], 
        wallet: str,
        proxy_wallet: Optional[str] = None
    ) -> bool:
        """
        发送交易通知
        
        Args:
            trade: 交易信息字典
            wallet: 监控的钱包地址
            proxy_wallet: 代理钱包地址（可选）
            
        Returns:
            是否发送成功
        """
        if not self._webhook_url:
            return False
        
        print(f"[{wallet[:10]}...] 发送Discord通知: {trade.get('transactionHash')}")
        
        proxy_wallet = proxy_wallet or wallet
        tx_hash = trade.get('transactionHash', '')
        side = trade.get('side', '')
        size = trade.get('size', '')
        price = trade.get('price', '')
        asset = trade.get('asset', '')
        title = trade.get('title', '')
        outcome = trade.get('outcome', '')
        timestamp = trade.get('timestamp', '')
        slug = trade.get("slug", "")
        icon = trade.get("icon", "")
        
        # 计算交易金额
        amount = 0.0
        try:
            amount = float(price) * float(size)
        except (ValueError, TypeError):
            pass
        
        # 根据交易方向选择颜色
        color = 0x00FF00 if side.lower() == 'yes' else 0xFF0000
        
        # 构建thumbnail
        thumbnail = {}
        if icon:
            thumbnail = {"url": icon}
        
        # 构建embed
        embed_content = {
            "title": f"新交易提醒 - {side.upper()}",
            "color": color,
            "thumbnail": thumbnail,
            "fields": [
                {"name": "监听地址", "value": f"{wallet[:10]}...{wallet[-6:]}", "inline": True},
                {"name": "标题", "value": title[:256] if title else "N/A", "inline": True},
                {"name": "结果", "value": outcome if outcome else "N/A", "inline": True},
                {"name": "数量", "value": str(size) if size else "N/A", "inline": True},
                {"name": "价格", "value": f"${price}" if price else "N/A", "inline": True},
                {"name": "金额", "value": f"${amount:.2f}" if amount else "N/A", "inline": True},
                {"name": "Asset", "value": asset[:256] if asset else "N/A", "inline": False},
                {"name": "交易Hash", "value": f"{tx_hash}", "inline": False},
                {"name": "市场链接", "value": f"[查看交易](https://polymarket.com/event/{slug})", "inline": False},
            ],
            "footer": {"text": f"交易时间: {timestamp}"},
            "timestamp": timestamp
        }
        
        payload = {"embeds": [embed_content]}
        
        try:
            response = requests.post(
                self._webhook_url, 
                json=payload, 
                timeout=self._timeout
            )
            
            if response.status_code in (204, 200):
                return True
            else:
                print(f"Discord通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Discord通知发送异常: {e}")
            return False

    def send_order_result(
        self,
        original_trade: Dict[str, Any],
        wallet: str,
        order_id: str = None,
        order_result: bool = False,
        token_id: str = None,
        amount: float = None,
        response: str = None
    ) -> bool:
        """
        发送下单结果通知
        
        Args:
            original_trade: 原始交易信息
            wallet: 钱包地址
            order_result: 下单是否成功
            token_id: token ID
            amount: 下单数量
            response: 下单响应信息
            
        Returns:
            是否发送成功
        """
        if not self._webhook_url:
            return False
        
        print(f"[{wallet[:10]}...] 发送下单结果通知: {'成功' if order_result else '失败'}")
        
        tx_hash = original_trade.get('transactionHash', '')
        title = original_trade.get('title', '')
        side = original_trade.get('side', '')
        
        color = 0x00FF00 if order_result else 0xFF0000
        status_emoji = "成功" if order_result else "失败"
        
        if order_id:
            fields = [
                {"name": "跟单状态", "value": f"{status_emoji}", "inline": True},
                {"name": "订单ID", "value": str(order_id), "inline": False},
                {"name": "原始交易", "value": f"{tx_hash[:20]}...", "inline": False},
                {"name": "市场", "value": title[:256] if title else "N/A", "inline": False},
            ]
        else:
            fields = [
                {"name": "跟单状态", "value": f"{status_emoji}", "inline": True},
                {"name": "原始交易", "value": f"{tx_hash[:20]}...", "inline": False},
                {"name": "市场", "value": title[:256] if title else "N/A", "inline": False},
            ]
        
        if token_id:
            fields.append({"name": "Token ID", "value": str(token_id), "inline": False})
        
        if amount is not None:
            fields.append({"name": "下单数量", "value": str(amount), "inline": True})
        
        if response:
            fields.append({"name": "下单响应", "value": str(response)[:500], "inline": False})
        
        embed = {
            "title": f"跟单{'成功' if order_result else '失败'}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"监听地址: {wallet[:10]}..."},
        }
        
        try:
            payload = {"embeds": [embed]}
            response = requests.post(
                self._webhook_url, 
                json=payload, 
                timeout=self._timeout
            )
            
            if response.status_code in (204, 200):
                return True
            else:
                print(f"Discord通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Discord通知发送异常: {e}")
            return False


# 创建全局通知管理器实例
from config import DISCORD_WEBHOOK_URL
notification_manager = NotificationManager(DISCORD_WEBHOOK_URL)

