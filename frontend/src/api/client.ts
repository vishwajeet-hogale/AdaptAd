import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 30000 })

// Types
export interface User {
  id: number; name: string; age_group: string; profession: string
  interests: string[]; preferred_watch_time: string; ad_tolerance: number
  fatigue_level: number; engagement_score: number; binge_tendency: number
  content_preferences: string[]
}

export interface Ad {
  id: string; category: string; advertiser: string; duration_seconds: number
  priority: number; creative_type: string; has_softened_version: boolean
  target_demographics: string[]
}

export interface ContentItem {
  id: number; title: string; genre: string; duration_minutes: number
  mood: string; is_series: boolean; natural_break_points: number[]
}

export interface AgentScore {
  agent_name: string; score: number; reasoning: string
  factors: Record<string, number>
}

export interface DecisionResult {
  decision: 'SHOW' | 'SOFTEN' | 'DELAY' | 'SUPPRESS'
  user_advocate: AgentScore; advertiser_advocate: AgentScore
  combined_score: number; reasoning: string; timestamp: string
  session_id: string; user_id: number; ad_id: string
}

export interface GenerationStats {
  generation: number; best_fitness: number; avg_fitness: number; diversity: number
}

export interface EvolutionJob {
  job_id: string; status: string; current_generation: number
  best_fitness: number | null; history: GenerationStats[]
  best_chromosome: { genes?: number[] } | null; chromosome_path: string | null
}

export interface SimulationResult {
  session_id: string; content_title: string; content_duration_minutes: number
  decisions: Array<{
    break_minute: number; ad_id: string; ad_category: string
    ad_duration: number; decision: string; combined_score: number
    user_advocate_score: number; advertiser_advocate_score: number
    reasoning: string; fatigue_at_break: number; ads_shown_before: number
  }>
  summary: { total_breaks: number; ads_shown: number; final_fatigue: number; decision_counts: Record<string, number> }
  chromosome_genes: number[]
}

// API helpers
export const dataApi = {
  getUsers: (limit = 1000) => api.get<{ users: User[]; total: number }>(`/users?limit=${limit}`),
  getUser: (id: number) => api.get<User>(`/users/${id}`),
  getAds: (limit = 200) => api.get<{ ads: Ad[]; total: number }>(`/ads?limit=${limit}`),
  getContent: (limit = 300) => api.get<{ content: ContentItem[]; total: number }>(`/content?limit=${limit}`),
  health: () => api.get('/health'),
}

export const evolveApi = {
  start: (maxGenerations = 50, seed = Math.floor(Math.random() * 100000)) =>
    api.post<{ job_id: string; status: string }>('/evolve', { max_generations: maxGenerations, seed }),
  status: (jobId: string) => api.get<EvolutionJob>(`/evolve/${jobId}`),
  stop: (jobId: string) => api.post(`/evolve/${jobId}/stop`),
  listChromosomes: () => api.get<{ chromosomes: Array<{ path: string; filename: string; fitness: number; saved_at: string; genes: number[] }> }>('/chromosomes'),
  loadBest: () => api.post('/chromosome/load', {}),
  setChromosome: (genes: number[]) => api.post('/chromosome/set', genes),
}

export const decideApi = {
  decide: (params: {
    user_id: number; ad_id: string; time_of_day?: string; season?: string
    ads_shown_this_session?: number; session_fatigue?: number
    content_id?: number; current_minute?: number; is_binging?: boolean; use_llm?: boolean
  }) => api.post<DecisionResult>('/decide', params),
  batch: (params: { ad_id: string; time_of_day?: string; season?: string; ads_shown_this_session?: number; session_fatigue?: number }) =>
    api.post<{ ad_id: string; total_users: number; decision_counts: Record<string, number>; results: Array<{ user_id: number; user_name: string; age_group: string; decision: string; combined_score: number }> }>('/decide/batch', params),
}

export const simulateApi = {
  session: (params: { user_id: number; content_id: number; time_of_day?: string; season?: string; use_llm?: boolean }) =>
    api.post<SimulationResult>('/simulate/session', params),
}

export const abApi = {
  start: (params?: { user_id?: number; content_id?: number; seed?: number }) =>
    api.post<{ session_id: string; user_name: string; content_title: string; session_x: unknown[]; session_y: unknown[] }>('/ab/start', params || {}),
  startCustom: (params: {
    person_name: string; age_group: string; country: string
    interests: string[]; ad_tolerance: number
    show_title: string; show_genre: string; show_duration_minutes: number; is_series: boolean
    seed?: number
  }) =>
    api.post<{ session_id: string; user_name: string; content_title: string; session_x: unknown[]; session_y: unknown[] }>('/ab/custom', params),
  rate: (sessionId: string, params: { session_label: string; annoyance: number; relevance: number; willingness: number; notes?: string }) =>
    api.post(`/ab/${sessionId}/rate`, params),
  results: () => api.get('/ab/results'),
  session: (sessionId: string) => api.get(`/ab/${sessionId}`),
}

export const experimentApi = {
  run: (params: { num_runs?: number; max_generations?: number; num_users?: number }) =>
    api.post('/experiments/run', params),
  status: (jobId: string) => api.get(`/experiments/${jobId}`),
  sensitivity: (chromosome_genes?: number[]) =>
    api.post('/experiments/sensitivity', { chromosome_genes }),
}
