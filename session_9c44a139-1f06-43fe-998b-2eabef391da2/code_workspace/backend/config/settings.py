"""
系统配置文件
"""
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ModelProvider(Enum):
    """支持的模型提供商"""
    KIMI = "kimi"
    CHATGPT = "chatgpt"
    GLM5 = "glm5"
    DEEPSEEK = "deepseek"


class DepartmentType(Enum):
    """部门类型"""
    D1_MACRO = "D1"  # 宏观国际新闻部
    D2_INDUSTRY = "D2"  # 行业部
    D3_STOCK = "D3"  # 单股新闻部
    D4_EXPERT = "D4"  # 专业材料部
    D5_QUANT = "D5"  # 量化部
    D6_IC = "D6"  # 投资决策委员会
    D7_STOCK_SELECTION = "D7"  # 选股部


class Stance(Enum):
    """立场"""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class TradeAction(Enum):
    """交易动作"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    NO_TRADE = "NO_TRADE"


@dataclass
class SystemConfig:
    """系统配置"""
    # 调度频率（分钟）
    d5_interval: int = 3  # 量化部：本地高频刷新（分钟）
    d1_interval: int = 60  # 宏观部：60分钟
    d2_interval: int = 60  # 行业部：60分钟
    d3_interval: int = 60  # 单股部：60分钟
    d4_interval: int = 360  # 专家材料部：6小时
    d6_interval: int = 30  # 投委会：30分钟
    d7_interval: int = 1440  # 选股部：每天一次
    
    # 事件触发冷却时间（分钟）
    event_cooldown: int = 15
    
    # 交易规则
    max_daily_trades_per_stock: int = 2  # 每天每只股票最多交易2次
    max_weekly_trading_days_per_stock: int = 3  # 每周每只股票最多选择3天交易
    
    # 风控参数
    max_position: float = 1.0  # 最大仓位
    max_daily_loss: float = 0.02  # 最大日亏损 2%
    max_drawdown: float = 0.05  # 最大回撤 5%
    
    # 模型配置
    default_analyst_models: list = field(default_factory=lambda: [
        ModelProvider.KIMI,
        ModelProvider.CHATGPT,
        ModelProvider.GLM5
    ])
    default_critic_model: ModelProvider = ModelProvider.DEEPSEEK
    default_decider_model: ModelProvider = ModelProvider.DEEPSEEK
    analyst_model_names: list = field(default_factory=lambda: [
        "kimi-k2.5",
        "gpt-4o-mini",
        "glm-4-plus"
    ])
    critic_model_name: str = "deepseek-chat"
    decider_model_name: str = "deepseek-chat"
    model_capabilities: Dict[str, bool] = field(default_factory=lambda: {
        "enable_web_search": True,
        "enable_vision": True,
        "allow_mock_fallback": False,
    })
    
    # API配置
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # 数据库配置
    database_url: str = "sqlite:///trading_platform.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/trading_platform.log"


# 全局配置实例
config = SystemConfig()
