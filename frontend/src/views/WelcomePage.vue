<template>
  <div
    class="welcome-root"
    @wheel.passive="onWheel"
    @touchstart.passive="onTouchStart"
    @touchend.passive="onTouchEnd"
  >
    <div class="bg-blobs" aria-hidden="true" v-html="bgSvg"></div>

    <div class="page-frame">
      <div class="container">
        <!-- 顶部：WelcomeHeader（占比 2）-->
        <header class="header-area">
          <WelcomeHeader :lines="welcomeLines" />
        </header>

        <!-- 中部：AgentDescription（占比 6 -> 扩大为主要区块）-->
        <main class="mid-area">
          <!-- 让 AgentDescription 尽可能填满 mid-area（height:100%） -->
          <AgentDescription
            class="agent-desc-fill"
            :title="agentTitle"
            :intro="agentIntro"
            :developers="developers"
            :features="features"
            :illustration1="logo"
            :illustration2="illustration"
          />
        </main>

        <!-- 底部：ScrollEntry（占比 2）-->
        <footer class="footer-area">
          <ScrollEntry to="/agent" />
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import WelcomeHeader from '@/components/WelcomeHeader.vue'
import AgentDescription from '@/components/AgentDescription.vue'
import ScrollEntry from '@/components/ScrollEntry.vue'
import logo from '@/assets/logo-welcome.svg'
import illustration from '@/assets/welcome-bg.svg'

const router = useRouter()
const triggered = ref(false)
let touchStartY = 0

const welcomeLines = [
  '基于知识图谱（KG）+ 检索增强生成（RAG）',
  '面向财会场景的智能问答与溯源'
]

const agentTitle = '智能体简介'
const agentIntro = `本项目面向企业会计/财务人员，基于财会知识图谱与向量检索，实现问答式智能助手：
- 支持规范解读、查询历史凭证、科目关系问询
- 输出答案时给出命中文档或知识点引用，方便审计与复核。
-
-
-`

const developers = [
  { name: '郑宇，吴瑞祥', role: '后端 / 知识图谱' },
  { name: '金鹏', role: '前端 / RAG UI' },
  { name: '冷佳兴，叶凯旋，曾汇颖', role: '知识图谱构建' }
]

const features = [
  'RAG（检索 + 生成）问答',
  '知识图谱实体与关系可视化（后续）',
  '结果溯源与文档引用',
  '多轮会话与上下文管理'
]

const bgSvg = ref<string>(illustration)

function onWheel(e: WheelEvent) {
  if (triggered.value) return
  // 向下滚动超过 100px 触发
  if (e.deltaY > 100) {
    triggerNavigate()
  }
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches?.[0]?.clientY ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (triggered.value) return
  const endY = e.changedTouches?.[0]?.clientY ?? 0
  // 手指向上滑动超过 100px 触发
  if (touchStartY - endY > 100) {
    triggerNavigate()
  }
}

function triggerNavigate() {
  if (triggered.value) return
  triggered.value = true
  router.push('/agent').catch(() => {})
}
</script>

<style scoped>
/* 根容器：保持铺满视口 */
.welcome-root {
  min-height: 100vh;
  position: relative;
  padding: var(--page-vertical-gap) var(--page-side-gap);
  background: linear-gradient(180deg, #0f1722 0%, #061124 100%);
  color: #e6eef8;
  overflow: auto;
}

/* page-frame 使用全局变量控制黑框厚度 & 内边距 */
.page-frame {
  width: calc(100vw - (var(--page-side-gap) * 2));
  height: calc(100vh - (var(--page-vertical-gap) * 2));
  border: var(--page-frame-border) solid #000;
  border-radius: 0;
  padding: var(--page-frame-padding);
  box-sizing: border-box;
  display: flex;
  align-items: stretch;
  justify-content: center;
  margin: 0;
}

/* container: 三块区域，减小间隙 */
.container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 按比例分配高度： header:2, mid:6, footer:2 (可以调整成你需要的比例) */
.header-area { flex: 2 1 0%; display:flex; align-items:center; justify-content:center; padding: 8px 12px; }
.mid-area    { flex: 6 1 0%; display:flex; align-items:stretch; justify-content:center; padding: 6px 14px; overflow: hidden; }
.footer-area { flex: 2 1 0%; display:flex; align-items:center; justify-content:center; padding: 6px; }

/* 使传入的 AgentDescription 填满 mid-area */
.agent-desc-fill {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
}

/* 背景 blob */
.bg-blobs {
  position: absolute;
  inset: 0;
  z-index: 0;
  opacity: 0.18;
  filter: blur(34px) saturate(120%);
  pointer-events: none;
}

/* 响应式：窄屏上可自动调整 */
@media (max-width: 1000px) {
  .header-area, .mid-area, .footer-area { padding-left: 10px; padding-right: 10px; }
  .container { gap: 8px; }
}
</style>