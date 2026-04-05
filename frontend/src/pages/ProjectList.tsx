import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ProjectSummary } from '../types'

export default function ProjectList() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch(() => setError('无法连接到后端，请确认 uvicorn 已启动'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-700 px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">FictionGPT</h1>
          <p className="text-xs text-slate-500 mt-0.5">AI 长篇小说生成平台</p>
        </div>
        <button
          onClick={() => navigate('/new')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + 新建项目
        </button>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-10">
        <h2 className="text-lg font-semibold text-slate-200 mb-6">我的小说</h2>

        {loading && (
          <div className="text-center text-slate-500 py-20">加载中...</div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-700 text-red-300 rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="text-center py-20">
            <p className="text-slate-500 text-lg mb-4">还没有项目</p>
            <button
              onClick={() => navigate('/new')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              创建第一个故事
            </button>
          </div>
        )}

        <div className="grid gap-4">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/project/${p.id}`}
              className="block bg-slate-800 border border-slate-700 hover:border-slate-500 rounded-xl p-6 transition-colors group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">
                    {p.title}
                  </h3>
                  <p className="text-sm text-slate-400 mt-1">{p.genre || '未分类'}</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-slate-300">{p.chapter_count}</div>
                  <div className="text-xs text-slate-500">章</div>
                </div>
              </div>
              <div className="mt-3 text-xs text-slate-600">
                创建于 {p.created_at ? new Date(p.created_at).toLocaleDateString('zh-CN') : '—'}
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  )
}
