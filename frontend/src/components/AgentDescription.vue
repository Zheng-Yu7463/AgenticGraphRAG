<template>
  <section class="agent-desc">
    <!-- 左：说明 -->
    <div class="desc-left">
      <h3>{{ title }}</h3>
      <p class="intro" v-html="formattedIntro"></p>

      <div class="meta-row">
        <div class="meta-block">

          <div class="meta-block">
          <div class="meta-title">主要功能</div>
          <ul>
            <li v-for="f in features" :key="f">{{ f }}</li>
          </ul>
        </div>
        
          <div class="meta-title">小组成员</div>
          <ul>
            <li v-for="d in developers" :key="d.name">{{ d.name }} — <span class="role">{{ d.role }}</span></li>
          </ul>
        </div>

        
      </div>
    </div>

    <!-- 中：图一 -->
    <div class="desc-mid">
      <div class="image-card">
        <img v-if="illustration1" :src="illustration1" alt="图一" />
        <div v-else class="placeholder">占位图一</div>
      </div>
    </div>

    <!-- 右：图二 -->
    <div class="desc-right">
      <div class="image-card">
        <img v-if="illustration2" :src="illustration2" alt="图二" />
        <div v-else class="placeholder">占位图二</div>
      </div>
    </div>
  </section>
</template>


<script setup lang="ts">
import { computed, type PropType } from 'vue'

const props = defineProps({
  title: { type: String as PropType<string>, default: '智能体说明' },
  intro: { type: String as PropType<string>, default: '' },
  developers: { type: Array as PropType<Array<{name:string, role?:string}>>, default: () => [] },
  features: { type: Array as PropType<string[]>, default: () => [] },
  illustration1: { type: String as PropType<string>, default: '' },
  illustration2: { type: String as PropType<string>, default: '' }
})

const formattedIntro = computed(() => {
  return props.intro.replace(/\n/g, '<br/>')
})
</script>

<style scoped>
/* 三列布局：左自适应，中右固定宽（可按需调整） */
/* 高度改为 100% 并使用 grid-auto-rows: 1fr，让列在有空间时垂直拉伸 */
.agent-desc {
  display: grid;
  grid-template-columns: 1fr 420px 360px; /* 中间和右边扩大宽度（你可以根据需要调整） */
  gap: 18px;
  background: rgba(255,255,255,0.01);
  border-radius: 8px;
  padding: 12px;
  box-sizing: border-box;
  height: 100%;            /* 关键：随父容器高度拉伸 */
  grid-auto-rows: 1fr;     /* 关键：使单行占满可用高度，从而中/右列的 image-card 能垂直扩展 */
  min-height: 0;           /* 避免 overflow 问题 */
}

/* 左列说明靠上 */
.desc-left { align-self: start; overflow: auto; }

/* 左列文本样式 */
.desc-left h3 {
  margin: 0 0 10px 0;
  color: #eaf8ff;
  font-size: 16px;
}

.intro {
  color: rgba(230,238,248,0.85);
  font-size: 13px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.meta-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-block {
  min-width: 160px;
  background: rgba(255,255,255,0.01);
  padding: 10px;
  border-radius: 6px;
}

.meta-title {
  color: #bfe9ff;
  font-weight: 600;
  margin-bottom: 8px;
}

.role { color: rgba(230,238,248,0.7); font-size: 13px; }

/* 中右列图片容器：垂直居中并扩展高度 */
.desc-mid, .desc-right {
  display: flex;
  align-items: center;   /* 关键：垂直居中 */
  justify-content: center;
  overflow: hidden;
}

/* 图片卡片改为填满列高度 */
.image-card {
  width: 100%;
  height: 100%; /* 关键：填满分配给该列的高度 */
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(0,0,0,0.25), rgba(255,255,255,0.02));
  box-shadow: 0 10px 24px rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 12px;
}

.image-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  border-radius: 6px;
}

/* 占位样式 */
.placeholder {
  color: rgba(200,220,230,0.6);
  font-size: 16px;
  text-align: center;
}

/* 窄屏下改为垂直堆叠 */
@media (max-width: 1000px) {
  .agent-desc {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
    height: auto;
  }
  .image-card { height: 220px; }
  .desc-left { align-self: stretch; }
}
</style>