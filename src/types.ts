export type Difficulty = 'easy' | 'medium' | 'hard'

export interface ExamOption {
  id: string
  text: string
}

export interface ExamQuestion {
  id: string
  prompt: string
  explanation?: string
  topic: string
  difficulty: Difficulty
  scoreValue?: number
  timeLimitSec?: number
  options: ExamOption[]
  correctOptionId: string
}

export interface Exam {
  id: string
  title: string
  description: string
  subject: string
  subjectColor?: string
  durationMinutes: number
  effectiveDurationMinutes?: number
  effectiveDurationSeconds?: number
  passingScore: number
  questions: ExamQuestion[]
}

export interface Attempt {
  id: string
  examId: string
  examTitle: string
  userName: string
  startedAt: string
  finishedAt: string
  score: number
  scoringPoints?: number
  maxScoringPoints?: number
  total: number
  durationSeconds: number
}

export interface SprintResult {
  id: string
  userName: string
  score: number
  total: number
  startedAt: string
  finishedAt: string
}

export interface LearningRecord {
  id: string
  attemptId: string
  questionId: string
  topic: string
  prompt: string
  options: ExamOption[]
  correctOptionId: string
  selectedOptionId: string
  isCorrect: boolean
  createdAt: string
}

