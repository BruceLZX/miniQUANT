"""
系统验证脚本 - 快速验证所有模块是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_imports():
    """验证所有模块导入"""
    print("\n" + "="*60)
    print("验证模块导入...")
    print("="*60)
    
    try:
        # 配置
        from config.settings import config, DepartmentType, Stance
        print("✓ config.settings")
        
        # 模型
        from models.base_models import (
            Evidence, AnalystOutput, CriticOutput, DeciderOutput,
            DepartmentFinal, MarketData, WhaleFlow, QuantOutput,
            TradingDecision, StockCase
        )
        print("✓ models.base_models")
        
        # Agent
        from agents.base_agent import BaseAgent, AgentConfig, MockAgent
        from agents.analyst import AnalystAgent
        from agents.critic import CriticAgent
        from agents.decider import DeciderAgent
        print("✓ agents.*")
        
        # 记忆
        from memory.memory_store import (
            MemoryStore, InMemoryStore, MemoryManager,
            MemoryEntry, MemoryScope, MemoryType
        )
        print("✓ memory.memory_store")
        
        # 部门
        from departments.base_department import BaseDepartment
        from departments.d1_macro import D1MacroDepartment
        from departments.d2_industry import D2IndustryDepartment
        from departments.d3_stock import D3StockDepartment
        from departments.d4_expert import D4ExpertDepartment
        from departments.d6_ic import D6ICDepartment
        from departments.d7_stock_selection import D7StockSelectionDepartment
        print("✓ departments.*")
        
        # 量化
        from quantitative.d5_quant import D5QuantDepartment
        print("✓ quantitative.d5_quant")
        
        # 交易
        from trading.paper_trading import PaperTradingEngine, Order, Position, TradingAccount
        print("✓ trading.paper_trading")
        
        # 数据
        from data.data_collector import DataCollector
        print("✓ data.data_collector")
        
        # 工具
        from utils.evaluation import EvaluationEngine, EvaluationMetrics, CaseEvaluation
        print("✓ utils.evaluation")
        
        # 核心
        from core.scheduler import TradingPlatformScheduler, SchedulerState
        print("✓ core.scheduler")
        
        print("\n" + "="*60)
        print("✓ 所有模块导入成功！")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_basic_functionality():
    """验证基本功能"""
    print("\n" + "="*60)
    print("验证基本功能...")
    print("="*60 + "\n")
    
    try:
        from datetime import datetime
        from models.base_models import Evidence
        from memory.memory_store import InMemoryStore, MemoryManager, MemoryType, MemoryScope
        from trading.paper_trading import PaperTradingEngine
        
        # 1. 测试证据创建
        evidence = Evidence(
            content="Test evidence",
            timestamp=datetime.now(),
            source_id="test_001",
            reliability_score=0.9,
            summary="Test"
        )
        assert evidence.content == "Test evidence"
        print("✓ Evidence创建正常")
        
        # 2. 测试记忆系统
        store = InMemoryStore()
        manager = MemoryManager(store)
        entry = manager.add_memory(
            memory_type=MemoryType.STM,
            scope=MemoryScope.GLOBAL,
            content="Test memory",
            department="D1"
        )
        assert entry.entry_id is not None
        print("✓ 记忆系统正常")
        
        # 3. 测试交易引擎
        engine = PaperTradingEngine(initial_capital=100000)
        account = engine.get_account_summary()
        assert account['total_value'] == 100000
        print("✓ 交易引擎正常")
        
        print("\n" + "="*60)
        print("✓ 基本功能验证通过！")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 功能验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主验证流程"""
    print("\n" + "="*60)
    print("AI Agent Stock Trading Platform - 系统验证")
    print("="*60)
    
    # 验证导入
    if not validate_imports():
        return 1
    
    # 验证基本功能
    if not validate_basic_functionality():
        return 1
    
    print("\n" + "="*60)
    print("✓✓✓ 系统验证完成！所有模块正常工作。✓✓✓")
    print("="*60 + "\n")
    
    print("下一步:")
    print("  1. 运行测试: python tests/test_system.py")
    print("  2. 查看示例: python examples/basic_usage.py")
    print("  3. 启动API: python -m uvicorn api.main:app --reload")
    print("  4. 查看文档: http://localhost:8000/docs")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
