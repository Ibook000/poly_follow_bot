"""
交易模块 - 负责与Polymarket CLOB交互进行交易
"""
from typing import Optional
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY, SELL
import time
from config import PRIVATE_KEY, FUNDER, SIGNATURE_TYPE


class TradingClient:
    """交易客户端类"""
    
    def __init__(
        self,
        host: str = "https://clob.polymarket.com",
        key: str = None,
        chain_id: int = 137,
        signature_type: int = 0,
        funder: str = None
    ):
        """
        初始化交易客户端
        
        Args:
            host: CLOB服务地址
            key: 私钥
            chain_id: 链ID（137 = Polygon）
            signature_type: 签名类型
            funder: funder地址
        """
        self._key = key or PRIVATE_KEY
        self._signature_type = signature_type or SIGNATURE_TYPE
        self._funder = funder or FUNDER
        self._chain_id = chain_id
        self._host = host
        self._client: Optional[ClobClient] = None
        self._init_client()
    
    def _init_client(self) -> None:
        """初始化ClobClient"""
        try:
            self._client = ClobClient(
                host=self._host,
                key=self._key,
                chain_id=self._chain_id,
                signature_type=self._signature_type,
                funder=self._funder or None,
            )
            self._client.set_api_creds(self._client.create_or_derive_api_creds())
        except Exception as e:
            print(f"初始化ClobClient失败: {e}")
            self._client = None
    
    @property
    def client(self) -> Optional[ClobClient]:
        """获取CLOB客户端实例"""
        return self._client
    
    def get_balance(self) -> float:
        """获取当前USDC余额"""
        if not self._client:
            return 0.0
        
        try:
            balance = self._client.get_balance_allowance(
                BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )
            return int(balance.get('balance', 0)) / 1000000
        except Exception as e:
            print(f"获取余额失败: {e}")
            return 0.0
    
    def place_market_order(
        self,
        token_id: str,
        amount: float,
        side: str = "BUY",
        order_type: OrderType = OrderType.FOK,
        max_attempts: int = 2
    ):
        """
        下市价单
        
        Args:
            token_id: 合约token ID
            amount: 数量
            side: 买卖方向 (BUY/SELL)
            order_type: 订单类型
            max_attempts: 最大重试次数
            
        Returns:
            是否下单成功, 下单结果或错误信息, 订单ID
        """
        if not self._client:
            print("交易客户端未初始化")
            return False,"交易客户端未初始化",None
        
        if amount <= 0:
            print("下单数量必须大于0")
            return False,"下单数量必须大于0",None
        
        print(f"尝试下单: token_id={token_id}, 数量={amount}")
        if side.upper() == "BUY":
            side_constant=BUY
        else:
            side_constant=SELL
        
        
        for attempt in range(max_attempts):
            try:
                market_order = MarketOrderArgs(
                    token_id=token_id,
                    amount=amount,
                    side=side_constant,
                    order_type=order_type,
                )
                
                signed_order = self._client.create_market_order(market_order)
                response = self._client.post_order(signed_order, order_type)
                
                print(f"下单成功: {response},下单信息{signed_order}")
                return True,response,response.get("orderID") 
            except Exception as e:
                print(f"下单失败 (尝试 {attempt + 1}/{max_attempts}) 数量:{amount}: {e}")
        return False, "重试次数耗尽",None 

    def place_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str = "SELL",
        max_attempts: int = 10
    ) -> tuple:
        """
        下限价单（用于止止盈）
        
        Args:
            token_id: 合约token ID
            price: 限价价格 (0.00-1.00)
            size: 数量
            side: 买卖方向 (BUY/SELL)
            max_attempts: 最大重试次数
            
        Returns:
            (是否成功, 结果或错误信息)
        """
        if not self._client:
            return False, "交易客户端未初始化",None
        
        if price <= 0 or price > 1:
            return False, "价格必须在0-1之间",None
        
        if size <= 0:
            return False, "数量必须大于0",None
        
        print(f"尝试下限价单: token_id={token_id}, 价格={price}, 数量={size}, 方向={side}")
        
        side_constant = SELL if side.upper() == "SELL" else BUY
        
        for attempt in range(max_attempts):
            try:
                order = OrderArgs(
                    token_id=token_id,
                    price=price,
                    size=size,
                    side=side_constant,
                )
                
                signed_order = self._client.create_order(order)
                response = self._client.post_order(signed_order, OrderType.GTC)
                
                print(f"限价单下单成功: {response}")
                return True, response,response.get("orderID")
                
            except Exception as e:
                time.sleep(0.1)
                size=size-0.1
                print(f"限价单下单失败 (尝试 {attempt + 1}/{max_attempts}) 数量:{size}: {e}")
        return False, "重试次数耗尽",None 
    def wait_for_order_matched(self,order_id, timeout=10, interval=2,unmatched_cancel=True):
        end = time.time() + timeout
        while time.time() < end:
            order = self._client.get_order(order_id)
            if order is None:
                print(f"警告: 订单 {order_id} 查询结果为空")
                time.sleep(interval)
                continue
            print(f"查询订单 {order_id} 状态: {order}")
            status = order.get("status")
            if status is None:
                print(f"警告: 订单 {order_id} 状态为空, 响应: {order}")
                time.sleep(interval)
                continue
            status = status.lower()
            if status == "unmatched" and unmatched_cancel:
                self._client.cancel(order_id)
                print(f"市价成交失败,撤销订单{order_id}")
            if status in ["matched", "live", "cancelled"]:
                return order
            print("waiting...", status)
            time.sleep(interval)
        return order




# 创建全局交易客户端实例
try:
    trading_client = TradingClient()
except Exception as e:
    print(f"警告: 交易客户端初始化失败: {e}")
    trading_client = None
