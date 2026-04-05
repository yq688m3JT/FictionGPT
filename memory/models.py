"""
memory/models.py
SQLAlchemy ORM 数据模型定义
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    genre = Column(String)
    setting_worldview = Column(Text)          # 世界观设定（用户原文）
    setting_tone = Column(Text)               # 叙事基调
    setting_style_sample = Column(Text)       # 风格样本
    setting_constraints = Column(Text)        # 约束/禁忌
    setting_narrative_person = Column(String, default="第三")
    output_language = Column(String, default="zh") # 项目创作语言：zh / en
    narrative_architecture = Column(Text)     # 叙事解构 JSON
    # （里程碑式滚动规划）
    current_milestone = Column(Integer)       # 当前里程碑章节号
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan", order_by="Chapter.chapter_number")
    foreshadowing = relationship("Foreshadowing", back_populates="project", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="project", cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    lang = Column(String, default="zh")       # 语言标识
    aliases = Column(Text)                    # JSON数组
    role = Column(String)                     # 主角/配角/反派/龙套
    personality = Column(Text)
    appearance = Column(Text)
    speech_style = Column(Text)               # 说话风格 + 样本对话
    background = Column(Text)
    abilities = Column(Text)
    current_state = Column(Text)              # JSON: {位置, 情绪, 已知信息, 状态}
    relationships = Column(Text)              # JSON: {角色ID: 关系描述}
    is_alive = Column(Boolean, default=True)
    first_appearance = Column(Integer)        # 首次出场章节
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="characters")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    lang = Column(String, default="zh")       # 语言标识
    title = Column(String)
    summary = Column(Text)                    # 自动生成的章节摘要
    full_text = Column(Text)
    word_count = Column(Integer)
    director_plan = Column(Text)              # 导演原始规划JSON
    screenwriter_outline = Column(Text)       # 编剧段落提纲JSON（Phase 2）
    editor_issues = Column(Text)              # 编辑问题JSON（Phase 2）
    status = Column(String, default="draft")  # draft/reviewed/final
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="chapters")


class Foreshadowing(Base):
    __tablename__ = "foreshadowing"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    planted_chapter = Column(Integer, nullable=False)
    planned_recall = Column(Integer)
    actual_recall = Column(Integer)
    status = Column(String, default="planted")   # planted/recalled/abandoned
    importance = Column(String, default="minor")  # major/minor

    project = relationship("Project", back_populates="foreshadowing")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    story_time = Column(String)
    event_description = Column(Text, nullable=False)
    chapter_number = Column(Integer)
    characters_involved = Column(Text)        # JSON数组
    location = Column(String)
    significance = Column(Text)

    project = relationship("Project", back_populates="timeline_events")


def get_engine(db_path: str):
    """创建SQLite引擎并建表"""
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine
