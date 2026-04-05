export interface ProjectSummary {
  id: string
  title: string
  genre: string
  chapter_count: number
  created_at: string
}

export interface ProjectDetail extends ProjectSummary {
  worldview: string
  tone: string
  constraints: string
  narrative_person: string
}

export interface Chapter {
  number: number
  title: string
  summary: string
  word_count: number
}

export interface ChapterDetail extends Chapter {
  full_text: string
}

export interface Character {
  id: string
  name: string
  role: string
  personality: string
  background: string
  current_state: Record<string, string>
  is_alive: boolean
}

export interface Foreshadowing {
  id: string
  description: string
  planted_chapter: number
  actual_recall?: number
}

export interface ForeshadowingList {
  planted: Foreshadowing[]
  recalled: Foreshadowing[]
}

export interface CharacterCreate {
  name: string
  role: string
  personality: string
  appearance: string
  speech_style: string
  background: string
  abilities: string
}

export interface ProjectCreate {
  title: string
  genre: string
  worldview: string
  tone: string
  constraints: string
  style_sample: string
  narrative_person: string
  language: string
  characters: CharacterCreate[]
}

export type GenerationStatus = 'idle' | 'generating' | 'error'

export interface WsMessage {
  type: 'stage' | 'token' | 'chapter_complete' | 'error'
  stage?: string
  message?: string
  content?: string
  chapter_number?: number
  title?: string
  word_count?: number
  summary?: string
}
