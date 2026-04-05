import { BrowserRouter, Route, Routes, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ProjectList from './pages/ProjectList'
import NewProject from './pages/NewProject'
import ProjectView from './pages/ProjectView'

function Layout({ children }: { children: React.ReactNode }) {
  const { i18n, t } = useTranslation()
  const isZh = i18n.language.startsWith('zh')

  const toggleLanguage = () => {
    i18n.changeLanguage(isZh ? 'en' : 'zh')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
              <span className="text-white font-bold text-lg">F</span>
            </div>
            <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              {t('app_name', 'FictionGPT')}
            </span>
          </Link>

          {/* 语言切换滑动开关 */}
          <div className="flex items-center gap-3">
            <span className={`text-[10px] font-bold tracking-widest transition-colors ${!isZh ? 'text-indigo-400' : 'text-slate-600'}`}>EN</span>
            <button
              onClick={toggleLanguage}
              className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none bg-slate-700 hover:bg-slate-600"
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  isZh ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
            <span className={`text-[10px] font-bold tracking-widest transition-colors ${isZh ? 'text-indigo-400' : 'text-slate-600'}`}>中</span>
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/new" element={<NewProject />} />
          <Route path="/project/:id" element={<ProjectView />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
