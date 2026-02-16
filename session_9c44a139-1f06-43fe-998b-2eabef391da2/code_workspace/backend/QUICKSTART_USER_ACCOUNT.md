# 用户账户管理系统 - 快速开始指南

## 🎯 概述

本系统现已支持完整的用户账户管理功能，允许用户：
- 创建模拟账户进行模拟交易
- 创建真实账户连接券商API进行真实交易
- 管理多个独立账户

## 🚀 快速开始

### 1. 创建模拟账户

**Python代码**:
```python
from core.scheduler import TradingPlatformScheduler

scheduler = TradingPlatformScheduler()

# 创建模拟账户
account = scheduler.create_user_account(
    user_id="my_user_001",
    account_type="paper"
)

print(f"账户ID: {account.account_id}")
print(f"账户状态: {scheduler.get_user_account_status('my_user_001')}")
```

**API调用**:
```bash
curl -X POST http://localhost:8000/api/account/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "my_user_001",
    "account_type": "paper"
  }'
```

### 2. 创建真实账户

**Python代码**:
```python
# 创建真实账户
account = scheduler.create_user_account(
    user_id="my_user_002",
    account_type="real",
    brokerage="ibkr",  # 券商名称
    api_key="your_api_key",
    api_secret="your_api_secret"
)

print(f"账户ID: {account.account_id}")
print(f"券商: {account.brokerage}")
```

**API调用**:
```bash
curl -X POST http://localhost:8000/api/account/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "my_user_002",
    "account_type": "real",
    "brokerage": "ibkr",
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }'
```

### 3. 查询账户信息

**获取账户信息**:
```bash
curl http://localhost:8000/api/account/my_user_001
```

**获取账户状态**:
```bash
curl http://localhost:8000/api/account/my_user_001/status
```

**获取交易历史**:
```bash
curl http://localhost:8000/api/account/my_user_001/trades
```

## 📝 使用流程

### 模拟账户流程
```
1. 创建模拟账户 (account_type="paper")
   ↓
2. 系统自动创建交易引擎
   ↓
3. 初始资金: $100,000
   ↓
4. 开始模拟交易
```

### 真实账户流程
```
1. 创建真实账户 (account_type="real")
   ↓
2. 提供券商信息 (brokerage, api_key, api_secret)
   ↓
3. 系统验证信息
   ↓
4. 创建交易引擎
   ↓
5. 开始真实交易
```

## 🔒 安全说明

### 敏感信息保护
- ✅ API密钥和密文不会在API响应中返回
- ✅ 敏感信息仅在内部使用
- ✅ 建议使用环境变量存储API密钥

### 账户隔离
- ✅ 每个用户拥有独立的账户
- ✅ 每个用户拥有独立的交易引擎
- ✅ 账户ID全局唯一

## 📚 完整文档

- [实现文档](docs/USER_ACCOUNT_MANAGEMENT.md)
- [实现日志](docs/USER_ACCOUNT_IMPLEMENTATION_LOG.md)
- [验证清单](USER_ACCOUNT_VERIFICATION_CHECKLIST.md)

## 🧪 测试

### 运行单元测试
```bash
cd backend
python tests/test_user_account_management.py
```

### 运行验证脚本
```bash
cd backend
python verify_user_account_implementation.py
```

### 运行API测试
```bash
# 先启动服务
python -m api.main

# 在另一个终端运行测试
python examples/test_user_account_api.py
```

## ⚠️ 注意事项

### 真实交易引擎
当前真实交易引擎是**占位符实现**，实际使用时需要：
1. 实现券商API适配器
2. 添加额外的风控措施
3. 完善错误处理

### 用户认证
当前系统使用简单的 `user_id`，生产环境建议：
1. 实现完整的用户认证系统
2. 使用JWT令牌
3. 添加权限管理

### 数据持久化
当前数据存储在内存中，生产环境建议：
1. 使用数据库持久化
2. 定期备份
3. 实现数据恢复机制

## 🎓 示例场景

### 场景1：新手用户
```python
# 创建模拟账户，学习使用平台
account = scheduler.create_user_account(
    user_id="beginner_001",
    account_type="paper"
)

# 查看账户状态
status = scheduler.get_user_account_status("beginner_001")
print(f"当前余额: ${status['cash']:,.2f}")
```

### 场景2：专业交易员
```python
# 创建真实账户，连接券商
account = scheduler.create_user_account(
    user_id="pro_trader_001",
    account_type="real",
    brokerage="ibkr",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# 监控交易
trades = scheduler.get_user_trade_history("pro_trader_001")
for trade in trades:
    print(f"{trade['symbol']}: {trade['side']} {trade['quantity']} @ ${trade['filled_price']}")
```

### 场景3：多账户管理
```python
# 为不同策略创建不同账户
strategy_a = scheduler.create_user_account(
    user_id="strategy_a",
    account_type="paper"
)

strategy_b = scheduler.create_user_account(
    user_id="strategy_b",
    account_type="paper"
)

# 分别监控两个策略的表现
status_a = scheduler.get_user_account_status("strategy_a")
status_b = scheduler.get_user_account_status("strategy_b")

print(f"策略A收益: ${status_a['total_pnl']:,.2f}")
print(f"策略B收益: ${status_b['total_pnl']:,.2f}")
```

## 📞 支持

如有问题，请查看：
- [完整实现文档](docs/USER_ACCOUNT_MANAGEMENT.md)
- [测试文件](tests/test_user_account_management.py)
- [验证脚本](verify_user_account_implementation.py)

## ✅ 功能清单

- [x] 创建模拟账户
- [x] 创建真实账户
- [x] 账户信息查询
- [x] 账户状态查询
- [x] 交易历史查询
- [x] 多用户支持
- [x] 敏感信息保护
- [x] 向后兼容

**系统已准备就绪！** 🎉
