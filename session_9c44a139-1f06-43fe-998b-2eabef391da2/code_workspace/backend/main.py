"""
主入口文件 - 用于启动交易平台
"""
import asyncio
import logging
from core.scheduler import TradingPlatformScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("Starting AI Agent Stock Trading Platform...")
    
    # 创建调度器
    scheduler = TradingPlatformScheduler()
    
    try:
        # 手动添加一些股票进行测试
        logger.info("Adding initial stocks...")
        scheduler.add_stock("AAPL")
        scheduler.add_stock("NVDA")
        scheduler.add_stock("MSFT")
        
        # 启动调度器
        await scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
        await scheduler.stop()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
