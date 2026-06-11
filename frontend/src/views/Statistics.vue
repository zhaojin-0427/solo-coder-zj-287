<template>
  <div>
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="24">
        <div class="page-card" style="display:flex;align-items:center;gap:16px;padding:12px 20px">
          <span style="color:#64748b;font-size:14px">统计周期:</span>
          <el-radio-group v-model="months" @change="loadData">
            <el-radio-button :value="3">近3月</el-radio-button>
            <el-radio-button :value="6">近6月</el-radio-button>
            <el-radio-button :value="12">近12月</el-radio-button>
          </el-radio-group>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">总投资</div>
          <div class="value" style="color:#64748b">{{ stats.total_investment?.toLocaleString() }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计收益</div>
          <div class="value" style="color:#f59e0b">{{ stats.total_revenue?.toLocaleString() }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">回本进度</div>
          <div class="value" style="color:#22c55e">{{ stats.payback_pct }}<span class="unit">%</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">IRR</div>
          <div class="value" style="color:#8b5cf6">{{ stats.irr }}<span class="unit">%</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><DataLine /></el-icon> 月度发电量趋势
          </div>
          <v-chart :option="generationTrendOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><TrendCharts /></el-icon> 月度收益趋势
          </div>
          <v-chart :option="incomeTrendOption" class="chart-container" autoresize />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><PieChart /></el-icon> 自用率变化趋势
          </div>
          <v-chart :option="selfUseRateOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Histogram /></el-icon> 峰谷用电匹配度
          </div>
          <v-chart :option="peakValleyOption" class="chart-container" autoresize />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Warning /></el-icon> 月度异常次数趋势
          </div>
          <v-chart :option="anomalyTrendOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Odometer /></el-icon> 各板组健康评分对比
          </div>
          <v-chart :option="panelGroupHealthOption" class="chart-container" autoresize />
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
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { DataLine, TrendCharts, PieChart, Histogram, Warning, Odometer } from '@element-plus/icons-vue'
import api from '../api'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const months = ref(12)
const stats = ref({
  generation_trend: [], self_use_rate_trend: [], peak_valley_match: [],
  payback_pct: 0, total_investment: 0, total_revenue: 0, irr: 0, monthly_income: [],
  anomaly_trend: [], panel_group_health: []
})

const generationTrendOption = computed(() => {
  const trend = stats.value.generation_trend
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trend.map(t => t.month) },
    yAxis: { type: 'value', name: 'kWh' },
    series: [{
      type: 'bar', data: trend.map(t => t.kwh), itemStyle: {
        color: (params) => {
          const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4', '#ef4444', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16', '#0ea5e9']
          return colors[params.dataIndex % colors.length]
        }
      },
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 }
    }]
  }
})

const incomeTrendOption = computed(() => {
  const trend = stats.value.monthly_income
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trend.map(t => t.month) },
    yAxis: { type: 'value', name: '元' },
    series: [{
      type: 'line', data: trend.map(t => t.income), smooth: true,
      itemStyle: { color: '#f59e0b' }, lineStyle: { width: 3 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(245,158,11,0.3)' }, { offset: 1, color: 'rgba(245,158,11,0.02)' }] } },
      label: { show: true, position: 'top', formatter: '¥{c}', fontSize: 10 }
    }]
  }
})

const selfUseRateOption = computed(() => {
  const trend = stats.value.self_use_rate_trend
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trend.map(t => t.month) },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: [{
      type: 'line', data: trend.map(t => t.rate), smooth: true,
      itemStyle: { color: '#22c55e' }, lineStyle: { width: 3 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(34,197,94,0.3)' }, { offset: 1, color: 'rgba(34,197,94,0.02)' }] } },
      markLine: { data: [{ yAxis: 50, label: { formatter: '目标50%' }, lineStyle: { color: '#ef4444', type: 'dashed' } }] }
    }]
  }
})

const peakValleyOption = computed(() => {
  const match = stats.value.peak_valley_match
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['峰时用电', '谷时用电', '匹配度(%)'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: match.map(m => m.month) },
    yAxis: [
      { type: 'value', name: 'kWh', position: 'left' },
      { type: 'value', name: '%', min: 0, max: 100, position: 'right' }
    ],
    series: [
      { name: '峰时用电', type: 'bar', data: match.map(m => m.peak_kwh), itemStyle: { color: '#f59e0b' } },
      { name: '谷时用电', type: 'bar', data: match.map(m => m.valley_kwh), itemStyle: { color: '#3b82f6' } },
      { name: '匹配度(%)', type: 'line', yAxisIndex: 1, data: match.map(m => m.match_rate), smooth: true, itemStyle: { color: '#22c55e' }, lineStyle: { width: 3 } }
    ]
  }
})

const anomalyTrendOption = computed(() => {
  const trend = stats.value.anomaly_trend || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trend.map(t => t.month) },
    yAxis: { type: 'value', name: '次数', minInterval: 1 },
    series: [{
      type: 'bar', data: trend.map(t => t.count),
      itemStyle: {
        color: (params) => {
          if (params.value >= 20) return '#ef4444'
          if (params.value >= 10) return '#f97316'
          if (params.value >= 5) return '#f59e0b'
          return '#22c55e'
        }
      },
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 }
    }]
  }
})

const panelGroupHealthOption = computed(() => {
  const pgHealth = stats.value.panel_group_health || []
  const names = pgHealth.map(p => p.name)
  const scores = pgHealth.map(p => p.avg_health_score ?? 0)
  return {
    tooltip: { trigger: 'axis', formatter: (params) => {
      const p = params[0]
      return `${p.name}<br/>平均健康评分: ${p.value}`
    }},
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', name: '分', min: 0, max: 100 },
    series: [{
      type: 'bar', data: scores,
      itemStyle: {
        color: (params) => {
          if (params.value >= 90) return '#22c55e'
          if (params.value >= 70) return '#f59e0b'
          if (params.value >= 50) return '#f97316'
          return '#ef4444'
        }
      },
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 12, fontWeight: 600 },
      barWidth: '40%'
    }]
  }
})

const loadData = async () => {
  try {
    stats.value = await api.statistics(months.value)
  } catch (e) { console.error(e) }
}

onMounted(loadData)
</script>
