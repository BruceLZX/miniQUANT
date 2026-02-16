"""
Test script to verify paper trading fixes
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime
from trading.paper_trading import PaperTradingEngine, Order
from models.base_models import TradingDecision


async def test_paper_trading():
    """Test the paper trading engine with fixes"""
    print("Testing Paper Trading Engine...")
    
    # Create engine
    engine = PaperTradingEngine(account_id="test_account", initial_capital=100000.0)
    
    # Create a test decision
    decision = TradingDecision(
        decision_id="test_decision_001",
        symbol="AAPL",
        direction="LONG",
        target_position=100,
        confidence=0.8,
        rationale="Test trade",
        risk_controls={},
        execution_plan={},
        timestamp=datetime.now()
    )
    
    # Execute decision
    current_price = 150.0
    order = await engine.execute_decision(decision, current_price)
    
    # Verify results
    print(f"\nOrder Status: {order.status}")
    print(f"Order ID: {order.order_id}")
    print(f"Symbol: {order.symbol}")
    print(f"Side: {order.side}")
    print(f"Quantity: {order.quantity}")
    print(f"Filled Quantity: {order.filled_quantity}")
    print(f"Filled Price: {order.filled_price}")
    
    # Check account
    account = engine.get_account_summary()
    print(f"\nAccount Cash: {account['cash']}")
    print(f"Account Total Value: {account['total_value']}")
    print(f"Positions: {account['positions']}")
    
    # Verify the order was filled
    assert order.status == "FILLED", "Order should be FILLED"
    assert order.filled_quantity > 0, "Filled quantity should be > 0"
    assert order.filled_price > 0, "Filled price should be > 0"
    
    # Verify account was updated
    assert account['cash'] < 100000.0, "Cash should be reduced after BUY"
    assert 'AAPL' in account['positions'], "AAPL should be in positions"
    
    print("\n✅ All tests passed! Paper trading engine is working correctly.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_paper_trading())
