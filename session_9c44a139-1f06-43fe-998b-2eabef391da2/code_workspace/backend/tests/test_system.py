"""
测试文件 - 测试核心功能
"""
import pytest
import asyncio
from datetime import datetime

from models.base_models import Evidence, AnalystOutput, CriticOutput, DeciderOutput
from memory.memory_store import InMemoryStore, MemoryManager, MemoryType, MemoryScope
from agents.base_agent import MockAgent, AgentConfig
from agents.analyst import AnalystAgent
from agents.critic import CriticAgent
from agents.decider import DeciderAgent
from departments.d1_macro import D1MacroDepartment
from quantitative.d5_quant import D5QuantDepartment
from trading.paper_trading import PaperTradingEngine
from utils.evaluation import EvaluationEngine


def test_evidence_creation():
    """测试证据创建"""
    evidence = Evidence(
        content="Test content",
        timestamp=datetime.now(),
        source_id="test_source",
        reliability_score=0.9,
        summary="Test summary"
    )
    
    assert evidence.content == "Test content"
    assert evidence.reliability_score == 0.9
    assert evidence.to_dict() is not None
    print("✓ Evidence creation test passed")


def test_memory_store():
    """测试记忆存储"""
    store = InMemoryStore()
    manager = MemoryManager(store)
    
    # 添加记忆
    entry = manager.add_memory(
        memory_type=MemoryType.STM,
        scope=MemoryScope.GLOBAL,
        content="Test memory",
        department="D1",
        importance=0.8
    )
    
    assert entry.entry_id is not None
    
    # 查询记忆
    memories = manager.get_department_memory(department="D1")
    assert len(memories) == 1
    assert memories[0].content == "Test memory"
    
    # 获取摘要
    summary = manager.get_summary(department="D1")
    assert "Test memory" in summary
    
    print("✓ Memory store test passed")


@pytest.mark.asyncio
async def test_mock_agent():
    """测试Mock Agent"""
    config = AgentConfig(
        agent_id="test_agent",
        model_provider="mock"
    )
    
    agent = MockAgent(config)
    result = await agent.execute({"test": "context"})
    
    assert "stance" in result
    assert "score" in result
    assert "confidence" in result
    print("✓ Mock agent test passed")


@pytest.mark.asyncio
async def test_analyst_agent():
    """测试分析者Agent"""
    config = AgentConfig(
        agent_id="test_analyst",
        model_provider="mock"
    )
    
    agent = AnalystAgent(config, "analyst_001")
    
    evidence = Evidence(
        content="Test evidence",
        timestamp=datetime.now(),
        source_id="test",
        reliability_score=0.9,
        summary="Test"
    )
    
    context = {
        "department": "Test",
        "stock_symbol": "AAPL",
        "evidence_pack": [evidence],
        "memory_summary": "No relevant memory"
    }
    
    result = await agent.execute(context)
    
    assert result.analyst_id == "analyst_001"
    assert result.stance in ["bull", "bear", "neutral"]
    assert -1 <= result.score <= 1
    assert 0 <= result.confidence <= 1
    print("✓ Analyst agent test passed")


@pytest.mark.asyncio
async def test_department_workflow():
    """测试部门工作流"""
    store = InMemoryStore()
    manager = MemoryManager(store)
    
    dept = D1MacroDepartment(manager)
    
    # 运行三轮讨论
    result = await dept.run_three_round_discussion()
    
    assert result.department_type == "D1"
    assert len(result.round1_outputs) == 3  # 3个分析者
    assert result.round2_output is not None  # 批评者
    assert result.round3_output is not None  # 拍板者
    assert -1 <= result.score <= 1
    
    print("✓ Department workflow test passed")


def test_quant_department():
    """测试量化部门"""
    store = InMemoryStore()
    manager = MemoryManager(store)
    
    quant = D5QuantDepartment(manager)
    
    # 测试参数
    params = quant.get_params()
    assert 'beta_1' in params
    assert 'alpha_M' in params
    
    # 更新参数
    quant.update_params({'beta_1': 0.5})
    assert quant.get_params()['beta_1'] == 0.5
    
    print("✓ Quant department test passed")


def test_paper_trading():
    """测试Paper Trading"""
    engine = PaperTradingEngine(initial_capital=100000)
    
    # 检查初始状态
    account = engine.get_account_summary()
    assert account['initial_capital'] == 100000
    assert account['cash'] == 100000
    
    print("✓ Paper trading test passed")


def test_evaluation_engine():
    """测试评估引擎"""
    eval_engine = EvaluationEngine()
    
    # 模拟一个案例
    case = {
        'case_id': 'test_case',
        'symbol': 'AAPL',
        'created_at': datetime.now().isoformat(),
        'trading_decision': {'direction': 'LONG'},
        'quant_output': {'divergence': 0.2},
        'department_finals': {
            'D6': {'confidence': 0.7, 'score': 0.5}
        }
    }
    
    # 评估案例
    evaluation = eval_engine.evaluate_case(case, actual_return=0.05)
    
    assert evaluation.hit == True
    assert evaluation.confidence_at_decision == 0.7
    
    # 获取指标
    metrics = eval_engine.get_metrics()
    assert metrics.total_trades == 1
    assert metrics.winning_trades == 1
    
    print("✓ Evaluation engine test passed")


def run_all_tests():
    """运行所有测试"""
    print("\n=== Running All Tests ===\n")
    
    # 同步测试
    test_evidence_creation()
    test_memory_store()
    test_quant_department()
    test_paper_trading()
    test_evaluation_engine()
    
    # 异步测试
    asyncio.run(test_mock_agent())
    asyncio.run(test_analyst_agent())
    asyncio.run(test_department_workflow())
    
    print("\n=== All Tests Passed ✓ ===\n")


if __name__ == "__main__":
    run_all_tests()
