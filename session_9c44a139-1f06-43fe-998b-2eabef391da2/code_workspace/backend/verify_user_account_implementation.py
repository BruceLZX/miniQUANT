"""
简单的验证脚本 - 验证用户账户管理核心功能

运行方法：
cd backend
python verify_user_account_implementation.py
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from core.scheduler import TradingPlatformScheduler
from models.base_models import UserAccount


def test_user_account_model():
    """测试 UserAccount 模型"""
    print("\n" + "="*60)
    print("测试 1: UserAccount 模型")
    print("="*60)
    
    # 创建模拟账户
    paper_account = UserAccount(
        user_id="test_user_001",
        account_type="paper",
        account_id="paper_test_user_001"
    )
    
    print(f"✓ 创建模拟账户成功")
    print(f"  - user_id: {paper_account.user_id}")
    print(f"  - account_type: {paper_account.account_type}")
    print(f"  - account_id: {paper_account.account_id}")
    print(f"  - is_active: {paper_account.is_active}")
    
    # 创建真实账户
    real_account = UserAccount(
        user_id="test_user_002",
        account_type="real",
        brokerage="ibkr",
        api_key="test_key",
        api_secret="test_secret",
        account_id="real_test_user_002"
    )
    
    print(f"\n✓ 创建真实账户成功")
    print(f"  - user_id: {real_account.user_id}")
    print(f"  - account_type: {real_account.account_type}")
    print(f"  - brokerage: {real_account.brokerage}")
    
    # 测试 to_dict() 方法
    paper_dict = paper_account.to_dict()
    print(f"\n✓ 测试 to_dict() 方法")
    print(f"  - 返回字段: {list(paper_dict.keys())}")
    
    # 验证敏感信息不返回
    real_dict = real_account.to_dict()
    assert "api_key" not in real_dict, "api_key 不应该出现在 to_dict() 中"
    assert "api_secret" not in real_dict, "api_secret 不应该出现在 to_dict() 中"
    print(f"  - 敏感信息已过滤 ✓")


def test_scheduler_create_paper_account():
    """测试调度器创建模拟账户"""
    print("\n" + "="*60)
    print("测试 2: 调度器创建模拟账户")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 创建模拟账户
    user_account = scheduler.create_user_account(
        user_id="test_user_paper",
        account_type="paper"
    )
    
    print(f"✓ 创建模拟账户成功")
    print(f"  - user_id: {user_account.user_id}")
    print(f"  - account_id: {user_account.account_id}")
    
    # 验证交易引擎创建
    engine = scheduler.get_user_trading_engine("test_user_paper")
    assert engine is not None, "交易引擎应该被创建"
    print(f"✓ 交易引擎创建成功")
    print(f"  - engine.account_id: {engine.account.account_id}")
    
    # 验证账户状态
    status = scheduler.get_user_account_status("test_user_paper")
    assert status is not None, "账户状态应该存在"
    assert status["total_value"] == 100000.0, "初始资金应该是 100000"
    print(f"✓ 账户状态正确")
    print(f"  - total_value: ${status['total_value']:,.2f}")
    print(f"  - cash: ${status['cash']:,.2f}")


def test_scheduler_create_real_account():
    """测试调度器创建真实账户"""
    print("\n" + "="*60)
    print("测试 3: 调度器创建真实账户")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 创建真实账户
    user_account = scheduler.create_user_account(
        user_id="test_user_real",
        account_type="real",
        brokerage="ibkr",
        api_key="test_api_key",
        api_secret="test_api_secret"
    )
    
    print(f"✓ 创建真实账户成功")
    print(f"  - user_id: {user_account.user_id}")
    print(f"  - account_type: {user_account.account_type}")
    print(f"  - brokerage: {user_account.brokerage}")
    
    # 验证交易引擎创建（目前是占位符实现）
    engine = scheduler.get_user_trading_engine("test_user_real")
    assert engine is not None, "交易引擎应该被创建"
    print(f"✓ 交易引擎创建成功（占位符实现）")


def test_real_account_validation():
    """测试真实账户验证"""
    print("\n" + "="*60)
    print("测试 4: 真实账户验证")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 测试缺少必要信息
    try:
        scheduler.create_user_account(
            user_id="test_user_invalid",
            account_type="real",
            brokerage="ibkr"
            # 缺少 api_key 和 api_secret
        )
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        print(f"✓ 验证成功：缺少必要信息时抛出异常")
        print(f"  - 错误信息: {str(e)}")


def test_multiple_users():
    """测试多用户场景"""
    print("\n" + "="*60)
    print("测试 5: 多用户场景")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 创建多个用户
    user_ids = ["user_001", "user_002", "user_003"]
    account_ids = []
    
    for user_id in user_ids:
        account = scheduler.create_user_account(
            user_id=user_id,
            account_type="paper"
        )
        account_ids.append(account.account_id)
        print(f"✓ 创建用户: {user_id} -> {account.account_id}")
    
    # 验证账户ID唯一
    assert len(account_ids) == len(set(account_ids)), "所有账户ID应该唯一"
    print(f"✓ 所有账户ID唯一")
    
    # 验证每个用户都可以获取
    for user_id in user_ids:
        account = scheduler.get_user_account(user_id)
        engine = scheduler.get_user_trading_engine(user_id)
        assert account is not None, f"用户 {user_id} 的账户应该存在"
        assert engine is not None, f"用户 {user_id} 的交易引擎应该存在"
    
    print(f"✓ 所有用户账户和交易引擎都可以正确获取")


def test_get_nonexistent_user():
    """测试获取不存在的用户"""
    print("\n" + "="*60)
    print("测试 6: 获取不存在的用户")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 测试获取不存在的用户
    account = scheduler.get_user_account("nonexistent_user")
    assert account is None, "不存在的用户应该返回 None"
    print(f"✓ 不存在的用户返回 None")
    
    # 测试获取不存在的用户状态
    status = scheduler.get_user_account_status("nonexistent_user")
    assert status is None, "不存在的用户状态应该返回 None"
    print(f"✓ 不存在的用户状态返回 None")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("测试 7: 向后兼容性")
    print("="*60)
    
    scheduler = TradingPlatformScheduler()
    
    # 测试原有的方法仍然可用
    status = scheduler.get_account_status()
    assert status is not None, "原有的 get_account_status() 应该可用"
    print(f"✓ 原有的 get_account_status() 方法仍然可用")
    print(f"  - total_value: ${status['total_value']:,.2f}")
    
    # 测试原有的交易引擎
    assert scheduler.trading_engine is not None, "原有的交易引擎应该存在"
    print(f"✓ 原有的交易引擎仍然存在")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print(" " * 20 + "🚀 用户账户管理功能验证")
    print("="*80)
    
    try:
        test_user_account_model()
        test_scheduler_create_paper_account()
        test_scheduler_create_real_account()
        test_real_account_validation()
        test_multiple_users()
        test_get_nonexistent_user()
        test_backward_compatibility()
        
        print("\n" + "="*80)
        print(" " * 25 + "✅ 所有测试通过！")
        print("="*80)
        
        print("\n" + "="*80)
        print(" " * 20 + "📋 实现总结")
        print("="*80)
        print("\n✅ 已实现的功能：")
        print("  1. UserAccount 数据模型")
        print("  2. 创建模拟账户")
        print("  3. 创建真实账户")
        print("  4. 真实账户验证")
        print("  5. 多用户支持")
        print("  6. 用户账户管理API")
        print("  7. 交易引擎隔离")
        print("  8. 敏感信息保护")
        print("  9. 向后兼容性")
        
        print("\n📝 符合需求文档（agent.md 0.2节）要求：")
        print("  ✓ 允许用户输入自己的股票账号")
        print("  ✓ 在没有用户提供股票账号的情况下，提供模拟账号")
        print("  ✓ 支持多用户独立账户管理")
        print("  ✓ 提供完整的账户管理API")
        
        print("\n" + "="*80 + "\n")
        
        return True
        
    except AssertionError as e:
        print("\n" + "="*80)
        print(" " * 25 + "❌ 测试失败！")
        print("="*80)
        print(f"错误: {e}\n")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print("\n" + "="*80)
        print(" " * 25 + "❌ 发生异常！")
        print("="*80)
        print(f"错误: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
