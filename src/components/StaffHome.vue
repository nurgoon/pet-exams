<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  completeQuest,
  fetchDuties,
  fetchQuestLeaderboard,
  fetchQuestProfile,
  fetchQuests,
  submitQuest,
} from '../lib/api'
import type { DutyAssignment, Quest, QuestLeaderboardEntry, QuestProfile } from '../types'

const props = defineProps<{
  userName: string
}>()

const profile = ref<QuestProfile | null>(null)
const quests = ref<Quest[]>([])
const leaderboard = ref<QuestLeaderboardEntry[]>([])
const duties = ref<DutyAssignment[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const completingId = ref<string | null>(null)
const proofFiles = ref<Record<string, File | null>>({})
const soundEnabled = ref(localStorage.getItem('protocol-sound') !== '0')

const todayLabel = computed(() => {
  const now = new Date()
  return now.toLocaleDateString('ru-RU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
})

const rubLabel = computed(() => {
  const rub = (profile.value?.rubCents ?? 0) / 100
  return `${rub.toFixed(2)} ₽`
})

const expLabel = computed(() => `${profile.value?.exp ?? 0} EXP`)
const completedToday = computed(() => profile.value?.completedToday ?? 0)
const questsDone = computed(() => quests.value.filter((quest) => quest.completed).length)
const questsTotal = computed(() => quests.value.length)
const questProgress = computed(() => (questsTotal.value ? Math.round((questsDone.value / questsTotal.value) * 100) : 0))
const leaderboardShort = computed(() => leaderboard.value.slice(0, 5))

const todayIso = computed(() => {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
})

const cleaningSchedule = computed(() =>
  duties.value
    .filter((item) => item.dutyType === 'cleaning')
    .slice()
    .sort((a, b) => a.businessDate.localeCompare(b.businessDate))
)


const load = async (): Promise<void> => {
  const normalized = props.userName.trim()
  if (!normalized) {
    return
  }

  loading.value = true
  error.value = null
  try {
    const [profileResponse, questsResponse, leaderboardResponse, dutiesResponse] = await Promise.all([
      fetchQuestProfile(normalized),
      fetchQuests(normalized),
      fetchQuestLeaderboard(25),
      fetchDuties({ dutyType: 'cleaning', from: todayIso.value, days: 7 }),
    ])
    profile.value = profileResponse
    quests.value = questsResponse
    leaderboard.value = leaderboardResponse
    duties.value = dutiesResponse
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Не удалось загрузить данные'
  } finally {
    loading.value = false
  }
}

const complete = async (quest: Quest): Promise<void> => {
  if (quest.completed || completingId.value) {
    return
  }
  const normalized = props.userName.trim()
  if (!normalized) {
    return
  }

  completingId.value = quest.id
  error.value = null
  try {
    await completeQuest(quest.id, { userName: normalized })
    playSound('success')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Не удалось выполнить задачу'
  } finally {
    completingId.value = null
  }
}

const submitForReview = async (quest: Quest): Promise<void> => {
  if (quest.completed || completingId.value) {
    return
  }
  const normalized = props.userName.trim()
  if (!normalized) {
    return
  }

  const proofImage = proofFiles.value[quest.id] ?? null
  if (quest.requiresProof && !proofImage) {
    error.value = 'Нужен скриншот/фото для отправки на проверку'
    return
  }

  completingId.value = quest.id
  error.value = null
  try {
    await submitQuest(quest.id, { userName: normalized, proofImage })
    playSound('submit')
    proofFiles.value[quest.id] = null
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Не удалось отправить на проверку'
  } finally {
    completingId.value = null
  }
}

const playSound = (kind: 'success' | 'submit'): void => {
  if (!soundEnabled.value) {
    return
  }
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    const now = ctx.currentTime
    osc.type = 'triangle'
    osc.frequency.value = kind === 'success' ? 880 : 620
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.08, now + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2)
    osc.connect(gain).connect(ctx.destination)
    osc.start(now)
    osc.stop(now + 0.22)
    osc.onended = () => ctx.close()
  } catch {
    // ignore audio errors
  }
}

watch(
  () => props.userName,
  () => {
    void load()
  }
)

onMounted(() => {
  void load()
})
</script>

<template>
  <section class="panel-stack staff-stack">
    <article class="card hero staff-hero">
      <div>
        <h1>Кабинет сотрудника</h1>
        <p class="lead">
          Сегодня: <strong>{{ todayLabel }}</strong>
        </p>
      </div>
      <div class="hero-controls staff-hero-controls">
        <div class="staff-stats">
          <div class="staff-stat">
            <span>Опыт</span>
            <strong>{{ expLabel }}</strong>
          </div>
          <div class="staff-stat">
            <span>Награда</span>
            <strong>{{ rubLabel }}</strong>
          </div>
          <div class="staff-stat">
            <span>Выполнено сегодня</span>
            <strong>{{ completedToday }}</strong>
          </div>
        </div>
        <div class="staff-progress">
          <div class="progress-row">
            <span>Прогресс задач</span>
            <strong>{{ questProgress }}%</strong>
          </div>
          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${questProgress}%` }"></div>
          </div>
          <p class="muted">Выполнено: {{ questsDone }} / {{ questsTotal }}</p>
        </div>
      </div>
    </article>

    <article v-if="cleaningSchedule.length" class="card">
      <div class="staff-section-head">
        <div>
          <h2>Табель уборки</h2>
          <p class="muted">Ответственный по дням (заполняется в админке).</p>
        </div>
        <a class="admin-link" href="http://127.0.0.1:8000/admin/quests/dutyassignment/" target="_blank" rel="noopener noreferrer">
          Редактировать
        </a>
      </div>

      <div class="duty-table">
        <div class="duty-head">
          <span>Дата</span>
          <span>Ответственный</span>
          <span>Комментарий</span>
        </div>
        <div v-for="row in cleaningSchedule" :key="row.id" class="duty-row">
          <strong>{{ new Date(row.businessDate).toLocaleDateString('ru-RU', { weekday: 'short', month: 'short', day: 'numeric' }) }}</strong>
          <span>{{ row.userName }}</span>
          <span class="muted">{{ row.notes || '—' }}</span>
        </div>
      </div>
    </article>


    <article class="card">
      <div class="staff-section-head">
        <div>
          <h2>Квесты и задания</h2>
          <p class="muted">Каждая выполненная задача приносит EXP и/или ₽.</p>
        </div>
        <button :disabled="loading" @click="load">Обновить</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="quests.length" class="quest-list">
        <div v-for="quest in quests" :key="quest.id" class="quest-row" :class="{ done: quest.completed }">
          <div class="quest-main">
            <div class="quest-topline">
              <strong class="quest-title">{{ quest.title }}</strong>
              <span v-if="quest.category" class="quest-chip">{{ quest.category }}</span>
              <span class="quest-chip subtle">{{ quest.repeat === 'daily' ? 'ежедневно' : 'один раз' }}</span>
              <span v-if="quest.submissionStatus === 'pending'" class="quest-chip subtle">на проверке</span>
              <span v-if="quest.submissionStatus === 'rejected'" class="quest-chip subtle">отклонено</span>
            </div>
            <p v-if="quest.description" class="muted quest-desc">{{ quest.description }}</p>
            <p v-if="quest.submissionStatus === 'rejected' && quest.reviewComment" class="error quest-desc">
              {{ quest.reviewComment }}
            </p>
            <div class="quest-rewards">
              <span v-if="quest.rewardExp" class="reward-pill reward-exp">+{{ quest.rewardExp }} EXP</span>
              <span v-if="quest.rewardRubCents" class="reward-pill reward-rub">+{{ (quest.rewardRubCents / 100).toFixed(2) }} ₽</span>
            </div>
          </div>

          <div class="quest-actions">
            <span v-if="quest.completed && quest.completedAt" class="muted quest-time">
              {{ new Date(quest.completedAt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
            <input
              v-if="!quest.completed && quest.requiresProof && quest.submissionStatus !== 'pending'"
              type="file"
              accept="image/*"
              @change="(e) => (proofFiles[quest.id] = (e.target as HTMLInputElement).files?.[0] ?? null)"
            />
            <button
              class="cta"
              :class="{ 'cta-success': quest.completed }"
              :disabled="quest.completed || quest.submissionStatus === 'pending' || completingId === quest.id"
              @click="quest.requiresApproval || quest.requiresProof ? submitForReview(quest) : complete(quest)"
            >
              {{
                quest.completed
                  ? 'Выполнено'
                  : quest.submissionStatus === 'pending'
                    ? 'На проверке'
                    : completingId === quest.id
                      ? '...'
                      : quest.requiresApproval || quest.requiresProof
                        ? 'Отправить на проверку'
                        : 'Забрать награду'
              }}
            </button>
          </div>
        </div>
      </div>

    </article>

    <article class="card">
      <h2>Рейтинг сотрудников</h2>
      <div v-if="leaderboardShort.length" class="staff-leaderboard">
        <div class="staff-leaderboard-head">
          <span>Сотрудник</span>
          <span>EXP</span>
          <span>₽</span>
        </div>
        <div v-for="entry in leaderboardShort" :key="entry.userName" class="staff-leaderboard-row">
          <strong>{{ entry.userName }}</strong>
          <span>{{ entry.exp }}</span>
          <span>{{ (entry.rubCents / 100).toFixed(2) }}</span>
        </div>
      </div>
    </article>
  </section>
</template>
