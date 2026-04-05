import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
    language: 'zh',
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
      setError(t('error_title_required'))
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
          ← {t('back')}
        </Link>
        <h1 className="text-xl font-bold text-white">{t('new_project_title')}</h1>
      </header>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto px-8 py-10 space-y-8">
        {/* 基础信息 */}
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            {t('basic_info')}
          </h2>
          <div className="space-y-4">
            <Field label={`${t('story_title')} *`}>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setField('title', e.target.value)}
                placeholder={t('title_placeholder')}
                className={inputCls}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t('genre')}>
                <input
                  type="text"
                  value={form.genre}
                  onChange={(e) => setField('genre', e.target.value)}
                  placeholder={t('genre_placeholder')}
                  className={inputCls}
                />
              </Field>
              <Field label={t('narrative_pov')}>
                <select
                  value={form.narrative_person}
                  onChange={(e) => setField('narrative_person', e.target.value)}
                  className={inputCls}
                >
                  <option value="第三">{t('third_person')}</option>
                  <option value="第一">{t('first_person')}</option>
                </select>
              </Field>
              <Field label={t('writing_language')}>
                <select
                  value={form.language}
                  onChange={(e) => setField('language', e.target.value)}
                  className={inputCls}
                >
                  <option value="zh">{t('language_zh')}</option>
                  <option value="en">{t('language_en')}</option>
                </select>
              </Field>
            </div>
          </div>
        </section>

        {/* 世界观 */}
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
            {t('worldview_style')}
          </h2>
          <div className="space-y-4">
            <Field label={t('worldview_setting')}>
              <textarea
                value={form.worldview}
                onChange={(e) => setField('worldview', e.target.value)}
                rows={5}
                placeholder={t('worldview_placeholder')}
                className={inputCls}
              />
            </Field>
            <Field label={t('narrative_tone')}>
              <input
                type="text"
                value={form.tone}
                onChange={(e) => setField('tone', e.target.value)}
                placeholder={t('tone_placeholder')}
                className={inputCls}
              />
            </Field>
            <Field label={t('constraints')}>
              <input
                type="text"
                value={form.constraints}
                onChange={(e) => setField('constraints', e.target.value)}
                placeholder={t('constraints_placeholder')}
                className={inputCls}
              />
            </Field>
            <Field label={t('style_sample')}>
              <textarea
                value={form.style_sample}
                onChange={(e) => setField('style_sample', e.target.value)}
                rows={4}
                placeholder={t('style_sample_placeholder')}
                className={inputCls}
              />
            </Field>
          </div>
        </section>

        {/* 角色 */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              {t('character_settings')}
            </h2>
            <button
              type="button"
              onClick={addChar}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              + {t('add_character')}
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
                    {t('character')} {i + 1}
                  </span>
                  {characters.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeChar(i)}
                      className="text-xs text-slate-500 hover:text-red-400 transition-colors"
                    >
                      {t('delete')}
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t('name')}>
                    <input
                      type="text"
                      value={char.name}
                      onChange={(e) => setChar(i, 'name', e.target.value)}
                      placeholder={t('name_placeholder')}
                      className={inputCls}
                    />
                  </Field>
                  <Field label={t('role')}>
                    <select
                      value={char.role}
                      onChange={(e) => setChar(i, 'role', e.target.value)}
                      className={inputCls}
                    >
                      <option value="主角">{t('protagonist')}</option>
                      <option value="配角">{t('supporting')}</option>
                      <option value="反派">{t('antagonist')}</option>
                      <option value="龙套">{t('extra')}</option>
                    </select>
                  </Field>
                </div>
                <Field label={t('personality')}>
                  <input
                    type="text"
                    value={char.personality}
                    onChange={(e) => setChar(i, 'personality', e.target.value)}
                    placeholder={t('personality_placeholder')}
                    className={inputCls}
                  />
                </Field>
                <Field label={t('backstory')}>
                  <textarea
                    value={char.background}
                    onChange={(e) => setChar(i, 'background', e.target.value)}
                    rows={2}
                    placeholder={t('backstory_placeholder')}
                    className={inputCls}
                  />
                </Field>
                <Field label={t('speech_style')}>
                  <input
                    type="text"
                    value={char.speech_style}
                    onChange={(e) => setChar(i, 'speech_style', e.target.value)}
                    placeholder={t('speech_style_placeholder')}
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
            {saving ? t('creating') : t('create_and_start')}
          </button>
          <Link
            to="/"
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg font-medium transition-colors text-center"
          >
            {t('cancel')}
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
