"""
scripts/generate.py
FictionGPT Phase 1 命令行入口

用法：
  python scripts/generate.py                  # 交互式输入设定
  python scripts/generate.py --project <id>   # 继续已有项目
  python scripts/generate.py --chapters 10    # 生成章节数（默认10）
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from memory.store import StoryDatabase
from orchestrator.pipeline import ChapterPipeline


# ======================================================================
# 配置加载
# ======================================================================

def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ======================================================================
# 交互式设定收集
# ======================================================================

def collect_setting() -> dict:
    """交互式收集初始小说设定"""
    print("\n" + "="*60)
    print("  FictionGPT — 长篇小说自动生成系统  (Phase 1 MVP)")
    print("="*60)
    print("请输入你的小说设定（直接回车跳过可选项）\n")

    title = _prompt("小说标题", required=True)
    genre = _prompt("题材（如：东方玄幻、科幻、悬疑）", required=True)
    worldview = _prompt("世界观设定（可多行，输入空行结束）", multiline=True, required=True)
    tone = _prompt("叙事基调（如：热血成长、黑暗压抑）", required=True)
    constraints = _prompt("禁忌/约束（如：不要后宫、不要系统流）", default="无")
    narrative_person = _prompt("叙事人称（第一/第三，默认第三）", default="第三")
    style_sample = _prompt(
        "风格参考样本（可粘贴喜欢的文字片段，直接回车跳过）",
        multiline=True,
        default="",
    )

    print("\n--- 角色设定 ---")
    print("（至少添加主角，输入空名称结束）")
    characters = []
    while True:
        name = input("\n角色姓名（回车结束添加）：").strip()
        if not name:
            break
        role = _prompt(f"  {name} 的角色类型（主角/配角/反派/龙套）", default="配角")
        personality = _prompt(f"  {name} 的性格描述", default="")
        speech_style = _prompt(f"  {name} 的说话风格（可选）", default="")
        background = _prompt(f"  {name} 的背景故事（可选）", default="")
        characters.append({
            "name": name,
            "role": role,
            "personality": personality,
            "speech_style": speech_style,
            "background": background,
        })
        print(f"  ✓ 已添加角色：{name}")

    if not characters:
        print("[警告] 未添加任何角色，导演规划可能质量较低。")

    return {
        "title": title,
        "genre": genre,
        "worldview": worldview,
        "tone": tone,
        "constraints": constraints,
        "narrative_person": narrative_person,
        "style_sample": style_sample,
        "characters": characters,
    }


def _prompt(label: str, default: str = "", required: bool = False, multiline: bool = False) -> str:
    if multiline:
        print(f"{label}：")
        lines = []
        while True:
            line = input()
            if not line and (lines or not required):
                break
            lines.append(line)
        result = "\n".join(lines).strip()
        return result if result else default
    else:
        suffix = f"（默认：{default}）" if default and not required else ""
        value = input(f"{label}{suffix}：").strip()
        if not value:
            if required:
                print("  此项为必填，请重新输入。")
                return _prompt(label, default, required, multiline)
            return default
        return value


# ======================================================================
# 项目初始化
# ======================================================================

def create_project(setting: dict, db: StoryDatabase, project_id: str = None) -> str:
    """将设定写入数据库，返回 project_id"""
    pid = db.create_project(
        title=setting["title"],
        genre=setting["genre"],
        worldview=setting["worldview"],
        tone=setting["tone"],
        constraints=setting["constraints"],
        style_sample=setting["style_sample"],
        narrative_person=setting["narrative_person"],
        project_id=project_id,
    )
    for char in setting["characters"]:
        db.create_character(pid, **char)
    return pid


# ======================================================================
# 输出到文件
# ======================================================================

def save_output(project_id: str, db: StoryDatabase, output_dir: str) -> str:
    """将所有章节拼接成一个TXT文件"""
    chapters = db.get_all_chapters(project_id)
    if not chapters:
        return ""

    project = db.get_project(project_id)
    title = project.title if project else "小说"

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{title}_{project_id[:8]}.txt"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write("="*60 + "\n\n")
        for ch in chapters:
            f.write(f"第{ch.chapter_number}章 {ch.title or ''}\n")
            f.write("-"*40 + "\n")
            f.write(ch.full_text or "")
            f.write("\n\n")

    return filepath


# ======================================================================
# 主流程
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="FictionGPT 命令行生成器")
    parser.add_argument("--project", type=str, help="继续已有项目的 project_id")
    parser.add_argument("--chapters", type=int, default=10, help="要生成的章节数（默认10）")
    parser.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    parser.add_argument("--output", type=str, default="./output", help="TXT输出目录")
    args = parser.parse_args()

    # 强制 UTF-8 输出（Windows 兼容）
    sys.stdout.reconfigure(encoding="utf-8")

    config = load_config(args.config)

    if args.project:
        project_id = args.project
        # 用 project_id 创建对应数据库连接
        db = StoryDatabase(config, project_id=project_id)
        project = db.get_project(project_id)
        if not project:
            print(f"[错误] 找不到项目 {project_id}")
            sys.exit(1)
        already_done = db.get_chapter_count(project_id)
        print(f"\n继续项目《{project.title}》（已生成 {already_done} 章）")
    else:
        setting = collect_setting()

        # 预先生成 project_id，DB 路径和记录使用同一个 ID
        project_id = str(uuid.uuid4())
        db = StoryDatabase(config, project_id=project_id)
        create_project(setting, db, project_id=project_id)

        already_done = 0
        print(f"\n项目已创建：{project_id}")
        print(f"《{setting['title']}》，{args.chapters} 章目标")

    target_chapters = db.get_chapter_count(project_id) + args.chapters
    pipeline = ChapterPipeline(project_id, config)

    print("\n开始生成，每章约5000字，请耐心等待...")
    print("首章生成前将先构建全篇叙事解构（可能需要1-2分钟）\n")
    print("="*60)

    generated = 0
    while db.get_chapter_count(project_id) < target_chapters:
        try:
            result = pipeline.generate_chapter(
                on_token=lambda t: print(t, end="", flush=True),
            )
            generated += 1
            print(f"\n\n{'='*60}")
            print(f"✓ 第{result['chapter_number']}章《{result['title']}》完成")
            print(f"  字数：{result['word_count']}  |  摘要：{result['summary'][:80]}...")
            print("="*60)

            # 每章完成后保存一次输出文件
            output_file = save_output(project_id, db, args.output)
            if output_file:
                print(f"  已保存到：{output_file}")

        except KeyboardInterrupt:
            print("\n\n[中断] 用户中止生成。")
            break
        except Exception as e:
            print(f"\n[错误] 第{db.get_chapter_count(project_id)+1}章生成失败：{e}")
            import traceback
            traceback.print_exc()
            choice = input("继续尝试下一章？(y/n): ").strip().lower()
            if choice != "y":
                break

    # 最终保存
    output_file = save_output(project_id, db, args.output)
    total = db.get_chapter_count(project_id)
    print(f"\n生成完成：共 {total} 章")
    if output_file:
        print(f"完整小说已保存至：{output_file}")
    print(f"项目ID（下次继续用）：{project_id}")


if __name__ == "__main__":
    main()
