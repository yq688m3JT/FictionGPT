import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ProjectCreate, CharacterCreate } from '../types'

const EMPTY_CHAR: CharacterCreate = {
  name: '',
  role: '配角',
  personality: '',
  appearance: '',
  speech_style: '',
  background: '',
  abilities: '',
}

export default function NewProject() {
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState<Omit<ProjectCreate, 'characters'>>({
    title: '',
    genre: '',
    worldview: '',
    tone: '',
    constraints: '',
    style_sample: '',
    narrative_person: '第三',
  })
  const [characters, setCharacters] = useState<CharacterCreate[]>([{ ...EMPTY_CHAR }])

  function setField(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function setChar(i: number, key: keyof CharacterCreate, value: string) {
    setCharacters((prev) => {
      const next = [...prev]
      next[i] = { ...next[i], [key]: value }
      return next
    })
  }

  function addChar() {
    setCharacters((prev) => [...prev, { ...EMPTY_CHAR }])
  }

  function removeChar(i: number) {
    setCharacters((prev) => prev.filter((_, idx) => idx !== i))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim()) {
      setError('请填写小说标题')
      return
    }
    setSaving(true)
    setError('')
    try {
      const validChars = characters.filter((c) => c.name.trim())
      const { id } = await api.createProject({ ...form, characters: validChars })
      navigate(`/project/${id}`)
    } catch (err) {
      setError(String(err))
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-700 px-8 py-5 flex items-center gap-4">
        <Link to="/" className="text-slate-400 hover:text-white transition-colors text-sm">
          ← 返回
        </Link>
        <h1 className="text-xl font-bold text-white">新建小说项目</h1>
      </header>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto px-8 py-10 space-y-8">
        {/* 基础信息 */}
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            基础信息
          </h2>
          <div className="space-y-4">
            <Field label="小说标题 *">
              <input
                type="text"
                value={form.title}
                onChange={(e) => setField('title', e.target.value)}
                placeholder="如：苍穹之巅"
                className={inputCls}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="题材">
                <input
                  type="text"
                  value={form.genre}
                  onChange={(e) => setField('genre', e.target.value)}
                  placeholder="如：东方玄幻、科幻、悬疑"
                  className={inputCls}
                />
              </Field>
              <Field label="叙事人称">
                <select
                  value={form.narrative_person}
                  onChange={(e) => setField('narrative_person', e.target.value)}
                  className={inputCls}
                >
                  <option value="第三">第三人称</option>
                  <option value="第一">第一人称</option>
                </select>
              </Field>
            </div>
          </div>
        </section>

        {/* 世界观 */}
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            世界观与风格
          </h2>
          <div className="space-y-4">
            <Field label="世界观设定">
              <textarea
                value={form.worldview}
                onChange={(e) => setField('worldview', e.target.value)}
                rows={5}
                placeholder="描述故事发生的世界背景、规则体系、历史背景等..."
                className={inputCls}
              />
            </Field>
            <Field label="叙事基调">
              <input
                type="text"
                value={form.tone}
                onChange={(e) => setField('tone', e.target.value)}
                placeholder="如：热血成长、黑暗压抑、轻松治愈"
                className={inputCls}
              />
            </Field>
            <Field label="禁忌 / 约束（可选）">
              <input
                type="text"
                value={form.constraints}
                onChange={(e) => setField('constraints', e.target.value)}
                placeholder="如：不要后宫、不要系统流、不要NTR"
                className={inputCls}
              />
            </Field>
            <Field label="风格参考样本（可选，粘贴喜欢的文字片段）">
              <textarea
                value={form.style_sample}
                onChange={(e) => setField('style_sample', e.target.value)}
                rows={4}
                placeholder="粘贴一段你喜欢的文字风格，AI 将尝试模仿..."
                className={inputCls}
              />
            </Field>
          </div>
        </section>

        {/* 角色 */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              角色设定
            </h2>
            <button
              type="button"
              onClick={addChar}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              + 添加角色
            </button>
          </div>
          <div className="space-y-4">
            {characters.map((char, i) => (
              <div
                key={i}
                className="bg-slate-800 border border-slate-700 rounded-xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-300">
                    角色 {i + 1}
                  </span>
                  {characters.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeChar(i)}
                      className="text-xs text-slate-500 hover:text-red-400 transition-colors"
                    >
                      删除
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="姓名">
                    <input
                      type="text"
                      value={char.name}
                      onChange={(e) => setChar(i, 'name', e.target.value)}
                      placeholder="角色名字"
                      className={inputCls}
                    />
                  </Field>
                  <Field label="定位">
                    <select
                      value={char.role}
                      onChange={(e) => setChar(i, 'role', e.target.value)}
                      className={inputCls}
                    >
                      <option value="主角">主角</option>
                      <option value="配角">配角</option>
                      <option value="反派">反派</option>
                      <option value="龙套">龙套</option>
                    </select>
                  </Field>
                </div>
                <Field label="性格">
                  <input
                    type="text"
                    value={char.personality}
                    onChange={(e) => setChar(i, 'personality', e.target.value)}
                    placeholder="性格特点..."
                    className={inputCls}
                  />
                </Field>
                <Field label="背景故事">
                  <textarea
                    value={char.background}
                    onChange={(e) => setChar(i, 'background', e.target.value)}
                    rows={2}
                    placeholder="身世背景..."
                    className={inputCls}
                  />
                </Field>
                <Field label="说话风格（可选）">
                  <input
                    type="text"
                    value={char.speech_style}
                    onChange={(e) => setChar(i, 'speech_style', e.target.value)}
                    placeholder="如：言简意赅、喜欢引用诗词"
                    className={inputCls}
                  />
                </Field>
              </div>
            ))}
          </div>
        </section>

        {error && (
          <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-4 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            {saving ? '创建中...' : '创建项目并开始写作'}
          </button>
          <Link
            to="/"
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg font-medium transition-colors text-center"
          >
            取消
          </Link>
        </div>
      </form>
    </div>
  )
}

// ── 辅助组件 ──────────────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
      {children}
    </div>
  )
}

const inputCls =
  'w-full bg-slate-900 border border-slate-600 focus:border-blue-500 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 outline-none transition-colors resize-none'
