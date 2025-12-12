<template>
  <section class="welcome-header">
    <div class="title-wrap">
      <div class="title-main">welcome</div>
      <div class="title-sub">
        <div class="typing">{{ currentText }}</div>
        <span class="cursor" :class="{ blink }">|</span>
      </div>
      <p class="sub">智能会计助手 — 精准、可溯源、可扩展</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, type PropType } from 'vue'

const props = defineProps({
  lines: { type: Array as PropType<string[]>, default: () => ['欢迎使用 — 财会领域知识图谱 RAG 智能体'] },
  speed: { type: Number as PropType<number>, default: 120 } // 默认较慢：120ms/字符
})

const currentText = ref('')
const blink = ref(true)
let blinkTimer: number | undefined
let running = true

function sleep(ms = 0) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function runTyping() {
  const lines: string[] = props.lines.length ? props.lines : ['欢迎使用智能体']
  let idx = 0
  while (running) {
    const line = lines[idx]!
    // 打字
    for (let i = 1; i <= line.length && running; i++) {
      currentText.value = line.slice(0, i)
      await sleep(props.speed)
    }
    // 打完后停顿一会儿
    await sleep(1200)
    // 删除文本
    for (let i = line.length; i >= 0 && running; i--) {
      currentText.value = line.slice(0, i)
      await sleep(props.speed / 1.6) // 删除稍快一点
    }
    await sleep(300)
    idx = (idx + 1) % lines.length
  }
}

onMounted(() => {
  blinkTimer = window.setInterval(() => { blink.value = !blink.value }, 500)
  runTyping()
})

onUnmounted(() => {
  running = false
  if (blinkTimer) window.clearInterval(blinkTimer)
})
</script>

<style scoped>
.welcome-header {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 4px 8px;
  background: transparent;
}

/* 放大并居中文本 */
.title-wrap { text-align: center; }

.title-main {
  font-size: 40px;
  color: #bfe9ff;
  font-weight: 700;
  margin-bottom: 6px;
}

.title-sub {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 10px;
}

.typing {
  font-size: 28px; 
  font-weight: 700;
  color: #ffffff;
}

.cursor {
  color: #9be7ff;
  margin-left: 6px;
  opacity: 0.95;
}

.cursor.blink {
  animation: blink 1s steps(2, start) infinite;
}
@keyframes blink { 50% { opacity: 0; } }

.sub {
  font-size: 13px;
  color: rgba(230,238,248,0.76);
  margin-top: 8px;
}
</style>