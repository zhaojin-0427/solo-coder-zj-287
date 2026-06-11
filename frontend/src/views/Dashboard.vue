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
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/storage')">
          <div class="label">当前电池SOC</div>
          <div class="value" :style="{color: socColor(data.storage_today_soc)}">{{ data.storage_today_soc || '--' }}<span class="unit">%</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/storage')">
          <div class="label">今日充电量</div>
          <div class="value" style="color:#06b6d4">{{ data.storage_today_charge_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/storage')">
          <div class="label">今日放电量</div>
          <div class="value" style="color:#f97316">{{ data.storage_today_discharge_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/storage')">
          <div class="label">今日储能增益</div>
          <div class="value" :style="{color: (data.storage_today_profit || 0) >= 0 ? '#22c55e' : '#ef4444'}">{{ data.storage_today_profit || 0 }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/storage')">
          <div class="label">本月储能增益</div>
          <div class="value" :style="{color: (data.storage_month_profit || 0) >= 0 ? '#f59e0b' : '#ef4444'}">{{ data.storage_month_profit || 0 }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">储能总容量</div>
          <div class="value" style="color:#8b5cf6">{{ data.storage_total_capacity_kwh || 0 }}<span class="unit">kWh</span></div>
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

    <el-row :gutter="16" class="stat-row" style="margin-top:16px">
      <el-col :xs="12" :sm="6">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/cleaning')">
          <div class="label">近期待清洁板组</div>
          <div class="value" style="color:#f97316">{{ data.upcoming_cleaning_count || 0 }}<span class="unit">组</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/cleaning')">
          <div class="label">最近清洁收益恢复</div>
          <div class="value" style="color:#22c55e">+{{ data.latest_cleaning_revenue || 0 }}<span class="unit">元</span></div>
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
import { ALERT_LEVEL_LABELS, ALERT_LEVEL_COLORS, getSocColor, getHealthColor, THEME_COLORS } from '../utils/constants'
import { formatMonthDay } from '../utils/format'
import { createDualAxisChart, createPieChart, createLineChart } from '../utils/charts'

use([CanvasRenderer, BarChart, LineChart, PieChartType, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const levelLabelMap = ALERT_LEVEL_LABELS
const levelColorMap = ALERT_LEVEL_COLORS

const data = ref({
  total_capacity_kw: 0, today_generation_kwh: 0, today_theoretical_kwh: 0,
  today_efficiency_rate: 0, month_generation_kwh: 0, month_income: 0,
  total_income: 0, total_investment: 0, self_use_rate: 0, payback_pct: 0,
  panel_group_count: 0, inverter_count: 0, recent_7_days: [],
  unhandled_alert_count: 0, highest_alert_level: 'normal', health_score_trend: [],
  storage_battery_count: 0, storage_total_capacity_kwh: 0,
  storage_today_soc: 0, storage_today_charge_kwh: 0,
  storage_today_discharge_kwh: 0, storage_today_profit: 0,
  storage_month_profit: 0,
  upcoming_cleaning_count: 0, latest_cleaning_revenue: 0
})

const socColor = getSocColor

const todayHealthScore = computed(() => {
  const trend = data.value.health_score_trend
  if (trend && trend.length > 0) {
    const todayEntry = trend[trend.length - 1]
    return todayEntry.avg_health_score ?? '--'
  }
  return '--'
})

const todayHealthColor = computed(() => getHealthColor(todayHealthScore.value))

const paybackColor = computed(() => {
  const pct = data.value.payback_pct
  if (pct >= 80) return THEME_COLORS.success
  if (pct >= 50) return THEME_COLORS.warning
  return THEME_COLORS.primary
})

const weekChartOption = computed(() => {
  const days = data.value.recent_7_days || []
  return createDualAxisChart({
    xData: days.map(d => formatMonthDay(d.date)),
    leftYAxisName: 'kWh',
    rightYAxisName: '元',
    leftSeries: [
      { name: '实际发电', type: 'bar', data: days.map(d => d.actual_kwh), itemStyle: { color: THEME_COLORS.success } },
      { name: '理论发电', type: 'bar', data: days.map(d => d.theoretical_kwh), itemStyle: { color: THEME_COLORS.primary, opacity: 0.5 } }
    ],
    rightSeries: [
      { name: '收益', type: 'line', data: days.map(d => d.income), smooth: true, itemStyle: { color: THEME_COLORS.warning }, lineStyle: { width: 3 } }
    ],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } }
  })
})

const selfUsePieOption = computed(() => createPieChart({
  data: [
    { value: data.value.self_use_rate, name: '自用', itemStyle: { color: THEME_COLORS.success } },
    { value: 100 - data.value.self_use_rate, name: '上网', itemStyle: { color: THEME_COLORS.primary } }
  ]
}))

const healthTrendOption = computed(() => {
  const trend = data.value.health_score_trend || []
  return createLineChart({
    xData: trend.map(d => formatMonthDay(d.date)),
    yAxisName: '分',
    yMin: 0,
    yMax: 100,
    lineColor: THEME_COLORS.purple,
    areaStyle: true,
    areaColor: THEME_COLORS.purple,
    series: {
      data: trend.map(d => d.avg_health_score),
      markLine: {
        data: [{ yAxis: 70, label: { formatter: '警戒线70' }, lineStyle: { color: THEME_COLORS.danger, type: 'dashed' } }]
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>健康评分: ${p.value ?? '无数据'}`
      }
    }
  })
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
