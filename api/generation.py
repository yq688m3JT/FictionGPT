"""
api/generation.py
WebSocket 流式生成路由
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# 正在生成的项目集合（同一项目不允许并发生成）
_active: set[str] = set()


@router.get("/projects/{project_id}/generate/status")
async def generation_status(project_id: str):
    return {"generating": project_id in _active}


@router.websocket("/projects/{project_id}/generate/ws")
async def generate_stream(websocket: WebSocket, project_id: str):
    """
    WebSocket 流式章节生成。

    服务端消息类型：
      {"type": "stage",    "stage": "director",  "message": "..."}  进度阶段
      {"type": "token",    "content": "..."}                        作家输出 token
      {"type": "chapter_complete", "chapter_number": N, "title": "...",
       "word_count": N, "summary": "..."}                           完成
      {"type": "error",   "message": "..."}                         异常
    """
    await websocket.accept()

    config = websocket.app.state.config

    if project_id in _active:
        await websocket.send_json({"type": "error", "message": "该项目正在生成中，请稍后再试"})
        await websocket.close()
        return

    _active.add(project_id)

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    # 延迟导入避免循环依赖
    from orchestrator.pipeline import ChapterPipeline

    try:
        pipeline = ChapterPipeline(project_id, config)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"初始化失败：{e}"})
        await websocket.close()
        _active.discard(project_id)
        return

    def on_token(token: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "token", "content": token})

    def on_stage(stage: str, message: str) -> None:
        loop.call_soon_threadsafe(
            queue.put_nowait, {"type": "stage", "stage": stage, "message": message}
        )

    async def _run_pipeline() -> None:
        try:
            result = await asyncio.to_thread(
                pipeline.generate_chapter,
                on_token=on_token,
                on_stage=on_stage,
            )
            # full_text 可能超 4000 字，不通过 WebSocket 传输，前端按需 REST 拉取
            await queue.put(
                {
                    "type": "chapter_complete",
                    "chapter_number": result["chapter_number"],
                    "title": result["title"],
                    "word_count": result["word_count"],
                    "summary": result["summary"],
                }
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(None)  # sentinel
            _active.discard(project_id)

    task = asyncio.create_task(_run_pipeline())

    try:
        while True:
            try:
                # 核心修正：设置 1 小时超时，给 27B 模型留出极慢速生成的空间
                msg = await asyncio.wait_for(queue.get(), timeout=3600.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "error", "message": "生成超时（已满 1 小时无响应）"})
                break
            if msg is None:
                break
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        task.cancel()
        _active.discard(project_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
