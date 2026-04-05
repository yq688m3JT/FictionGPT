import { BrowserRouter, Route, Routes } from 'react-router-dom'
import ProjectList from './pages/ProjectList'
import NewProject from './pages/NewProject'
import ProjectView from './pages/ProjectView'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/new" element={<NewProject />} />
        <Route path="/project/:id" element={<ProjectView />} />
      </Routes>
    </BrowserRouter>
  )
}
