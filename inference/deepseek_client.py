"""
inference/deepseek_client.py
DeepSeek API 推理引擎：支持 R1（reasoner）和 V3（chat）
"""

import os
import re
import time
from openai import OpenAI
from typing import Iterator, Optional


class DeepSeekInference:
    """
    DeepSeek API 推理引擎。
    支持 deepseek-reasoner (R1) 和 deepseek-chat (V3)，兼容 OpenAI 协议。
    """

    def __init__(self, config: dict):
        self.config = config
        self.agent_configs = config["agents"]

        ds_cfg = config.get("deepseek", {})
        base_url = ds_cfg.get("base_url", "https://api.deepseek.com/v1")
        api_key_env = ds_cfg.get("api_key_env", "DEEPSEEK_API_KEY")
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise EnvironmentError(
                f"环境变量 {api_key_env} 未设置。"
                f"请在 .env 文件或系统环境中配置 DeepSeek API Key。"
            )

        self._client = OpenAI(base_url=base_url, api_key=api_key)

    # ------------------------------------------------------------------
    # R1 适配
    # ------------------------------------------------------------------

    def _is_r1(self, agent_role: str) -> bool:
        """DeepSeek-R1 需要特殊处理（无 temperature、无 system role）"""
        model = self.agent_configs.get(agent_role, {}).get("model", "")
        return model == "deepseek-reasoner"

    def _convert_system_to_user(self, messages: list[dict]) -> list[dict]:
        """
        R1 不支持 system role。
        将 system 消息转为 user 消息，并合并相邻同角色消息。
        """
        result = []
        for msg in messages:
            if msg["role"] == "system":
                result.append({"role": "user", "content": msg["content"]})
            else:
                result.append(msg)

        # 合并相邻的同角色 user 消息
        merged: list[dict] = []
        for msg in result:
            if merged and merged[-1]["role"] == msg["role"] == "user":
                merged[-1]["content"] += "\n\n---\n\n" + msg["content"]
            else:
                merged.append(dict(msg))
        return merged

    # ------------------------------------------------------------------
    # 普通调用
    # ------------------------------------------------------------------

    def call_agent(
        self,
        agent_role: str,
        messages: list[dict],
        response_format: Optional[dict] = None,
        max_tokens_override: Optional[int] = None,
    ) -> str:
        cfg = self.agent_configs[agent_role]
        is_r1 = self._is_r1(agent_role)

        _messages = self._convert_system_to_user(messages) if is_r1 else messages

        kwargs: dict = {
            "model": cfg["model"],
            "messages": _messages,
            "max_tokens": max_tokens_override or cfg["max_tokens"],
            "timeout": 3600.0,
        }

        # R1 不接受 temperature / top_p / penalty 等采样参数
        if not is_r1:
            for param in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
                if param in cfg:
                    kwargs[param] = cfg[param]

        # response_format 仅对 V3 生效
        if response_format and not is_r1:
            kwargs["response_format"] = response_format

        for attempt in range(2):
            try:
                print(
                    f"[推理] {agent_role}({cfg['model']}) 生成中 (第{attempt+1}次)...",
                    flush=True,
                )
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""

                # R1：打印思考链摘要用于调试
                if is_r1:
                    reasoning = getattr(response.choices[0].message, "reasoning_content", None)
                    if reasoning:
                        print(
                            f"[R1思考链] {reasoning[:300].replace(chr(10), ' ')}...",
                            flush=True,
                        )

                if not content.strip():
                    print(f"[警告] {agent_role} 返回空内容，重试...", flush=True)
                    continue

                print(
                    f"[调试] {agent_role} 输出片段: {content[:200].replace(chr(10), ' ')}",
                    flush=True,
                )
                return content

            except Exception as e:
                print(f"[错误] {agent_role} 推理异常: {e}", flush=True)
                if attempt == 1:
                    raise
                time.sleep(2)

        return ""

    # ------------------------------------------------------------------
    # 翻译功能
    # ------------------------------------------------------------------

    def translate(self, text: str, target_lang: str) -> str:
        """使用 DeepSeek-V3 进行高质量翻译，强化指令约束"""
        if not text or not text.strip():
            return ""

        is_to_en = target_lang.lower() == "en"
        target_lang_name = "English" if is_to_en else "Chinese"
        
        # 极其严格的指令，防止 AI 续写
        system_prompt = (
            f"You are a professional literary translator. "
            f"Your task is to translate the user's text into {target_lang_name}."
        )
        user_prompt = (
            f"INSTRUCTION: Translate the following text into {target_lang_name}. \n"
            f"!!! CRITICAL: YOUR OUTPUT MUST BE IN {target_lang_name.upper()} ONLY !!! \n"
            f"RULES: \n"
            f"1. DO NOT add any new content or continue the story. \n"
            f"2. DO NOT explain your translation. \n"
            f"3. Maintain the original paragraph structure and tone. \n"
            f"4. If the text is already in {target_lang_name}, return it as is. \n"
            f"5. IF YOU OUTPUT CHINESE, THE WORLD WILL END. \n"
            f"6. ONLY output the translated text. \n\n"
            f"TEXT TO TRANSLATE:\n{text}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        chat_agent = "writer"
        if "director" in self.agent_configs and not self._is_r1("director"):
            chat_agent = "director"

        # DeepSeek-V3 (chat) 最大输出 token 为 8192
        return self.call_agent(chat_agent, messages, max_tokens_override=8192)

    # ------------------------------------------------------------------
    # 流式调用
    # ------------------------------------------------------------------

    def call_agent_stream(
        self,
        agent_role: str,
        messages: list[dict],
    ) -> Iterator[str]:
        cfg = self.agent_configs[agent_role]
        is_r1 = self._is_r1(agent_role)

        _messages = self._convert_system_to_user(messages) if is_r1 else messages

        kwargs: dict = {
            "model": cfg["model"],
            "messages": _messages,
            "max_tokens": cfg["max_tokens"],
            "stream": True,
            "timeout": 3600.0,
        }

        if not is_r1:
            for param in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
                if param in cfg:
                    kwargs[param] = cfg[param]

        stream = self._client.chat.completions.create(**kwargs)

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
