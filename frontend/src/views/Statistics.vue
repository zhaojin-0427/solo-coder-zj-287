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

    <el-row :gutter="16" class="stat-row" style="margin-top:0">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">储能累计增益</div>
          <div class="value" style="color:#f59e0b">{{ (stats.total_storage_profit || 0).toLocaleString() }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计减少弃光</div>
          <div class="value" style="color:#22c55e">{{ (stats.total_reduced_curtailment_kwh || 0).toFixed(1) }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/cleaning')">
          <div class="label">累计清洁次数</div>
          <div class="value" style="color:#06b6d4">{{ stats.total_cleaning_count || 0 }}<span class="unit">次</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card" style="cursor:pointer" @click="$router.push('/cleaning')">
          <div class="label">清洁累计收益恢复</div>
          <div class="value" style="color:#8b5cf6">+{{ (stats.total_cleaning_revenue || 0).toLocaleString() }}<span class="unit">元</span></div>
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

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Lightning /></el-icon> 月度储能增益趋势
          </div>
          <v-chart :option="storageProfitOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Coin /></el-icon> 峰谷套利贡献分析
          </div>
          <v-chart :option="peakValleyArbitrageOption" class="chart-container" autoresize />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Brush /></el-icon> 月度清洁次数趋势
          </div>
          <v-chart :option="monthlyCleaningOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><DataLine /></el-icon> 清洁前后发电效率对比
          </div>
          <v-chart :option="cleaningEfficiencyCompareOption" class="chart-container" autoresize />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><TrendCharts /></el-icon> 各板组清洁收益贡献排行
            <span style="margin-left:auto;font-size:13px;font-weight:400;color:#94a3b8">累计恢复发电: +{{ (stats.total_cleaning_recovered_kwh || 0).toLocaleString() }} kWh</span>
          </div>
          <v-chart :option="panelCleaningRankingOption" style="width:100%;height:320px" autoresize />
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
import { DataLine, TrendCharts, PieChart, Histogram, Warning, Odometer, Lightning, Coin, Brush } from '@element-plus/icons-vue'
import api from '../api'
import { THEME_COLORS, CHART_COLOR_PALETTE, getHealthColor } from '../utils/constants'
import { formatMoney, formatKwh, formatPercent, formatNumber } from '../utils/format'
import { createLineChart, createBarChart, createDualAxisChart, createHorizontalBarChart } from '../utils/charts'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const months = ref(12)
const stats = ref({
  generation_trend: [], self_use_rate_trend: [], peak_valley_match: [],
  payback_pct: 0, total_investment: 0, total_revenue: 0, irr: 0, monthly_income: [],
  anomaly_trend: [], panel_group_health: [],
  storage_profit_trend: [], peak_valley_arbitrage: [],
  total_storage_profit: 0, total_reduced_curtailment_kwh: 0,
  monthly_cleaning_trend: [], cleaning_efficiency_compare: [], panel_cleaning_ranking: [],
  total_cleaning_count: 0, total_cleaning_revenue: 0, total_cleaning_recovered_kwh: 0
})

const generationTrendOption = computed(() => {
  const trend = stats.value.generation_trend || []
  return createBarChart({
    xData: trend.map(t => t.month),
    yAxisName: 'kWh',
    colorByIndex: true,
    series: {
      data: trend.map(t => t.kwh),
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 }
    }
  })
})

const incomeTrendOption = computed(() => {
  const trend = stats.value.monthly_income || []
  return createLineChart({
    xData: trend.map(t => t.month),
    yAxisName: '元',
    lineColor: THEME_COLORS.warning,
    areaStyle: true,
    areaColor: THEME_COLORS.warning,
    series: {
      data: trend.map(t => t.income),
      label: { show: true, position: 'top', formatter: '¥{c}', fontSize: 10 }
    }
  })
})

const selfUseRateOption = computed(() => {
  const trend = stats.value.self_use_rate_trend || []
  return createLineChart({
    xData: trend.map(t => t.month),
    yAxisName: '%',
    yMin: 0,
    yMax: 100,
    lineColor: THEME_COLORS.success,
    areaStyle: true,
    areaColor: THEME_COLORS.success,
    series: {
      data: trend.map(t => t.rate),
      markLine: {
        data: [{ yAxis: 50, label: { formatter: '目标50%' }, lineStyle: { color: THEME_COLORS.danger, type: 'dashed' } }]
      }
    },
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' }
  })
})

const peakValleyOption = computed(() => {
  const match = stats.value.peak_valley_match || []
  return createDualAxisChart({
    xData: match.map(m => m.month),
    leftYAxisName: 'kWh',
    rightYAxisName: '%',
    rightYMin: 0,
    rightYMax: 100,
    leftSeries: [
      { name: '峰时用电', type: 'bar', data: match.map(m => m.peak_kwh), itemStyle: { color: THEME_COLORS.warning } },
      { name: '谷时用电', type: 'bar', data: match.map(m => m.valley_kwh), itemStyle: { color: THEME_COLORS.primary } }
    ],
    rightSeries: [
      { name: '匹配度(%)', type: 'line', data: match.map(m => m.match_rate), smooth: true, itemStyle: { color: THEME_COLORS.success }, lineStyle: { width: 3 } }
    ]
  })
})

const anomalyTrendOption = computed(() => {
  const trend = stats.value.anomaly_trend || []
  return createBarChart({
    xData: trend.map(t => t.month),
    yAxisName: '次数',
    yAxis: { minInterval: 1 },
    series: {
      data: trend.map(t => t.count),
      itemStyle: {
        color: (params) => {
          if (params.value >= 20) return THEME_COLORS.danger
          if (params.value >= 10) return THEME_COLORS.orange
          if (params.value >= 5) return THEME_COLORS.warning
          return THEME_COLORS.success
        }
      },
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 10 }
    }
  })
})

const panelGroupHealthOption = computed(() => {
  const pgHealth = stats.value.panel_group_health || []
  const names = pgHealth.map(p => p.name)
  const scores = pgHealth.map(p => p.avg_health_score ?? 0)
  return createBarChart({
    xData: names,
    yAxisName: '分',
    yMin: 0,
    yMax: 100,
    series: {
      data: scores,
      itemStyle: {
        color: (params) => {
          if (params.value >= 90) return THEME_COLORS.success
          if (params.value >= 70) return THEME_COLORS.warning
          if (params.value >= 50) return THEME_COLORS.orange
          return THEME_COLORS.danger
        }
      },
      label: { show: true, position: 'top', formatter: '{c}', fontSize: 12, fontWeight: 600 },
      barWidth: '40%'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>平均健康评分: ${p.value}`
      }
    }
  })
})

const storageProfitOption = computed(() => {
  const trend = stats.value.storage_profit_trend || []
  return createBarChart({
    xData: trend.map(t => t.month),
    yAxisName: '元',
    series: {
      data: trend.map(t => t.profit),
      itemStyle: {
        color: (params) => params.value >= 0 ? THEME_COLORS.warning : THEME_COLORS.danger
      },
      label: {
        show: true, position: 'top',
        formatter: (p) => (p.value >= 0 ? '+' : '') + p.value,
        fontSize: 11, fontWeight: 600
      },
      markLine: {
        data: [{ type: 'average', name: '平均值', label: { formatter: '均值 ¥{c}' } }],
        lineStyle: { color: THEME_COLORS.purple, type: 'dashed' }
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>储能增益: ¥${p.value}`
      }
    }
  })
})

const peakValleyArbitrageOption = computed(() => {
  const arb = stats.value.peak_valley_arbitrage || []
  return createDualAxisChart({
    xData: arb.map(a => a.month),
    leftYAxisName: '元',
    rightYAxisName: 'kWh',
    leftSeries: [
      {
        name: '峰时节省', type: 'bar', stack: 'cost',
        data: arb.map(a => a.peak_saving),
        itemStyle: { color: THEME_COLORS.success }
      },
      {
        name: '谷电成本', type: 'bar', stack: 'cost',
        data: arb.map(a => -a.valley_cost),
        itemStyle: { color: THEME_COLORS.orange },
        label: {
          show: true, position: 'inside',
          formatter: (p) => p.value === 0 ? '' : ('-¥' + Math.abs(p.value).toFixed(0)),
          fontSize: 10, color: '#fff'
        }
      },
      {
        name: '净收益', type: 'line',
        data: arb.map(a => a.net_profit),
        smooth: true, itemStyle: { color: THEME_COLORS.purple },
        lineStyle: { width: 3 },
        label: { show: true, position: 'top', formatter: '¥{c}', fontSize: 10, fontWeight: 600 }
      }
    ],
    rightSeries: [
      {
        name: '减少弃光(kWh)', type: 'bar',
        data: arb.map(a => a.reduced_curtailment_kwh),
        itemStyle: { color: THEME_COLORS.info, opacity: 0.6 },
        barWidth: '20%'
      }
    ]
  })
})

const monthlyCleaningOption = computed(() => {
  const trend = stats.value.monthly_cleaning_trend || []
  return createBarChart({
    xData: trend.map(t => t.month),
    yAxisName: '次',
    yAxis: { minInterval: 1 },
    series: {
      data: trend.map(t => t.count),
      itemStyle: {
        color: (params) => {
          const colors = [THEME_COLORS.info, THEME_COLORS.primary, THEME_COLORS.purple, THEME_COLORS.warning, THEME_COLORS.success, THEME_COLORS.orange]
          return colors[params.dataIndex % colors.length]
        },
        borderRadius: [4, 4, 0, 0]
      },
      label: { show: true, position: 'top', formatter: '{c}次', fontSize: 12, fontWeight: 600 },
      barWidth: '40%'
    },
    tooltip: { trigger: 'axis', formatter: '{b}<br/>清洁次数: {c} 次' }
  })
})

const cleaningEfficiencyCompareOption = computed(() => {
  const data = stats.value.cleaning_efficiency_compare || []
  return createBarChart({
    xData: data.map(d => d.month),
    yAxisName: '%',
    yMin: 0,
    yMax: 100,
    legend: { data: ['清洁前效率', '清洁后效率'], top: 0 },
    series: [
      {
        name: '清洁前效率',
        data: data.map(d => d.before_cleaning),
        itemStyle: { color: THEME_COLORS.danger },
        label: { show: true, position: 'top', formatter: '{c}%', fontSize: 10 }
      },
      {
        name: '清洁后效率',
        data: data.map(d => d.after_cleaning),
        itemStyle: { color: THEME_COLORS.success },
        label: { show: true, position: 'top', formatter: '{c}%', fontSize: 10 }
      }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        let html = params[0].axisValue + '<br/>'
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${p.value}%<br/>`
        })
        const imp = data[params[0].dataIndex]
        if (imp && imp.improvement) {
          html += `<b style="color:${THEME_COLORS.success}">提升: +${imp.improvement}%</b>`
        }
        return html
      }
    }
  })
})

const panelCleaningRankingOption = computed(() => {
  const ranking = stats.value.panel_cleaning_ranking || []
  const sorted = [...ranking].sort((a, b) => a.revenue - b.revenue)
  const names = sorted.map(r => r.name)
  const revenues = sorted.map(r => r.revenue)
  const recovered = sorted.map(r => r.recovered_kwh)
  return createHorizontalBarChart({
    yData: names,
    xAxisNames: ['元', 'kWh'],
    legend: { data: ['收益恢复(元)', '发电恢复(kWh)'], top: 0 },
    series: [
      {
        name: '收益恢复(元)',
        data: revenues,
        itemStyle: { color: THEME_COLORS.purple, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', formatter: '+¥{c}', fontSize: 11, fontWeight: 600 }
      },
      {
        name: '发电恢复(kWh)',
        data: recovered,
        itemStyle: { color: THEME_COLORS.info, opacity: 0.7, borderRadius: [0, 4, 4, 0] }
      }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const idx = params[0].dataIndex
        const item = sorted[idx]
        return `${item.name}<br/>
          清洁次数: ${item.count} 次<br/>
          收益恢复: +¥${item.revenue}<br/>
          发电恢复: +${item.recovered_kwh} kWh`
      }
    }
  })
})

const loadData = async () => {
  try {
    stats.value = await api.statistics(months.value)
  } catch (e) { console.error(e) }
}

onMounted(loadData)
</script>
