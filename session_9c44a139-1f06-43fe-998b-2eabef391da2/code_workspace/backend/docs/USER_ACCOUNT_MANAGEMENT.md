# 用户账户管理系统实现文档

## 概述

根据需求文档（agent.md 0.2节）的要求，我们实现了完整的用户账户管理系统，允许用户：
1. 输入自己的股票账号进行真实交易
2. 在没有提供股票账号的情况下，使用平台提供的模拟账号进行模拟交易

## 实现的功能

### 1. 用户账户模型 (`backend/models/base_models.py`)

新增 `UserAccount` 数据类，包含以下字段：
- `user_id`: 用户ID
- `account_type`: 账户类型（"paper" 或 "real"）
- `brokerage`: 券商名称（真实账户需要）
- `api_key`: API密钥（真实账户需要，不对外暴露）
- `api_secret`: API密钥密文（真实账户需要，不对外暴露）
- `account_id`: 账户ID（自动生成或用户指定）
- `created_at`: 创建时间
- `is_active`: 是否激活

**安全特性**：
- `to_dict()` 方法不返回敏感信息（api_key, api_secret）

### 2. 调度器用户账户管理 (`backend/core/scheduler.py`)

新增方法和属性：
- `user_accounts`: 存储用户账户的字典
- `user_trading_engines`: 存储用户交易引擎的字典
- `create_user_account()`: 创建用户账户（支持真实和模拟）
- `get_user_account()`: 获取用户账户信息
- `get_user_trading_engine()`: 获取用户交易引擎
- `get_user_account_status()`: 获取用户账户状态
- `get_user_trade_history()`: 获取用户交易历史
- `_create_real_trading_engine()`: 创建真实交易引擎（占位符实现）

**验证逻辑**：
- 创建真实账户时验证必要信息（brokerage, api_key, api_secret）
- 为每个用户创建独立的交易引擎
- 自动生成唯一的账户ID

### 3. API端点 (`backend/api/main.py`)

新增API端点：

#### POST `/api/account/create`
创建用户账户（真实或模拟）

**请求体**：
```json
{
  "user_id": "user123",
  "account_type": "paper",  // 或 "real"
  "brokerage": "ibkr",      // 真实账户需要
  "api_key": "xxx",         // 真实账户需要
  "api_secret": "yyy",      // 真实账户需要
  "account_id": "custom_id" // 可选
}
```

**响应**：
```json
{
  "success": true,
  "message": "Paper account created",
  "account": {
    "user_id": "user123",
    "account_type": "paper",
    "account_id": "paper_user123_1234567890.123",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/account/{user_id}`
获取用户账户信息

**响应**：
```json
{
  "account": {
    "user_id": "user123",
    "account_type": "paper",
    "account_id": "paper_user123_1234567890.123",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/account/{user_id}/status`
获取用户账户状态（余额、持仓等）

**响应**：
```json
{
  "status": {
    "account_id": "paper_user123_1234567890.123",
    "initial_capital": 100000.0,
    "cash": 95000.0,
    "positions": {
      "AAPL": {
        "symbol": "AAPL",
        "quantity": 100,
        "avg_cost": 150.0,
        "current_price": 155.0,
        "market_value": 15500.0,
        "unrealized_pnl": 500.0,
        "realized_pnl": 0.0
      }
    },
    "total_value": 110500.0,
    "daily_pnl": 500.0,
    "total_pnl": 10500.0,
    "max_drawdown": 0.0
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

#### GET `/api/account/{user_id}/trades`
获取用户交易历史

**查询参数**：
- `symbol`: 可选，筛选特定股票的交易记录

**响应**：
```json
{
  "trades": [
    {
      "order_id": "order_123",
      "symbol": "AAPL",
      "side": "BUY",
      "quantity": 100,
      "filled_quantity": 100,
      "filled_price": 150.0,
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T00:00:00"
}
```

### 4. Paper Trading Engine 改进 (`backend/trading/paper_trading.py`)

修改了 `PaperTradingEngine` 的初始化方法：
- `account_id` 参数现在应该动态传入（不再硬编码为 "paper_account_001"）
- 每个用户可以拥有独立的交易引擎实例
- 添加了文档说明

## 使用示例

### 示例1：创建模拟账户

```python
from core.scheduler import TradingPlatformScheduler

scheduler = TradingPlatformScheduler()

# 创建模拟账户
user_account = scheduler.create_user_account(
    user_id="user_001",
    account_type="paper"
)

print(f"Created paper account: {user_account.account_id}")
print(f"Account status: {scheduler.get_user_account_status('user_001')}")
```

### 示例2：创建真实账户

```python
# 创建真实账户
user_account = scheduler.create_user_account(
    user_id="user_002",
    account_type="real",
    brokerage="ibkr",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

print(f"Created real account: {user_account.account_id}")
print(f"Brokerage: {user_account.brokerage}")
```

### 示例3：通过API创建账户

```bash
# 创建模拟账户
curl -X POST http://localhost:8000/api/account/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "account_type": "paper"
  }'

# 创建真实账户
curl -X POST http://localhost:8000/api/account/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_002",
    "account_type": "real",
    "brokerage": "ibkr",
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }'

# 获取账户信息
curl http://localhost:8000/api/account/user_001

# 获取账户状态
curl http://localhost:8000/api/account/user_001/status

# 获取交易历史
curl http://localhost:8000/api/account/user_001/trades
```

## 测试

运行测试脚本：

```bash
cd backend
python tests/test_user_account_management.py
```

测试覆盖：
- ✓ 创建模拟账户
- ✓ 创建真实账户
- ✓ 真实账户验证
- ✓ 获取用户账户
- ✓ 获取用户账户状态
- ✓ 多用户场景
- ✓ UserAccount.to_dict() 方法

## 安全考虑

1. **敏感信息保护**：
   - `UserAccount.to_dict()` 方法不返回 `api_key` 和 `api_secret`
   - 这些信息仅在内部使用，不对外暴露

2. **账户隔离**：
   - 每个用户拥有独立的交易引擎
   - 账户ID唯一，防止混淆

3. **验证机制**：
   - 创建真实账户时验证必要信息
   - 防止不完整配置导致的错误

## 后续工作

### 真实交易引擎实现

当前真实交易引擎是占位符实现，需要后续完成：

1. **券商API适配器**：
   - 实现不同券商的API适配器（IBKR, TD Ameritrade, Alpaca等）
   - 标准化接口，统一调用方式

2. **风控措施**：
   - 添加额外的风控检查
   - 实现交易限制和熔断机制
   - 实时监控账户状态

3. **错误处理**：
   - API调用失败重试机制
   - 网络异常处理
   - 限流和配额管理

### 用户认证和授权

当前实现使用简单的 `user_id`，后续需要：

1. **用户认证系统**：
   - 实现用户注册/登录
   - JWT令牌认证
   - 密码加密和存储

2. **权限管理**：
   - 角色和权限定义
   - 资源访问控制
   - 操作审计日志

3. **数据持久化**：
   - 数据库存储用户信息
   - 账户配置持久化
   - 交易历史归档

## 向后兼容性

为了保持向后兼容：
- 保留了原有的 `self.trading_engine` 作为默认交易引擎
- 原有的 API 端点（如 `/api/account/status`）继续工作
- 新的API端点与原有端点并存

## 总结

本次实现完成了需求文档中要求的核心功能：
1. ✅ 允许用户输入自己的股票账号
2. ✅ 在没有用户提供股票账号的情况下，提供模拟账号
3. ✅ 支持多用户独立账户管理
4. ✅ 提供完整的账户管理API
5. ✅ 实现了基本的验证和安全措施

这为平台提供了完整的用户账户管理能力，用户可以自由选择使用真实账户或模拟账户进行交易。
