import type { Attempt, Exam, SprintResult } from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api'

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

const get = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

const post = async <T>(path: string, payload: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

