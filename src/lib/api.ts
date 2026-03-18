import type {
  Attempt,
  DutyAssignment,
  Exam,
  Quest,
  QuestLeaderboardEntry,
  QuestProfile,
  SprintResult,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api'

interface ApiExam {
  id: number
  title: string
  description: string
  subject: string
  subject_color?: string
  duration_minutes: number
  effective_duration_minutes?: number
  effective_duration_seconds?: number
  passing_score: number
  questions: Array<{
    id: number
    prompt: string
    explanation: string
    topic: string
    difficulty: 'easy' | 'medium' | 'hard'
    score_value: number
    time_limit_sec?: number | null
    order: number
    options: Array<{ id: number; text: string; order: number }>
  }>
}

interface SubmitPayload {
  user_name: string
  started_at?: string
  duration_seconds: number
  answers: Record<string, number>
}

export interface SubmitResponse {
  attempt: {
    id: number
    exam: number
    exam_title: string
    user_name: string
    started_at: string
    finished_at: string
    score: number
    scoring_points: number
    max_scoring_points: number
    correct_count: number
    total_questions: number
    duration_seconds: number
  }
  exam_title: string
  passing_score: number
  reviews: Array<{
    question_id: number
    prompt: string
    topic: string
    explanation: string
    score_value: number
    selected_option_id: number | null
    selected_text: string
    correct_option_id: number
    correct_text: string
    is_correct: boolean
  }>
}

const getAuthHeaders = (): Record<string, string> => {
  const userName = localStorage.getItem('pet-user-name')?.trim() ?? ''
  const userPhone = localStorage.getItem('pet-user-phone')?.trim() ?? ''
  if (!userName || !userPhone) {
    return {}
  }
  return {
    'X-User-Name': encodeURIComponent(userName),
    'X-User-Phone': userPhone,
  }
}

const get = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

const post = async <T>(path: string, payload: unknown): Promise<T> => {
  const authHeaders = getAuthHeaders()
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

const mapExam = (exam: ApiExam): Exam => ({
  id: String(exam.id),
  title: exam.title,
  description: exam.description,
  subject: exam.subject,
  subjectColor: exam.subject_color || '#2563eb',
  durationMinutes: exam.effective_duration_minutes ?? exam.duration_minutes,
  effectiveDurationMinutes: exam.effective_duration_minutes,
  effectiveDurationSeconds: exam.effective_duration_seconds,
  passingScore: exam.passing_score,
  questions: exam.questions
    .slice()
    .sort((a, b) => a.order - b.order)
    .filter((question) => question.options.length > 0)
    .map((question) => ({
      id: String(question.id),
      prompt: question.prompt,
      explanation: question.explanation,
      topic: question.topic,
      difficulty: question.difficulty,
      scoreValue: question.score_value,
      timeLimitSec: question.time_limit_sec ?? undefined,
      options: question.options
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((option) => ({ id: String(option.id), text: option.text })),
      correctOptionId: '',
    })),
})

export const fetchExams = async (): Promise<Exam[]> => {
  const list = await get<Array<{ id: number }>>('/exams/')
  const details = await Promise.all(list.map((item) => get<ApiExam>(`/exams/${item.id}/`)))
  return details.map(mapExam)
}

export const submitAttempt = async (examId: string, payload: SubmitPayload): Promise<SubmitResponse> =>
  post<SubmitResponse>(`/exams/${examId}/submit/`, payload)

export const fetchAttempts = async (): Promise<Attempt[]> => {
  const data = await get<
    Array<{
      id: number
      exam: number
      exam_title: string
      user_name: string
      started_at: string
      finished_at: string
      score: number
      scoring_points: number
      max_scoring_points: number
      total_questions: number
      duration_seconds: number
    }>
  >('/stats/attempts/')

  return data.map((item) => ({
    id: String(item.id),
    examId: String(item.exam),
    examTitle: item.exam_title,
    userName: item.user_name,
    startedAt: item.started_at,
    finishedAt: item.finished_at,
    score: item.score,
    scoringPoints: item.scoring_points,
    maxScoringPoints: item.max_scoring_points,
    total: item.total_questions,
    durationSeconds: item.duration_seconds,
  }))
}

export const fetchUserStats = async (): Promise<
  Array<{ user_name: string; attempts_count: number; best_score: number; avg_score: number }>
> => get('/stats/users/')

export const fetchSprintResults = async (): Promise<SprintResult[]> => []

interface ApiQuest {
  id: number
  title: string
  description: string
  category: string
  repeat: 'daily' | 'once'
  reward_exp: number
  reward_rub_cents: number
  requires_approval: boolean
  requires_proof: boolean
  is_active: boolean
  completed: boolean
  completed_at?: string | null
  submission_status?: 'pending' | 'approved' | 'rejected' | null
  submission_id?: number | null
  submitted_at?: string | null
  reviewed_at?: string | null
  review_comment?: string | null
}

interface ApiQuestProfile {
  user_name: string
  exp: number
  rub_cents: number
  completed_today: number
}

const mapQuest = (item: ApiQuest): Quest => ({
  id: String(item.id),
  title: item.title,
  description: item.description,
  category: item.category || '',
  repeat: item.repeat,
  rewardExp: item.reward_exp ?? 0,
  rewardRubCents: item.reward_rub_cents ?? 0,
  requiresApproval: item.requires_approval,
  requiresProof: item.requires_proof,
  isActive: item.is_active,
  completed: Boolean(item.completed),
  completedAt: item.completed_at ?? null,
  submissionStatus: item.submission_status ?? null,
  submissionId: item.submission_id ?? null,
  submittedAt: item.submitted_at ?? null,
  reviewedAt: item.reviewed_at ?? null,
  reviewComment: item.review_comment ?? null,
})

export const fetchQuestProfile = async (userName: string): Promise<QuestProfile> => {
  const data = await get<ApiQuestProfile>(`/quests/profile/?user_name=${encodeURIComponent(userName)}`)
  return {
    userName: data.user_name,
    exp: data.exp,
    rubCents: data.rub_cents,
    completedToday: data.completed_today,
  }
}

export const requestCallCheck = async (payload: {
  userName: string
  phone: string
}): Promise<{ sent: boolean; expires_in: number; call_phone?: string; call_phone_pretty?: string }> =>
  post('/auth/request_call/', { user_name: payload.userName, phone: payload.phone })

export const verifyCallCheck = async (payload: {
  userName: string
  phone: string
}): Promise<{ verified: boolean; status?: 'pending' | 'expired' | 'error' }> =>
  post('/auth/check_call/', { user_name: payload.userName, phone: payload.phone })

export const fetchQuests = async (userName: string): Promise<Quest[]> => {
  const data = await get<ApiQuest[]>(`/quests/?user_name=${encodeURIComponent(userName)}`)
  return data.map(mapQuest)
}

export const completeQuest = async (
  questId: string,
  payload: { userName: string; businessDate?: string; notes?: string }
): Promise<{
  created: boolean
  exp: number
  rub_cents: number
  completion: { id: number; quest_id: number; business_date: string; completed_at: string }
}> => {
  const body = {
    user_name: payload.userName,
    business_date: payload.businessDate,
    notes: payload.notes,
  }
  return post(`/quests/${questId}/complete/`, body)
}

export const submitQuest = async (
  questId: string,
  payload: { userName: string; businessDate?: string; notes?: string; proofImage?: File | null }
): Promise<{
  created: boolean
  submission: { id: number; status: string; business_date: string; created_at: string }
}> => {
  const form = new FormData()
  form.set('user_name', payload.userName)
  if (payload.businessDate) {
    form.set('business_date', payload.businessDate)
  }
  if (payload.notes) {
    form.set('notes', payload.notes)
  }
  if (payload.proofImage) {
    form.set('proof_image', payload.proofImage)
  }

  const response = await fetch(`${API_BASE}/quests/${questId}/submit/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: form,
  })
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }
  return (await response.json()) as {
    created: boolean
    submission: { id: number; status: string; business_date: string; created_at: string }
  }
}

export const fetchQuestLeaderboard = async (top = 25): Promise<QuestLeaderboardEntry[]> => {
  const data = await get<Array<{ user_name: string; exp: number; rub_cents: number }>>(`/quests/leaderboard/?top=${top}`)
  return data.map((item) => ({ userName: item.user_name, exp: item.exp, rubCents: item.rub_cents }))
}

export const fetchDuties = async ({
  dutyType = 'cleaning',
  from,
  days = 7,
}: {
  dutyType?: 'cleaning'
  from?: string
  days?: number
}): Promise<DutyAssignment[]> => {
  const params = new URLSearchParams()
  params.set('duty_type', dutyType)
  if (from) params.set('from', from)
  if (days) params.set('days', String(days))
  const data = await get<Array<{ id: number; duty_type: 'cleaning'; business_date: string; user_name: string; notes: string }>>(
    `/duties/?${params.toString()}`
  )
  return data.map((item) => ({
    id: String(item.id),
    dutyType: item.duty_type,
    businessDate: item.business_date,
    userName: item.user_name,
    notes: item.notes,
  }))
}
