<template>
  <!-- Agent 页面采用与 Welcome 相同的“铺满 + 黑框”结构以保证下滑进入后视觉一致 -->
  <div
    class="welcome-root"
    @wheel.passive="onWheel"
    @touchstart.passive="onTouchStart"
    @touchend.passive="onTouchEnd"
  >
    <div class="page-frame">
      <div class="container agent-container">
        <div class="top-area">
          <h1 class="agent-title">智能体使用页面（Agent）</h1>
          <p class="agent-desc-txt">此处为占位的 Agent 使用页面，后续集成聊天界面与检索结果显示。</p>

          <!-- 可以在这里复用 AgentDescription 或其它组件 -->
        </div>

        <div class="bottom-area">
          <router-link to="/welcome" class="back-link">返回欢迎页</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const triggered = ref(false)
let touchStartY = 0

function onWheel(e: WheelEvent) {
  if (triggered.value) return
  // 向上滚动超过 100px 触发返回
  if (e.deltaY < -100) {
    triggerNavigate()
  }
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches?.[0]?.clientY ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (triggered.value) return
  const endY = e.changedTouches?.[0]?.clientY ?? 0
  // 手指向下滑动超过 100px 触发返回
  if (touchStartY - endY < -100) {
    triggerNavigate()
  }
}

function triggerNavigate() {
  if (triggered.value) return
  triggered.value = true
  router.push('/welcome').catch(() => {})
}
</script>

<style scoped>
/* 复用变量确保视觉一致 */
.welcome-root {
  min-height: 100vh;
  padding: var(--page-vertical-gap) var(--page-side-gap);
  background: linear-gradient(180deg, #0f1722 0%, #061124 100%);
}

/* 与 welcome 相同的 page-frame */
.page-frame {
  width: calc(100vw - (var(--page-side-gap) * 2));
  height: calc(100vh - (var(--page-vertical-gap) * 2));
  border: var(--page-frame-border) solid #000;
  border-radius: 0;
  padding: var(--page-frame-padding);
  box-sizing: border-box;
  margin: 0;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

/* container 与 welcome 保持一致 */
.container.agent-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 8px;
  gap: 12px;
}

/* top area */
.agent-title {
  color: #eaf8ff;
  margin: 0 0 8px 0;
  font-size: 20px;
}
.agent-desc-txt {
  color: rgba(230,238,248,0.85);
  font-size: 13px;
}

/* 底部返回链接 */
.back-link {
  display: inline-block;
  margin: 8px 0;
  color: #9be7ff;
  font-weight: 600;
  text-decoration: none;
}
</style>