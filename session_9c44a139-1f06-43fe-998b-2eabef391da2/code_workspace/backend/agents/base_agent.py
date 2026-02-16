"""
Agent基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio
from datetime import datetime
import json
import random
import re
import base64
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import html


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str
    model_provider: str
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60


class LLMCaller:
    """LLM调用器 - 统一管理不同模型的API调用"""

    @staticmethod
    def _extract_text(result: Dict[str, Any]) -> str:
        try:
            msg = result["choices"][0]["message"]["content"]
            if isinstance(msg, str):
                return msg
            if isinstance(msg, list):
                chunks = []
                for item in msg:
                    if isinstance(item, dict) and item.get("type") == "text":
                        chunks.append(str(item.get("text", "")))
                return "\n".join([x for x in chunks if x]).strip() or json.dumps(msg, ensure_ascii=False)
            return str(msg)
        except Exception:
            return json.dumps(result, ensure_ascii=False)
    
    @staticmethod
    async def call_openai(
        prompt: str,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """调用OpenAI API"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages or [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    data["tools"] = tools
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return LLMCaller._extract_text(result)
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}") from e
    
    @staticmethod
    async def call_kimi(
        prompt: str,
        api_key: str,
        model: str = "kimi-k2.5",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """调用Kimi API (Moonshot)"""
        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": messages or [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            # US 环境默认只走 moonshot.ai，避免跨区鉴权问题
            if tools:
                data["tools"] = tools
            endpoints = ["https://api.moonshot.ai/v1/chat/completions"]
            last_error = ""
            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints:
                    try:
                        async with session.post(
                            endpoint,
                            headers=headers,
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                return LLMCaller._extract_text(result)
                            last_error = f"{endpoint} -> {response.status}: {await response.text()}"
                    except Exception as inner_e:
                        last_error = f"{endpoint} -> {inner_e}"
            raise Exception(last_error)
        except Exception as e:
            raise RuntimeError(f"Kimi call failed: {e}") from e
    
    @staticmethod
    async def call_deepseek(
        prompt: str,
        api_key: str,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """调用DeepSeek API"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages or [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    data["tools"] = tools
                async with session.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return LLMCaller._extract_text(result)
                    else:
                        error_text = await response.text()
                        raise Exception(f"DeepSeek API error: {response.status} - {error_text}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek call failed: {e}") from e

    @staticmethod
    async def call_glm5(
        prompt: str,
        api_key: str,
        model: str = "glm-4-plus",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """调用GLM API（OpenAI兼容接口）"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": messages or [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if tools:
                    data["tools"] = tools
                async with session.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return LLMCaller._extract_text(result)
                    else:
                        error_text = await response.text()
                        raise Exception(f"GLM API error: {response.status} - {error_text}")
        except Exception as e:
            raise RuntimeError(f"GLM call failed: {e}") from e
    
    @staticmethod
    def _generate_fallback_response() -> str:
        """生成后备响应（当API调用失败时）"""
        stances = ["bull", "bear", "neutral"]
        return json.dumps({
            "stance": random.choice(stances),
            "score": round(random.uniform(-1, 1), 2),
            "confidence": round(random.uniform(0.5, 1.0), 2),
            "reasoning": "Fallback response due to API unavailability",
            "key_evidence": [],
            "counter_evidence": [],
            "falsifiable_conditions": ["API service unavailable"]
        })


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.model_provider = config.model_provider
        self.conversation_history: List[Dict[str, str]] = []
        self.llm_caller = LLMCaller()

    def _extract_web_queries(self, prompt: str) -> List[str]:
        marker_start = "WEB_SEARCH_QUERIES_START"
        marker_end = "WEB_SEARCH_QUERIES_END"
        queries: List[str] = []
        if marker_start in prompt and marker_end in prompt:
            try:
                block = prompt.split(marker_start, 1)[1].split(marker_end, 1)[0]
                for line in block.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("-"):
                        q = line[1:].strip()
                        if q:
                            queries.append(q[:180])
            except Exception:
                pass
        if queries:
            return queries[:5]

        # 兜底：从prompt前部提取关键词
        compact = " ".join(prompt.split())
        if compact:
            queries.append(compact[:140])
        return queries[:3]

    async def _search_google_news(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        import aiohttp
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        )
        out: List[Dict[str, str]] = []
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {"User-Agent": "Mozilla/5.0 (MyQuantAgent/1.0)"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return out
                xml_text = await resp.text()
        try:
            root = ET.fromstring(xml_text)
            for node in root.findall("./channel/item")[:limit]:
                title = html.unescape((node.findtext("title") or "").strip())
                link = (node.findtext("link") or "").strip()
                pub = (node.findtext("pubDate") or "").strip()
                source_node = node.find("source")
                source = (source_node.text or "").strip() if source_node is not None else "Google News"
                ts = ""
                try:
                    ts = parsedate_to_datetime(pub).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    ts = pub
                if " - " in title and len(title.split(" - ")) > 1:
                    left = title.rsplit(" - ", 1)[0].strip()
                    if len(left) >= 10:
                        title = left
                if not title:
                    continue
                out.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "timestamp": ts
                })
        except Exception:
            return []
        return out

    async def _augment_prompt_with_web_context(self, prompt: str) -> str:
        try:
            queries = self._extract_web_queries(prompt)
            if not queries:
                return prompt
            snippets: List[str] = []
            for q in queries[:4]:
                try:
                    items = await self._search_google_news(q, limit=2)
                except Exception:
                    items = []
                if not items:
                    continue
                snippets.append(f"[Query] {q}")
                for it in items:
                    snippets.append(
                        f"- {it['title']} | source={it['source']} | time={it['timestamp']} | url={it['link']}"
                    )
            if not snippets:
                return prompt
            header = (
                f"以下是联网检索摘要（抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）。\n"
                "你必须优先基于这些来源分析，并在输出里保留 source_id/url 的可追溯信息。\n"
            )
            return header + "\n".join(snippets) + "\n\n" + prompt
        except Exception:
            return prompt

    async def _build_multimodal_messages(self, prompt: str, provider: str) -> Optional[List[Dict[str, Any]]]:
        image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", prompt)
        if not image_refs:
            return None

        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", prompt).strip()
        parts: List[Dict[str, Any]] = [{"type": "text", "text": text or "请分析这张图。"}]

        async def _to_data_url(ref: str) -> str:
            if ref.startswith("data:image/"):
                return ref
            if not ref.startswith("http://") and not ref.startswith("https://"):
                return ref
            try:
                import aiohttp
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(ref) as resp:
                        if resp.status != 200:
                            return ref
                        raw = await resp.read()
                        ctype = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip() or "image/jpeg"
                        b64 = base64.b64encode(raw).decode("ascii")
                        return f"data:{ctype};base64,{b64}"
            except Exception:
                return ref

        for ref in image_refs[:3]:
            url = ref.strip()
            if provider == "kimi":
                url = await _to_data_url(url)
            parts.append({"type": "image_url", "image_url": {"url": url}})
        return [{"role": "user", "content": parts}]
    
    async def call_model(self, prompt: str) -> str:
        """调用模型API - 提供默认实现"""
        def _normalize_key(raw: Optional[str]) -> str:
            key = (raw or "").strip().strip("'").strip('"')
            if key.lower().startswith("bearer "):
                key = key[7:].strip()
            return key.replace("\n", "").replace("\r", "")

        provider = self.model_provider.lower()
        if provider == "chatgpt":
            provider = "openai"

        # 优先使用显式传入，其次读取全局配置（支持运行时更新）
        api_key = self.config.api_key
        if not api_key:
            from config.settings import config
            key_map = {
                "openai": "OPENAI_API_KEY",
                "kimi": "KIMI_API_KEY",
                "glm5": "GLM5_API_KEY",
                "deepseek": "DEEPSEEK_API_KEY"
            }
            key_name = key_map.get(provider)
            if key_name:
                api_key = config.api_keys.get(key_name)
        api_key = _normalize_key(api_key)

        from config.settings import config as system_config
        caps = getattr(system_config, "model_capabilities", {}) or {}
        enable_web_search = bool(caps.get("enable_web_search", False))
        enable_vision = bool(caps.get("enable_vision", False))
        allow_mock_fallback = bool(caps.get("allow_mock_fallback", False))

        # 如果没有API key，默认直接报错（除非显式允许mock）
        if not api_key:
            if allow_mock_fallback:
                await asyncio.sleep(0.1)
                return self._generate_mock_response()
            raise RuntimeError(f"Missing API key for provider: {provider}")

        messages: Optional[List[Dict[str, Any]]] = None
        if enable_vision:
            messages = await self._build_multimodal_messages(prompt, provider)

        tools: Optional[List[Dict[str, Any]]] = None
        effective_prompt = prompt
        if enable_web_search:
            # 所有模型都先注入抓取摘要，保证“可搜索、可抓取”落地
            effective_prompt = await self._augment_prompt_with_web_context(prompt)
            if provider == "kimi":
                # Kimi 额外启用内置 web_search tool
                tools = [{"type": "builtin_function", "function": {"name": "$web_search"}}]

        # 根据不同的模型提供商调用不同的API
        try:
            if provider == "openai":
                return await self.llm_caller.call_openai(
                    prompt=effective_prompt,
                    api_key=api_key,
                    model=self.config.model_name or "gpt-4",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=messages,
                    tools=tools,
                )
            elif provider == "kimi":
                return await self.llm_caller.call_kimi(
                    prompt=effective_prompt,
                    api_key=api_key,
                    model=self.config.model_name or "kimi-k2.5",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=messages,
                    tools=tools,
                )
            elif provider == "glm5":
                return await self.llm_caller.call_glm5(
                    prompt=effective_prompt,
                    api_key=api_key,
                    model=self.config.model_name or "glm-4-plus",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=messages,
                    tools=tools,
                )
            elif provider == "deepseek":
                return await self.llm_caller.call_deepseek(
                    prompt=effective_prompt,
                    api_key=api_key,
                    model=self.config.model_name or "deepseek-chat",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=messages,
                    tools=tools,
                )
            else:
                if allow_mock_fallback:
                    return self._generate_mock_response()
                raise RuntimeError(f"Unsupported provider: {provider}")
        except Exception as e:
            if allow_mock_fallback:
                return self._generate_mock_response()
            raise RuntimeError(f"{self.agent_id} model call failed ({provider}/{self.config.model_name}): {e}") from e
    
    def _generate_mock_response(self) -> str:
        """生成模拟响应 - 子类可以重写"""
        stances = ["bull", "bear", "neutral"]
        return json.dumps({
            "stance": random.choice(stances),
            "score": round(random.uniform(-1, 1), 2),
            "confidence": round(random.uniform(0.5, 1.0), 2),
            "reasoning": "Mock response for testing",
            "key_evidence": [],
            "counter_evidence": [],
            "falsifiable_conditions": ["Test condition"]
        })
    
    @abstractmethod
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """构建提示词"""
        pass
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent任务"""
        prompt = self.build_prompt(context)
        response = await self.call_model(prompt)
        return self.parse_response(response)
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析模型响应"""
        pass
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })


class MockAgent(BaseAgent):
    """模拟Agent（用于测试）"""
    
    async def call_model(self, prompt: str) -> str:
        """模拟模型调用"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return self._generate_mock_response()
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """构建提示词"""
        return f"Analyze the following context: {context}"
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应"""
        try:
            return json.loads(response)
        except:
            return {
                "stance": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "reasoning": response
            }
