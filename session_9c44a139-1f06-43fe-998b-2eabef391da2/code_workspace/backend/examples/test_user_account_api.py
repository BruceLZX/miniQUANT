"""
用户账户管理API测试脚本

使用方法：
1. 启动后端服务：python -m api.main
2. 运行此脚本：python examples/test_user_account_api.py
"""
import requests
import json
from datetime import datetime


# API基础URL
BASE_URL = "http://localhost:8000"


def print_response(response, title="Response"):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print('='*60)


def test_create_paper_account():
    """测试创建模拟账户"""
    print("\n\n🧪 Test 1: 创建模拟账户")
    
    url = f"{BASE_URL}/api/account/create"
    data = {
        "user_id": "test_user_paper_001",
        "account_type": "paper"
    }
    
    response = requests.post(url, json=data)
    print_response(response, "创建模拟账户响应")
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["account"]["account_type"] == "paper"
    
    return result["account"]["user_id"]


def test_create_real_account():
    """测试创建真实账户"""
    print("\n\n🧪 Test 2: 创建真实账户")
    
    url = f"{BASE_URL}/api/account/create"
    data = {
        "user_id": "test_user_real_001",
        "account_type": "real",
        "brokerage": "ibkr",
        "api_key": "test_api_key_123",
        "api_secret": "test_api_secret_456"
    }
    
    response = requests.post(url, json=data)
    print_response(response, "创建真实账户响应")
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["account"]["account_type"] == "real"
    assert result["account"]["brokerage"] == "ibkr"
    
    # 验证敏感信息不返回
    assert "api_key" not in result["account"]
    assert "api_secret" not in result["account"]
    
    return result["account"]["user_id"]


def test_create_real_account_missing_info():
    """测试创建真实账户时缺少必要信息"""
    print("\n\n🧪 Test 3: 创建真实账户时缺少必要信息（应该失败）")
    
    url = f"{BASE_URL}/api/account/create"
    data = {
        "user_id": "test_user_real_002",
        "account_type": "real",
        "brokerage": "ibkr"
        # 缺少 api_key 和 api_secret
    }
    
    response = requests.post(url, json=data)
    print_response(response, "创建真实账户响应（缺少信息）")
    
    # 应该返回400错误
    assert response.status_code == 400


def test_get_user_account(user_id):
    """测试获取用户账户信息"""
    print(f"\n\n🧪 Test 4: 获取用户账户信息 (user_id: {user_id})")
    
    url = f"{BASE_URL}/api/account/{user_id}"
    response = requests.get(url)
    print_response(response, "获取用户账户信息响应")
    
    assert response.status_code == 200
    result = response.json()
    assert result["account"]["user_id"] == user_id


def test_get_user_account_status(user_id):
    """测试获取用户账户状态"""
    print(f"\n\n🧪 Test 5: 获取用户账户状态 (user_id: {user_id})")
    
    url = f"{BASE_URL}/api/account/{user_id}/status"
    response = requests.get(url)
    print_response(response, "获取用户账户状态响应")
    
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert "total_value" in result["status"]
    assert "cash" in result["status"]


def test_get_user_trade_history(user_id):
    """测试获取用户交易历史"""
    print(f"\n\n🧪 Test 6: 获取用户交易历史 (user_id: {user_id})")
    
    url = f"{BASE_URL}/api/account/{user_id}/trades"
    response = requests.get(url)
    print_response(response, "获取用户交易历史响应")
    
    assert response.status_code == 200
    result = response.json()
    assert "trades" in result
    assert "count" in result["status"]


def test_get_nonexistent_user():
    """测试获取不存在的用户"""
    print("\n\n🧪 Test 7: 获取不存在的用户（应该返回404）")
    
    url = f"{BASE_URL}/api/account/nonexistent_user_12345"
    response = requests.get(url)
    print_response(response, "获取不存在的用户响应")
    
    assert response.status_code == 404


def test_multiple_users():
    """测试多用户场景"""
    print("\n\n🧪 Test 8: 创建多个用户")
    
    user_ids = []
    for i in range(3):
        url = f"{BASE_URL}/api/account/create"
        data = {
            "user_id": f"test_user_multi_{i:03d}",
            "account_type": "paper"
        }
        
        response = requests.post(url, json=data)
        assert response.status_code == 200
        user_ids.append(data["user_id"])
        print(f"✓ Created user: {data['user_id']}")
    
    # 验证每个用户都可以获取
    print("\n验证每个用户都可以获取:")
    for user_id in user_ids:
        url = f"{BASE_URL}/api/account/{user_id}"
        response = requests.get(url)
        assert response.status_code == 200
        print(f"✓ Retrieved user: {user_id}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print(" " * 20 + "🚀 用户账户管理API测试")
    print("="*80)
    
    try:
        # 测试创建账户
        paper_user_id = test_create_paper_account()
        real_user_id = test_create_real_account()
        
        # 测试验证逻辑
        test_create_real_account_missing_info()
        
        # 测试获取账户信息
        test_get_user_account(paper_user_id)
        test_get_user_account(real_user_id)
        
        # 测试获取账户状态
        test_get_user_account_status(paper_user_id)
        
        # 测试获取交易历史
        test_get_user_trade_history(paper_user_id)
        
        # 测试不存在的用户
        test_get_nonexistent_user()
        
        # 测试多用户
        test_multiple_users()
        
        print("\n" + "="*80)
        print(" " * 25 + "✅ 所有测试通过！")
        print("="*80 + "\n")
        
    except AssertionError as e:
        print("\n" + "="*80)
        print(" " * 25 + "❌ 测试失败！")
        print("="*80)
        print(f"错误: {e}\n")
        
    except requests.exceptions.ConnectionError:
        print("\n" + "="*80)
        print(" " * 20 + "❌ 无法连接到服务器！")
        print("="*80)
        print("\n请确保后端服务正在运行：")
        print("  cd backend")
        print("  python -m api.main\n")


if __name__ == "__main__":
    run_all_tests()
