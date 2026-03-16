"""
监控模块 - 负责监控钱包交易并处理跟单逻辑
"""
import time
import threading
import traceback
from typing import Dict, Any, Set, List
from queue import Queue, Empty

from api import PolymarketAPI, api
from cache import CacheManager, cache_manager
from notification import NotificationManager, notification_manager
from trading import TradingClient, trading_client
from config import WALLETS, POLL_INTERVAL, config


class WalletMonitor:
    """钱包监控类"""
    
    def __init__(
        self,
        wallets: List[str],
        poll_interval: int = 10,
        api_client: PolymarketAPI = None,
        cache_mgr: CacheManager = None,
        notification_mgr: NotificationManager = None,
        trading_client: TradingClient = None
    ):
        """
        初始化钱包监控器
        
        Args:
            wallets: 要监控的钱包地址列表
            poll_interval: 轮询间隔（秒）
            api_client: API客户端实例
            cache_mgr: 缓存管理器实例
            notification_mgr: 通知管理器实例
            trading_client: 交易客户端实例
        """
        self._wallets = wallets
        self._poll_interval = poll_interval
        self._running = False
        self._lock = threading.Lock()
        self._trade_queue = Queue()
        
        # 已跟单市场记录 {token_id: timestamp}
        self._followed_markets: Dict[str, float] = {}
        
        # 依赖注入
        self._api = api_client or api
        self._cache = cache_mgr or cache_manager
        self._notification = notification_mgr or notification_manager
        self._trading = trading_client if trading_client is not None else None
    
    @property
    def trade_queue(self) -> Queue:
        """获取交易队列"""
        return self._trade_queue
    
    def start(self) -> List[threading.Thread]:
        """
        启动所有监控线程
        
        Returns:
            线程列表
        """
        global running
        self._running = True
        
        threads = []
        
        # 为每个钱包启动监控线程
        for wallet in self._wallets:
            t = threading.Thread(
                target=self._monitor_wallet, 
                args=(wallet,), 
                daemon=True
            )
            t.start()
            threads.append(t)
            time.sleep(0.5)
        
        # 启动跟单处理线程
        follow_thread = threading.Thread(
            target=self._process_follow_trades, 
            daemon=True
        )
        follow_thread.start()
        threads.append(follow_thread)
        
        return threads
    
    def stop(self) -> None:
        """停止所有监控"""
        self._running = False
    
    def _monitor_wallet(self, wallet: str) -> None:
        """
        监控单个钱包的线程函数
        
        Args:
            wallet: 钱包地址
        """
        # 初始化已见哈希集合
        seen_hashes = self._cache.load_seen_hashes(wallet)
        
        # 初始加载历史交易
        all_trades = self._api.get_trades(wallet, 100)
        seen_hashes.update(
            trade.get("transactionHash") 
            for trade in all_trades 
            if trade.get("transactionHash")
        )
        self._cache.save_seen_hashes(wallet, seen_hashes)
        print(f"[{wallet[:10]}...] 初始化完成，已加载 {len(seen_hashes)} 个缓存")
        
        while self._running:
            try:
                all_trades = self._api.get_trades(wallet, 50)
                new_trades = []
                
                for trade in all_trades:
                    tx_hash = trade.get("transactionHash")
                    if not tx_hash:
                        continue
                    if tx_hash not in seen_hashes:
                        new_trades.append(trade)
                
                if new_trades:
                    self._handle_new_trades(new_trades, wallet, seen_hashes)
                
                time.sleep(self._poll_interval)
                
            except Exception as e:
                print(f"[{wallet[:10]}...] 监控异常: {e}")
                time.sleep(self._poll_interval)
        
        print(f"[{wallet[:10]}...] 线程已停止")
    
    def _handle_new_trades(
        self, 
        new_trades: List[Dict[str, Any]], 
        wallet: str,
        seen_hashes: Set[str]
    ) -> None:
        """
        处理新发现的交易
        
        Args:
            new_trades: 新交易列表
            wallet: 钱包地址
            seen_hashes: 已见哈希集合
        """
        print(f"\n[{time.strftime('%H:%M:%S')}] [{wallet[:10]}...] 发现 {len(new_trades)} 条新交易!")
        
        for trade in new_trades:
            self._print_trade(trade, wallet)
            self._trade_queue.put((trade, wallet))
            seen_hashes.add(trade.get("transactionHash"))
        
        self._cache.save_seen_hashes(wallet, seen_hashes)
        print(f"[{wallet[:10]}...] 已保存 {len(seen_hashes)} 个 transactionHash 到缓存")
    
    def _print_trade(self, trade: Dict[str, Any], wallet: str) -> None:
        """
        格式化打印交易信息
        
        Args:
            trade: 交易信息
            wallet: 钱包地址
        """
        print(f"[{wallet[:10]}...] transactionHash: {trade.get('transactionHash')}")
        print(f"[{wallet[:10]}...] token_id: {trade.get('asset')}")
        print(f"[{wallet[:10]}...] side: {trade.get('side')}")
        print(f"[{wallet[:10]}...] size: {trade.get('size')}, price: {trade.get('price')}")
        print(f"[{wallet[:10]}...] title: {trade.get('title')}")
        print("-" * 40)
    
    def _process_follow_trades(self) -> None:
        """处理跟单交易的线程函数"""
        print("[跟单线程] 启动成功")
        
        while self._running:
            try:
                trade, wallet = self._trade_queue.get(timeout=1)
                
                
                price = trade.get("price", 0)
                
                # 价格区间过滤
                price_filter = config.price_filter
                if price_filter and price_filter.get("enabled", False):
                    min_price = price_filter.get("min_price", 0)
                    max_price = price_filter.get("max_price", 1)
                    if not (min_price <= price <= max_price):
                        print(f"[跟单线程] 价格不在区间内 ({min_price}-{max_price}), 跳过: {price}")
                        continue
                print(f"\n[跟单线程] 收到新交易: {trade.get('transactionHash', '')[:20]}...")
                # 不重复跟单过滤
                no_duplicate = config.no_duplicate
                if no_duplicate and no_duplicate.get("enabled", False):
                    token_id = trade.get("asset")
                    expire_seconds = no_duplicate.get("expire_seconds", 3600)
                    current_time = time.time()
                    
                    if token_id in self._followed_markets:
                        last_time = self._followed_markets[token_id]
                        if current_time - last_time < expire_seconds:
                            print(f"[跟单线程] 市场 {token_id} 已在 {expire_seconds} 秒内跟单过, 跳过")
                            continue
                    
                    self._followed_markets[token_id] = current_time
                
                # 执行跟单逻辑(在新线程中执行)
                follow_thread = threading.Thread(
                    target=self._execute_follow_trade,
                    args=(trade, wallet),
                    daemon=True
                )
                follow_thread.start()
                
                # 发送通知
                self._notification.send_trade_notification(trade, wallet)
                
            except Empty:
                continue
            except Exception as e:
                print(f"[跟单线程] 处理异常: {e}")
                traceback.print_exc()
                continue
            
            time.sleep(2)
        
        print("[跟单线程] 已停止")
    
    def _execute_follow_trade(self, trade: Dict[str, Any], wallet: str) -> None:
        """
        执行跟单交易
        
        Args:
            trade: 交易信息
            wallet: 钱包地址
        """
        token_id = trade.get("asset")
        
        if not token_id:
            print(f"[跟单线程] 跳过: 缺少 token_id")
            return

        if not self._trading:
            print(f"[跟单线程] 跳过: 交易客户端未初始化")
            return

        # 跟单数量，可配置
        follow_amount = 1
        
        result,response,order_id = self._trading.place_market_order(token_id, follow_amount)
        self._notification.send_order_result(
            original_trade=trade,
            wallet=wallet,
            order_id=order_id,
            order_result=result,
            token_id=token_id,
            amount=follow_amount,
            response=response
        )
        
        # 只有下单成功才查询订单状态
        if not result or not order_id:
            print(f"[跟单线程] 下单失败，跳过订单状态查询")
            return
        
        order = self._trading.wait_for_order_matched(order_id)
        print(order)
        if result:
            size_matched = float(order.get("size_matched", 0))
            size = size_matched
            entry_price = trade.get("price", 0)
            tp_config = config.tp
            sl_config = config.sl
            if tp_config.get("enabled", False):
                tp_price = tp_config.get("value", 0.99)
                tp_result, tp_msg,order_id = self._trading.place_limit_order(
                    token_id=token_id,
                    price=tp_price,
                    size=size,
                    side="SELL"
                )
                if tp_result:
                    print(f"[跟单线程] 止盈单设置成功! 订单ID: {order_id},入场价: {entry_price}, 止盈价: {tp_price},数量:{size}")
                else:
                    print(f"[跟单线程] 止盈单设置失败: {tp_msg}")
            if sl_config.get("enabled", False):
                sl_price = sl_config.get("value", 0.5)
                entry_price = float(entry_price)
                sl_price = entry_price * (1 - sl_price)
                sl_result, sl_msg,order_id = self._trading.place_limit_order(
                    token_id=token_id,
                    price=sl_price,
                    size=size,
                    side="SELL"
                )
                if sl_result:
                    print(f"[跟单线程] 止损单设置成功! 订单ID: {order_id},入场价: {entry_price}, 止损价: {sl_price},数量:{size}")
                else:
                    print(f"[跟单线程] 止损单设置失败: {sl_msg}")

        else:
            print(f"[跟单线程] 下单失败! token_id: {token_id},{response}")


# 创建全局监控器实例
monitor = WalletMonitor(
    wallets=WALLETS,
    poll_interval=POLL_INTERVAL
)
