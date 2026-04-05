"""
agents/director.py
导演Agent：全局叙事架构师
- 里程碑式叙事解构生成
- 每章审查 + 动态微调
- 单章规划（从叙事解构中细化）
"""

import json
import re
from pathlib import Path
from typing import Callable, Optional

from agents.base import BaseAgent
from memory.store import StoryDatabase


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# 每批次细化的章节数
_DETAIL_BATCH_SIZE = 5


class DirectorAgent(BaseAgent):
    def __init__(self, inference):
        super().__init__(inference, "director", "director_system.txt")
        # 额外加载架构生成和审查 prompt 模板
        self._arch_skeleton_template = _load_prompt("director_architecture_skeleton.txt")
        self._arch_detail_template = _load_prompt("director_architecture_detail.txt")
        self._review_template = _load_prompt("director_review.txt")

    # ==================================================================
    # 1. 叙事解构生成（项目开始 / 到达里程碑时调用）
    #    拆分为两阶段：骨架 → 分批细化
    # ==================================================================

    def create_narrative_architecture(
        self,
        project_id: str,
        db: StoryDatabase,
        on_stage: Optional[Callable[[str, str], None]] = None,
    ) -> dict:
        """
        生成里程碑式叙事解构（两阶段）。
        阶段1：生成骨架（主题/故事线/弧光/伏笔/节奏 + 每章一句话概要）
        阶段2：分批细化每章的详细场景规划
        返回完整叙事解构 dict。
        """

        def _log(msg: str) -> None:
            print(msg, flush=True)
            if on_stage:
                on_stage("architecture", msg)

        # ── 阶段1：生成骨架 ──────────────────────────
        _log("[导演] 阶段1/2：生成叙事骨架（主题/故事线/弧光/伏笔/节奏）...")

        context = self._build_architecture_context(project_id, db)
        prompt = self._arch_skeleton_template
        for key, value in context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value) if value is not None else "")

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (
                "请设计叙事解构骨架。自行决定关键节点章节号，"
                "输出主题、故事线、角色弧光、伏笔、节奏设计，"
                "以及每章的一句话概要和远景章节。只输出JSON。"
            )},
        ]

        # 骨架生成使用 R1（deepseek-reasoner）做深度推理
        raw = self.inference.call_agent("director_reasoner", messages)
        print(f"[调试] 骨架原始输出片段: {raw[:300].replace(chr(10), ' ')}", flush=True)

        skeleton = _safe_parse_json(raw)
        if "error" in skeleton or "milestone_chapter" not in skeleton:
            return skeleton

        milestone = skeleton["milestone_chapter"]
        chapters_brief = skeleton.get("chapters_brief", [])
        _log(
            f"[导演] 骨架完成：里程碑=第{milestone}章，"
            f"概要{len(chapters_brief)}章，"
            f"远景{len(skeleton.get('chapters_beyond', []))}章"
        )

        # ── 阶段2：分批细化章节详情 ──────────────────
        all_detailed = []
        batches = [
            chapters_brief[i:i + _DETAIL_BATCH_SIZE]
            for i in range(0, len(chapters_brief), _DETAIL_BATCH_SIZE)
        ]

        for batch_idx, batch in enumerate(batches, 1):
            ch_range = f"{batch[0]['chapter_number']}-{batch[-1]['chapter_number']}"
            _log(
                f"[导演] 阶段2/2：细化第 {ch_range} 章"
                f"（批次 {batch_idx}/{len(batches)}）..."
            )

            detail_result = self._detail_chapters_batch(
                project_id, db, skeleton, batch
            )

            if "error" in detail_result:
                _log(f"[导演] 批次 {batch_idx} 细化失败: {detail_result.get('error')}")
                # 降级：用骨架概要生成最小化详情
                for brief in batch:
                    all_detailed.append(_brief_to_minimal_detail(brief))
            else:
                all_detailed.extend(detail_result.get("chapters_detailed", []))

        # ── 组装最终架构 ─────────────────────────────
        arch = {
            "milestone_chapter": milestone,
            "milestone_description": skeleton.get("milestone_description", ""),
            "narrative_theme": skeleton.get("narrative_theme", ""),
            "story_lines": skeleton.get("story_lines", []),
            "character_arcs": skeleton.get("character_arcs", {}),
            "foreshadowing_plan": skeleton.get("foreshadowing_plan", []),
            "pacing_design": skeleton.get("pacing_design", {}),
            "chapters_detailed": all_detailed,
            "chapters_beyond": skeleton.get("chapters_beyond", []),
            "estimated_total_chapters": skeleton.get("estimated_total_chapters", 0),
        }

        db.save_narrative_architecture(project_id, arch, milestone)
        _log(
            f"[导演] 叙事解构完成：里程碑=第{milestone}章，"
            f"详细规划{len(all_detailed)}章，"
            f"远景{len(arch.get('chapters_beyond', []))}章"
        )
        return arch

    def _detail_chapters_batch(
        self,
        project_id: str,
        db: StoryDatabase,
        skeleton: dict,
        batch: list[dict],
    ) -> dict:
        """为一批章节（来自骨架的 chapters_brief）生成详细场景规划。"""
        project = db.get_project(project_id)
        characters = db.get_all_characters(project_id)
        chapters = db.get_all_chapters(project_id)

        character_states = "\n".join(
            f"- {c.name}（{c.role}）：{c.current_state or '状态未知'}"
            for c in characters
        ) or "（暂无角色信息）"

        recent = chapters[-3:] if len(chapters) >= 3 else chapters
        recent_summaries = "\n".join(
            f"第{c.chapter_number}章《{c.title}》：{c.summary or '（无摘要）'}"
            for c in recent
        ) or "（尚无章节）"

        # 故事线摘要
        story_lines_summary = "\n".join(
            f"- [{sl['type']}] {sl['name']}：{sl['description']}"
            for sl in skeleton.get("story_lines", [])
        ) or "（无）"

        # 角色弧光摘要
        arcs = skeleton.get("character_arcs", {})
        character_arcs_summary = "\n".join(
            f"- {name}（{info.get('arc_type', '?')}）：{info.get('starting_state', '?')} → {info.get('ending_state', '?')}"
            for name, info in arcs.items()
        ) or "（无）"

        # 伏笔摘要
        fs_plan = skeleton.get("foreshadowing_plan", [])
        foreshadowing_summary = "\n".join(
            f"- [{f['importance']}] {f['description']}（第{f['plant_chapter']}章埋 → 第{f['recall_chapter']}章收）"
            for f in fs_plan
        ) or "（无）"

        # 本批次章节概要
        batch_briefs = "\n".join(
            f"第{b['chapter_number']}章《{b.get('chapter_title_hint', '?')}》"
            f"[{b.get('narrative_position', '?')}]：{b.get('narrative_goal', '?')}"
            for b in batch
        )

        context = {
            "project_settings": _format_project_settings(project),
            "character_states": character_states,
            "milestone_chapter": skeleton["milestone_chapter"],
            "milestone_description": skeleton.get("milestone_description", ""),
            "narrative_theme": skeleton.get("narrative_theme", ""),
            "story_lines_summary": story_lines_summary,
            "character_arcs_summary": character_arcs_summary,
            "foreshadowing_summary": foreshadowing_summary,
            "recent_summaries": recent_summaries,
            "batch_briefs": batch_briefs,
        }

        prompt = self._arch_detail_template
        for key, value in context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value) if value is not None else "")

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (
                f"请为第 {batch[0]['chapter_number']} 到第 {batch[-1]['chapter_number']} 章"
                f"输出详细场景规划。只输出JSON。"
            )},
        ]

        raw = self.inference.call_agent(
            self.role, messages, max_tokens_override=128000
        )
        print(
            f"[调试] 细化批次输出片段: {raw[:200].replace(chr(10), ' ')}",
            flush=True,
        )
        return _safe_parse_json(raw)

    # ==================================================================
    # 2. 章节审查（每章开始时审查上一章）
    # ==================================================================

    def review_previous_chapter(
        self, project_id: str, db: StoryDatabase
    ) -> dict:
        """
        审查上一章正文与规划的偏差。
        返回 {needs_revision, revision_notes, score, deviations, architecture_adjustments}
        """
        chapters = db.get_all_chapters(project_id)
        if not chapters:
            return {"needs_revision": False, "revision_notes": "", "score": 0}

        last_chapter = chapters[-1]
        arch = db.get_narrative_architecture(project_id)

        # 从叙事解构中找到上一章的规划
        planned = _find_chapter_in_architecture(arch, last_chapter.chapter_number)
        planned_goal = planned.get("narrative_goal", "未知") if planned else "未知"
        planned_scenes = json.dumps(
            planned.get("key_scenes", []), ensure_ascii=False, indent=2
        ) if planned else "（无规划）"

        # 叙事解构摘要（给审查提供全局视角）
        arch_summary = _summarize_architecture(arch) if arch else "（无叙事解构）"

        # 构建审查 prompt
        context = {
            "project_settings": _format_project_settings(db.get_project(project_id)),
            "narrative_architecture_summary": arch_summary,
            "chapter_number": last_chapter.chapter_number,
            "planned_narrative_goal": planned_goal,
            "planned_scenes_summary": planned_scenes,
            "chapter_text": (last_chapter.full_text or "")[:6000],
        }

        prompt = self._review_template
        for key, value in context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value) if value is not None else "")

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请审阅上一章正文。只输出JSON。"},
        ]

        raw = self.inference.call_agent(
            self.role, messages, max_tokens_override=128000
        )
        print(f"[调试] 审查原始输出片段: {raw[:200].replace(chr(10), ' ')}", flush=True)

        result = _safe_parse_json(raw)
        if "error" in result:
            return {"needs_revision": False, "revision_notes": "", "score": 7}
        return result

    # ==================================================================
    # 3. 单章规划（从叙事解构中细化）
    # ==================================================================

    def plan_chapter(self, project_id: str, db: StoryDatabase) -> dict:
        """
        基于叙事解构为下一章生成详细执行规划。
        返回 chapter plan dict（兼容编剧/作家接口）。
        """
        context = self._build_plan_context(project_id, db)
        system_prompt = self._build_system_prompt(context)

        chapter_num = context.get("chapter_count", 0) + 1
        user_msg = f"请为第 {chapter_num} 章输出最终执行规划。只输出JSON。"

        if chapter_num == 1:
            user_msg = (
                f"这是第 1 章（开篇章）。请务必忠实于叙事解构中第1章的规划，"
                f"将本章情节设计为整个故事的强力开篇。只输出JSON。"
            )

        messages = self._make_messages(system_prompt, user_msg)
        raw = self.inference.call_agent(
            self.role, messages, max_tokens_override=128000
        )

        print(f"[调试] 导演规划输出片段: {raw[:200].replace(chr(10), ' ')}", flush=True)
        return _safe_parse_json(raw)

    # ==================================================================
    # 里程碑检查
    # ==================================================================

    def should_regenerate_architecture(
        self, project_id: str, db: StoryDatabase
    ) -> bool:
        """检查是否需要重新生成叙事解构（到达里程碑）"""
        milestone = db.get_current_milestone(project_id)
        if milestone is None:
            return True  # 没有叙事解构，需要生成
        current = db.get_chapter_count(project_id)
        return current >= milestone

    # ==================================================================
    # 私有：构建上下文
    # ==================================================================

    def _build_architecture_context(self, project_id: str, db: StoryDatabase) -> dict:
        project = db.get_project(project_id)
        chapters = db.get_all_chapters(project_id)
        characters = db.get_all_characters(project_id)
        pending_fs = db.get_foreshadowing(project_id, status="planted")

        start_chapter = len(chapters) + 1

        recent = chapters[-5:] if len(chapters) >= 5 else chapters
        recent_summaries = "\n".join(
            f"第{c.chapter_number}章《{c.title}》：{c.summary or '（无摘要）'}"
            for c in recent
        ) or "（尚无章节，这是全新项目）"

        # 之前的远景章节概要（里程碑刷新时使用）
        previous_beyond = ""
        old_arch = db.get_narrative_architecture(project_id)
        if old_arch and "chapters_beyond" in old_arch:
            previous_beyond = "\n".join(
                f"第{c['chapter_number']}章：{c['brief']}"
                for c in old_arch["chapters_beyond"]
            )
        if not previous_beyond:
            previous_beyond = "（无，这是首次生成叙事解构）"

        pending_foreshadowing = "\n".join(
            f"- [{f.importance}] {f.description}（第{f.planted_chapter}章埋设）"
            for f in pending_fs
        ) or "（暂无未回收伏笔）"

        character_states = "\n".join(
            f"- {c.name}（{c.role}）：{c.current_state or '状态未知'}"
            for c in characters
        ) or "（暂无角色信息）"

        return {
            "project_settings": _format_project_settings(project),
            "character_states": character_states,
            "chapter_count": len(chapters),
            "recent_summaries": recent_summaries,
            "previous_beyond_chapters": previous_beyond,
            "pending_foreshadowing": pending_foreshadowing,
            "constraints": project.setting_constraints or "无",
            "start_chapter": start_chapter,
        }

    def _build_plan_context(self, project_id: str, db: StoryDatabase) -> dict:
        project = db.get_project(project_id)
        chapters = db.get_all_chapters(project_id)
        characters = db.get_all_characters(project_id)
        pending_fs = db.get_foreshadowing(project_id, status="planted")

        chapter_num = len(chapters) + 1
        arch = db.get_narrative_architecture(project_id)

        # 从叙事解构中提取本章预设规划
        arch_plan = _find_chapter_in_architecture(arch, chapter_num)
        if arch_plan:
            architecture_chapter_plan = json.dumps(
                arch_plan, ensure_ascii=False, indent=2
            )
        else:
            architecture_chapter_plan = "（叙事解构中未找到本章详细规划，请根据整体叙事方向自行规划）"

        recent = chapters[-5:] if len(chapters) >= 5 else chapters
        recent_summaries = "\n".join(
            f"第{c.chapter_number}章《{c.title}》：{c.summary or '（无摘要）'}"
            for c in recent
        ) or "（尚无章节）"

        pending_foreshadowing = "\n".join(
            f"- [{f.importance}] {f.description}（第{f.planted_chapter}章埋设）"
            for f in pending_fs
        ) or "（暂无未回收伏笔）"

        character_states = "\n".join(
            f"- {c.name}（{c.role}）：{c.current_state or '状态未知'}"
            for c in characters
        ) or "（暂无角色信息）"

        return {
            "project_settings": _format_project_settings(project),
            "architecture_chapter_plan": architecture_chapter_plan,
            "chapter_count": len(chapters),
            "recent_summaries": recent_summaries,
            "pending_foreshadowing": pending_foreshadowing,
            "character_states": character_states,
            "constraints": project.setting_constraints or "无",
        }


# ==================================================================
# 工具函数
# ==================================================================

def _load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt 模板文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def _format_project_settings(project) -> str:
    lines = [
        f"标题：{project.title}",
        f"题材：{project.genre or '未指定'}",
        f"世界观：{project.setting_worldview or '未指定'}",
        f"叙事基调：{project.setting_tone or '未指定'}",
        f"叙事人称：{project.setting_narrative_person or '第三'}人称",
    ]
    if project.setting_style_sample:
        lines.append(f"风格参考样本：\n{project.setting_style_sample}")
    return "\n".join(lines)


def _brief_to_minimal_detail(brief: dict) -> dict:
    """骨架概要降级为最小化的详细规划（批次细化失败时使用）"""
    ch_num = brief.get("chapter_number", 0)
    return {
        "chapter_number": ch_num,
        "chapter_title_hint": brief.get("chapter_title_hint", f"第{ch_num}章"),
        "narrative_goal": brief.get("narrative_goal", "推进故事发展"),
        "narrative_position": brief.get("narrative_position", "铺垫期"),
        "story_lines_advanced": [],
        "key_scenes": [
            {
                "scene_id": f"{ch_num}-1",
                "location": "待定",
                "characters": [],
                "conflict": brief.get("narrative_goal", "推进故事发展"),
                "emotion_arc": "平稳推进",
                "pacing": "舒缓",
            }
        ],
        "foreshadowing": {"plant": [], "recall": []},
        "tone": "自然",
        "word_count_target": 4000,
    }


def _find_chapter_in_architecture(arch: Optional[dict], chapter_number: int) -> Optional[dict]:
    """从叙事解构中查找指定章节的详细规划"""
    if not arch:
        return None
    for ch in arch.get("chapters_detailed", []):
        if ch.get("chapter_number") == chapter_number:
            return ch
    return None


def _summarize_architecture(arch: dict) -> str:
    """将叙事解构压缩为审查用的摘要"""
    parts = []
    parts.append(f"里程碑：第{arch.get('milestone_chapter', '?')}章 — {arch.get('milestone_description', '')}")
    parts.append(f"主题：{arch.get('narrative_theme', '')}")

    story_lines = arch.get("story_lines", [])
    if story_lines:
        parts.append("故事线：" + "、".join(
            f"{sl['name']}({sl['type']})" for sl in story_lines
        ))

    arcs = arch.get("character_arcs", {})
    if arcs:
        parts.append("角色弧光：" + "、".join(
            f"{name}({info.get('arc_type', '?')})" for name, info in arcs.items()
        ))

    return "\n".join(parts)


def _fix_unescaped_quotes(text: str) -> str:
    """
    修复JSON字符串值中未转义的双引号。
    LLM常用 "词语" 做中文引用，但这会破坏JSON解析。
    通过状态机判断哪些 " 是JSON结构符号，哪些是字符串内容。
    """
    result = []
    in_string = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # 处理转义字符
        if c == '\\' and in_string and i + 1 < n:
            result.append(c)
            result.append(text[i + 1])
            i += 2
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # 判断此引号是否为JSON字符串的结束符：
                # 结束符后面应该是空白+结构字符（, : } ]）或文本结束
                rest = text[i + 1:].lstrip()
                if not rest or rest[0] in ',:}]':
                    in_string = False
                    result.append(c)
                else:
                    # 字符串内容中的引号，需要转义
                    result.append('\\"')
        else:
            result.append(c)
        i += 1
    return ''.join(result)


def _safe_parse_json(text: str) -> dict:
    """宽松JSON解析，处理LLM常见格式问题"""
    # 移除可能的 think 标签
    if "<think>" in text:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.strip()

    # 第一步：去除 markdown 代码块包裹（LLM最常见问题）
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```\s*$", "", text)
    text = text.strip()

    # 第二步：提取 { 到 } 的内容（去除JSON前后的多余文本）
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 第三步：修复未转义的引号（LLM中文输出最常见问题）
    fixed = _fix_unescaped_quotes(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 移除尾部逗号后重试
    cleaned = re.sub(r",\s*([}\]])", r"\1", fixed)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试修复截断的JSON（LLM输出被max_tokens截断时）
    truncated = _repair_truncated_json(fixed)
    if truncated is not None:
        return truncated

    return {"error": "JSON解析失败", "raw": text[:500]}


def _repair_truncated_json(text: str) -> Optional[dict]:
    """
    修复被 max_tokens 截断的 JSON。
    策略：从截断点向前回退到最近的完整值边界，然后闭合所有未关闭的结构。
    """
    # 先尝试逐步补全（处理简单截断）
    patched = text
    for _ in range(50):
        try:
            return json.loads(patched)
        except json.JSONDecodeError as e:
            err_msg = str(e)
            if "Unterminated string" in err_msg:
                patched += '"'
            elif "Expecting ',' delimiter" in err_msg or "Expecting property name" in err_msg:
                patched += "}"
            elif "Expecting value" in err_msg:
                patched += '""}'
            else:
                break

    # 逐步补全失败，使用回退策略：
    # 从末尾向前找到最近的完整 JSON 值边界，截断后闭合
    # 完整值的结束标志: ", }, ], 数字, true, false, null
    for trim in range(len(text) - 1, 0, -1):
        ch = text[trim]
        if ch not in '"}]\t\n\r ':
            continue
        candidate = text[:trim + 1].rstrip().rstrip(",")
        # 计算未闭合的括号
        open_braces = 0
        open_brackets = 0
        in_str = False
        prev_backslash = False
        for c in candidate:
            if prev_backslash:
                prev_backslash = False
                continue
            if c == '\\' and in_str:
                prev_backslash = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == '{':
                open_braces += 1
            elif c == '}':
                open_braces -= 1
            elif c == '[':
                open_brackets += 1
            elif c == ']':
                open_brackets -= 1

        if open_braces < 0 or open_brackets < 0:
            continue

        # 闭合
        suffix = "]" * open_brackets + "}" * open_braces
        try:
            return json.loads(candidate + suffix)
        except json.JSONDecodeError:
            continue

    return None
