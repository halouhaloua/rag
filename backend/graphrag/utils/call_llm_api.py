import os
import re

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class LLMCompletionCallStream:
    def __init__(self):
        self.llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        if not self.llm_api_key:
            raise ValueError("LLM API key not provided")
        self.client = AsyncOpenAI(base_url=self.llm_base_url, api_key=self.llm_api_key)

    async def call_api_stream(self, content: str):
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": content}],
                temperature=0.3,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}}
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM streaming api calling failed. Error: {e}")
            raise e

    async def call_api_stream_messages(self, messages: list, temperature: float = 0.3):
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=temperature,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}}
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM streaming api calling failed. Error: {e}")
            raise e


class LLMCompletionCall:
    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        if not self.llm_api_key:
            raise ValueError("LLM API key not provided")
        self.client = OpenAI(base_url=self.llm_base_url, api_key=self.llm_api_key)

    def call_api(self, content: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": content}],
                temperature=0.3,
                extra_body={"thinking": {"type": "disabled"}}
            )
            raw = completion.choices[0].message.content or ""
            return self._clean_llm_content(raw)
        except Exception as e:
            logger.error(f"LLM api calling failed. Error: {e}")
            raise e

    @staticmethod
    def _clean_llm_content(text: str) -> str:
        if not isinstance(text, str):
            return ""
        t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
        fence_re = re.compile(
            r"^\s*```(?:\s*\w+)?\s*\n(?P<body>[\s\S]*?)\n\s*```\s*$", re.MULTILINE
        )
        m = fence_re.match(t)
        if m:
            t = m.group("body").strip()
        else:
            if t.startswith("```") and t.endswith("```") and len(t) >= 6:
                t = t[3:-3].strip()
        if t.lower().startswith("json\n"):
            t = t.split("\n", 1)[1].strip()
        return t
