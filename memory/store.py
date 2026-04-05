"""
memory/store.py
SQLite数据访问层（CRUD）
"""

import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from memory.models import (
    Base,
    Chapter,
    Character,
    Foreshadowing,
    Project,
    TimelineEvent,
    get_engine,
)


class StoryDatabase:
    """小说数据库 CRUD 操作封装"""

    def __init__(self, config: dict, project_id: Optional[str] = None):
        db_path = config["memory"]["db_path"]
        if project_id:
            db_path = db_path.format(project_id=project_id)
        else:
            # 占位，实际使用时会被 project_id 替换
            db_path = db_path.format(project_id="default")

        self.engine = get_engine(db_path)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _session(self) -> Session:
        return self.SessionLocal()

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    def create_project(
        self,
        title: str,
        genre: str = "",
        worldview: str = "",
        tone: str = "",
        constraints: str = "",
        style_sample: str = "",
        narrative_person: str = "第三",
        project_id: Optional[str] = None,
    ) -> str:
        if project_id is None:
            project_id = str(uuid.uuid4())
        with self._session() as s:
            project = Project(
                id=project_id,
                title=title,
                genre=genre,
                setting_worldview=worldview,
                setting_tone=tone,
                setting_constraints=constraints,
                setting_style_sample=style_sample,
                setting_narrative_person=narrative_person,
            )
            s.add(project)
            s.commit()
        return project_id

    def get_project(self, project_id: str) -> Optional[Project]:
        with self._session() as s:
            project = s.get(Project, project_id)
            if project:
                s.expunge(project)
            return project

    # ------------------------------------------------------------------
    # Character
    # ------------------------------------------------------------------

    def create_character(
        self,
        project_id: str,
        name: str,
        role: str = "配角",
        personality: str = "",
        appearance: str = "",
        speech_style: str = "",
        background: str = "",
        abilities: str = "",
        aliases: Optional[list] = None,
    ) -> str:
        char_id = str(uuid.uuid4())
        with self._session() as s:
            char = Character(
                id=char_id,
                project_id=project_id,
                name=name,
                role=role,
                personality=personality,
                appearance=appearance,
                speech_style=speech_style,
                background=background,
                abilities=abilities,
                aliases=json.dumps(aliases or [], ensure_ascii=False),
                current_state=json.dumps(
                    {"位置": "未知", "情绪": "平静", "状态": "正常"},
                    ensure_ascii=False,
                ),
            )
            s.add(char)
            s.commit()
        return char_id

    def get_all_characters(self, project_id: str) -> list[Character]:
        with self._session() as s:
            chars = (
                s.query(Character)
                .filter_by(project_id=project_id)
                .all()
            )
            s.expunge_all()
            return chars

    def get_character_by_name(self, project_id: str, name: str) -> Optional[Character]:
        with self._session() as s:
            char = (
                s.query(Character)
                .filter_by(project_id=project_id, name=name)
                .first()
            )
            if char:
                s.expunge(char)
            return char

    def update_character_state(self, project_id: str, name: str, state: dict) -> None:
        with self._session() as s:
            char = (
                s.query(Character)
                .filter_by(project_id=project_id, name=name)
                .first()
            )
            if char:
                char.current_state = json.dumps(state, ensure_ascii=False)
                s.commit()

    # ------------------------------------------------------------------
    # Chapter
    # ------------------------------------------------------------------

    def save_chapter(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        full_text: str,
        summary: str = "",
        director_plan: str = "",
        screenwriter_outline: str = "",
    ) -> str:
        chapter_id = str(uuid.uuid4())
        with self._session() as s:
            chapter = Chapter(
                id=chapter_id,
                project_id=project_id,
                chapter_number=chapter_number,
                title=title,
                full_text=full_text,
                word_count=len(full_text),
                summary=summary,
                director_plan=director_plan,
                screenwriter_outline=screenwriter_outline,
                status="draft",
            )
            s.add(chapter)
            s.commit()
        return chapter_id

    def get_all_chapters(self, project_id: str) -> list[Chapter]:
        with self._session() as s:
            chapters = (
                s.query(Chapter)
                .filter_by(project_id=project_id)
                .order_by(Chapter.chapter_number)
                .all()
            )
            s.expunge_all()
            return chapters

    def get_chapter(self, project_id: str, chapter_number: int) -> Optional[Chapter]:
        with self._session() as s:
            chapter = (
                s.query(Chapter)
                .filter_by(project_id=project_id, chapter_number=chapter_number)
                .first()
            )
            if chapter:
                s.expunge(chapter)
            return chapter

    def get_chapter_count(self, project_id: str) -> int:
        with self._session() as s:
            return s.query(Chapter).filter_by(project_id=project_id).count()

    def get_latest_chapter_text(self, project_id: str, char_count: int = 800) -> str:
        """返回最新章节末尾 char_count 字（用于作家的上文衔接）"""
        with self._session() as s:
            chapter = (
                s.query(Chapter)
                .filter_by(project_id=project_id)
                .order_by(Chapter.chapter_number.desc())
                .first()
            )
            if chapter and chapter.full_text:
                return chapter.full_text[-char_count:]
            return ""

    # ------------------------------------------------------------------
    # Foreshadowing
    # ------------------------------------------------------------------

    def add_foreshadowing(
        self,
        project_id: str,
        description: str,
        planted_chapter: int,
        planned_recall: Optional[int] = None,
        importance: str = "minor",
    ) -> str:
        fid = str(uuid.uuid4())
        with self._session() as s:
            f = Foreshadowing(
                id=fid,
                project_id=project_id,
                description=description,
                planted_chapter=planted_chapter,
                planned_recall=planned_recall,
                importance=importance,
            )
            s.add(f)
            s.commit()
        return fid

    def get_foreshadowing(self, project_id: str, status: str = "planted") -> list[Foreshadowing]:
        with self._session() as s:
            items = (
                s.query(Foreshadowing)
                .filter_by(project_id=project_id, status=status)
                .all()
            )
            s.expunge_all()
            return items

    def recall_foreshadowing(self, foreshadowing_id: str, actual_chapter: int) -> None:
        with self._session() as s:
            f = s.get(Foreshadowing, foreshadowing_id)
            if f:
                f.status = "recalled"
                f.actual_recall = actual_chapter
                s.commit()

    # ------------------------------------------------------------------
    # Narrative Architecture（叙事解构）
    # ------------------------------------------------------------------

    def get_narrative_architecture(self, project_id: str) -> Optional[dict]:
        """获取当前叙事解构 JSON，无则返回 None"""
        with self._session() as s:
            project = s.get(Project, project_id)
            if project and project.narrative_architecture:
                return json.loads(project.narrative_architecture)
            return None

    def save_narrative_architecture(
        self, project_id: str, architecture: dict, milestone_chapter: int
    ) -> None:
        """保存/更新叙事解构和里程碑章节号"""
        with self._session() as s:
            project = s.get(Project, project_id)
            if project:
                project.narrative_architecture = json.dumps(
                    architecture, ensure_ascii=False
                )
                project.current_milestone = milestone_chapter
                s.commit()

    def get_current_milestone(self, project_id: str) -> Optional[int]:
        """获取当前里程碑章节号"""
        with self._session() as s:
            project = s.get(Project, project_id)
            if project:
                return project.current_milestone
            return None

    def update_chapter_text(
        self, project_id: str, chapter_number: int, new_text: str, new_summary: str = ""
    ) -> None:
        """更新已有章节的正文（导演审查后重写用）"""
        with self._session() as s:
            chapter = (
                s.query(Chapter)
                .filter_by(project_id=project_id, chapter_number=chapter_number)
                .first()
            )
            if chapter:
                chapter.full_text = new_text
                chapter.word_count = len(new_text)
                if new_summary:
                    chapter.summary = new_summary
                s.commit()
