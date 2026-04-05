"""
main.py
FictionGPT Phase 3 — FastAPI 应用入口
"""

from pathlib import Path

import yaml
from fastapi import FastAPI

# 加载 .env 文件中的环境变量（DEEPSEEK_API_KEY 等）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装时跳过，依赖系统环境变量
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import generation, projects
from inference.deepseek_client import DeepSeekInference

# ── 配置加载 ──────────────────────────────────────────────
with open("config.yaml", encoding="utf-8") as f:
    app_config = yaml.safe_load(f)

# ── 应用初始化 ────────────────────────────────────────────
app = FastAPI(title="FictionGPT", version="3.0")
app.state.config = app_config
app.state.inference = DeepSeekInference(app_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(generation.router, prefix="/api")


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# ── 生产环境：挂载前端静态文件（npm run build 后生效）────────
_dist = Path("frontend/dist")
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
