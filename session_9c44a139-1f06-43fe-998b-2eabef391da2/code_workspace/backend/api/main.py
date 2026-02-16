"""
API主入口 - FastAPI应用
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
import os
import json

from core.scheduler import TradingPlatformScheduler
from models.base_models import Evidence
from datetime import datetime

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="AI Agent Stock Trading Platform",
    description="A quantitative trading platform with multi-agent deliberation workflow",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局调度器实例
scheduler = TradingPlatformScheduler()
RUNTIME_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", ".runtime_config.json")
)


# ============== 请求/响应模型 ==============

class StockRequest(BaseModel):
    symbol: str


class UserConfigRequest(BaseModel):
    api_keys: Optional[Dict[str, str]] = None
    intervals: Optional[Dict[str, int]] = None
    risk_params: Optional[Dict[str, float]] = None
    model_settings: Optional[Dict[str, Any]] = None


class ConfigValidateRequest(BaseModel):
    api_keys: Optional[Dict[str, str]] = None
    model_settings: Optional[Dict[str, Any]] = None


class MaterialUploadRequest(BaseModel):
    stock_symbol: Optional[str] = None
    content: str = ""
    summary: str = "用户上传材料"
    reliability_score: float = 0.8
    image_urls: Optional[List[str]] = None
    broadcast_to_all_d4: bool = True


class UserAccountRequest(BaseModel):
    user_id: str
    account_type: str  # "paper" 或 "real"
    brokerage: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    account_id: Optional[str] = None


def _provider_to_key_name(provider: str) -> str:
    p = provider.lower()
    if p in ("openai", "chatgpt"):
        return "OPENAI_API_KEY"
    if p == "kimi":
        return "KIMI_API_KEY"
    if p == "glm5":
        return "GLM5_API_KEY"
    if p == "deepseek":
        return "DEEPSEEK_API_KEY"
    return ""


def _provider_endpoint(provider: str) -> str:
    p = provider.lower()
    if p in ("openai", "chatgpt"):
        return "https://api.openai.com/v1/chat/completions"
    if p == "kimi":
        return "https://api.moonshot.ai/v1/chat/completions"
    if p == "glm5":
        return "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    if p == "deepseek":
        return "https://api.deepseek.com/v1/chat/completions"
    return ""


def _default_model_for_provider(provider: str) -> str:
    p = provider.lower()
    if p in ("openai", "chatgpt"):
        return "gpt-4o-mini"
    if p == "kimi":
        return "kimi-k2.5"
    if p == "glm5":
        return "glm-4-plus"
    if p == "deepseek":
        return "deepseek-chat"
    return ""


def _load_runtime_config():
    from config.settings import config, ModelProvider
    if not os.path.exists(RUNTIME_CONFIG_PATH):
        return
    try:
        with open(RUNTIME_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        api_keys = data.get("api_keys", {})
        if isinstance(api_keys, dict):
            config.api_keys.update({k: _normalize_api_key(v) for k, v in api_keys.items()})
        intervals = data.get("intervals", {})
        if isinstance(intervals, dict):
            for key in ("d1", "d2", "d3", "d4", "d6"):
                if key in intervals:
                    try:
                        setattr(config, f"{key}_interval", max(5, min(7 * 24 * 60, int(intervals[key]))))
                    except Exception:
                        continue

        ms = data.get("model_settings", {})
        alias = {
            "openai": ModelProvider.CHATGPT,
            "chatgpt": ModelProvider.CHATGPT,
            "kimi": ModelProvider.KIMI,
            "glm5": ModelProvider.GLM5,
            "deepseek": ModelProvider.DEEPSEEK
        }
        if ms.get("analyst_models"):
            config.default_analyst_models = [alias[m.lower()] for m in ms["analyst_models"] if m.lower() in alias][:3]
        if ms.get("critic_model") and ms["critic_model"].lower() in alias:
            config.default_critic_model = alias[ms["critic_model"].lower()]
        if ms.get("decider_model") and ms["decider_model"].lower() in alias:
            config.default_decider_model = alias[ms["decider_model"].lower()]
        if ms.get("analyst_model_names"):
            config.analyst_model_names = [str(x) for x in ms["analyst_model_names"]][:3]
        if ms.get("critic_model_name") is not None:
            config.critic_model_name = str(ms["critic_model_name"])
        if ms.get("decider_model_name") is not None:
            config.decider_model_name = str(ms["decider_model_name"])
        cap = ms.get("model_capabilities")
        if isinstance(cap, dict):
            config.model_capabilities.update({
                "enable_web_search": bool(cap.get("enable_web_search", config.model_capabilities.get("enable_web_search", False))),
                "enable_vision": bool(cap.get("enable_vision", config.model_capabilities.get("enable_vision", False))),
                "allow_mock_fallback": bool(cap.get("allow_mock_fallback", config.model_capabilities.get("allow_mock_fallback", False))),
            })
    except Exception as e:
        logger.warning(f"Failed to load runtime config: {e}")


def _save_runtime_config():
    from config.settings import config
    data = {
        "api_keys": config.api_keys,
        "model_settings": {
            "analyst_models": [m.value for m in config.default_analyst_models],
            "analyst_model_names": config.analyst_model_names,
            "critic_model": config.default_critic_model.value,
            "critic_model_name": config.critic_model_name,
            "decider_model": config.default_decider_model.value,
            "decider_model_name": config.decider_model_name,
            "model_capabilities": config.model_capabilities,
        },
        "intervals": {
            "d1": config.d1_interval,
            "d2": config.d2_interval,
            "d3": config.d3_interval,
            "d4": config.d4_interval,
            "d6": config.d6_interval
        },
    }
    try:
        with open(RUNTIME_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save runtime config: {e}")


async def _validate_model_call(provider: str, model: str, api_key: str) -> Dict[str, Any]:
    import aiohttp

    endpoint = _provider_endpoint(provider)
    if not endpoint:
        return {"ok": False, "message": f"Unsupported provider: {provider}"}
    if not api_key:
        return {"ok": False, "message": "Missing API key"}

    clean_key = _normalize_api_key(api_key)
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8
    }
    if provider.lower() != "kimi":
        payload["temperature"] = 0

    endpoints = [endpoint]
    if provider.lower() == "kimi":
        endpoints = ["https://api.moonshot.ai/v1/chat/completions"]

    try:
        timeout = aiohttp.ClientTimeout(total=18)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            last_message = ""
            for ep in endpoints:
                async with session.post(ep, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        return {"ok": True, "message": f"OK via {ep}"}
                    text = await resp.text()
                    if resp.status == 401:
                        last_message = f"{ep} -> HTTP 401 auth failed. Raw: {text[:200]}"
                    else:
                        last_message = f"{ep} -> HTTP {resp.status}: {text[:200]}"
            return {"ok": False, "message": last_message}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _normalize_api_key(raw: str) -> str:
    key = (raw or "").strip().strip("'").strip('"')
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    # 防止复制时带换行
    key = key.replace("\n", "").replace("\r", "")
    return key


def _is_masked_or_placeholder_key(value: str) -> bool:
    v = str(value or "").strip()
    if not v:
        return True
    if "..." in v:
        return True
    if "•" in v:
        return True
    if set(v) <= {"*", "x", "X"}:
        return True
    return False


@app.on_event("startup")
async def startup_event():
    """应用启动时运行"""
    logger.info("Starting trading platform...")
    _load_runtime_config()
    scheduler.reload_departments()
    # 清理历史遗留的无效股票代码（例如早期误输 APPL）
    stale_symbols = list(scheduler.state.active_stocks)
    removed = []
    for sym in stale_symbols:
        try:
            ok = await scheduler.validate_symbol_exists(sym)
            if not ok:
                scheduler.remove_stock(sym)
                removed.append(sym)
        except Exception:
            scheduler.remove_stock(sym)
            removed.append(sym)
    if removed:
        logger.warning(f"Removed invalid symbols on startup: {removed}")
    # 启动调度器（在后台运行）
    asyncio.create_task(scheduler.start())


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时运行"""
    logger.info("Shutting down trading platform...")
    _save_runtime_config()
    await scheduler.stop()


# ============== 股票管理 ==============

@app.post("/api/stocks/add")
async def add_stock(request: StockRequest):
    """添加股票到监控列表"""
    try:
        symbol = scheduler._normalize_symbol(request.symbol)
        # 严格校验代码存在性，避免 APPL 这类误输代码进入交易池
        exists = await scheduler.validate_symbol_exists(symbol)
        if not exists:
            raise HTTPException(status_code=400, detail=f"Symbol {symbol} not found in market data providers")
        await scheduler._get_market_data(symbol)
        scheduler.add_stock(symbol)
        return {
            "success": True,
            "message": f"Stock {symbol} added successfully",
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"Market data unavailable for symbol: {request.symbol}. {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stocks/remove")
async def remove_stock(request: StockRequest):
    """从监控列表移除股票"""
    try:
        symbol = scheduler._normalize_symbol(request.symbol)
        removed = scheduler.remove_stock(symbol)
        if not removed:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not in active pool")
        return {
            "success": True,
            "message": f"Stock {symbol} removed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/stocks/list")
async def list_stocks():
    """获取监控股票列表"""
    return {
        "stocks": scheduler.state.active_stocks,
        "count": len(scheduler.state.active_stocks),
        "timestamp": datetime.now().isoformat()
    }


# ============== 用户账户管理 ==============

@app.post("/api/account/create")
async def create_user_account(request: UserAccountRequest):
    """创建用户账户（真实或模拟）
    
    根据需求文档 0.2 节：
    - 允许用户输入自己的股票账号
    - 在没有用户提供股票账号的情况下，平台应该提供模拟账号
    """
    try:
        # 如果用户选择真实账户，验证必要信息
        if request.account_type == "real":
            if not all([request.brokerage, request.api_key, request.api_secret]):
                raise HTTPException(
                    status_code=400, 
                    detail="Real account requires brokerage, api_key, and api_secret"
                )
        
        # 创建用户账户
        user_account = scheduler.create_user_account(
            user_id=request.user_id,
            account_type=request.account_type,
            brokerage=request.brokerage,
            api_key=request.api_key,
            api_secret=request.api_secret,
            account_id=request.account_id
        )
        
        return {
            "success": True,
            "message": f"{'Paper' if request.account_type == 'paper' else 'Real'} account created",
            "account": user_account.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        logger.error(f"Validation error creating account: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/{user_id}")
async def get_user_account(user_id: str):
    """获取用户账户信息"""
    account = scheduler.get_user_account(user_id)
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    return {
        "account": account.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/account/{user_id}/status")
async def get_user_account_status(user_id: str):
    """获取用户账户状态（余额、持仓等）"""
    status = scheduler.get_user_account_status(user_id)
    if not status:
        raise HTTPException(status_code=404, detail="User account not found")
    return {
        "status": status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/account/{user_id}/trades")
async def get_user_trade_history(user_id: str, symbol: Optional[str] = None):
    """获取用户交易历史"""
    history = scheduler.get_user_trade_history(user_id, symbol)
    if history is None:
        raise HTTPException(status_code=404, detail="User account not found")
    return {
        "trades": history,
        "count": len(history),
        "timestamp": datetime.now().isoformat()
    }



# ============== 分析结果 ==============

@app.get("/api/analysis/all")
async def get_all_analysis():
    """获取所有股票的分析结果"""
    return {
        "analyses": scheduler.get_all_stocks_analysis(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/analysis/{symbol}")
async def get_stock_analysis(symbol: str):
    """获取单只股票的分析结果"""
    if symbol.lower() == "all":
        return {
            "analyses": scheduler.get_all_stocks_analysis(),
            "timestamp": datetime.now().isoformat()
        }
    analysis = scheduler.get_stock_analysis(symbol)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return analysis


# ============== 部门详情 ==============

@app.get("/api/departments/{symbol}")
async def get_department_outputs(symbol: str):
    """获取某只股票的各部门输出"""
    analysis = scheduler.get_stock_analysis(symbol)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    return {
        "symbol": symbol,
        "departments": analysis.get("department_finals", {}),
        "quant_output": analysis.get("quant_output"),
        "timestamp": datetime.now().isoformat()
    }


# ============== 交易相关 ==============

@app.get("/api/trading/account")
async def get_account_status():
    """获取账户状态"""
    return scheduler.get_account_status()


@app.get("/api/trading/positions")
async def get_positions():
    """获取持仓信息"""
    return {
        "positions": scheduler.trading_engine.get_positions(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/trading/history")
async def get_trade_history(symbol: Optional[str] = None):
    """获取交易历史"""
    return {
        "history": scheduler.get_trade_history(symbol),
        "timestamp": datetime.now().isoformat()
    }


# ============== 材料上传 ==============

@app.post("/api/materials/upload")
async def upload_material(request: MaterialUploadRequest):
    """上传专家材料"""
    try:
        stock_symbol = (request.stock_symbol or "").upper().strip()
        is_global = (not stock_symbol) or stock_symbol in ("GLOBAL", "ALL", "*")
        broadcast = bool(request.broadcast_to_all_d4 or is_global)
        image_urls = [str(x).strip() for x in (request.image_urls or []) if str(x).strip()]
        content = str(request.content or "").strip()
        if not content and not image_urls:
            raise HTTPException(status_code=400, detail="content and image_urls cannot both be empty")
        image_md = "\n".join([f"![uploaded_image]({u})" for u in image_urls])
        merged_content = content if not image_md else f"{content}\n\n{image_md}".strip()

        evidence = Evidence(
            content=merged_content,
            timestamp=datetime.now(),
            source_id=f"user_upload_{datetime.now().timestamp()}",
            reliability_score=request.reliability_score,
            summary=request.summary,
            metadata={
                "stock_symbol": stock_symbol or "GLOBAL",
                "scope": "global" if broadcast else "stock",
                "broadcast_to_all": broadcast,
                "image_urls": image_urls
            }
        )
        
        scheduler.d4.upload_material(evidence)
        scheduler.save_runtime_state()
        return {
            "success": True,
            "message": "Material uploaded successfully to D4 shared queue" if broadcast else "Material uploaded successfully to stock-targeted D4 queue",
            "material": evidence.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading material: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/materials/list")
async def list_materials():
    """查看 D4 上传材料队列"""
    try:
        rows = scheduler.d4.list_materials()
        return {
            "materials": rows,
            "count": len(rows),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing materials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/d5/train")
async def train_d5():
    """触发 D5 在线训练/校准"""
    try:
        report = await scheduler.train_d5()
        return {
            "success": True,
            "message": "D5 training completed",
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error training D5: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/d5/train/report")
async def get_d5_train_report():
    """获取最近一次 D5 训练报告"""
    try:
        return {
            "report": scheduler.get_d5_training_report(),
            "params": scheduler.d5.get_params(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting D5 train report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/update")
async def update_config(request: UserConfigRequest):
    """更新用户配置"""
    try:
        from config.settings import config, ModelProvider

        if request.api_keys:
            # 仅更新真实输入的新 key，避免掩码值/空值覆盖已保存 key
            cleaned = {}
            for k, v in request.api_keys.items():
                nv = _normalize_api_key(v)
                if _is_masked_or_placeholder_key(nv):
                    continue
                cleaned[k] = nv
            if cleaned:
                config.api_keys.update(cleaned)
                logger.info(f"Updated API keys for: {list(cleaned.keys())}")
        
        if request.intervals:
            # 更新调度间隔（D5 不开放用户改动，避免频繁误调）
            allowed = {"d1", "d2", "d3", "d4", "d6"}
            applied = {}
            for dept, interval in request.intervals.items():
                key = str(dept or "").lower().strip()
                if key not in allowed:
                    continue
                iv = int(interval)
                iv = max(5, min(7 * 24 * 60, iv))
                attr = f"{key}_interval"
                if hasattr(config, attr):
                    setattr(config, attr, iv)
                    applied[key] = iv
            if applied:
                logger.info(f"Updated intervals: {applied}")
        
        if request.risk_params:
            # 更新风控参数
            for param, value in request.risk_params.items():
                if hasattr(config, param):
                    setattr(config, param, value)
            logger.info(f"Updated risk params: {request.risk_params}")

        if request.model_settings:
            model_alias = {
                "openai": ModelProvider.CHATGPT,
                "chatgpt": ModelProvider.CHATGPT,
                "kimi": ModelProvider.KIMI,
                "glm5": ModelProvider.GLM5,
                "deepseek": ModelProvider.DEEPSEEK
            }

            analyst_models = request.model_settings.get("analyst_models")
            if analyst_models:
                config.default_analyst_models = [
                    model_alias[m.lower()] for m in analyst_models if m.lower() in model_alias
                ][:3]
                if len(config.default_analyst_models) < 3:
                    raise HTTPException(status_code=400, detail="analyst_models must include 3 valid providers")

            critic_model = request.model_settings.get("critic_model")
            if critic_model:
                key = critic_model.lower()
                if key not in model_alias:
                    raise HTTPException(status_code=400, detail=f"invalid critic_model: {critic_model}")
                config.default_critic_model = model_alias[key]

            decider_model = request.model_settings.get("decider_model")
            if decider_model:
                key = decider_model.lower()
                if key not in model_alias:
                    raise HTTPException(status_code=400, detail=f"invalid decider_model: {decider_model}")
                config.default_decider_model = model_alias[key]

            analyst_model_names = request.model_settings.get("analyst_model_names")
            if analyst_model_names:
                if len(analyst_model_names) < 3:
                    raise HTTPException(status_code=400, detail="analyst_model_names must include 3 model ids")
                config.analyst_model_names = [str(m).strip() for m in analyst_model_names[:3]]

            critic_model_name = request.model_settings.get("critic_model_name")
            if critic_model_name is not None:
                config.critic_model_name = str(critic_model_name).strip()

            decider_model_name = request.model_settings.get("decider_model_name")
            if decider_model_name is not None:
                config.decider_model_name = str(decider_model_name).strip()

            model_capabilities = request.model_settings.get("model_capabilities")
            if isinstance(model_capabilities, dict):
                config.model_capabilities["enable_web_search"] = bool(
                    model_capabilities.get("enable_web_search", config.model_capabilities.get("enable_web_search", False))
                )
                config.model_capabilities["enable_vision"] = bool(
                    model_capabilities.get("enable_vision", config.model_capabilities.get("enable_vision", False))
                )
                config.model_capabilities["allow_mock_fallback"] = bool(
                    model_capabilities.get("allow_mock_fallback", config.model_capabilities.get("allow_mock_fallback", False))
                )

            scheduler.reload_departments()
            logger.info(f"Updated model settings: {request.model_settings}")

        _save_runtime_config()
        
        return {
            "success": True,
            "message": "Configuration updated",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/current")
async def get_current_config():
    """获取当前可编辑配置"""
    from config.settings import config
    return {
        "api_keys": list(config.api_keys.keys()),
        "api_key_masked": {
            k: (f"{v[:4]}...{v[-4:]}" if isinstance(v, str) and len(v) >= 8 else "***")
            for k, v in config.api_keys.items()
        },
        "model_settings": {
            "analyst_models": [m.value for m in config.default_analyst_models],
            "analyst_model_names": config.analyst_model_names,
            "critic_model": config.default_critic_model.value,
            "critic_model_name": config.critic_model_name,
            "decider_model": config.default_decider_model.value,
            "decider_model_name": config.decider_model_name,
            "model_capabilities": config.model_capabilities,
        },
        "intervals": {
            "d1": config.d1_interval,
            "d2": config.d2_interval,
            "d3": config.d3_interval,
            "d4": config.d4_interval,
            "d5_readonly": config.d5_interval,
            "d6": config.d6_interval,
            "d7_manual_only": True,
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/config/validate")
async def validate_config(request: ConfigValidateRequest):
    """验证API Key与模型配置是否可实际调用"""
    from config.settings import config

    # 合并 key：传入优先，其次用当前运行配置
    merged_keys: Dict[str, str] = dict(config.api_keys)
    if request.api_keys:
        merged_keys.update({k: _normalize_api_key(v) for k, v in request.api_keys.items()})

    model_settings = request.model_settings or {}
    analyst_models = model_settings.get("analyst_models") or [m.value for m in config.default_analyst_models]
    analyst_model_names = model_settings.get("analyst_model_names") or config.analyst_model_names
    critic_model = model_settings.get("critic_model") or config.default_critic_model.value
    critic_model_name = model_settings.get("critic_model_name") or config.critic_model_name
    decider_model = model_settings.get("decider_model") or config.default_decider_model.value
    decider_model_name = model_settings.get("decider_model_name") or config.decider_model_name

    while len(analyst_models) < 3:
        analyst_models.append("deepseek")
    while len(analyst_model_names) < 3:
        analyst_model_names.append(_default_model_for_provider(analyst_models[len(analyst_model_names)]))

    targets = [
        {"role": "analyst_1", "provider": analyst_models[0], "model": analyst_model_names[0]},
        {"role": "analyst_2", "provider": analyst_models[1], "model": analyst_model_names[1]},
        {"role": "analyst_3", "provider": analyst_models[2], "model": analyst_model_names[2]},
        {"role": "critic", "provider": critic_model, "model": critic_model_name},
        {"role": "decider", "provider": decider_model, "model": decider_model_name},
    ]

    checks: List[Dict[str, Any]] = []
    warning_count = 0
    fail_count = 0

    for t in targets:
        provider = str(t["provider"]).lower()
        model = str(t["model"]).strip() or _default_model_for_provider(provider)
        key_name = _provider_to_key_name(provider)
        api_key = merged_keys.get(key_name, "")

        if not key_name:
            checks.append({
                "role": t["role"],
                "provider": provider,
                "model": model,
                "ok": False,
                "severity": "warning",
                "message": f"Unsupported provider: {provider}"
            })
            warning_count += 1
            continue

        if not api_key:
            checks.append({
                "role": t["role"],
                "provider": provider,
                "model": model,
                "ok": False,
                "severity": "warning",
                "message": f"Missing key: {key_name}"
            })
            warning_count += 1
            continue

        result = await _validate_model_call(provider, model, api_key)
        ok = bool(result.get("ok"))
        checks.append({
            "role": t["role"],
            "provider": provider,
            "model": model,
            "ok": ok,
            "severity": "ok" if ok else "error",
            "message": result.get("message", "")
        })
        if not ok:
            fail_count += 1

    return {
        "valid": fail_count == 0,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config/models/{provider}")
async def list_provider_models(provider: str):
    """列出 provider 可用模型（通过当前保存的 API Key 探测）"""
    import aiohttp
    from config.settings import config

    p = provider.lower().strip()
    key_name = _provider_to_key_name(p)
    if not key_name:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    api_key = _normalize_api_key(config.api_keys.get(key_name, ""))
    if not api_key:
        raise HTTPException(status_code=400, detail=f"Missing key: {key_name}")

    if p in ("openai", "chatgpt"):
        endpoints = ["https://api.openai.com/v1/models"]
    elif p == "kimi":
        endpoints = ["https://api.moonshot.ai/v1/models"]
    elif p == "deepseek":
        endpoints = ["https://api.deepseek.com/v1/models"]
    elif p == "glm5":
        endpoints = ["https://open.bigmodel.cn/api/paas/v4/models"]
    else:
        endpoints = []

    headers = {"Authorization": f"Bearer {api_key}"}
    timeout = aiohttp.ClientTimeout(total=18)
    tried: List[Dict[str, Any]] = []

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for ep in endpoints:
            try:
                async with session.get(ep, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        tried.append({"endpoint": ep, "status": resp.status, "message": text[:200]})
                        continue
                    data = json.loads(text)
                    raw_models = data.get("data", [])
                    model_ids = sorted({
                        str(item.get("id", "")).strip()
                        for item in raw_models if isinstance(item, dict) and item.get("id")
                    })
                    return {
                        "success": True,
                        "provider": p,
                        "endpoint": ep,
                        "count": len(model_ids),
                        "models": model_ids,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                tried.append({"endpoint": ep, "status": 0, "message": str(e)[:200]})

    raise HTTPException(
        status_code=502,
        detail={"message": f"Failed to fetch model list for {p}", "tried": tried}
    )

@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        return {
            "is_running": scheduler.state.is_running,
            "active_stocks": len(scheduler.state.active_stocks),
            "d7_status": scheduler.state.progress.get("d7", {}),
            "d7_recommendation_count": sum(len(v) for v in scheduler.state.d7_recommendations.values()),
            "last_run_times": {
                k: v.isoformat() for k, v in scheduler.state.last_run_times.items()
            },
            "account_value": scheduler.trading_engine.account.total_value,
            "total_pnl": scheduler.trading_engine.account.total_pnl,
            "max_drawdown": scheduler.trading_engine.account.max_drawdown,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/start")
async def start_system():
    """启动系统"""
    if not scheduler.state.is_running:
        asyncio.create_task(scheduler.start())
        return {"success": True, "message": "System started"}
    return {"success": False, "message": "System already running"}


@app.post("/api/system/run-d7")
async def run_d7_manual():
    """手动触发D7选股"""
    try:
        return {
            "success": True,
            "message": "D7 job started",
            "job_id": scheduler.run_d7_manual(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running D7 manually: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/run-once")
async def run_once_manual():
    """手动运行一轮分析和决策"""
    try:
        return {
            "success": True,
            "message": "Run-once job started",
            "job_id": scheduler.run_once_manual(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running one cycle manually: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/progress")
async def get_progress():
    """获取部门与个股进度"""
    return {
        "progress": scheduler.get_progress(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/system/jobs")
async def get_jobs():
    """获取后台任务状态"""
    return {
        "jobs": scheduler.get_jobs(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/d7/recommendations")
async def get_d7_recommendations():
    """获取D7推荐池（短/中/长）"""
    return {
        "recommendations": scheduler.get_d7_recommendations(),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/d7/select")
async def select_d7_recommendation(request: StockRequest):
    """将D7推荐股票加入交易池"""
    ok = scheduler.select_d7_recommendation(request.symbol)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Symbol {request.symbol} not found in D7 recommendations")
    return {
        "success": True,
        "message": f"Stock {request.symbol.upper()} added to active pool",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/market/quote/{symbol}")
async def get_market_quote(symbol: str):
    """获取单只股票最新模拟行情"""
    try:
        sym = scheduler._normalize_symbol(symbol)
        market_data, _ = await scheduler._get_market_data(sym)
        cached = scheduler.market_cache.get(sym) or {}
        source = cached.get("source", "unknown")
        return {
            "symbol": sym,
            "price": market_data.price,
            "timestamp": market_data.timestamp.isoformat(),
            "bid": market_data.bid_price,
            "ask": market_data.ask_price,
            "volume": market_data.volume,
            "change_percent": cached.get("change_percent"),
            "market_cap": cached.get("market_cap"),
            "avg_volume_3m": cached.get("avg_volume_3m"),
            "short_name": cached.get("short_name"),
            "source": source
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/system/stop")
async def stop_system():
    """停止系统"""
    await scheduler.stop()
    return {"success": True, "message": "System stopped"}


# ============== 健康检查 ==============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
