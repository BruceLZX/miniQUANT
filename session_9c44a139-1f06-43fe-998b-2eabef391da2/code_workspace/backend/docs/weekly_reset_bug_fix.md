# 每周交易天数重置逻辑修复文档

## 问题描述

原始代码中存在一个**关键bug**，导致股票在第一周交易2天后，将在后续所有周都无法再进行交易。

### 原始问题

1. **数据结构错误**：`weekly_trade_days` 原本使用 `Dict[str, set]` 结构，只存储交易日期，无法区分不同周的数据。

2. **缺少周重置机制**：代码计算了 `week_key` 但从未使用，也没有机制检测周的变化或清理旧周数据。

3. **永久阻塞**：一旦某股票在第一周交易了2天，该股票的交易日期集合就会一直保留，导致在后续周被误判为已达到交易天数限制。

## 修复方案

### 1. 修改数据结构

**修改前**：
```python
self.weekly_trade_days: Dict[str, set] = {}  # 每只股票每周交易天数
```

**修改后**：
```python
self.weekly_trade_days: Dict[str, Dict[str, set]] = {}  # 每只股票每周交易天数 {symbol: {week_key: set(dates)}}
```

### 2. 修复 `_check_trading_rules` 方法

**关键改进**：

```python
def _check_trading_rules(self, symbol: str) -> bool:
    """检查交易规则"""
    today = date.today()
    
    # 检查每日交易次数
    daily_key = f"{symbol}_{today}"
    if self.daily_trade_counts.get(daily_key, 0) >= self.max_daily_trades_per_stock:
        return False
    
    # 检查每周交易天数
    week_start = today - timedelta(days=today.weekday())
    week_key = f"{symbol}_{week_start}"
    
    # 初始化该股票的周交易记录
    if symbol not in self.weekly_trade_days:
        self.weekly_trade_days[symbol] = {}
    
    # 【关键修复】检查是否需要清理旧周的数据
    weeks_to_remove = [wk for wk in self.weekly_trade_days[symbol].keys() if wk != week_key]
    for wk in weeks_to_remove:
        del self.weekly_trade_days[symbol][wk]
    
    # 获取当前周的交易天数
    current_week_days = self.weekly_trade_days[symbol].get(week_key, set())
    
    if len(current_week_days) >= self.max_weekly_trading_days_per_stock:
        if today not in current_week_days:
            return False
    
    return True
```

### 3. 修复 `_update_account` 方法

**关键改进**：

```python
# 更新每周交易天数
week_start = today - timedelta(days=today.weekday())
week_key = f"{symbol}_{week_start}"

if symbol not in self.weekly_trade_days:
    self.weekly_trade_days[symbol] = {}

if week_key not in self.weekly_trade_days[symbol]:
    self.weekly_trade_days[symbol][week_key] = set()

self.weekly_trade_days[symbol][week_key].add(today)

# 【新增】清理过期的每日交易计数（保留最近7天）
week_ago = today - timedelta(days=7)
keys_to_remove = [k for k in self.daily_trade_counts.keys() 
                  if datetime.strptime(k.split('_')[-1], '%Y-%m-%d').date() < week_ago]
for k in keys_to_remove:
    del self.daily_trade_counts[k]
```

## 修复效果

### 修复前的问题流程

```
第1周周一：交易AAPL -> weekly_trade_days["AAPL"] = {周一}
第1周周二：交易AAPL -> weekly_trade_days["AAPL"] = {周一, 周二}
第1周周三：尝试交易 -> 被拒绝（已达到2天限制）✓ 正确

第2周周一：尝试交易AAPL -> 被拒绝（错误！集合仍包含第1周的数据）
第2周周二：尝试交易AAPL -> 被拒绝（错误！）
...所有后续周都无法交易
```

### 修复后的正确流程

```
第1周周一：交易AAPL -> weekly_trade_days["AAPL"] = {"week1": {周一}}
第1周周二：交易AAPL -> weekly_trade_days["AAPL"] = {"week1": {周一, 周二}}
第1周周三：尝试交易 -> 被拒绝（已达到2天限制）✓ 正确

第2周周一：尝试交易AAPL -> 清理week1数据，创建week2 -> 允许交易 ✓
第2周周二：交易AAPL -> weekly_trade_days["AAPL"] = {"week2": {周一, 周二}}
第2周周三：尝试交易 -> 被拒绝（已达到2天限制）✓ 正确
```

## 技术细节

### 周键（week_key）的计算

```python
week_start = today - timedelta(days=today.weekday())
week_key = f"{symbol}_{week_start}"
```

- `today.weekday()` 返回0-6（周一为0，周日为6）
- `week_start` 计算出本周周一的日期
- `week_key` 格式示例：`"AAPL_2024-01-01"`

### 数据清理策略

1. **周数据清理**：每次检查交易规则时，清理非当前周的数据
2. **日数据清理**：每次更新账户时，清理7天前的每日交易计数
3. **内存优化**：避免数据无限增长

## 测试验证

已创建单元测试文件 `backend/tests/test_paper_trading_weekly_reset.py`，包含以下测试用例：

1. `test_weekly_reset_logic` - 测试每周重置逻辑
2. `test_daily_trade_limit` - 测试每日交易次数限制
3. `test_weekly_data_structure` - 测试周数据结构
4. `test_old_data_cleanup` - 测试旧数据清理
5. `test_daily_counts_cleanup` - 测试每日计数清理

## 影响范围

- **文件修改**：`backend/trading/paper_trading.py`
- **新增测试**：`backend/tests/test_paper_trading_weekly_reset.py`
- **向后兼容**：完全兼容，不影响现有功能

## 建议

1. **监控日志**：建议添加日志记录周重置事件
2. **定期清理**：考虑添加定时任务在每周一开市前清理数据
3. **配置化**：将清理周期（7天）设为可配置参数

## 总结

此修复解决了系统在第一周后完全失效的关键bug，确保了每周交易天数限制能够正确重置，符合用户需求文档中"每周每只股票只能选择两天进行交易"的要求。
