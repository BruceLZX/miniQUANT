"""
测试用户账户管理功能
"""
import pytest
from datetime import datetime
from core.scheduler import TradingPlatformScheduler
from models.base_models import UserAccount


def test_create_paper_account():
    """测试创建模拟账户"""
    scheduler = TradingPlatformScheduler()
    
    # 创建模拟账户
    user_account = scheduler.create_user_account(
        user_id="test_user_001",
        account_type="paper"
    )
    
    # 验证账户创建成功
    assert user_account.user_id == "test_user_001"
    assert user_account.account_type == "paper"
    assert user_account.account_id is not None
    assert user_account.is_active is True
    assert user_account.brokerage is None
    
    # 验证交易引擎创建成功
    engine = scheduler.get_user_trading_engine("test_user_001")
    assert engine is not None
    assert engine.account.account_id == user_account.account_id
    
    print("✓ Paper account creation test passed")


def test_create_real_account():
    """测试创建真实账户"""
    scheduler = TradingPlatformScheduler()
    
    # 创建真实账户
    user_account = scheduler.create_user_account(
        user_id="test_user_002",
        account_type="real",
        brokerage="ibkr",
        api_key="test_api_key",
        api_secret="test_api_secret"
    )
    
    # 验证账户创建成功
    assert user_account.user_id == "test_user_002"
    assert user_account.account_type == "real"
    assert user_account.brokerage == "ibkr"
    assert user_account.account_id is not None
    assert user_account.is_active is True
    
    # 注意：api_key 和 api_secret 不应该出现在 to_dict() 中
    account_dict = user_account.to_dict()
    assert "api_key" not in account_dict
    assert "api_secret" not in account_dict
    
    # 验证交易引擎创建成功（目前是占位符实现）
    engine = scheduler.get_user_trading_engine("test_user_002")
    assert engine is not None
    
    print("✓ Real account creation test passed")


def test_real_account_validation():
    """测试真实账户创建时的验证"""
    scheduler = TradingPlatformScheduler()
    
    # 缺少必要信息应该抛出异常
    with pytest.raises(ValueError, match="Real account requires brokerage, api_key, and api_secret"):
        scheduler.create_user_account(
            user_id="test_user_003",
            account_type="real",
            brokerage="ibkr"
            # 缺少 api_key 和 api_secret
        )
    
    print("✓ Real account validation test passed")


def test_get_user_account():
    """测试获取用户账户"""
    scheduler = TradingPlatformScheduler()
    
    # 创建账户
    scheduler.create_user_account(
        user_id="test_user_004",
        account_type="paper"
    )
    
    # 获取账户
    account = scheduler.get_user_account("test_user_004")
    assert account is not None
    assert account.user_id == "test_user_004"
    
    # 获取不存在的账户
    account_not_found = scheduler.get_user_account("non_existent_user")
    assert account_not_found is None
    
    print("✓ Get user account test passed")


def test_get_user_account_status():
    """测试获取用户账户状态"""
    scheduler = TradingPlatformScheduler()
    
    # 创建账户
    scheduler.create_user_account(
        user_id="test_user_005",
        account_type="paper"
    )
    
    # 获取账户状态
    status = scheduler.get_user_account_status("test_user_005")
    assert status is not None
    assert "account_id" in status
    assert "total_value" in status
    assert "cash" in status
    assert status["total_value"] == 100000.0  # 初始资金
    
    # 获取不存在的账户状态
    status_not_found = scheduler.get_user_account_status("non_existent_user")
    assert status_not_found is None
    
    print("✓ Get user account status test passed")


def test_multiple_users():
    """测试多用户场景"""
    scheduler = TradingPlatformScheduler()
    
    # 创建多个用户
    user_ids = ["user_001", "user_002", "user_003"]
    for user_id in user_ids:
        scheduler.create_user_account(
            user_id=user_id,
            account_type="paper"
        )
    
    # 验证每个用户都有独立的账户和交易引擎
    for user_id in user_ids:
        account = scheduler.get_user_account(user_id)
        engine = scheduler.get_user_trading_engine(user_id)
        
        assert account is not None
        assert engine is not None
        assert account.user_id == user_id
        assert engine.account.account_id == account.account_id
    
    # 验证账户ID都是唯一的
    account_ids = [
        scheduler.get_user_account(user_id).account_id 
        for user_id in user_ids
    ]
    assert len(account_ids) == len(set(account_ids))  # 所有ID都唯一
    
    print("✓ Multiple users test passed")


def test_user_account_to_dict():
    """测试 UserAccount.to_dict() 方法"""
    account = UserAccount(
        user_id="test_user",
        account_type="paper",
        account_id="paper_test_user_123"
    )
    
    account_dict = account.to_dict()
    
    # 验证返回的字段
    assert account_dict["user_id"] == "test_user"
    assert account_dict["account_type"] == "paper"
    assert account_dict["account_id"] == "paper_test_user_123"
    assert account_dict["is_active"] is True
    assert "created_at" in account_dict
    
    # 验证敏感信息不包含在返回中
    account_with_secrets = UserAccount(
        user_id="test_user",
        account_type="real",
        api_key="secret_key",
        api_secret="secret_secret",
        account_id="real_test_user_123"
    )
    
    account_dict_safe = account_with_secrets.to_dict()
    assert "api_key" not in account_dict_safe
    assert "api_secret" not in account_dict_safe
    
    print("✓ UserAccount.to_dict() test passed")


if __name__ == "__main__":
    # 运行所有测试
    print("\n" + "="*60)
    print("Running User Account Management Tests")
    print("="*60 + "\n")
    
    test_create_paper_account()
    test_create_real_account()
    test_real_account_validation()
    test_get_user_account()
    test_get_user_account_status()
    test_multiple_users()
    test_user_account_to_dict()
    
    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60 + "\n")
