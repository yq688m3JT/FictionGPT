import type {
  ProjectSummary,
  ProjectDetail,
  ProjectCreate,
  Chapter,
  ChapterDetail,
  Character,
  CharacterCreate,
  ForeshadowingList,
} from '../types'

const BASE = '/api'

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

function post<T>(url: string, body: unknown): Promise<T> {
  return req<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  // Projects
  listProjects: () => req<ProjectSummary[]>('/projects'),
  createProject: (data: ProjectCreate) => post<{ id: string }>('/projects', data),
  getProject: (id: string) => req<ProjectDetail>(`/projects/${id}`),

  // Chapters
  listChapters: (id: string) =>
    req<Chapter[]>(`/projects/${id}/chapters`),
  getChapter: (id: string, num: number) =>
    req<ChapterDetail>(`/projects/${id}/chapters/${num}`),

  // Characters
  listCharacters: (id: string) =>
    req<Character[]>(`/projects/${id}/characters`),
  addCharacter: (id: string, data: CharacterCreate) =>
    post<{ id: string }>(`/projects/${id}/characters`, data),

  // Foreshadowing
  getForeshadowing: (id: string) =>
    req<ForeshadowingList>(`/projects/${id}/foreshadowing`),

  // Generation status (REST)
  getGenerationStatus: (id: string) =>
    req<{ generating: boolean }>(`/projects/${id}/generate/status`),
}

/** 构造 WebSocket URL（兼容 Vite dev proxy） */
export function buildWsUrl(projectId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/projects/${projectId}/generate/ws`
}
