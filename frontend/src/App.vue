<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type Role = 'user' | 'assistant'

type StreamPayload =
  | { type: 'thread'; thread_id: string }
  | {
      type: 'update'
      node?: string
      status?: string
      validation_status?: string
      reason?: string
      final_answer?: string
      answer?: string
    }
  | { type: 'error'; message: string }

interface ChatMessage {
  id: string
  role: Role
  content: string
}

interface ThreadSummary {
  thread_id: string
  title: string
  updated_at?: string
  message_count?: number
  pending?: boolean
}

const apiBase = ((import.meta.env.VITE_API_BASE as string | undefined) || 'http://localhost:8000').replace(
  /\/$/,
  '',
)

const messages = ref<ChatMessage[]>([])
const input = ref('')
const threadId = ref<string | null>(null)
const status = ref('等待提问')
const error = ref<string | null>(null)
const streaming = ref(false)
const activeAssistantId = ref<string | null>(null)
const controller = ref<AbortController | null>(null)
const threads = ref<ThreadSummary[]>([])
const loadingThreads = ref(false)
const loadingHistory = ref(false)
const deletingId = ref<string | null>(null)
const progress = ref(0)
const progressActive = ref(false)
const progressTimer = ref<ReturnType<typeof setInterval> | null>(null)
const syncing = ref(false)
const pendingThreadId = ref<string | null>(null)

const canSend = computed(() => input.value.trim().length > 0 && !streaming.value)

const appendMessage = (role: Role, content: string) => {
  const id = `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`
  messages.value.push({ id, role, content })
  return id
}

const updateAssistantMessage = (content: string) => {
  if (!activeAssistantId.value) {
    activeAssistantId.value = appendMessage('assistant', content)
    return
  }
  const target = messages.value.find((m) => m.id === activeAssistantId.value)
  if (target) target.content = content
}

const resetStreaming = () => {
  streaming.value = false
  controller.value = null
  activeAssistantId.value = null
}

const stop = () => {
  controller.value?.abort()
  status.value = '已停止'
  resetStreaming()
}

onBeforeUnmount(stop)

onMounted(() => {
  refreshThreads()
})

const stopProgressTimer = () => {
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
    progressTimer.value = null
  }
}

const startProgress = () => {
  stopProgressTimer()
  progressActive.value = true
  progress.value = 8
  progressTimer.value = window.setInterval(() => {
    if (progress.value >= 92) return
    const bump = 5 + Math.random() * 8
    progress.value = Math.min(92, progress.value + bump)
  }, 380)
}

const finishProgress = () => {
  if (!progressActive.value) return
  stopProgressTimer()
  progress.value = 100
  setTimeout(() => {
    progress.value = 0
    progressActive.value = false
  }, 400)
}

const fetchThreadHistory = async (id: string) => {
  const res = await fetch(`${apiBase}/api/v1/chat/history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: id }),
  })
  if (!res.ok) throw new Error('获取会话历史失败')
  const data = await res.json()
  return (data.messages || []) as { role: Role; content: string }[]
}

const refreshThreads = async () => {
  loadingThreads.value = true
  startProgress()
  try {
    const res = await fetch(`${apiBase}/api/v1/chat/threads`)
    if (!res.ok) throw new Error('无法获取会话列表')
    const data = (await res.json()) as ThreadSummary[]
    threads.value = data
  } catch (err) {
    console.warn(err)
  } finally {
    loadingThreads.value = false
    finishProgress()
  }
}

const loadHistory = async (id: string) => {
  if (streaming.value) stop()
  loadingHistory.value = true
  error.value = null
  startProgress()
  try {
    const history = await fetchThreadHistory(id)
    messages.value = history.map((m, idx) => ({
      id: `${m.role}-${idx}`,
      role: m.role,
      content: m.content,
    }))
    threadId.value = id
    status.value = `已加载会话 ${id}`
  } catch (err) {
    const msg = err instanceof Error ? err.message : '获取会话历史失败'
    error.value = msg
  } finally {
    loadingHistory.value = false
    finishProgress()
  }
}

const startNewThread = () => {
  if (streaming.value) stop()
  messages.value = []
  threadId.value = null
  error.value = null
  status.value = '新会话，等待提问'
}

const createPendingThread = (title: string) => {
  const tempId = `pending-${Date.now()}`
  const entry: ThreadSummary = {
    thread_id: tempId,
    title: title || '新会话',
    updated_at: new Date().toISOString(),
    message_count: 0,
    pending: true,
  }
  threads.value = [entry, ...threads.value]
  pendingThreadId.value = tempId
  threadId.value = tempId
}

const resolvePendingThread = (realId: string) => {
  if (!pendingThreadId.value) {
    threadId.value = realId
    return
  }
  threads.value = threads.value.map((t) =>
    t.thread_id === pendingThreadId.value
      ? { ...t, thread_id: realId, pending: false, updated_at: new Date().toISOString() }
      : t,
  )
  threadId.value = realId
  pendingThreadId.value = null
}

const syncKnowledgeBase = async () => {
  if (syncing.value) return
  syncing.value = true
  error.value = null
  status.value = '向量库更新中...'
  startProgress()
  try {
    const res = await fetch(`${apiBase}/api/v1/monitor/sync`, { method: 'POST' })
    if (!res.ok) throw new Error('向量库更新失败')
    const data = await res.json().catch(() => ({}))
    const msg = (data && data.status) || '向量库已更新'
    status.value = msg
  } catch (err) {
    const msg = err instanceof Error ? err.message : '向量库更新失败'
    error.value = msg
    status.value = '向量库更新失败'
  } finally {
    syncing.value = false
    finishProgress()
  }
}

const send = async () => {
  const question = input.value.trim()
  if (!question || streaming.value) return

  error.value = null
  status.value = '检索与生成中...'
  startProgress()

  // 如果是全新对话，先在列表里占位一个 pending 会话
  if (!threadId.value || threadId.value.startsWith('pending-')) {
    createPendingThread(question || '新会话')
  }

  appendMessage('user', question)
  input.value = ''
  streaming.value = true
  activeAssistantId.value = appendMessage('assistant', '...')

  const payload = {
    query: question,
    thread_id: threadId.value && !threadId.value.startsWith('pending-') ? threadId.value : null,
  }
  const url = `${apiBase}/api/v1/chat/stream`
  controller.value = new AbortController()

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.value.signal,
    })

    if (!response.ok || !response.body) {
      throw new Error(`请求失败: ${response.status}`)
    }

    await readStream(response.body.getReader())
    if (threadId.value) {
      // 结束后重新拉取后端存储的最新消息，防止流式遗漏
      const history = await fetchThreadHistory(threadId.value)
      messages.value = history.map((m, idx) => ({
        id: `${m.role}-${idx}`,
        role: m.role,
        content: m.content,
      }))
    }
    status.value = '完成'
    await refreshThreads()
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      status.value = '已停止'
    } else {
      const message = err instanceof Error ? err.message : '请求失败'
      error.value = message
      status.value = '出现错误'
    }
  } finally {
    resetStreaming()
    finishProgress()
  }
}

const confirmDeleteThread = async (id: string) => {
  const ok = window.confirm('确认删除该会话吗？此操作不可恢复。')
  if (!ok) return
  await deleteThread(id)
}

const deleteThread = async (id: string) => {
  if (deletingId.value) return
  deletingId.value = id
  error.value = null
  startProgress()
  try {
    const res = await fetch(`${apiBase}/api/v1/chat/history`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thread_id: id }),
    })
    if (!res.ok) throw new Error('删除会话失败')
    // 清空当前正在查看的会话
    if (threadId.value === id) {
      startNewThread()
      status.value = '会话已删除'
    }
    threads.value = threads.value.filter((t) => t.thread_id !== id)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '删除会话失败'
    error.value = msg
  } finally {
    deletingId.value = null
    finishProgress()
  }
}

const readStream = async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const raw of parts) {
      const line = raw.trim()
      if (!line.startsWith('data:')) continue

      const data = line.replace(/^data:\s*/, '')
      if (data === '[DONE]') return

      try {
        const payload = JSON.parse(data) as StreamPayload
        handlePayload(payload)
      } catch (err) {
        console.warn('parse error', err)
      }
    }

    if (done) break
  }

  // 处理残余缓冲
  if (buffer.trim().startsWith('data:')) {
    const data = buffer.replace(/^data:\s*/, '').trim()
    if (data && data !== '[DONE]') {
      try {
        const payload = JSON.parse(data) as StreamPayload
        handlePayload(payload)
      } catch (err) {
        console.warn('parse error tail', err)
      }
    }
  }
}

const handlePayload = (payload: StreamPayload) => {
  if (payload.type === 'thread') {
    resolvePendingThread(payload.thread_id)
    status.value = `会话 ${payload.thread_id}`
    refreshThreads()
    return
  }

  if (payload.type === 'error') {
    error.value = payload.message
    status.value = '后端返回错误'
    return
  }

  if (payload.type === 'update') {
    if (payload.final_answer || payload.answer) {
      updateAssistantMessage(payload.final_answer || payload.answer || '')
      status.value = payload.status || '生成完成'
    } else if (payload.status) {
      status.value = `${payload.node || 'flow'}: ${payload.status}`
    }
    if (payload.validation_status === 'retry_generation') {
      status.value = '重新生成中...'
    }
    if (payload.validation_status === 'retry_retrieval') {
      status.value = '重新检索中...'
    }
  }
}
</script>

<template>
  <main class="page">
    <section class="header">
      <div>
        <p class="eyebrow">Agentic GraphRAG</p>
        <h1>前端快速体验面板</h1>
        <p class="subtitle">
          通过 FastAPI LangGraph 后端进行检索、生成和校验，实时流式返回执行节点状态。
        </p>
        <div class="toolbar">
          <button class="ghost" type="button" @click="startNewThread" :disabled="streaming">新会话</button>
          <button class="ghost" type="button" @click="refreshThreads" :disabled="loadingThreads">
            {{ loadingThreads ? '刷新中...' : '刷新会话列表' }}
          </button>
          <button class="ghost" type="button" @click="syncKnowledgeBase" :disabled="syncing">
            {{ syncing ? '更新中...' : '更新向量库' }}
          </button>
        </div>
      </div>
      <div class="status-card">
        <p class="label">当前状态</p>
        <p class="value">{{ status }}</p>
        <p class="hint">API: {{ apiBase }}/api/v1/chat/stream</p>
        <p v-if="threadId" class="hint">Thread: {{ threadId }}</p>
        <div class="progress-track" :data-active="progressActive">
          <div class="progress-bar" :style="{ width: `${progress}%` }" />
        </div>
      </div>
    </section>

    <section class="workspace">
      <section class="threads">
        <div class="threads-header">
          <p class="label">会话列表</p>
          <p class="hint">点击可切换会话并加载历史</p>
        </div>
        <div class="thread-list">
          <div
            v-for="thread in threads"
            :key="thread.thread_id"
            class="thread-item"
            :data-active="thread.thread_id === threadId"
          >
            <button
              class="thread-main"
              type="button"
              @click="loadHistory(thread.thread_id)"
              :disabled="loadingHistory || streaming || thread.pending"
            >
              <div class="title">{{ thread.title || thread.thread_id }}</div>
              <div class="meta">
                <span>{{ thread.message_count || 0 }} 条</span>
                <span>{{ thread.updated_at }}</span>
              </div>
            </button>
            <button
              class="delete-btn"
              type="button"
              @click.stop="confirmDeleteThread(thread.thread_id)"
              :disabled="deletingId === thread.thread_id || loadingHistory || streaming || thread.pending"
            >
              {{ deletingId === thread.thread_id ? '删除中...' : '删除' }}
            </button>
          </div>
          <div v-if="!threads.length && !loadingThreads" class="empty">暂无会话，先发起一条消息吧</div>
        </div>
      </section>

      <section class="chat">
        <div class="chat-window">
          <div v-if="messages.length === 0" class="empty">开始提问，流式结果会实时呈现</div>
          <div v-for="message in messages" :key="message.id" class="bubble" :data-role="message.role">
            <p class="role">{{ message.role === 'user' ? '用户' : '助手' }}</p>
            <p class="content">{{ message.content }}</p>
          </div>
        </div>

        <div class="composer">
          <textarea
            v-model="input"
          placeholder="输入你的问题，比如：介绍 SpaceX 与星舰的关系"
          :disabled="streaming"
          rows="3"
        />
        <div class="actions">
          <div class="left">
            <p class="hint">在聊天框中输入内容以开始对话</p>
            <p v-if="error" class="error">错误：{{ error }}</p>
          </div>
          <div class="right">
            <button class="ghost" type="button" @click="stop" :disabled="!streaming">停止</button>
            <button class="primary" type="button" @click="send" :disabled="!canSend">发送</button>
            </div>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.thread-list {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.thread-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.1s ease;
}

.thread-item[data-active='true'] {
  border-color: rgba(34, 211, 238, 0.8);
  background: rgba(34, 211, 238, 0.08);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  transform: translateY(-1px);
}

.thread-main {
  flex: 1;
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  color: inherit;
  cursor: pointer;
}

.thread-main:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.thread-main .title {
  font-weight: 600;
  margin-bottom: 4px;
}

.thread-main .meta {
  display: flex;
  gap: 10px;
  color: #9fb3c8;
  font-size: 12px;
}

.delete-btn {
  border: 1px solid rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.12);
  color: #fecdd3;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.delete-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.22);
}

.delete-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.progress-track {
  position: relative;
  width: 100%;
  height: 8px;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  transition: opacity 0.2s ease;
  opacity: 0.6;
}

.progress-track[data-active='true'] {
  opacity: 1;
}

.progress-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #22d3ee, #a855f7);
  transition: width 0.3s ease;
}

.workspace {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  align-items: start;
}

.workspace .threads {
  height: calc(100vh - 220px);
  min-height: 360px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace .thread-list {
  grid-template-columns: 1fr;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.workspace .chat {
  height: 100%;
}

@media (max-width: 960px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}

.chat {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 220px);
  max-height: calc(100vh - 180px);
  min-height: 520px;
  overflow: hidden;
}

.chat-window {
  flex: 1;
  min-height: 320px;
  overflow-y: auto;
}

@media (max-width: 960px) {
  .chat {
    height: auto;
    min-height: 460px;
  }
}
</style>
