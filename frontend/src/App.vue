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
  try {
    const res = await fetch(`${apiBase}/api/v1/chat/threads`)
    if (!res.ok) throw new Error('无法获取会话列表')
    const data = (await res.json()) as ThreadSummary[]
    threads.value = data
  } catch (err) {
    console.warn(err)
  } finally {
    loadingThreads.value = false
  }
}

const loadHistory = async (id: string) => {
  if (streaming.value) stop()
  loadingHistory.value = true
  error.value = null
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
  }
}

const startNewThread = () => {
  if (streaming.value) stop()
  messages.value = []
  threadId.value = null
  error.value = null
  status.value = '新会话，等待提问'
}

const send = async () => {
  const question = input.value.trim()
  if (!question || streaming.value) return

  error.value = null
  status.value = '检索与生成中...'

  appendMessage('user', question)
  input.value = ''
  streaming.value = true
  activeAssistantId.value = appendMessage('assistant', '...')

  const payload = { query: question, thread_id: threadId.value }
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
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '请求失败'
    error.value = message
    status.value = '出现错误'
  } finally {
    resetStreaming()
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
    threadId.value = payload.thread_id
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
          <button class="ghost" type="button" @click="startNewThread">新会话</button>
          <button class="ghost" type="button" @click="refreshThreads" :disabled="loadingThreads">
            {{ loadingThreads ? '刷新中...' : '刷新会话列表' }}
          </button>
        </div>
      </div>
      <div class="status-card">
        <p class="label">当前状态</p>
        <p class="value">{{ status }}</p>
        <p class="hint">API: {{ apiBase }}/api/v1/chat/stream</p>
        <p v-if="threadId" class="hint">Thread: {{ threadId }}</p>
      </div>
    </section>

    <section class="threads">
      <div class="threads-header">
        <p class="label">会话列表</p>
        <p class="hint">点击可切换会话并加载历史</p>
      </div>
      <div class="thread-list">
        <button
          v-for="thread in threads"
          :key="thread.thread_id"
          type="button"
          class="thread-item"
          :data-active="thread.thread_id === threadId"
          @click="loadHistory(thread.thread_id)"
          :disabled="loadingHistory"
        >
          <div class="title">{{ thread.title || thread.thread_id }}</div>
          <div class="meta">
            <span>{{ thread.message_count || 0 }} 条</span>
            <span>{{ thread.updated_at }}</span>
          </div>
        </button>
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
            <p class="hint">会话自动复用 thread_id，刷新页面会重置</p>
            <p v-if="error" class="error">错误：{{ error }}</p>
          </div>
          <div class="right">
            <button class="ghost" type="button" @click="stop" :disabled="!streaming">停止</button>
            <button class="primary" type="button" @click="send" :disabled="!canSend">发送</button>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
