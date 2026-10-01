<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, DataZoomComponent, MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart, PieChart, BarChart,
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, DataZoomComponent, MarkLineComponent,
  CanvasRenderer,
])

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '280px' },
})

const el = ref(null)
let chart = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option, true)
}

let resizeTimer = null
function resize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => { chart?.resize() }, 500)
}

onMounted(async () => {
  await nextTick()
  render()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="el" class="chart" :style="{ height }"></div>
</template>

<style scoped>
.chart { width: 100%; }
</style>