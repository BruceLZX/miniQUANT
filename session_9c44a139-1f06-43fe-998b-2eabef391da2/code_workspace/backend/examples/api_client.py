"""
API客户端示例 - 用于前端调用
"""
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional


class TradingPlatformClient:
    """交易平台API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def add_stock(self, symbol: str) -> Dict[str, Any]:
        """添加股票"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/stocks/add",
                json={"symbol": symbol}
            ) as response:
                return await response.json()
    
    async def remove_stock(self, symbol: str) -> Dict[str, Any]:
        """移除股票"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/stocks/remove",
                json={"symbol": symbol}
            ) as response:
                return await response.json()
    
    async def list_stocks(self) -> Dict[str, Any]:
        """获取股票列表"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/stocks/list") as response:
                return await response.json()
    
    async def get_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取股票分析"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/analysis/{symbol}") as response:
                return await response.json()
    
    async def get_all_analysis(self) -> Dict[str, Any]:
        """获取所有分析"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/analysis/all") as response:
                return await response.json()
    
    async def get_account_status(self) -> Dict[str, Any]:
        """获取账户状态"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/trading/account") as response:
                return await response.json()
    
    async def get_positions(self) -> Dict[str, Any]:
        """获取持仓"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/trading/positions") as response:
                return await response.json()
    
    async def get_trade_history(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取交易历史"""
        url = f"{self.base_url}/api/trading/history"
        if symbol:
            url += f"?symbol={symbol}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    
    async def upload_material(self, 
                             stock_symbol: str,
                             content: str,
                             summary: str,
                             reliability_score: float = 0.8) -> Dict[str, Any]:
        """上传专家材料"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/materials/upload",
                json={
                    "stock_symbol": stock_symbol,
                    "content": content,
                    "summary": summary,
                    "reliability_score": reliability_score
                }
            ) as response:
                return await response.json()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/system/status") as response:
                return await response.json()


async def demo_client():
    """演示客户端使用"""
    client = TradingPlatformClient()
    
    print("\n=== Trading Platform Client Demo ===\n")
    
    # 1. 添加股票
    print("1. Adding stocks...")
    for symbol in ["AAPL", "NVDA", "MSFT"]:
        result = await client.add_stock(symbol)
        print(f"   {symbol}: {result.get('message', 'OK')}")
    
    # 2. 查看股票列表
    print("\n2. Listing stocks...")
    stocks = await client.list_stocks()
    print(f"   Active stocks: {stocks.get('stocks', [])}")
    
    # 3. 查看系统状态
    print("\n3. System status...")
    status = await client.get_system_status()
    print(f"   Running: {status.get('is_running')}")
    print(f"   Active stocks: {status.get('active_stocks')}")
    print(f"   Account value: ${status.get('account_value', 0):,.2f}")
    
    # 4. 查看账户状态
    print("\n4. Account status...")
    account = await client.get_account_status()
    print(f"   Total value: ${account.get('total_value', 0):,.2f}")
    print(f"   Cash: ${account.get('cash', 0):,.2f}")
    print(f"   Total PnL: ${account.get('total_pnl', 0):,.2f}")
    
    # 5. 上传材料
    print("\n5. Uploading expert material...")
    result = await client.upload_material(
        stock_symbol="AAPL",
        content="Apple's new product launch expected to drive 15% revenue growth",
        summary="Expert bullish on Apple",
        reliability_score=0.85
    )
    print(f"   Result: {result.get('message', 'OK')}")
    
    print("\n=== Demo Complete ===\n")


if __name__ == "__main__":
    asyncio.run(demo_client())
