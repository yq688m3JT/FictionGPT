import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useGeneration } from '../hooks/useGeneration'
import type { Chapter, ChapterDetail, Character, ProjectDetail } from '../types'

export default function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [chapterDetail, setChapterDetail] = useState<ChapterDetail | null>(null)
  const [loadingChapter, setLoadingChapter] = useState(false)

  const loadChapters = useCallback(async () => {
    if (!id) return
    const data = await api.listChapters(id)
    setChapters(data)
    return data
  }, [id])

  const { status, stage, streamBuffer, start, cancel } = useGeneration(id ?? '', {
    onChapterComplete: async (msg) => {
      const data = await loadChapters()
      const num = msg.chapter_number ?? (data?.length ?? 0)
      setSelectedChapter(num)
      // 直接用流式缓冲作为章节文本，避免多一次 API 请求
      setChapterDetail({
        number: num,
        title: msg.title ?? '',
        full_text: streamBuffer,
        summary: msg.summary ?? '',
        word_count: msg.word_count ?? streamBuffer.length,
      })
    },
  })

  // 初始加载
  useEffect(() => {
    if (!id) return
    api.getProject(id).then(setProject).catch(() => {})
    loadChapters().then((data) => {
      if (data && data.length > 0) setSelectedChapter(data[data.length - 1].number)
    })
    api.listCharacters(id).then(setCharacters).catch(() => {})
  }, [id, loadChapters])

  // 加载所选章节正文
  useEffect(() => {
    if (!id || selectedChapter === null || status === 'generating') return
    setLoadingChapter(true)
    api
      .getChapter(id, selectedChapter)
      .then(setChapterDetail)
      .catch(() => {})
      .finally(() => setLoadingChapter(false))
  }, [id, selectedChapter, status])

  const isGenerating = status === 'generating'

  return (
    <div className="flex h-screen overflow-hidden bg-slate-900 text-slate-100">
      {/* ── 左侧：章节目录 ── */}
      <aside className="w-52 flex-shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <Link
            to="/"
            className="text-slate-500 hover:text-slate-300 transition-colors text-xs"
            title="返回主页"
          >
            ←
          </Link>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            章节目录
          </span>
        </div>
        <div className="flex-1 overflow-y-auto">
          {chapters.length === 0 && (
            <p className="text-xs text-slate-600 text-center mt-8 px-4">
              还没有章节，点击右侧「生成」开始
            </p>
          )}
          {chapters.map((ch) => (
            <button
              key={ch.number}
              onClick={() => {
                if (!isGenerating) setSelectedChapter(ch.number)
              }}
              className={`w-full text-left px-4 py-3 border-b border-slate-700/40 transition-colors ${
                selectedChapter === ch.number && !isGenerating
                  ? 'bg-blue-600/20 text-blue-300'
                  : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-200'
              }`}
            >
              <div className="text-xs font-medium">第 {ch.number} 章</div>
              <div className="text-xs text-slate-500 truncate mt-0.5">{ch.title || '—'}</div>
              <div className="text-xs text-slate-600 mt-0.5">{ch.word_count.toLocaleString()} 字</div>
            </button>
          ))}
        </div>
      </aside>

      {/* ── 中间：阅读区 ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶栏 */}
        <div className="h-12 bg-slate-800 border-b border-slate-700 flex items-center px-6 gap-3 flex-shrink-0">
          <h1 className="font-semibold text-sm truncate">{project?.title ?? '加载中...'}</h1>
          {project?.genre && (
            <span className="text-xs text-slate-500 bg-slate-700 px-2 py-0.5 rounded-full">
              {project.genre}
            </span>
          )}
          <span className="text-xs text-slate-500 ml-auto">
            {project?.narrative_person}人称 · 共 {chapters.length} 章
          </span>
        </div>

        {/* 内容 */}
        <ReaderArea
          isGenerating={isGenerating}
          stage={stage}
          streamBuffer={streamBuffer}
          chapter={isGenerating ? null : chapterDetail}
          loading={loadingChapter}
        />
      </main>

      {/* ── 右侧：控制 + 信息 ── */}
      <aside className="w-72 flex-shrink-0 bg-slate-800 border-l border-slate-700 flex flex-col overflow-hidden">
        {/* 生成控制 */}
        <GenerationPanel
          status={status}
          stage={stage}
          chapterCount={chapters.length}
          onStart={start}
          onCancel={cancel}
        />

        {/* 角色状态 */}
        <div className="flex-1 overflow-y-auto">
          <CharacterPanel characters={characters} />
        </div>
      </aside>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────
// 阅读区
// ─────────────────────────────────────────────────────────────────────

interface ReaderAreaProps {
  isGenerating: boolean
  stage: string
  streamBuffer: string
  chapter: ChapterDetail | null
  loading: boolean
}

function ReaderArea({ isGenerating, stage, streamBuffer, chapter, loading }: ReaderAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // 流式生成时自动滚动到底部
  useEffect(() => {
    if (isGenerating) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamBuffer, isGenerating])

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-8 py-10">
        {/* 生成中：显示阶段提示 + 流式文本 */}
        {isGenerating && (
          <>
            <div className="flex items-center gap-2 mb-6 text-blue-400 text-sm">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              {stage || '生成中...'}
            </div>
            {streamBuffer.length > 0 && (
              <div className={`prose-novel ${streamBuffer.length > 0 ? 'cursor-blink' : ''}`}>
                {streamBuffer.split('\n').map((line, i) =>
                  line.trim() ? (
                    <p key={i} className="text-slate-200 leading-8 mb-4 indent-8">
                      {line}
                    </p>
                  ) : null,
                )}
              </div>
            )}
          </>
        )}

        {/* 未生成时：显示已选章节 */}
        {!isGenerating && loading && (
          <div className="text-center text-slate-600 py-20 text-sm">加载中...</div>
        )}

        {!isGenerating && !loading && !chapter && (
          <div className="text-center text-slate-600 py-20 text-sm">
            从左侧选择章节，或点击右侧「生成」创作新章节
          </div>
        )}

        {!isGenerating && !loading && chapter && (
          <>
            <div className="text-center mb-10">
              <div className="text-slate-500 text-sm mb-1">第 {chapter.number} 章</div>
              <h2 className="text-2xl font-bold text-white">{chapter.title}</h2>
              <div className="text-xs text-slate-600 mt-2">
                {chapter.word_count.toLocaleString()} 字
              </div>
            </div>
            <div className="prose-novel">
              {chapter.full_text.split('\n').map((line, i) =>
                line.trim() ? (
                  <p key={i} className="text-slate-200 leading-8 mb-4 indent-8">
                    {line}
                  </p>
                ) : null,
              )}
            </div>
            {chapter.summary && (
              <div className="mt-10 pt-6 border-t border-slate-700">
                <div className="text-xs text-slate-500 mb-2">本章摘要</div>
                <p className="text-sm text-slate-400 leading-7">{chapter.summary}</p>
              </div>
            )}
          </>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────
// 生成控制面板
// ─────────────────────────────────────────────────────────────────────

interface GenerationPanelProps {
  status: 'idle' | 'generating' | 'error'
  stage: string
  chapterCount: number
  onStart: () => void
  onCancel: () => void
}

function GenerationPanel({ status, stage, chapterCount, onStart, onCancel }: GenerationPanelProps) {
  return (
    <div className="p-4 border-b border-slate-700 flex-shrink-0">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          生成控制
        </span>
        <span className="text-xs text-slate-600">共 {chapterCount} 章</span>
      </div>

      {status === 'idle' && (
        <button
          onClick={onStart}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          生成第 {chapterCount + 1} 章
        </button>
      )}

      {status === 'generating' && (
        <div className="space-y-3">
          <div className="flex items-start gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse mt-1.5 flex-shrink-0" />
            <p className="text-xs text-blue-300 leading-5">{stage || '生成中...'}</p>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-1 overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full animate-[progress_3s_ease-in-out_infinite]" />
          </div>
          <button
            onClick={onCancel}
            className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-400 rounded-lg text-sm transition-colors"
          >
            取消
          </button>
        </div>
      )}

      {status === 'error' && (
        <div className="space-y-3">
          <p className="text-xs text-red-400 leading-5">{stage}</p>
          <button
            onClick={onStart}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            重试
          </button>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────
// 角色面板
// ─────────────────────────────────────────────────────────────────────

function CharacterPanel({ characters }: { characters: Character[] }) {
  const [open, setOpen] = useState(true)

  if (characters.length === 0) return null

  return (
    <div className="border-b border-slate-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 py-3 flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wide hover:bg-slate-700/30 transition-colors"
      >
        <span>角色 ({characters.length})</span>
        <span className="text-slate-600">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-2.5">
          {characters.map((c) => (
            <div key={c.id} className="bg-slate-900/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-sm text-slate-200">{c.name}</span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    c.role === '主角'
                      ? 'bg-yellow-900/40 text-yellow-400'
                      : c.role === '反派'
                        ? 'bg-red-900/40 text-red-400'
                        : 'bg-slate-700 text-slate-400'
                  }`}
                >
                  {c.role}
                </span>
                {!c.is_alive && (
                  <span className="text-xs text-slate-600">(已亡)</span>
                )}
              </div>
              {c.personality && (
                <p className="text-xs text-slate-500 leading-5">{c.personality}</p>
              )}
              {Object.keys(c.current_state).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {Object.entries(c.current_state).map(([k, v]) => (
                    <span key={k} className="text-xs text-slate-600 bg-slate-800 rounded px-1.5 py-0.5">
                      {k}：{v}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


