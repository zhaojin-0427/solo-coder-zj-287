<template>
  <div>
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计发电收益</div>
          <div class="value" style="color:#f59e0b">{{ summary.totalIncome }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计自用节省</div>
          <div class="value" style="color:#22c55e">{{ summary.selfUseSaving }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计上网收益</div>
          <div class="value" style="color:#3b82f6">{{ summary.gridSellIncome }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">日均收益</div>
          <div class="value" style="color:#8b5cf6">{{ summary.avgDaily }}<span class="unit">元</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
              <el-icon><Wallet /></el-icon> 收益明细
            </div>
            <div style="display:flex;gap:8px">
              <el-select v-model="filterPanelGroup" placeholder="全部板组" clearable size="small" style="width:150px" @change="loadData">
                <el-option v-for="pg in panelGroups" :key="pg.id" :label="pg.name" :value="pg.id" />
              </el-select>
              <el-date-picker v-model="filterDateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" size="small" @change="loadData" />
            </div>
          </div>
          <el-table :data="records" stripe style="width:100%" max-height="500" show-summary>
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="panel_group_name" label="光伏板组" width="150" />
            <el-table-column prop="generation_kwh" label="发电量(kWh)" width="120">
              <template #default="{ row }">{{ row.generation_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="self_use_kwh" label="自用(kWh)" width="110">
              <template #default="{ row }">{{ row.self_use_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="grid_sell_kwh" label="上网(kWh)" width="110">
              <template #default="{ row }">{{ row.grid_sell_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="self_use_saving" label="自用节省(元)" width="120">
              <template #default="{ row }">
                <span style="color:#22c55e">{{ row.self_use_saving?.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="grid_sell_income" label="上网收益(元)" width="120">
              <template #default="{ row }">
                <span style="color:#3b82f6">{{ row.grid_sell_income?.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="total_income" label="合计收益(元)" width="120">
              <template #default="{ row }">
                <span style="color:#f59e0b;font-weight:600">{{ row.total_income?.toFixed(2) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><TrendCharts /></el-icon> 收益构成分析
          </div>
          <v-chart :option="compositionChartOption" class="chart-container" autoresize />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-card-title">
            <el-icon><Coin /></el-icon> 电价配置
          </div>
          <el-table :data="prices" stripe style="width:100%">
            <el-table-column prop="price_type" label="类型" width="160">
              <template #default="{ row }">{{ priceTypeMap[row.price_type] || row.price_type }}</template>
            </el-table-column>
            <el-table-column prop="price" label="价格(元/kWh)" width="140">
              <template #default="{ row }">{{ row.price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="effective_date" label="生效日期" width="140" />
          </el-table>
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
import { PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { Wallet, TrendCharts, Coin } from '@element-plus/icons-vue'
import api from '../api'

use([CanvasRenderer, PieChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const panelGroups = ref([])
const records = ref([])
const prices = ref([])
const filterPanelGroup = ref(null)
const filterDateRange = ref(null)

const priceTypeMap = {
  grid_buy_peak: '电网购电-峰时',
  grid_buy_valley: '电网购电-谷时',
  grid_buy_shoulder: '电网购电-平时',
  grid_sell: '光伏上网电价'
}

const summary = computed(() => {
  const totalIncome = records.value.reduce((s, r) => s + (r.total_income || 0), 0)
  const selfUseSaving = records.value.reduce((s, r) => s + (r.self_use_saving || 0), 0)
  const gridSellIncome = records.value.reduce((s, r) => s + (r.grid_sell_income || 0), 0)
  const days = new Set(records.value.map(r => r.date)).size || 1
  return {
    totalIncome: totalIncome.toFixed(2),
    selfUseSaving: selfUseSaving.toFixed(2),
    gridSellIncome: gridSellIncome.toFixed(2),
    avgDaily: (totalIncome / days).toFixed(2),
  }
})

const compositionChartOption = computed(() => {
  const selfUse = records.value.reduce((s, r) => s + (r.self_use_saving || 0), 0)
  const gridSell = records.value.reduce((s, r) => s + (r.grid_sell_income || 0), 0)
  return {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
      data: [
        { value: selfUse.toFixed(2), name: '自用节省', itemStyle: { color: '#22c55e' } },
        { value: gridSell.toFixed(2), name: '上网收益', itemStyle: { color: '#3b82f6' } }
      ],
      label: { formatter: '{b}\n¥{c}' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' } }
    }]
  }
})

const loadData = async () => {
  try {
    const params = {}
    if (filterPanelGroup.value) params.panel_group = filterPanelGroup.value
    if (filterDateRange.value && filterDateRange.value[0]) params.date_from = filterDateRange.value[0]
    if (filterDateRange.value && filterDateRange.value[1]) params.date_to = filterDateRange.value[1]
    records.value = await api.revenueRecords.list(params)
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  panelGroups.value = await api.panelGroups.list()
  prices.value = await api.electricityPrices.list()
  await loadData()
})
</script>
