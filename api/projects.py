"""
api/projects.py
项目 CRUD + 角色 / 章节 / 伏笔查询路由
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from memory.store import StoryDatabase

router = APIRouter()


# ── 工具函数 ──────────────────────────────────────────────

def _db(config: dict, project_id: str) -> StoryDatabase:
    return StoryDatabase(config, project_id=project_id)


def _scan_projects(config: dict) -> list[dict]:
    """扫描 data 目录，枚举所有已存在的项目"""
    pattern = config["memory"]["db_path"]
    base_dir = Path(pattern.split("{project_id}")[0])
    result = []
    if not base_dir.exists():
        return result
    for db_path in base_dir.glob("*/story.db"):
        project_id = db_path.parent.name
        try:
            db = StoryDatabase(config, project_id=project_id)
            p = db.get_project(project_id)
            if p:
                result.append(
                    {
                        "id": project_id,
                        "title": p.title,
                        "genre": p.genre or "",
                        "chapter_count": db.get_chapter_count(project_id),
                        "created_at": p.created_at.isoformat() if p.created_at else "",
                    }
                )
        except Exception:
            pass
    return sorted(result, key=lambda x: x.get("created_at", ""), reverse=True)


# ── Pydantic 模型 ─────────────────────────────────────────

class CharacterIn(BaseModel):
    name: str
    role: str = "配角"
    personality: str = ""
    appearance: str = ""
    speech_style: str = ""
    background: str = ""
    abilities: str = ""


class ProjectCreate(BaseModel):
    title: str
    genre: str = ""
    worldview: str = ""
    tone: str = ""
    constraints: str = ""
    style_sample: str = ""
    narrative_person: str = "第三"
    language: str = "zh"
    characters: list[CharacterIn] = []


# ── 路由 ──────────────────────────────────────────────────

@router.get("/projects")
async def list_projects(request: Request):
    return _scan_projects(request.app.state.config)


@router.post("/projects", status_code=201)
async def create_project(data: ProjectCreate, request: Request):
    config = request.app.state.config
    project_id = str(uuid.uuid4())
    db = StoryDatabase(config, project_id=project_id)
    db.create_project(
        title=data.title,
        genre=data.genre,
        worldview=data.worldview,
        tone=data.tone,
        constraints=data.constraints,
        style_sample=data.style_sample,
        narrative_person=data.narrative_person,
        project_id=project_id,
        language=data.language,
    )
    for char in data.characters:
        db.create_character(project_id, **char.model_dump())
    return {"id": project_id}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    p = db.get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return {
        "id": project_id,
        "title": p.title,
        "genre": p.genre or "",
        "worldview": p.setting_worldview or "",
        "tone": p.setting_tone or "",
        "constraints": p.setting_constraints or "",
        "narrative_person": p.setting_narrative_person or "第三",
        "language": p.output_language or "zh",
        "chapter_count": db.get_chapter_count(project_id),
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


@router.get("/projects/{project_id}/chapters")
async def list_chapters(project_id: str, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    chapters = db.get_all_chapters(project_id)
    return [
        {
            "number": c.chapter_number,
            "title": c.title or "",
            "summary": c.summary or "",
            "word_count": c.word_count or 0,
        }
        for c in chapters
    ]


@router.get("/projects/{project_id}/chapters/{chapter_num}")
async def get_chapter(project_id: str, chapter_num: int, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    c = db.get_chapter(project_id, chapter_num)
    if not c:
        raise HTTPException(404, "Chapter not found")
    return {
        "number": c.chapter_number,
        "title": c.title or "",
        "full_text": c.full_text or "",
        "summary": c.summary or "",
        "word_count": c.word_count or 0,
    }


@router.get("/projects/{project_id}/characters")
async def list_characters(project_id: str, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    chars = db.get_all_characters(project_id)
    result = []
    for c in chars:
        try:
            state = json.loads(c.current_state) if c.current_state else {}
        except Exception:
            state = {}
        result.append(
            {
                "id": c.id,
                "name": c.name,
                "role": c.role or "",
                "personality": c.personality or "",
                "background": c.background or "",
                "current_state": state,
                "is_alive": c.is_alive,
            }
        )
    return result


@router.post("/projects/{project_id}/characters", status_code=201)
async def add_character(project_id: str, data: CharacterIn, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    char_id = db.create_character(project_id, **data.model_dump())
    return {"id": char_id}


@router.get("/projects/{project_id}/foreshadowing")
async def list_foreshadowing(project_id: str, request: Request):
    config = request.app.state.config
    db = _db(config, project_id)
    planted = db.get_foreshadowing(project_id, status="planted")
    recalled = db.get_foreshadowing(project_id, status="recalled")
    return {
        "planted": [
            {
                "id": f.id,
                "description": f.description,
                "planted_chapter": f.planted_chapter,
            }
            for f in planted
        ],
        "recalled": [
            {
                "id": f.id,
                "description": f.description,
                "planted_chapter": f.planted_chapter,
                "actual_recall": f.actual_recall,
            }
            for f in recalled
        ],
    }
