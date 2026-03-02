<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  loadLearningRecords,
  loadSprintResults,
  saveLearningRecords,
  saveSprintResult,
} from './lib/storage'
import { fetchAttempts, fetchExams, fetchUserStats, submitAttempt } from './lib/api'
import { exams as seedExams } from './data/exams'
import type { Attempt, Exam, ExamQuestion, LearningRecord, SprintResult } from './types'

type Tab = 'catalog' | 'leaderboard' | 'sprint' | 'learning'
type ReviewFilter = 'all' | 'wrong' | 'correct'
type Theme = 'light' | 'dark'
interface ExamReviewItem {
  questionNumber: number
  questionId: string
  topic: string
  prompt: string
  explanation: string
  scoreValue: number
  selectedText: string
  correctText: string
  isCorrect: boolean
}

interface ExamReview {
  attempt: Attempt
  examTitle: string
  passingScore: number
  scoringPoints: number
  maxScoringPoints: number
  correctCount: number
  total: number
  items: ExamReviewItem[]
}

const tab = ref<Tab>('catalog')
const storedUserName = localStorage.getItem('pet-user-name')?.trim() ?? ''
const userName = ref(storedUserName || 'Student')
const selectedSubject = ref('all')
const onboardingDone = ref(localStorage.getItem('pet-onboarding-done') === '1')
const onboardingName = ref(storedUserName)
const onboardingAccepted = ref(false)
const rawTheme = localStorage.getItem('pet-theme')
const theme = ref<Theme>(rawTheme === 'light' || rawTheme === 'dark' ? rawTheme : 'dark')

const attempts = ref<Attempt[]>([])
const sprintResults = ref<SprintResult[]>(loadSprintResults())
const learningRecords = ref<LearningRecord[]>(loadLearningRecords())
const examBank = ref<Exam[]>([])
const userStats = ref<Array<{ user_name: string; attempts_count: number; best_score: number; avg_score: number }>>([])
const dataLoadError = ref<string | null>(null)
const examSubmitError = ref<string | null>(null)

const activeExam = ref<Exam | null>(null)
const questionIndex = ref(0)
const answers = ref<Record<string, string>>({})
const examStartedAt = ref<number | null>(null)
const examElapsedSeconds = ref(0)
const lastAttempt = ref<Attempt | null>(null)
const examReview = ref<ExamReview | null>(null)
const reviewFilter = ref<ReviewFilter>('all')
const expandedReviewIds = ref<string[]>([])
const isFinishingExam = ref(false)
const learningQueue = ref<LearningRecord[]>([])
const learningIndex = ref(0)
const learningSelectedOptionId = ref<string | null>(null)
const learningAnswered = ref(0)
const learningCorrect = ref(0)
const learningFinished = ref(false)

const sprintDurationSeconds = 60
const sprintActive = ref(false)
const sprintTimeLeft = ref(sprintDurationSeconds)
const sprintScore = ref(0)
const sprintAnswered = ref(0)
const sprintQuestion = ref<ExamQuestion | null>(null)

let examTimer: number | undefined
let sprintTimer: number | undefined

const allQuestions = computed(() => examBank.value.flatMap((exam) => exam.questions))
const subjects = computed(() => ['all', ...new Set(examBank.value.map((exam) => exam.subject))])

const filteredExams = computed(() => {
  if (selectedSubject.value === 'all') {
    return examBank.value
  }

  return examBank.value.filter((exam) => exam.subject === selectedSubject.value)
})

const currentQuestion = computed(() => {
  if (!activeExam.value) {
    return null
  }

  return activeExam.value.questions[questionIndex.value] ?? null
})

const committedAnsweredCount = computed(() => {
  if (!activeExam.value) {
    return 0
  }

  const committedIds = activeExam.value.questions.slice(0, questionIndex.value).map((question) => question.id)
  return committedIds.reduce((sum, questionId) => sum + (answers.value[questionId] ? 1 : 0), 0)
})

const progress = computed(() => {
  if (!activeExam.value) {
    return 0
  }

  return Math.round((committedAnsweredCount.value / activeExam.value.questions.length) * 100)
})

const examTimeLeft = computed(() => {
  if (!activeExam.value) {
    return 0
  }

  const total = activeExam.value.durationMinutes * 60
  return Math.max(total - examElapsedSeconds.value, 0)
})

const leaderboard = computed(() => {
  if (userStats.value.length) {
    return userStats.value.map((item) => ({
      name: item.user_name,
      best: item.best_score,
      avg: Math.round(item.avg_score),
      attempts: item.attempts_count,
    }))
  }

  const grouped = attempts.value.reduce<Record<string, Attempt[]>>((acc, attempt) => {
    const key = attempt.userName
    const bucket = acc[key] ?? []
    bucket.push(attempt)
    acc[key] = bucket
    return acc
  }, {})

  return Object.entries(grouped)
    .map(([name, userAttempts]) => {
      const best = Math.max(...userAttempts.map((item) => item.score))
      const avg = Math.round(userAttempts.reduce((sum, item) => sum + item.score, 0) / userAttempts.length)
      return { name, best, avg, attempts: userAttempts.length }
    })
    .sort((a, b) => b.best - a.best || b.avg - a.avg)
})

const topSprintResults = computed(() =>
  [...sprintResults.value].sort((a, b) => b.score - a.score || b.total - a.total).slice(0, 8),
)

const filteredReviewItems = computed(() => {
  if (!examReview.value) {
    return []
  }

  if (reviewFilter.value === 'wrong') {
    return examReview.value.items.filter((item) => !item.isCorrect)
  }

  if (reviewFilter.value === 'correct') {
    return examReview.value.items.filter((item) => item.isCorrect)
  }

  return examReview.value.items
})

const weakTopics = computed(() => {
  if (!examReview.value) {
    return []
  }

  const grouped = examReview.value.items.reduce<Record<string, number>>((acc, item) => {
    if (item.isCorrect) {
      return acc
    }

    acc[item.topic] = (acc[item.topic] ?? 0) + 1
    return acc
  }, {})

  return Object.entries(grouped)
    .map(([topic, wrong]) => ({ topic, wrong }))
    .sort((a, b) => b.wrong - a.wrong)
})

const onboardingIcon = {
  src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-UcGo0Y7L4WfuBuX4pSAc1LnhyGgUlu.png',
  alt: 'Onboarding icon',
}

const resultStatus = computed(() => {
  if (!examReview.value) {
    return null
  }

  const passed = examReview.value.attempt.score >= examReview.value.passingScore
  return passed
    ? {
        label: 'Статус: Пройдено',
        icon: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-BwtahaCLSoUOyWdITnlPCNiwzCLUdL.png',
        tone: 'pass',
      }
    : {
        label: 'Статус: Не пройдено',
        icon: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-FSCFWX0DBeBr8jibfvCV3ikItvT0BX.png',
        tone: 'fail',
      }
})

const learningErrorPool = computed(() => {
  const latestByQuestion = new Map<string, LearningRecord>()
  for (const record of learningRecords.value) {
    if (!latestByQuestion.has(record.questionId)) {
      latestByQuestion.set(record.questionId, record)
    }
  }

  return [...latestByQuestion.values()].filter((record) => !record.isCorrect)
})

const currentLearningQuestion = computed(() => learningQueue.value[learningIndex.value] ?? null)

const isExpanded = (questionId: string): boolean => expandedReviewIds.value.includes(questionId)

const toggleReviewItem = (questionId: string): void => {
  if (isExpanded(questionId)) {
    expandedReviewIds.value = expandedReviewIds.value.filter((id) => id !== questionId)
    return
  }

  expandedReviewIds.value = [...expandedReviewIds.value, questionId]
}

const startLearningByErrors = (): void => {
  learningQueue.value = shuffle(learningErrorPool.value)
  learningIndex.value = 0
  learningSelectedOptionId.value = null
  learningAnswered.value = 0
  learningCorrect.value = 0
  learningFinished.value = learningQueue.value.length === 0
}

const answerLearningQuestion = (optionId: string): void => {
  if (!currentLearningQuestion.value || learningSelectedOptionId.value) {
    return
  }

  learningSelectedOptionId.value = optionId
  learningAnswered.value += 1
  const isCorrect = currentLearningQuestion.value.correctOptionId === optionId
  if (isCorrect) {
    learningCorrect.value += 1
  }

  const record: LearningRecord = {
    id: createId(),
    attemptId: `learning-${Date.now()}`,
    questionId: currentLearningQuestion.value.questionId,
    topic: currentLearningQuestion.value.topic,
    prompt: currentLearningQuestion.value.prompt,
    options: currentLearningQuestion.value.options,
    correctOptionId: currentLearningQuestion.value.correctOptionId,
    selectedOptionId: optionId,
    isCorrect,
    createdAt: new Date().toISOString(),
  }

  learningRecords.value = saveLearningRecords([record])
}

const nextLearningQuestion = (): void => {
  if (learningIndex.value >= learningQueue.value.length - 1) {
    learningFinished.value = true
    return
  }

  learningIndex.value += 1
  learningSelectedOptionId.value = null
}

const applyTheme = (value: Theme): void => {
  document.documentElement.setAttribute('data-theme', value)
  localStorage.setItem('pet-theme', value)
}

const toggleTheme = (): void => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

const completeOnboarding = (): void => {
  const normalized = onboardingName.value.trim()
  if (!normalized || !onboardingAccepted.value) {
    return
  }

  userName.value = normalized
  onboardingDone.value = true
  localStorage.setItem('pet-user-name', normalized)
  localStorage.setItem('pet-onboarding-done', '1')
}

const loadBackendData = async (): Promise<void> => {
  dataLoadError.value = null

  try {
    const remoteExams = await fetchExams()
    examBank.value = remoteExams
  } catch {
    const useSeedInDev = import.meta.env.DEV && import.meta.env.VITE_USE_SEED_EXAMS === '1'
    examBank.value = useSeedInDev ? seedExams : []
    attempts.value = []
    userStats.value = []
    dataLoadError.value = useSeedInDev
      ? 'Не удалось загрузить экзамены из API. Включены локальные заглушки (VITE_USE_SEED_EXAMS=1).'
      : 'Не удалось загрузить экзамены из API. Проверьте backend (/api).'
    return
  }

  const [remoteAttempts, remoteStats] = await Promise.allSettled([fetchAttempts(), fetchUserStats()])

  if (remoteAttempts.status === 'fulfilled') {
    attempts.value = remoteAttempts.value
  } else {
    attempts.value = []
    dataLoadError.value = 'Экзамены загружены, но статистика попыток сейчас недоступна.'
  }

  if (remoteStats.status === 'fulfilled') {
    userStats.value = remoteStats.value
  } else {
    userStats.value = []
    if (!dataLoadError.value) {
      dataLoadError.value = 'Экзамены загружены, но статистика пользователей сейчас недоступна.'
    }
  }
}

const formatSeconds = (value: number): string => {
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

const formatDate = (value: string): string =>
  new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))

const shuffle = <T>(items: T[]): T[] => {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const current = copy[i] as T
    copy[i] = copy[j] as T
    copy[j] = current
  }
  return copy
}

const createId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const getExamStats = (examId: string) => {
  const items = attempts.value.filter((attempt) => attempt.examId === examId)
  if (!items.length) {
    return { tries: 0, best: 0 }
  }

  return {
    tries: items.length,
    best: Math.max(...items.map((item) => item.score)),
  }
}

const getSubjectBadgeStyle = (exam: Exam): Record<string, string> => {
  const color = exam.subjectColor && /^#[0-9a-fA-F]{6}$/.test(exam.subjectColor) ? exam.subjectColor : '#2563eb'
  return { '--subject-color': color }
}

const subjectIcons: Record<string, { src: string; alt: string; source: string }> = {
  Frontend: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-GNGLsMOruOXjdF1rtx2ajfpU3YzrIS.png',
    alt: 'Code icon',
    source: 'https://www.thiings.co/things/code',
  },
  Backend: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-rgJwkWTrzrocDwMgi5sD0jwpdnH5Ot.png',
    alt: 'Database icon',
    source: 'https://www.thiings.co/things/database-icon',
  },
  QA: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-Ugm39CKBkd5PT6FpJkgvrkeKQmGBfZ.png',
    alt: 'Bug viewer icon',
    source: 'https://www.thiings.co/things/bug-viewer',
  },
  Безопасность: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-5i9EDsbgEZk9k7NBeKt3ImNXkx0F66.png',
    alt: 'Shield icon',
    source: 'https://www.thiings.co/things/blue-shield',
  },
  Сервис: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-UcGo0Y7L4WfuBuX4pSAc1LnhyGgUlu.png',
    alt: 'E-learning icon',
    source: 'https://www.thiings.co/things/e-learning',
  },
  Инфобез: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-5i9EDsbgEZk9k7NBeKt3ImNXkx0F66.png',
    alt: 'Security icon',
    source: 'https://www.thiings.co/things/blue-shield',
  },
  Операции: {
    src: 'https://lftz25oez4aqbxpq.public.blob.vercel-storage.com/image-73pNGHJBFF75t0zRsAgQInW9DAM4vd.png',
    alt: 'Bar chart icon',
    source: 'https://www.thiings.co/things/bar-chart',
  },
}

const getExamIcon = (exam: Exam) => subjectIcons[exam.subject]

const startExam = (exam: Exam): void => {
  if (exam.questions.length === 0) {
    return
  }

  activeExam.value = exam
  questionIndex.value = 0
  answers.value = {}
  examElapsedSeconds.value = 0
  examStartedAt.value = Date.now()
  examSubmitError.value = null
  lastAttempt.value = null
  examReview.value = null
  reviewFilter.value = 'all'
  expandedReviewIds.value = []

  clearInterval(examTimer)
  examTimer = window.setInterval(() => {
    examElapsedSeconds.value += 1
    if (examTimeLeft.value === 0) {
      finishExam()
    }
  }, 1000)
}

const cancelExam = (): void => {
  activeExam.value = null
  questionIndex.value = 0
  answers.value = {}
  examElapsedSeconds.value = 0
  examSubmitError.value = null
  clearInterval(examTimer)
}

const answerQuestion = (questionId: string, optionId: string): void => {
  answers.value = { ...answers.value, [questionId]: optionId }
}

const nextQuestion = (): void => {
  if (!activeExam.value) {
    return
  }

  if (questionIndex.value < activeExam.value.questions.length - 1) {
    questionIndex.value += 1
  }
}

const previousQuestion = (): void => {
  if (questionIndex.value > 0) {
    questionIndex.value -= 1
  }
}

const finishExam = async (): Promise<void> => {
  if (!activeExam.value || !examStartedAt.value || isFinishingExam.value) {
    return
  }

  isFinishingExam.value = true
  examSubmitError.value = null
  clearInterval(examTimer)
  let shouldCloseSession = true

  const exam = activeExam.value
  const payloadAnswers = Object.entries(answers.value).reduce<Record<string, number>>((acc, [questionId, optionId]) => {
    const parsed = Number(optionId)
    if (!Number.isNaN(parsed)) {
      acc[questionId] = parsed
    }
    return acc
  }, {})

  try {
    const result = await submitAttempt(exam.id, {
      user_name: userName.value.trim() || 'Student',
      started_at: new Date(examStartedAt.value).toISOString(),
      duration_seconds: examElapsedSeconds.value,
      answers: payloadAnswers,
    })

    const attempt: Attempt = {
      id: String(result.attempt.id),
      examId: String(result.attempt.exam),
      examTitle: result.attempt.exam_title,
      userName: result.attempt.user_name,
      startedAt: result.attempt.started_at,
      finishedAt: result.attempt.finished_at,
      score: result.attempt.score,
      scoringPoints: result.attempt.scoring_points,
      maxScoringPoints: result.attempt.max_scoring_points,
      total: result.attempt.total_questions,
      durationSeconds: result.attempt.duration_seconds,
    }

    attempts.value = [attempt, ...attempts.value]
    try {
      userStats.value = await fetchUserStats()
    } catch {
      // Do not break exam submit flow if stats endpoint is temporarily unavailable.
    }
    lastAttempt.value = attempt

    const questionById = new Map(exam.questions.map((question) => [Number(question.id), question]))
    learningRecords.value = saveLearningRecords(
      result.reviews.map((review) => {
        const question = questionById.get(review.question_id)
        const selectedOptionId = review.selected_option_id ? String(review.selected_option_id) : ''
        return {
          id: createId(),
          attemptId: String(result.attempt.id),
          questionId: String(review.question_id),
          topic: review.topic,
          prompt: review.prompt,
          options: question?.options ?? [],
          correctOptionId: String(review.correct_option_id),
          selectedOptionId,
          isCorrect: review.is_correct,
          createdAt: result.attempt.finished_at,
        }
      }),
    )

    examReview.value = {
      attempt,
      examTitle: result.exam_title,
      passingScore: result.passing_score,
      scoringPoints: result.attempt.scoring_points,
      maxScoringPoints: result.attempt.max_scoring_points,
      correctCount: result.attempt.correct_count,
      total: result.attempt.total_questions,
      items: result.reviews.map((review, index) => ({
        questionNumber: index + 1,
        questionId: String(review.question_id),
        topic: review.topic,
        prompt: review.prompt,
        explanation: review.explanation,
        scoreValue: review.score_value,
        selectedText: review.selected_text,
        correctText: review.correct_text,
        isCorrect: review.is_correct,
      })),
    }

    reviewFilter.value = result.attempt.correct_count === result.attempt.total_questions ? 'all' : 'wrong'
    const firstWrong = result.reviews.find((review) => !review.is_correct)
    expandedReviewIds.value = firstWrong ? [String(firstWrong.question_id)] : []
  } catch {
    // Fallback to local static data if API is unavailable.
    const hasLocalCorrectAnswers = exam.questions.every((question) => Boolean(question.correctOptionId))
    const correct = exam.questions.reduce((sum, question) => {
      return sum + (answers.value[question.id] === question.correctOptionId ? 1 : 0)
    }, 0)
    const score = Math.round((correct / exam.questions.length) * 100)
    const attempt: Attempt = {
      id: createId(),
      examId: exam.id,
      examTitle: exam.title,
      userName: userName.value.trim() || 'Student',
      startedAt: new Date(examStartedAt.value).toISOString(),
      finishedAt: new Date().toISOString(),
      score,
      scoringPoints: exam.questions.reduce(
        (sum, question) => sum + (answers.value[question.id] === question.correctOptionId ? question.scoreValue ?? 1 : 0),
        0,
      ),
      maxScoringPoints: exam.questions.reduce((sum, question) => sum + (question.scoreValue ?? 1), 0),
      total: exam.questions.length,
      durationSeconds: examElapsedSeconds.value,
    }
    attempts.value = [attempt, ...attempts.value]
    lastAttempt.value = attempt

    if (hasLocalCorrectAnswers) {
      const reviewItems = exam.questions.map((question, index) => {
        const selectedId = answers.value[question.id]
        const selectedText = question.options.find((option) => option.id === selectedId)?.text ?? 'Не выбран'
        const correctText =
          question.options.find((option) => option.id === question.correctOptionId)?.text ?? 'Не задан'
        return {
          questionNumber: index + 1,
          questionId: question.id,
          topic: question.topic,
          prompt: question.prompt,
          explanation: question.explanation ?? `Верный вариант: ${correctText}`,
          scoreValue: question.scoreValue ?? 1,
          selectedText,
          correctText,
          isCorrect: selectedId === question.correctOptionId,
        }
      })

      examReview.value = {
        attempt,
        examTitle: exam.title,
        passingScore: exam.passingScore,
        scoringPoints: attempt.scoringPoints ?? 0,
        maxScoringPoints: attempt.maxScoringPoints ?? 0,
        correctCount: correct,
        total: exam.questions.length,
        items: reviewItems,
      }

      reviewFilter.value = correct === exam.questions.length ? 'all' : 'wrong'
      const firstWrong = reviewItems.find((item) => !item.isCorrect)
      expandedReviewIds.value = firstWrong ? [firstWrong.questionId] : []
    } else {
      examSubmitError.value = 'Не удалось отправить результаты в API. Проверь backend и нажми "Завершить" еще раз.'
      shouldCloseSession = false
    }
  }

  if (!shouldCloseSession) {
    isFinishingExam.value = false
    return
  }

  activeExam.value = null
  questionIndex.value = 0
  answers.value = {}
  examElapsedSeconds.value = 0
  isFinishingExam.value = false
}

const nextSprintQuestion = (): void => {
  const questions = allQuestions.value
  const index = Math.floor(Math.random() * questions.length)
  sprintQuestion.value = questions[index] ?? null
}

const startSprint = (): void => {
  if (allQuestions.value.length === 0) {
    return
  }

  sprintActive.value = true
  sprintTimeLeft.value = sprintDurationSeconds
  sprintScore.value = 0
  sprintAnswered.value = 0
  nextSprintQuestion()

  clearInterval(sprintTimer)
  sprintTimer = window.setInterval(() => {
    sprintTimeLeft.value -= 1
    if (sprintTimeLeft.value <= 0) {
      finishSprint()
    }
  }, 1000)
}

const answerSprint = (optionId: string): void => {
  if (!sprintActive.value || !sprintQuestion.value) {
    return
  }

  sprintAnswered.value += 1
  if (sprintQuestion.value.correctOptionId === optionId) {
    sprintScore.value += 1
  }

  nextSprintQuestion()
}

const finishSprint = (): void => {
  if (!sprintActive.value) {
    return
  }

  clearInterval(sprintTimer)
  sprintActive.value = false

  const result: SprintResult = {
    id: createId(),
    userName: userName.value.trim() || 'Student',
    score: sprintScore.value,
    total: sprintAnswered.value,
    startedAt: new Date(Date.now() - (sprintDurationSeconds - sprintTimeLeft.value) * 1000).toISOString(),
    finishedAt: new Date().toISOString(),
  }

  sprintResults.value = saveSprintResult(result)
}

watch(theme, (value) => applyTheme(value))
watch(userName, (value) => {
  const normalized = value.trim()
  if (normalized) {
    localStorage.setItem('pet-user-name', normalized)
  }
})

onMounted(() => {
  applyTheme(theme.value)
  void loadBackendData()
})

onBeforeUnmount(() => {
  clearInterval(examTimer)
  clearInterval(sprintTimer)
})
</script>

<template>
  <div class="app-shell">
    <section v-if="!onboardingDone" class="onboarding-wrap">
      <article class="card onboarding-card">
        <div class="onboarding-top">
          <div class="onboarding-hero">
            <img :src="onboardingIcon.src" :alt="onboardingIcon.alt" loading="lazy" />
          </div>
          <h1>Добро пожаловать</h1>
        </div>
        <p class="lead">Перед началом укажи имя и ознакомься с правилами прохождения тестов.</p>
        <label class="username-field">
          Как вас зовут
          <input v-model="onboardingName" type="text" maxlength="30" placeholder="Например, Анна" />
        </label>
        <ul class="rules-list">
          <li>У каждого теста есть таймер и порог прохождения.</li>
          <li>После завершения вы увидите детальный разбор ответов.</li>
          <li>Ошибки автоматически попадут в раздел обучения.</li>
          <li>Результаты сохраняются локально в этом браузере.</li>
        </ul>
        <label class="accept-row">
          <input v-model="onboardingAccepted" type="checkbox" />
          <span>Я ознакомился с правилами</span>
        </label>
        <button class="cta" :disabled="!onboardingName.trim() || !onboardingAccepted" @click="completeOnboarding">
          Продолжить
        </button>
      </article>
    </section>

    <div v-else>
    <div class="app-topbar">
      <span class="app-topbar-user">{{ userName }}</span>
      <button @click="toggleTheme">{{ theme === 'dark' ? 'Светлая тема' : 'Темная тема' }}</button>
    </div>
    <section v-if="tab === 'catalog' && !activeExam && examReview" class="panel-stack">
      <article class="card result-page">
        <div v-if="resultStatus" class="result-status-hero" :class="resultStatus.tone">
          <img :src="resultStatus.icon" :alt="resultStatus.label" loading="lazy" />
          <strong>{{ resultStatus.label }}</strong>
        </div>
        <h2>{{ examReview.examTitle }}: результаты</h2>
        <div class="result-overview">
          <div class="overview-item highlight">
            <span>Скоринговый балл</span>
            <strong>{{ examReview.scoringPoints }} / {{ examReview.maxScoringPoints }}</strong>
          </div>
          <div class="overview-item">
            <span>Счет</span>
            <strong>{{ examReview.attempt.score }}%</strong>
          </div>
          <div class="overview-item">
            <span>Верных</span>
            <strong>{{ examReview.correctCount }}/{{ examReview.total }}</strong>
          </div>
          <div class="overview-item">
            <span>Порог</span>
            <strong>{{ examReview.passingScore }}%</strong>
          </div>
          <div class="overview-item">
            <span>Статус</span>
            <strong :class="{ success: examReview.attempt.score >= examReview.passingScore, fail: examReview.attempt.score < examReview.passingScore }">
              {{ examReview.attempt.score >= examReview.passingScore ? 'Пройдено' : 'Не пройдено' }}
            </strong>
          </div>
          <div class="overview-item meta-item">
            <span>Время</span>
            <strong>{{ formatSeconds(examReview.attempt.durationSeconds) }}</strong>
          </div>
          <div class="overview-item meta-item">
            <span>Дата</span>
            <strong>{{ formatDate(examReview.attempt.finishedAt) }}</strong>
          </div>
        </div>
        <article class="recommend-card">
          <h3>Рекомендации для самообразования</h3>
          <p v-if="!weakTopics.length" class="muted">Ошибок нет. Попробуй усложненный тест или спринт-режим.</p>
          <ul v-else class="recommend-list">
            <li v-for="topic in weakTopics.slice(0, 3)" :key="topic.topic">
              Тема <strong>{{ topic.topic }}</strong>: {{ topic.wrong }} ошибок. Рекомендуется пройти тренировку по ошибкам.
            </li>
          </ul>
        </article>
        <div class="review-filters">
          <button :class="{ active: reviewFilter === 'all' }" @click="reviewFilter = 'all'">Все</button>
          <button :class="{ active: reviewFilter === 'wrong' }" @click="reviewFilter = 'wrong'">Только ошибки</button>
          <button :class="{ active: reviewFilter === 'correct' }" @click="reviewFilter = 'correct'">Только верные</button>
          <button @click="expandedReviewIds = filteredReviewItems.map((item) => item.questionId)">Раскрыть все</button>
          <button @click="expandedReviewIds = []">Свернуть все</button>
        </div>
        <div class="review-list">
          <p v-if="!filteredReviewItems.length" class="empty">По текущему фильтру вопросов нет.</p>
          <article
            v-for="item in filteredReviewItems"
            :key="item.questionId"
            class="review-item"
            :class="{ correct: item.isCorrect, wrong: !item.isCorrect }"
          >
            <div class="review-head">
              <p class="question-index">
                Вопрос {{ item.questionNumber }}
                <span>{{ item.topic }}</span>
              </p>
              <div class="review-head-actions">
                <span class="review-status" :class="{ correct: item.isCorrect, wrong: !item.isCorrect }">
                  {{ item.isCorrect ? 'Верно' : 'Ошибка' }}
                </span>
                <button class="review-toggle" @click="toggleReviewItem(item.questionId)">
                  {{ isExpanded(item.questionId) ? 'Скрыть' : 'Показать' }}
                </button>
              </div>
            </div>
            <h3>{{ item.prompt }}</h3>
            <div v-if="isExpanded(item.questionId)" class="answer-stack">
              <div class="answer-line correct">
                <span>Правильный:</span>
                <strong>{{ item.correctText }}</strong>
              </div>
              <div class="answer-line" :class="{ wrong: !item.isCorrect }">
                <span>Ваш ответ:</span>
                <strong>{{ item.selectedText }}</strong>
              </div>
              <div class="explanation-box">
                <span>Пояснение</span>
                <p>{{ item.explanation }}</p>
                <small>Баллы за вопрос: {{ item.scoreValue }}</small>
              </div>
            </div>
          </article>
        </div>
      </article>
      <button class="cta result-back-btn" @click="examReview = null">Обратно к тестам</button>
    </section>

    <section v-if="tab === 'catalog' && !activeExam && !examReview" class="panel-stack">
      <article v-if="lastAttempt" class="card result-card">
        <h2>{{ lastAttempt.examTitle }} завершен</h2>
        <p class="result-score" :class="{ success: lastAttempt.score >= 70 }">{{ lastAttempt.score }}%</p>
        <p>
          Время: {{ formatSeconds(lastAttempt.durationSeconds) }} · Дата: {{ formatDate(lastAttempt.finishedAt) }}
        </p>
      </article>

      <div class="catalog-toolbar card">
        <h2>Каталог экзаменов</h2>
        <p v-if="dataLoadError" class="error">{{ dataLoadError }}</p>
        <div class="chips">
          <button
            v-for="subject in subjects"
            :key="subject"
            :class="{ active: selectedSubject === subject }"
            @click="selectedSubject = subject"
          >
            {{ subject === 'all' ? 'Все направления' : subject }}
          </button>
        </div>
      </div>

      <div class="exam-grid">
        <article v-for="exam in filteredExams" :key="exam.id" class="card exam-card">
          <div v-if="getExamIcon(exam)" class="exam-icon-wrap">
            <img class="exam-icon" :src="getExamIcon(exam)?.src" :alt="getExamIcon(exam)?.alt" loading="lazy" />
          </div>
          <div class="exam-meta">
            <span class="subject-pill" :style="getSubjectBadgeStyle(exam)">{{ exam.subject }}</span>
            <span>{{ exam.durationMinutes }} мин</span>
          </div>
          <h3>{{ exam.title }}</h3>
          <p>{{ exam.description }}</p>
          <div class="exam-stats">
            <div class="exam-stat">
              <span>Вопросов</span>
              <strong>{{ exam.questions.length }}</strong>
            </div>
            <div class="exam-stat">
              <span>Порог</span>
              <strong>{{ exam.passingScore }}%</strong>
            </div>
            <div class="exam-stat">
              <span>Рекорд</span>
              <strong>{{ getExamStats(exam.id).best }}%</strong>
            </div>
          </div>
          <button class="cta" :disabled="exam.questions.length === 0" @click="startExam(exam)">
            {{ exam.questions.length === 0 ? 'Нет готовых вопросов' : 'Начать' }}
          </button>
        </article>
      </div>

      <article class="card history-card">
        <h2>Последние попытки</h2>
        <div v-if="attempts.length" class="history-list">
          <div v-for="attempt in attempts.slice(0, 6)" :key="attempt.id" class="history-item">
            <span>{{ attempt.examTitle }}</span>
            <strong>{{ attempt.score }}%</strong>
            <span>{{ attempt.userName }}</span>
            <time>{{ formatDate(attempt.finishedAt) }}</time>
          </div>
        </div>
        <p v-else class="empty">Пока нет попыток.</p>
      </article>
    </section>

    <section v-if="tab === 'catalog' && activeExam" class="panel-stack">
      <article class="card exam-session">
        <div class="session-layout">
          <div v-if="currentQuestion" :key="currentQuestion.id" class="question-block">
            <p class="question-index">
              Вопрос {{ questionIndex + 1 }} / {{ activeExam.questions.length }}
              <span>{{ currentQuestion.topic }}</span>
            </p>
            <h3>{{ currentQuestion.prompt }}</h3>

            <div class="options">
              <button
                v-for="option in currentQuestion.options"
                :key="option.id"
                :class="{ selected: answers[currentQuestion.id] === option.id }"
                @click="answerQuestion(currentQuestion.id, option.id)"
              >
                {{ option.text }}
              </button>
            </div>
          </div>

          <aside class="session-sidebar">
            <h2>{{ activeExam.title }}</h2>
            <div class="timer">{{ formatSeconds(examTimeLeft) }}</div>

            <div class="progress-row">
              <span>Прогресс</span>
              <strong>{{ progress }}%</strong>
            </div>
            <div class="progress-row">
              <span>Ответы</span>
              <strong>{{ committedAnsweredCount }}/{{ activeExam.questions.length }}</strong>
            </div>
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
            </div>

            <div class="session-actions">
              <button :disabled="questionIndex === 0" @click="previousQuestion">Назад</button>
              <button
                v-if="questionIndex < activeExam.questions.length - 1"
                :disabled="!currentQuestion || !answers[currentQuestion.id]"
                class="cta"
                @click="nextQuestion"
              >
                Далее
              </button>
              <button
                v-else
                :disabled="!currentQuestion"
                class="cta"
                @click="finishExam"
              >
                Завершить
              </button>
            </div>
            <p v-if="examSubmitError" class="error">{{ examSubmitError }}</p>
          </aside>
        </div>
      </article>
      <button class="cancel-link" @click="cancelExam">Отмена</button>
    </section>

    <section v-if="tab === 'learning' && !activeExam" class="panel-stack">
      <article class="card learning-card">
        <h2>Тренировка по ошибкам</h2>
        <p class="muted">
          В пуле для тренировки: <strong>{{ learningErrorPool.length }}</strong> вопросов из прошлых попыток.
        </p>
        <button class="cta" :disabled="!learningErrorPool.length" @click="startLearningByErrors">Начать тренировку</button>
      </article>

      <article v-if="learningQueue.length" class="card learning-card">
        <div v-if="!learningFinished && currentLearningQuestion">
          <p class="question-index">
            Тренировка: {{ learningIndex + 1 }} / {{ learningQueue.length }}
            <span>{{ currentLearningQuestion.topic }}</span>
          </p>
          <h3>{{ currentLearningQuestion.prompt }}</h3>
          <div class="options">
            <button
              v-for="option in currentLearningQuestion.options"
              :key="option.id"
              :class="{
                selected: learningSelectedOptionId === option.id,
                correct: learningSelectedOptionId && option.id === currentLearningQuestion.correctOptionId,
                wrong:
                  learningSelectedOptionId === option.id && option.id !== currentLearningQuestion.correctOptionId,
              }"
              :disabled="Boolean(learningSelectedOptionId)"
              @click="answerLearningQuestion(option.id)"
            >
              {{ option.text }}
            </button>
          </div>
          <div class="editor-actions">
            <button class="cta" :disabled="!learningSelectedOptionId" @click="nextLearningQuestion">Дальше</button>
          </div>
        </div>

        <div v-else class="learning-summary">
          <h3>Тренировка завершена</h3>
          <p>
            Верно: <strong>{{ learningCorrect }}</strong> из <strong>{{ learningAnswered }}</strong>
          </p>
          <button class="cta" :disabled="!learningErrorPool.length" @click="startLearningByErrors">
            Пройти заново
          </button>
        </div>
      </article>
    </section>

    <section v-if="tab === 'leaderboard' && !activeExam" class="panel-stack">
      <article class="card">
        <h2>Лидерборд участников</h2>
        <div v-if="leaderboard.length" class="leaderboard">
          <div class="leaderboard-head">
            <span>Участник</span>
            <span>Best</span>
            <span>Avg</span>
            <span>Попыток</span>
          </div>
          <div v-for="entry in leaderboard" :key="entry.name" class="leaderboard-row">
            <span>{{ entry.name }}</span>
            <strong>{{ entry.best }}%</strong>
            <span>{{ entry.avg }}%</span>
            <span>{{ entry.attempts }}</span>
          </div>
        </div>
        <p v-else class="empty">Пока пусто.</p>
      </article>
    </section>

    <section v-if="tab === 'sprint' && !activeExam" class="panel-stack">
      <article class="card sprint-card">
        <h2>Спринт на 60 секунд</h2>
        <div class="sprint-meta">
          <strong>{{ formatSeconds(sprintTimeLeft) }}</strong>
          <span>Счет: {{ sprintScore }} / {{ sprintAnswered }}</span>
        </div>

        <button v-if="!sprintActive" class="cta" :disabled="!allQuestions.length" @click="startSprint">Старт</button>
        <button v-else @click="finishSprint">Завершить</button>

        <div v-if="sprintActive && sprintQuestion" class="sprint-question">
          <p class="question-index">{{ sprintQuestion.topic }}</p>
          <h3>{{ sprintQuestion.prompt }}</h3>
          <div class="options">
            <button v-for="option in sprintQuestion.options" :key="option.id" @click="answerSprint(option.id)">
              {{ option.text }}
            </button>
          </div>
        </div>
      </article>

      <article class="card history-card">
        <h2>Топ спринтов</h2>
        <div v-if="topSprintResults.length" class="history-list">
          <div v-for="item in topSprintResults" :key="item.id" class="history-item">
            <span>{{ item.userName }}</span>
            <strong>{{ item.score }} / {{ item.total }}</strong>
            <span></span>
            <time>{{ formatDate(item.finishedAt) }}</time>
          </div>
        </div>
        <p v-else class="empty">Результатов пока нет.</p>
      </article>
    </section>
    </div>
    <footer class="app-footer">
      3D icons by
      <a href="https://www.thiings.co/things" target="_blank" rel="noopener noreferrer">thiings.co</a>
    </footer>
  </div>
</template>
