import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import type { ProjectSummary } from '../types'

export default function ProjectList() {
  const { t } = useTranslation()
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch(() => setError('Failed to connect to backend.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            {t('my_stories', '我的小说')}
          </h1>
          <p className="text-slate-400 mt-2 text-lg">
            {t('manage_projects', '管理并继续你的创作旅程')}
          </p>
        </div>
        <button
          onClick={() => navigate('/new')}
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-xl shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all transform hover:scale-105"
        >
          <span className="mr-2 text-xl">+</span>
          {t('new_project')}
        </button>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-24 bg-slate-900/50 rounded-3xl border border-slate-800 border-dashed">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
          <p className="text-slate-400 font-medium">Loading...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-900/20 border border-red-500/50 text-red-200 rounded-2xl p-6 text-center">
          <p className="font-medium">{error}</p>
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="text-center py-32 bg-slate-900/50 rounded-3xl border border-slate-800 border-dashed">
          <div className="mx-auto w-24 h-24 bg-slate-800 rounded-full flex items-center justify-center mb-6">
            <span className="text-4xl text-slate-600">📚</span>
          </div>
          <p className="text-slate-400 text-xl font-medium mb-8">{t('no_projects')}</p>
          <button
            onClick={() => navigate('/new')}
            className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-bold rounded-2xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-xl transition-all transform hover:scale-105"
          >
            {t('create_project')}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {projects.map((p) => (
          <Link
            key={p.id}
            to={`/project/${p.id}`}
            className="group relative bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-3xl p-8 transition-all hover:shadow-2xl hover:shadow-indigo-500/10"
          >
            <div className="absolute top-0 right-0 p-8">
              <div className="text-4xl font-black text-slate-800 group-hover:text-indigo-500/20 transition-colors">
                {p.chapter_count}
              </div>
            </div>
            <div className="relative">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-400 mb-4 uppercase tracking-widest">
                {p.genre || 'Novel'}
              </div>
              <h3 className="text-2xl font-bold text-white mb-3 group-hover:text-indigo-400 transition-colors leading-tight">
                {p.title}
              </h3>
              <p className="text-slate-400 text-sm mb-8 line-clamp-2 leading-relaxed">
                {'Continuing the masterpiece...'}
              </p>
              <div className="flex items-center justify-between mt-auto pt-6 border-t border-slate-800/50">
                <span className="text-xs font-medium text-slate-500">
                  {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                </span>
                <span className="text-indigo-400 font-bold group-hover:translate-x-2 transition-transform">
                  &rarr;
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
