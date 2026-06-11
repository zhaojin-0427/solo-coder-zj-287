<template>
  <div>
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">总装机容量</div>
          <div class="value" style="color:#f59e0b">{{ data.total_capacity_kw }}<span class="unit">kW</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">今日发电量</div>
          <div class="value" style="color:#22c55e">{{ data.today_generation_kwh }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">今日理论发电</div>
          <div class="value" style="color:#3b82f6">{{ data.today_theoretical_kwh }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">今日效率</div>
          <div class="value" style="color:#8b5cf6">{{ data.today_efficiency_rate }}<span class="unit">%</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">本月发电量</div>
          <div class="value" style="color:#06b6d4">{{ data.month_generation_kwh }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <div class="stat-card">
          <div class="label">本月收益</div>
          <div class="value" style="color:#ef4444">{{ data.month_income }}<span class="unit">元</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stat-row" style="margin-top:16px">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计收益</div>
          <div class="value" style="color:#f59e0b">{{ data.total_income }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">总投资</div>
          <div class="value" style="color:#64748b">{{ data.total_investment }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">自用率</div>
          <div class="value" style="color:#22c55e">{{ data.self_use_rate }}<span class="unit">%</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">回本进度</div>
          <div class="value" style="color:#8b5cf6">{{ data.payback_pct }}<span class="unit">%</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stat-row" style="margin-top:16px">
      <el-col :xs="12" :sm="8">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/alerts')">
          <div class="label">未处理告警</div>
          <div class="value" style="color:#ef4444">{{ data.unhandled_alert_count || 0 }}<span class="unit">条</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/alerts')">
          <div class="label">最高告警等级</div>
          <div class="value" :style="{color: levelColorMap[data.highest_alert_level] || '#22c55e'}">{{ levelLabelMap[data.highest_alert_level] || '正常' }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8">
        <div class="stat-card">
          <div class="label">今日平均健康评分</div>
          <div class="value" :style="{color: todayHealthColor}">{{ todayHealthScore }}<span class="unit">分</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="16">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><TrendCharts /></el-icon> 近7日发电量与收益趋势
          </div>
          <v-chart :option="weekChartOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><PieChart /></el-icon> 自用/上网比例
          </div>
          <v-chart :option="selfUsePieOption" class="chart-container" autoresize />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="8">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><DataLine /></el-icon> 近7日健康评分趋势
          </div>
          <v-chart :option="healthTrendOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Cpu /></el-icon> 设备概况
          </div>
          <div class="device-info">
            <div class="device-item">
              <span class="device-label">光伏板组数</span>
              <span class="device-value">{{ data.panel_group_count }} 组</span>
            </div>
            <div class="device-item">
              <span class="device-label">逆变器数量</span>
              <span class="device-value">{{ data.inverter_count }} 台</span>
            </div>
            <div class="device-item">
              <span class="device-label">总装机容量</span>
              <span class="device-value">{{ data.total_capacity_kw }} kW</span>
            </div>
            <div class="device-item">
              <span class="device-label">单位投资</span>
              <span class="device-value">~4000 元/kW</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Timer /></el-icon> 回本进度
          </div>
          <el-progress
            :percentage="data.payback_pct"
            :stroke-width="24"
            :color="paybackColor"
            style="margin-top: 30px;"
          />
          <div style="display:flex;justify-content:space-between;margin-top:12px;color:#64748b;font-size:13px;">
            <span>累计收益: ¥{{ data.total_income }}</span>
            <span>总投资: ¥{{ data.total_investment }}</span>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart as PieChartType } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { TrendCharts, Cpu, DataLine, PieChart, Timer } from '@element-plus/icons-vue'
import api from '../api'

use([CanvasRenderer, BarChart, LineChart, PieChartType, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const levelLabelMap = { normal: '正常', low: '低', medium: '中', high: '高', critical: '严重' }
const levelColorMap = { normal: '#22c55e', low: '#3b82f6', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' }

const data = ref({
  total_capacity_kw: 0, today_generation_kwh: 0, today_theoretical_kwh: 0,
  today_efficiency_rate: 0, month_generation_kwh: 0, month_income: 0,
  total_income: 0, total_investment: 0, self_use_rate: 0, payback_pct: 0,
  panel_group_count: 0, inverter_count: 0, recent_7_days: [],
  unhandled_alert_count: 0, highest_alert_level: 'normal', health_score_trend: []
})

const todayHealthScore = computed(() => {
  const trend = data.value.health_score_trend
  if (trend && trend.length > 0) {
    const todayEntry = trend[trend.length - 1]
    return todayEntry.avg_health_score ?? '--'
  }
  return '--'
})

const todayHealthColor = computed(() => {
  const score = todayHealthScore.value
  if (score === '--') return '#64748b'
  if (score >= 90) return '#22c55e'
  if (score >= 70) return '#f59e0b'
  return '#ef4444'
})

const paybackColor = computed(() => {
  const pct = data.value.payback_pct
  if (pct >= 80) return '#22c55e'
  if (pct >= 50) return '#f59e0b'
  return '#3b82f6'
})

const weekChartOption = computed(() => {
  const days = data.value.recent_7_days
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['实际发电', '理论发电', '收益'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: days.map(d => d.date.slice(5)) },
    yAxis: [
      { type: 'value', name: 'kWh', position: 'left' },
      { type: 'value', name: '元', position: 'right' }
    ],
    series: [
      { name: '实际发电', type: 'bar', data: days.map(d => d.actual_kwh), itemStyle: { color: '#22c55e' } },
      { name: '理论发电', type: 'bar', data: days.map(d => d.theoretical_kwh), itemStyle: { color: '#3b82f6', opacity: 0.5 } },
      { name: '收益', type: 'line', yAxisIndex: 1, data: days.map(d => d.income), smooth: true, itemStyle: { color: '#f59e0b' }, lineStyle: { width: 3 } }
    ]
  }
})

const selfUsePieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
    data: [
      { value: data.value.self_use_rate, name: '自用', itemStyle: { color: '#22c55e' } },
      { value: 100 - data.value.self_use_rate, name: '上网', itemStyle: { color: '#3b82f6' } }
    ],
    label: { formatter: '{b}\n{d}%' },
    emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' } }
  }]
}))

const healthTrendOption = computed(() => {
  const trend = data.value.health_score_trend || []
  return {
    tooltip: { trigger: 'axis', formatter: (params) => {
      const p = params[0]
      return `${p.name}<br/>健康评分: ${p.value ?? '无数据'}`
    }},
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trend.map(d => d.date.slice(5)) },
    yAxis: { type: 'value', name: '分', min: 0, max: 100 },
    series: [{
      type: 'line', data: trend.map(d => d.avg_health_score), smooth: true,
      itemStyle: { color: '#8b5cf6' }, lineStyle: { width: 3 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(139,92,246,0.3)' }, { offset: 1, color: 'rgba(139,92,246,0.02)' }] } },
      markLine: { data: [{ yAxis: 70, label: { formatter: '警戒线70' }, lineStyle: { color: '#ef4444', type: 'dashed' } }] }
    }]
  }
})

onMounted(async () => {
  try {
    data.value = await api.dashboard()
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.stat-row .el-col { min-width: 0; }
.device-info { padding: 10px 0; }
.device-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 0; border-bottom: 1px solid #f1f5f9;
}
.device-item:last-child { border-bottom: none; }
.device-label { color: #64748b; font-size: 14px; }
.device-value { color: #1e293b; font-weight: 600; font-size: 15px; }
</style>
