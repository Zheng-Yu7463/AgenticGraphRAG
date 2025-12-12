
<template>
  <!-- 轻量顶层容器：只负责路由视图与过渡 -->
  <div id="vpp-root">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup lang="ts">
// 无需额外逻辑
</script>

<style>
/* 路由切换过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity .36s ease, transform .36s cubic-bezier(.2,.9,.3,1);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
.fade-enter-to,
.fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* 根容器不施加额外外边距/padding，页面布局与全局样式由 global.css 控制 */
#vpp-root {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>