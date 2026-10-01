<script setup>
import { RouterView } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

// PERF-001：改为按需引入后不再有 app.use(ElementPlus) 提供的全局 locale，
// 中文语言包改由 el-config-provider 在最外层统一注入。
</script>

<template>
  <el-config-provider :locale="zhCn">
    <RouterView />
  </el-config-provider>
</template>

<style scoped></style>