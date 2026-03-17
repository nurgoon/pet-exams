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

export interface QuestProfile {
  userName: string
  exp: number
  rubCents: number
  completedToday: number
}

export interface Quest {
  id: string
  title: string
  description: string
  category?: string
  repeat: 'daily' | 'once'
  rewardExp: number
  rewardRubCents: number
  requiresApproval: boolean
  requiresProof: boolean
  isActive: boolean
  completed: boolean
  completedAt?: string | null
  submissionStatus?: 'pending' | 'approved' | 'rejected' | null
  submissionId?: string | number | null
  submittedAt?: string | null
  reviewedAt?: string | null
  reviewComment?: string | null
}

export interface QuestLeaderboardEntry {
  userName: string
  exp: number
  rubCents: number
}

export interface DutyAssignment {
  id: string
  dutyType: 'cleaning'
  businessDate: string
  userName: string
  notes: string
}
