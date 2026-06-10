<template>
  <div>
    <el-row :gutter="16">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">总投资</div>
          <div class="value" style="color:#64748b">{{ data.total_investment }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计收益</div>
          <div class="value" style="color:#f59e0b">{{ data.total_revenue }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">剩余回本</div>
          <div class="value" style="color:#ef4444">{{ data.remaining_amount }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">预计回本日期</div>
          <div class="value" style="color:#8b5cf6;font-size:20px">{{ data.payback_date || '-' }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="8">
        <div class="page-card" style="text-align:center;padding:30px 20px">
          <div class="page-card-title" style="justify-content:center">
            <el-icon><Timer /></el-icon> 回本进度
          </div>
          <el-progress type="dashboard" :percentage="Math.min(data.payback_pct, 100)" :width="180" :color="paybackColor">
            <template #default>
              <div style="font-size:28px;font-weight:700" :style="{color:paybackColor}">{{ data.payback_pct }}%</div>
            </template>
          </el-progress>
          <div style="margin-top:16px;color:#64748b;font-size:13px">距离完全回本还需约 <b style="color:#1e293b">{{ data.days_to_payback }}</b> 天</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card" style="text-align:center;padding:30px 20px">
          <div class="page-card-title" style="justify-content:center">
            <el-icon><TrendCharts /></el-icon> IRR 内部收益率
          </div>
          <div style="margin-top:30px">
            <div style="font-size:48px;font-weight:700;color:#22c55e">{{ data.irr }}<span style="font-size:20px;color:#94a3b8">%</span></div>
          </div>
          <div style="margin-top:16px;color:#64748b;font-size:13px">年化收益估算</div>
          <div style="margin-top:20px;padding:16px;background:#f8fafc;border-radius:8px;text-align:left">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
              <span style="color:#64748b">年均收入</span>
              <span style="font-weight:600">¥{{ data.annual_income }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
              <span style="color:#64748b">日均收入</span>
              <span style="font-weight:600">¥{{ data.avg_daily_income }}</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span style="color:#64748b">NPV (5%折现)</span>
              <span style="font-weight:600" :style="{color: data.npv >= 0 ? '#22c55e' : '#ef4444'}">¥{{ data.npv }}</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card" style="text-align:center;padding:30px 20px">
          <div class="page-card-title" style="justify-content:center">
            <el-icon><Coin /></el-icon> 投资概览
          </div>
          <div style="margin-top:20px;padding:16px;background:#f8fafc;border-radius:8px;text-align:left">
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
              <span style="color:#64748b">总投资额</span>
              <span style="font-weight:600;color:#1e293b">¥{{ data.total_investment?.toLocaleString() }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
              <span style="color:#64748b">累计收益</span>
              <span style="font-weight:600;color:#f59e0b">¥{{ data.total_revenue?.toLocaleString() }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:12px">
              <span style="color:#64748b">剩余回本</span>
              <span style="font-weight:600;color:#ef4444">¥{{ data.remaining_amount?.toLocaleString() }}</span>
            </div>
            <el-divider />
            <div style="display:flex;justify-content:space-between">
              <span style="color:#64748b">预计回本天数</span>
              <span style="font-weight:600;color:#8b5cf6">{{ data.days_to_payback }} 天</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><DataLine /></el-icon> 回本进度预测（未来12个月）
          </div>
          <v-chart :option="projectionChartOption" class="chart-container" autoresize />
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
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { Timer, TrendCharts, Coin, DataLine } from '@element-plus/icons-vue'
import api from '../api'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const data = ref({
  total_investment: 0, total_revenue: 0, avg_daily_income: 0,
  payback_pct: 0, remaining_amount: 0, days_to_payback: 0,
  payback_date: null, irr: 0, npv: 0, annual_income: 0,
  monthly_projection: []
})

const paybackColor = computed(() => {
  const pct = data.value.payback_pct
  if (pct >= 80) return '#22c55e'
  if (pct >= 50) return '#f59e0b'
  return '#3b82f6'
})

const projectionChartOption = computed(() => {
  const proj = data.value.monthly_projection
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['回本进度(%)', '累计收益(元)'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: proj.map(p => p.month) },
    yAxis: [
      { type: 'value', name: '%', min: 0, max: 100, position: 'left' },
      { type: 'value', name: '元', position: 'right' }
    ],
    series: [
      {
        name: '回本进度(%)', type: 'line', data: proj.map(p => p.projected_pct),
        smooth: true, itemStyle: { color: '#f59e0b' }, lineStyle: { width: 3 },
        markLine: { data: [{ yAxis: 100, label: { formatter: '回本线' }, lineStyle: { color: '#22c55e', type: 'dashed' } }] }
      },
      {
        name: '累计收益(元)', type: 'bar', yAxisIndex: 1,
        data: proj.map(p => p.projected_revenue),
        itemStyle: { color: '#3b82f6', opacity: 0.6 }
      }
    ]
  }
})

onMounted(async () => {
  try {
    data.value = await api.paybackPrediction()
  } catch (e) { console.error(e) }
})
</script>
