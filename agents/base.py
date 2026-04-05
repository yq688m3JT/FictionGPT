"""
agents/base.py
Agent基类：负责加载prompt模板、格式化消息
"""

import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent:
    """所有Agent的基类"""

    def __init__(self, inference, role: str, prompt_file: str):
        """
        inference: DeepSeekInference 实例
        role: config.yaml 中的 agent key（"director" / "writer" 等）
        prompt_file: prompts/ 目录下的文件名（不含路径）
        """
        self.inference = inference
        self.role = role
        self.system_prompt_template = self._load_prompt(prompt_file)

    def _load_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt 模板文件不存在: {path}")
        return path.read_text(encoding="utf-8")

    def _build_system_prompt(self, context: dict) -> str:
        """将 context 字典填充到模板占位符中"""
        prompt = self.system_prompt_template
        for key, value in context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value) if value is not None else "")
        return prompt

    def _make_messages(self, system_prompt: str, user_content: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
