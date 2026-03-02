import type { Attempt, Exam, LearningRecord, SprintResult } from '../types'

const attemptsKey = 'pet-exam-attempts'
const sprintKey = 'pet-sprint-results'
const examsKey = 'pet-exams-bank'
const learningKey = 'pet-learning-records'

const parse = <T>(raw: string | null): T[] => {
  if (!raw) {
    return []
  }

  try {
    const data = JSON.parse(raw)
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

export const loadAttempts = (): Attempt[] => parse<Attempt>(localStorage.getItem(attemptsKey))

export const saveAttempt = (attempt: Attempt): Attempt[] => {
  const attempts = [attempt, ...loadAttempts()]
  localStorage.setItem(attemptsKey, JSON.stringify(attempts))
  return attempts
}

export const loadSprintResults = (): SprintResult[] => parse<SprintResult>(localStorage.getItem(sprintKey))

export const saveSprintResult = (result: SprintResult): SprintResult[] => {
  const results = [result, ...loadSprintResults()]
  localStorage.setItem(sprintKey, JSON.stringify(results))
  return results
}

export const loadExamBank = (): Exam[] => parse<Exam>(localStorage.getItem(examsKey))

export const saveExamBank = (exams: Exam[]): Exam[] => {
  localStorage.setItem(examsKey, JSON.stringify(exams))
  return exams
}

export const resetExamBank = (): void => {
  localStorage.removeItem(examsKey)
}

export const loadLearningRecords = (): LearningRecord[] => parse<LearningRecord>(localStorage.getItem(learningKey))

export const saveLearningRecords = (records: LearningRecord[]): LearningRecord[] => {
  const next = [...records, ...loadLearningRecords()]
  localStorage.setItem(learningKey, JSON.stringify(next))
  return next
}
