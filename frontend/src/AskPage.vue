<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  CircleHelp,
  FileText,
  LoaderCircle,
  Send,
  X,
} from 'lucide-vue-next'

import { ApiError, askQuestion } from './api'
import type { AskResponse, Citation } from './types'

interface AskMessage extends AskResponse {
  id: string
  query: string
}

const HISTORY_KEY = 'career-copilot.ask-history'
const query = ref('')
const messages = ref<AskMessage[]>([])
const isSending = ref(false)
const errorMessage = ref('')
const composer = ref<HTMLTextAreaElement | null>(null)
const thread = ref<HTMLElement | null>(null)

function loadHistory(): void {
  try {
    const saved = sessionStorage.getItem(HISTORY_KEY)
    if (!saved) return
    const parsed = JSON.parse(saved) as AskMessage[]
    if (Array.isArray(parsed)) messages.value = parsed
  } catch {
    sessionStorage.removeItem(HISTORY_KEY)
  }
}

function saveHistory(): void {
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(messages.value))
}

function clearError(): void {
  errorMessage.value = ''
}

function userFacingError(error: unknown): string {
  if (!(error instanceof ApiError)) return '问答服务暂时不可用，请稍后重试。'
  if (error.status === 400) return '问题不能为空，请先输入一个具体问题。'
  if (error.status === 500) return '问答服务暂时不可用，请确认模型服务和数据库正常。'
  return error.message
}

async function submitQuestion(): Promise<void> {
  const value = query.value.trim()
  clearError()
  if (!value) {
    errorMessage.value = '请输入问题后再发送。'
    composer.value?.focus()
    return
  }
  if (isSending.value) return

  isSending.value = true
  try {
    const response = await askQuestion(value)
    messages.value.push({ id: crypto.randomUUID(), query: value, ...response })
    query.value = ''
    await nextTick()
    thread.value?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    errorMessage.value = userFacingError(error)
  } finally {
    isSending.value = false
  }
}

function onComposerKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void submitQuestion()
  }
}

function citationLabel(citation: Citation): string {
  return `${citation.filename} · 第 ${citation.page_number} 页 · 片段 ${citation.chunk_index}`
}

function clearHistory(): void {
  messages.value = []
  sessionStorage.removeItem(HISTORY_KEY)
}

onMounted(loadHistory)
watch(messages, saveHistory, { deep: true })
</script>

<template>
  <main class="workspace ask-workspace">
    <section class="page-heading ask-heading" aria-labelledby="ask-title">
      <div>
        <p class="section-kicker">ASK / EVIDENCE</p>
        <h1 id="ask-title">资料问答</h1>
        <p class="heading-copy">只依据已处理完成的 PDF 资料回答，并保留文件、页码和片段引用。</p>
      </div>
      <div class="ask-heading-meta"><BookOpen :size="18" />基于你的资料库</div>
    </section>

    <div v-if="errorMessage" class="feedback feedback-error" role="alert">
      <AlertCircle :size="18" /><span>{{ errorMessage }}</span>
      <button class="feedback-close" title="关闭提示" aria-label="关闭提示" @click="clearError"><X :size="16" /></button>
    </div>

    <section ref="thread" class="ask-thread" aria-live="polite" aria-label="问答记录">
      <div v-if="messages.length === 0" class="ask-empty">
        <div class="empty-icon"><CircleHelp :size="28" /></div>
        <h2>从一个具体问题开始</h2>
        <p>例如：这个项目使用了什么技术？哪段经历最适合回答后端实习？</p>
      </div>

      <article v-for="message in messages" :key="message.id" class="ask-entry">
        <div class="question-row">
          <span class="message-label">你的问题</span>
          <p>{{ message.query }}</p>
        </div>
        <div class="answer-row">
          <div class="answer-heading"><span class="answer-mark"><CheckCircle2 :size="16" /></span><span>资料回答</span></div>
          <p class="answer-copy">{{ message.answer }}</p>
          <div v-if="message.has_evidence && message.citations.length" class="citation-block">
            <div class="citation-heading"><FileText :size="15" />引用资料</div>
            <ul class="citation-list">
              <li v-for="(citation, index) in message.citations" :key="`${message.id}-${citation.filename}-${citation.page_number}-${citation.chunk_index}`">
                <span class="citation-index">{{ index + 1 }}</span>
                <span class="citation-text"><strong>{{ citation.filename }}</strong><span>第 {{ citation.page_number }} 页 · 片段 {{ citation.chunk_index }}</span></span>
                <span class="citation-sr-only">{{ citationLabel(citation) }}</span>
              </li>
            </ul>
          </div>
          <div v-else class="no-evidence"><AlertCircle :size="15" />没有找到足够依据，暂时无法从资料中确认答案。</div>
        </div>
      </article>
    </section>

    <section class="ask-composer" aria-label="输入问题">
      <textarea
        ref="composer"
        v-model="query"
        rows="3"
        maxlength="1000"
        aria-label="输入问题"
        placeholder="输入你想从资料中确认的问题…"
        :disabled="isSending"
        @keydown="onComposerKeydown"
      />
      <div class="composer-footer">
        <span>Enter 发送 · Shift + Enter 换行</span>
        <button class="primary-button send-button" type="button" :disabled="isSending || !query.trim()" @click="submitQuestion">
          <LoaderCircle v-if="isSending" class="spin" :size="17" />
          <Send v-else :size="17" />
          {{ isSending ? '生成回答中' : '发送问题' }}
        </button>
      </div>
    </section>

    <div v-if="messages.length" class="ask-footer-actions">
      <button class="text-button" type="button" @click="clearHistory">清空本页问答记录</button>
    </div>
  </main>
</template>
