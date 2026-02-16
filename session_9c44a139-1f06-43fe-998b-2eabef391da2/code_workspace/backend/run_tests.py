"""
简单测试运行器 - 验证系统基本功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from models.base_models import Evidence
from memory.memory_store import InMemoryStore, MemoryManager, MemoryType, MemoryScope
from agents.base_agent import MockAgent, AgentConfig
from config.settings import config


def test_models():
    """测试数据模型"""
    print("\n[1/6] 测试数据模型...")
    
    # 测试Evidence
    evidence = Evidence(
        content="Test content",
        timestamp=datetime.now(),
        source_id="test_001",
        reliability_score=0.9,
        summary="Test summary"
    )
    assert evidence.content == "Test content"
    assert evidence.reliability_score == 0.9
    print("  ✓ Evidence模型正常")
    
    # 测试to_dict
    evidence_dict = evidence.to_dict()
    assert isinstance(evidence_dict, dict)
    print("  ✓ Evidence序列化正常")


def test_memory():
    """测试记忆系统"""
    print("\n[2/6] 测试记忆系统...")
    
    store = InMemoryStore()
    manager = MemoryManager(store)
    
    # 添加记忆
    entry = manager.add_memory(
        memory_type=MemoryType.STM,
        scope=MemoryScope.GLOBAL,
        content="Test memory content",
        department="D1",
        importance=0.8
    )
    assert entry.entry_id is not None
    print("  ✓ 记忆添加正常")
    
    # 查询记忆
    memories = manager.get_department_memory(department="D1")
    assert len(memories) == 1
    assert memories[0].content == "Test memory content"
    print("  ✓ 记忆查询正常")
    
    # 获取摘要
    summary = manager.get_summary(department="D1")
    assert "Test memory content" in summary
    print("  ✓ 记忆摘要正常")


def test_agents():
    """测试Agent系统"""
    print("\n[3/6] 测试Agent系统...")
    
    # 测试MockAgent
    config = AgentConfig(
        agent_id="test_agent",
        model_provider="mock"
    )
    agent = MockAgent(config)
    print("  ✓ Agent创建正常")
    
    # 测试执行（同步方式）
    import asyncio
    result = asyncio.run(agent.execute({"test": "context"}))
    assert "stance" in result
    assert "score" in result
    assert "confidence" in result
    print("  ✓ Agent执行正常")


def test_config():
    """测试配置系统"""
    print("\n[4/6] 测试配置系统...")
    
    assert config.d5_interval == 5
    assert config.d1_interval == 60
    assert config.max_daily_trades_per_stock == 2
    print("  ✓ 配置加载正常")
    
    # 测试枚举
    from config.settings import DepartmentType, Stance, TradeAction
    assert DepartmentType.D1_MACRO.value == "D1"
    assert Stance.BULL.value == "bull"
    assert TradeAction.LONG.value == "LONG"
    print("  ✓ 枚举定义正常")


def test_quant_params():
    """测试量化参数"""
    print("\n[5/6] 测试量化参数...")
    
    from quantitative.d5_quant import D5QuantDepartment
    from memory.memory_store import InMemoryStore, MemoryManager
    
    store = InMemoryStore()
    manager = MemoryManager(store)
    quant = D5QuantDepartment(manager)
    
    # 检查参数
    params = quant.get_params()
    assert 'beta_1' in params
    assert 'alpha_M' in params
    assert 'gamma_1' in params
    print("  ✓ 量化参数初始化正常")
    
    # 测试参数更新
    quant.update_params({'beta_1': 0.5})
    assert quant.get_params()['beta_1'] == 0.5
    print("  ✓ 参数更新正常")


def test_trading_engine():
    """测试交易引擎"""
    print("\n[6/6] 测试交易引擎...")
    
    from trading.paper_trading import PaperTradingEngine
    
    engine = PaperTradingEngine(initial_capital=100000)
    
    # 检查初始状态
    account = engine.get_account_summary()
    assert account['initial_capital'] == 100000
    assert account['cash'] == 100000
    assert account['total_value'] == 100000
    print("  ✓ 交易引擎初始化正常")
    
    # 检查持仓
    positions = engine.get_positions()
    assert len(positions) == 0
    print("  ✓ 持仓查询正常")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("AI Agent Stock Trading Platform - 系统测试")
    print("="*60)
    
    try:
        test_models()
        test_memory()
        test_agents()
        test_config()
        test_quant_params()
        test_trading_engine()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！系统运行正常。")
        print("="*60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
