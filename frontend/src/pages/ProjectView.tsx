import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useGeneration } from '../hooks/useGeneration'
import type { Chapter, ChapterDetail, Character } from '../types'

export default function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()

  const [chapters, setChapters] = useState<Chapter[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [chapterDetail, setChapterDetail] = useState<ChapterDetail | null>(null)
  const [loadingChapter, setLoadingChapter] = useState(false)

  const { status, stage, streamBuffer, start, cancel } = useGeneration(id || '', {
    onChapterComplete: () => {
      loadChapters().then((data) => {
        if (data && data.length > 0) {
          setSelectedChapter(data[data.length - 1].number)
        }
      })
    },
  })

  const loadChapters = useCallback(async () => {
    if (!id) return
    const data = await api.listChapters(id)
    setChapters(data)
    return data
  }, [id])

  // 初始加载
  useEffect(() => {
    if (!id) return
    loadChapters().then((data) => {
      if (data && data.length > 0 && selectedChapter === null) {
        setSelectedChapter(data[data.length - 1].number)
      }
    })
    api.listCharacters(id).then(setCharacters).catch(() => {})
  }, [id, loadChapters])

  // 加载所选章节正文
  useEffect(() => {
    if (!id || selectedChapter === null || status === 'generating') return
    
    setChapterDetail(null) 
    setLoadingChapter(true)
    
    api
      .getChapter(id, selectedChapter)
      .then(setChapterDetail)
      .catch((err) => {
        console.error("Failed to fetch chapter:", err)
      })
      .finally(() => setLoadingChapter(false))
  }, [id, selectedChapter, status])

  const isGenerating = status === 'generating'

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-slate-950 text-slate-100">
      {/* ── 左侧：章节目录 ── */}
      <aside className="w-64 flex-shrink-0 bg-slate-900/50 border-r border-slate-800 flex flex-col">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
            {t('chapters', '章节目录')}
          </span>
          <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
            {chapters.length}
          </span>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {chapters.length === 0 && (
            <div className="px-6 py-12 text-center">
              <div className="text-3xl mb-4 opacity-20">✍️</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {t('no_chapters_hint')}
              </p>
            </div>
          )}
          {chapters.map((ch) => (
            <button
              key={ch.number}
              onClick={() => {
                if (!isGenerating) setSelectedChapter(ch.number)
              }}
              className={`w-full text-left px-6 py-4 border-b border-slate-800/50 transition-all group ${
                selectedChapter === ch.number && !isGenerating
                  ? 'bg-indigo-600/10 border-r-4 border-r-indigo-500'
                  : 'hover:bg-slate-800/50'
              }`}
            >
              <div className={`text-[10px] font-bold mb-1 uppercase tracking-tighter ${
                selectedChapter === ch.number ? 'text-indigo-400' : 'text-slate-500'
              }`}>
                {t('chapter')} {ch.number} {t('chapter_unit')}
              </div>
              <div className={`text-sm font-semibold truncate transition-colors ${
                selectedChapter === ch.number ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
              }`}>
                {ch.title || '未命名章节'}
              </div>
              <div className="text-[10px] text-slate-600 mt-2 font-medium">
                {ch.word_count.toLocaleString()} {t('words')}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* ── 中间：阅读区 ── */}
      <main className="flex-1 flex flex-col overflow-hidden bg-slate-950">
        <ReaderArea
          isGenerating={isGenerating}
          stage={stage}
          streamBuffer={streamBuffer}
          chapter={isGenerating ? null : chapterDetail}
          loading={loadingChapter}
          t={t}
        />
      </main>

      {/* ── 右侧：控制 + 信息 ── */}
      <aside className="w-80 flex-shrink-0 bg-slate-900/50 border-l border-slate-800 flex flex-col overflow-hidden">
        <GenerationPanel
          status={status}
          stage={stage}
          chapterCount={chapters.length}
          onStart={start}
          onCancel={cancel}
          t={t}
        />

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <CharacterPanel characters={characters} t={t} />
        </div>
      </aside>
    </div>
  )
}

function ReaderArea({ isGenerating, stage, streamBuffer, chapter, loading, t }: any) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isGenerating) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamBuffer, isGenerating])

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-indigo-500/5 via-transparent to-transparent">
      <div className="max-w-3xl mx-auto px-12 py-16">
        {isGenerating && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex items-center gap-3 mb-12 bg-indigo-500/10 w-fit px-4 py-2 rounded-full border border-indigo-500/20">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </span>
              <span className="text-xs font-bold text-indigo-400 uppercase tracking-widest">{stage || t('generating')}</span>
            </div>
            {streamBuffer.length > 0 && (
              <div className="prose-novel space-y-6">
                {streamBuffer.split('\n').map((line: string, i: number) =>
                  line.trim() ? (
                    <p key={i} className="text-slate-300 text-lg leading-relaxed indent-8 selection:bg-indigo-500/30">
                      {line}
                    </p>
                  ) : null,
                )}
              </div>
            )}
          </div>
        )}

        {!isGenerating && loading && (
          <div className="flex flex-col items-center justify-center py-32 opacity-40">
            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mb-6"></div>
            <p className="text-sm font-medium tracking-widest text-slate-500 uppercase">{t('translating_or_loading')}</p>
          </div>
        )}

        {!isGenerating && !loading && !chapter && (
          <div className="flex flex-col items-center justify-center py-48 text-center opacity-20">
            <div className="text-6xl mb-8">📖</div>
            <p className="text-xl font-medium max-w-xs leading-relaxed">
              {t('select_chapter_hint')}
            </p>
          </div>
        )}

        {!isGenerating && !loading && chapter && (
          <div className="animate-in fade-in duration-1000">
            <header className="text-center mb-16 relative">
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 text-8xl font-black text-slate-800/10 pointer-events-none">
                {chapter.number}
              </div>
              <div className="text-indigo-500 text-xs font-black uppercase tracking-[0.3em] mb-4">
                {t('chapter')} {chapter.number} {t('chapter_unit')}
              </div>
              <h2 className="text-4xl font-extrabold text-white tracking-tight leading-tight mb-6">
                {chapter.title}
              </h2>
              <div className="w-12 h-1 bg-indigo-600 mx-auto rounded-full mb-6"></div>
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                {chapter.word_count.toLocaleString()} {t('words')}
              </div>
            </header>
            
            <div className="prose-novel space-y-8">
              {chapter.full_text.split('\n').map((line: string, i: number) =>
                line.trim() ? (
                  <p key={i} className="text-slate-300 text-lg leading-relaxed indent-8 selection:bg-indigo-500/30">
                    {line}
                  </p>
                ) : null,
              )}
            </div>

            {chapter.summary && (
              <div className="mt-20 p-8 bg-slate-900/50 rounded-3xl border border-slate-800 shadow-inner">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
                  <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t('summary')}</div>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed italic">{chapter.summary}</p>
              </div>
            )}
          </div>
        )}

        <div ref={bottomRef} className="h-24" />
      </div>
    </div>
  )
}

function GenerationPanel({ status, stage, chapterCount, onStart, onCancel, t }: any) {
  return (
    <div className="p-8 border-b border-slate-800 bg-slate-900">
      <div className="flex items-center justify-between mb-6">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
          {t('generation_control')}
        </span>
        <span className="text-[10px] font-mono text-slate-600 px-2 py-0.5 bg-slate-800 rounded">
          VOL. {chapterCount}
        </span>
      </div>

      {status === 'idle' && (
        <button
          onClick={onStart}
          className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-sm font-bold shadow-lg shadow-indigo-600/20 transition-all transform hover:scale-[1.02] active:scale-[0.98]"
        >
          {t('write_next_chapter')}
        </button>
      )}

      {status === 'generating' && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-indigo-500/5 rounded-2xl border border-indigo-500/10">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping mt-1.5 flex-shrink-0" />
            <p className="text-xs text-indigo-300 font-medium leading-relaxed">{stage || t('generating')}</p>
          </div>
          <button
            onClick={onCancel}
            className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-2xl text-xs font-bold transition-all"
          >
            {t('cancel')}
          </button>
        </div>
      )}

      {status === 'error' && (
        <div className="space-y-4">
          <div className="p-4 bg-red-500/10 rounded-2xl border border-red-500/20">
            <p className="text-xs text-red-400 font-medium leading-relaxed">{stage}</p>
          </div>
          <button
            onClick={onStart}
            className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-sm font-bold shadow-lg shadow-indigo-600/20 transition-all"
          >
            {t('retry')}
          </button>
        </div>
      )}
    </div>
  )
}

function CharacterPanel({ characters, t }: { characters: Character[], t: any }) {
  const [open, setOpen] = useState(true)

  if (characters.length === 0) return null

  return (
    <div className="border-b border-slate-800">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full px-8 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-all"
      >
        <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
          {t('characters')} ({characters.length})
        </span>
        <span className={`text-slate-600 text-[10px] transition-transform duration-300 ${open ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>
      {open && (
        <div className="px-6 pb-8 space-y-4">
          {characters.map((c) => (
            <div key={c.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 hover:border-indigo-500/30 transition-colors group">
              <div className="flex items-center justify-between mb-3">
                <span className="font-bold text-sm text-white group-hover:text-indigo-400 transition-colors">{c.name}</span>
                <span
                  className={`text-[9px] px-2 py-0.5 rounded-full font-black uppercase tracking-tighter ${
                    c.role === '主角' || c.role === 'Protagonist'
                      ? 'bg-indigo-500/10 text-indigo-400'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {c.role}
                </span>
              </div>
              {c.personality && (
                <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-3 italic">"{c.personality}"</p>
              )}
              {Object.keys(c.current_state).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(c.current_state).map(([k, v]) => (
                    <div key={k} className="flex flex-col bg-slate-800/50 rounded-lg px-2 py-1.5 border border-slate-800 min-w-[60px]">
                      <span className="text-[8px] font-black text-slate-600 uppercase mb-0.5">{k}</span>
                      <span className="text-[10px] font-bold text-slate-400 truncate">{v as string}</span>
                    </div>
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
