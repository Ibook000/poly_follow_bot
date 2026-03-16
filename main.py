"""
程序主入口 - 启动多钱包监控和跟单系统
"""
import signal
import sys
import time

from config import config, POLL_INTERVAL, WALLETS
from trading import trading_client
from monitor import WalletMonitor, monitor


# 全局运行标志
running = True


def signal_handler(signum, frame):
    """处理退出信号"""
    global running
    print("\n收到退出信号，正在停止所有线程...")
    running = False 


def main(poll_interval: int = None):
    """
    主函数：启动多个监控线程
    
    Args:
        poll_interval: 轮询间隔（秒），默认为配置值
    """
    global running
    
    if poll_interval is None:
        poll_interval = POLL_INTERVAL
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 打印启动信息
    print(" Polymarket 多钱包监控启动")
    print(f"监控钱包数量: {len(WALLETS)}")
    print(f"轮询间隔: {poll_interval}秒")
    # 检查余额
    balance = trading_client.get_balance()
    print(f"当前可用余额: {balance:.6f} USDC")
    
    # 创建并启动监控器
    wallet_monitor = WalletMonitor(
        wallets=WALLETS,
        poll_interval=poll_interval,
        trading_client=trading_client
    )
    
    threads = wallet_monitor.start()
    
    try:
        while running:
            time.sleep(1)
            if not running:
                break
    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")
        running = False
    
    # 停止监控器
    wallet_monitor.stop()
    
    # 等待所有线程结束
    for t in threads:
        t.join(timeout=3)
    
    print("所有线程已停止，程序退出")


if __name__ == "__main__":
    main()
