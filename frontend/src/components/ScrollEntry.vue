<template>
  <div
    class="scroll-entry"
    :class="{ 'exiting': exiting }"
    @wheel.passive="onWheel"
    @touchstart.passive="onTouchStart"
    @touchend.passive="onTouchEnd"
    role="button"
    aria-label="下滑进入智能体页面（或点击箭头）"
    tabindex="0"
    @keydown.enter.prevent="triggerNavigate"
  >
    <div class="hint">
      <div class="arrow-wrap" @click.stop="triggerNavigate" role="link" aria-hidden="false">
        <svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M12 5v14M5 12l7 7 7-7" stroke-linecap="round" stroke-linejoin="round"></path>
        </svg>
      </div>
      <div class="text">下滑进入</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  to: { type: String, default: '/agent' },
  threshold: { type: Number, default: 48 } // 滚动阈值（deltaY 或触摸位移）
})

const router = useRouter()
const exiting = ref(false)
const triggered = ref(false)

let touchStartY = 0

function onWheel(e: WheelEvent) {
  if (triggered.value) return
  // 只有明显的向下滚动才触发
  if (e.deltaY > props.threshold) {
    triggerNavigate()
  }
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches?.[0]?.clientY ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (triggered.value) return
  const endY = e.changedTouches?.[0]?.clientY ?? 0
  // 手指向上滑动： startY - endY > threshold 表示上滑（页面向上移动 => 用户想看下面内容）
  if (touchStartY - endY > props.threshold) {
    triggerNavigate()
  }
}

function triggerNavigate() {
  if (triggered.value) return
  triggered.value = true
  exiting.value = true
  // 给一点动画时间再跳转
  setTimeout(() => {
    router.push(props.to).catch(() => {})
  }, 420)
}
</script>

<style scoped>
.scroll-entry {
  display: flex;
  justify-content: center;
  padding: 18px 0 8px 0;
  cursor: ns-resize;
  user-select: none;
  transition: transform .42s cubic-bezier(.2,.9,.3,1), opacity .4s ease;
  transform: translateY(0);
  opacity: 1;
}

/* 触发后淡出并向下移动，给人“滑入下一页”的感觉 */
.scroll-entry.exiting {
  transform: translateY(36px);
  opacity: 0;
  pointer-events: none;
}

.hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #dff8ff;
  font-weight: 600;
  font-size: 14px;
}

.arrow-wrap {
  width: 54px;
  height: 54px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  box-shadow: 0 8px 26px rgba(0,0,0,0.45), inset 0 -2px 6px rgba(255,255,255,0.02);
  transition: transform .2s ease, box-shadow .2s ease;
}

.arrow-wrap:hover {
  transform: translateY(-6px);
  box-shadow: 0 14px 36px rgba(0,0,0,0.55);
}

.arrow {
  width: 22px;
  height: 22px;
  color: #80f0ff;
  transform: translateY(0);
  animation: float 1.6s ease-in-out infinite;
}

@keyframes float {
  0% { transform: translateY(0); }
  50% { transform: translateY(6px); }
  100% { transform: translateY(0); }
}

.text {
  font-size: 13px;
  color: rgba(220,245,255,0.9);
}
</style>