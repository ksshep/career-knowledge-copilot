<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  FileText,
  FolderOpen,
  Inbox,
  LoaderCircle,
  MessageCircle,
  RefreshCw,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-vue-next'

import { ApiError, deleteDocument, listDocuments, uploadDocument } from './api'
import type { DocumentItem, DocumentStatus } from './types'
import AskPage from './AskPage.vue'

type Page = 'documents' | 'ask'

function pageFromHash(): Page {
  return window.location.hash === '#ask' ? 'ask' : 'documents'
}

const currentPage = ref<Page>(pageFromHash())

function syncPageFromHash(): void {
  currentPage.value = pageFromHash()
}

function navigateTo(page: Page): void {
  window.location.hash = page === 'ask' ? '#ask' : '#documents'
}

const documents = ref<DocumentItem[]>([])
const isLoading = ref(true)
const isUploading = ref(false)
const isDeleting = ref(false)
const isDragging = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const selectedForDeletion = ref<DocumentItem | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const readyCount = computed(() => documents.value.filter((document) => document.status === 'ready').length)
const attentionCount = computed(() => documents.value.filter((document) => document.status === 'failed').length)

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function statusLabel(status: DocumentStatus): string {
  return { processing: '处理中', ready: '已就绪', failed: '处理失败' }[status]
}

function statusHint(status: DocumentStatus): string {
  return {
    processing: '正在提取与建立索引',
    ready: '可以用于搜索和问答',
    failed: '请删除后重新上传',
  }[status]
}

function clearFeedback(): void {
  errorMessage.value = ''
  successMessage.value = ''
}

async function loadDocuments(): Promise<void> {
  isLoading.value = true
  errorMessage.value = ''
  try {
    documents.value = (await listDocuments()).items
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '文档列表加载失败。'
  } finally {
    isLoading.value = false
  }
}

function openFilePicker(): void {
  fileInput.value?.click()
}

function onFileInput(event: Event): void {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) void handleFile(file)
  target.value = ''
}

function onDrop(event: DragEvent): void {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) void handleFile(file)
}

async function handleFile(file: File): Promise<void> {
  clearFeedback()
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '只能上传 PDF 文件。'
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    errorMessage.value = '文件不能超过 20 MB。'
    return
  }

  isUploading.value = true
  try {
    const uploaded = await uploadDocument(file)
    documents.value = [uploaded, ...documents.value.filter((document) => document.id !== uploaded.id)]
    successMessage.value = `${uploaded.filename} 已加入处理队列。`
    window.setTimeout(() => {
      void loadDocuments()
    }, 1200)
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '上传失败，请稍后再试。'
  } finally {
    isUploading.value = false
  }
}

function requestDelete(document: DocumentItem): void {
  clearFeedback()
  selectedForDeletion.value = document
}

function closeDeleteDialog(): void {
  selectedForDeletion.value = null
}

function onGlobalKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && selectedForDeletion.value) closeDeleteDialog()
}

async function confirmDelete(): Promise<void> {
  const document = selectedForDeletion.value
  if (!document || isDeleting.value) return

  clearFeedback()
  isDeleting.value = true
  try {
    await deleteDocument(document.id)
    documents.value = documents.value.filter((item) => item.id !== document.id)
    successMessage.value = `${document.filename} 已删除。`
    closeDeleteDialog()
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除失败，请稍后再试。'
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  window.addEventListener('hashchange', syncPageFromHash)
  window.addEventListener('keydown', onGlobalKeydown)
  if (currentPage.value === 'documents') void loadDocuments()
})

watch(currentPage, (page) => {
  if (page === 'documents') void loadDocuments()
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', syncPageFromHash)
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand-lockup">
        <div class="brand-mark" aria-hidden="true"><FolderOpen :size="20" stroke-width="2.2" /></div>
        <div>
          <p class="brand-name">Career Knowledge Copilot</p>
          <p class="brand-context">求职资料知识库</p>
        </div>
      </div>
      <div class="topbar-meta"><span class="online-dot" />本地工作区</div>
    </header>

    <nav class="topbar-nav" aria-label="主导航">
      <a href="#documents" :class="{ 'is-active': currentPage === 'documents' }" @click="navigateTo('documents')"><FolderOpen :size="16" />文档库</a>
      <a href="#ask" :class="{ 'is-active': currentPage === 'ask' }" @click="navigateTo('ask')"><MessageCircle :size="16" />资料问答</a>
    </nav>

    <main v-if="currentPage === 'documents'" class="workspace">
      <section class="page-heading" aria-labelledby="page-title">
        <div>
          <p class="section-kicker">DOCUMENTS / LIBRARY</p>
          <h1 id="page-title">资料文档</h1>
          <p class="heading-copy">集中管理简历、岗位 JD 和面试资料，保持你的知识库随时可用。</p>
        </div>
        <button class="primary-button" type="button" :disabled="isUploading" @click="openFilePicker">
          <LoaderCircle v-if="isUploading" class="spin" :size="18" />
          <UploadCloud v-else :size="18" />
          {{ isUploading ? '上传中…' : '上传 PDF' }}
        </button>
        <input ref="fileInput" class="visually-hidden" type="file" accept="application/pdf,.pdf" @change="onFileInput" />
      </section>

      <section class="summary-strip" aria-label="文档概览">
        <div class="summary-item"><span class="summary-label">全部文档</span><strong>{{ documents.length }}</strong></div>
        <div class="summary-item"><span class="summary-label">已就绪</span><strong class="mint-number">{{ readyCount }}</strong></div>
        <div class="summary-item"><span class="summary-label">需要处理</span><strong class="coral-number">{{ attentionCount }}</strong></div>
        <div class="summary-note"><CheckCircle2 :size="16" />数据来自 PostgreSQL</div>
      </section>

      <div v-if="errorMessage" class="feedback feedback-error" role="alert">
        <AlertCircle :size="18" /><span>{{ errorMessage }}</span><button class="feedback-close" title="关闭提示" aria-label="关闭提示" @click="errorMessage = ''"><X :size="16" /></button>
      </div>
      <div v-if="successMessage" class="feedback feedback-success" role="status">
        <Check :size="18" /><span>{{ successMessage }}</span><button class="feedback-close" title="关闭提示" aria-label="关闭提示" @click="successMessage = ''"><X :size="16" /></button>
      </div>

      <section
        class="upload-zone"
        :class="{ 'is-dragging': isDragging, 'is-uploading': isUploading }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <div class="upload-zone-icon"><UploadCloud :size="22" /></div>
        <div class="upload-zone-copy"><strong>把 PDF 拖到这里</strong><span>单个文件不超过 20 MB</span></div>
        <button class="text-button" type="button" :disabled="isUploading" @click="openFilePicker">从电脑选择 <ArrowUpRight :size="15" /></button>
      </section>

      <section class="ledger-section" aria-labelledby="ledger-title">
        <div class="ledger-heading">
          <div><h2 id="ledger-title">文档目录</h2><span class="ledger-count">{{ documents.length }} 个文件</span></div>
          <button class="icon-button" type="button" title="刷新文档列表" aria-label="刷新文档列表" :disabled="isLoading" @click="loadDocuments"><RefreshCw :class="{ spin: isLoading }" :size="17" /></button>
        </div>

        <div v-if="isLoading" class="ledger-list loading-list" aria-live="polite" aria-label="正在加载文档">
          <div v-for="row in 3" :key="row" class="skeleton-row"><span /><span /><span /><span /></div>
        </div>

        <div v-else-if="documents.length === 0" class="empty-state">
          <div class="empty-icon"><Inbox :size="28" /></div>
          <h3>还没有文档</h3>
          <p>上传第一份 PDF，让资料进入你的知识库。</p>
          <button class="secondary-button" type="button" @click="openFilePicker"><UploadCloud :size="17" />上传第一份 PDF</button>
        </div>

        <div v-else class="ledger-list">
          <div class="ledger-row ledger-row-header" aria-hidden="true"><span>文件名</span><span>大小</span><span>状态</span><span>操作</span></div>
          <article v-for="document in documents" :key="document.id" class="ledger-row">
            <div class="file-cell"><div class="file-icon"><FileText :size="19" /></div><div class="file-copy"><strong :title="document.filename">{{ document.filename }}</strong><span>PDF 文档</span></div></div>
            <div class="size-cell">{{ formatFileSize(document.size_bytes) }}</div>
            <div class="status-cell"><span class="status-badge" :class="`status-${document.status}`"><LoaderCircle v-if="document.status === 'processing'" class="spin" :size="14" /><CheckCircle2 v-else-if="document.status === 'ready'" :size="14" /><AlertCircle v-else :size="14" />{{ statusLabel(document.status) }}</span><small>{{ statusHint(document.status) }}</small></div>
            <div class="action-cell"><button class="delete-button" type="button" title="删除文档" :aria-label="`删除 ${document.filename}`" @click="requestDelete(document)"><Trash2 :size="17" /></button></div>
          </article>
        </div>
      </section>
    </main>

    <AskPage v-else />

    <Teleport to="body">
      <div v-if="selectedForDeletion" class="modal-backdrop" role="presentation" @click.self="closeDeleteDialog">
        <section class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
          <div class="dialog-icon"><Trash2 :size="20" /></div>
          <h2 id="confirm-title">删除这份文档？</h2>
          <p><strong>{{ selectedForDeletion.filename }}</strong> 及其页面文本和向量都会被删除，无法恢复。</p>
          <div class="dialog-actions"><button class="secondary-button" type="button" :disabled="isDeleting" @click="closeDeleteDialog">取消</button><button class="danger-button" type="button" :disabled="isDeleting" @click="confirmDelete"><LoaderCircle v-if="isDeleting" class="spin" :size="16" /><Trash2 v-else :size="16" />{{ isDeleting ? '删除中' : '确认删除' }}</button></div>
        </section>
      </div>
    </Teleport>
  </div>
</template>
