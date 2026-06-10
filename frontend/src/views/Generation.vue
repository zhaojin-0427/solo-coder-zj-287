<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
              <el-icon><DataLine /></el-icon> 发电数据录入
            </div>
            <div style="display:flex;gap:8px">
              <el-date-picker v-model="importDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" size="small" />
              <el-select v-model="importPanelGroup" placeholder="选择光伏板组" size="small" style="width:160px">
                <el-option v-for="pg in panelGroups" :key="pg.id" :label="pg.name" :value="pg.id" />
              </el-select>
              <el-input-number v-model="importKwh" :min="0" :precision="2" placeholder="发电量(kWh)" size="small" style="width:140px" />
              <el-button type="primary" @click="handleImport" :loading="importing" size="small">导入数据</el-button>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
              <el-icon><TrendCharts /></el-icon> 发电记录
            </div>
            <div style="display:flex;gap:8px">
              <el-select v-model="filterPanelGroup" placeholder="全部板组" clearable size="small" style="width:150px" @change="loadData">
                <el-option v-for="pg in panelGroups" :key="pg.id" :label="pg.name" :value="pg.id" />
              </el-select>
              <el-date-picker v-model="filterDateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" size="small" @change="loadData" />
            </div>
          </div>
          <el-table :data="records" stripe style="width:100%" max-height="500">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="panel_group_name" label="光伏板组" width="150" />
            <el-table-column prop="actual_kwh" label="实际发电(kWh)" width="130">
              <template #default="{ row }">{{ row.actual_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="theoretical_kwh" label="理论发电(kWh)" width="130">
              <template #default="{ row }">{{ row.theoretical_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="效率(%)" width="100">
              <template #default="{ row }">
                <el-tag :type="row.theoretical_kwh > 0 ? (row.actual_kwh / row.theoretical_kwh >= 0.8 ? 'success' : 'warning') : 'info'" size="small">
                  {{ row.theoretical_kwh > 0 ? (row.actual_kwh / row.theoretical_kwh * 100).toFixed(1) : '-' }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="peak_kwh" label="峰时(kWh)" width="110">
              <template #default="{ row }">{{ row.peak_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="valley_kwh" label="谷时(kWh)" width="110">
              <template #default="{ row }">{{ row.valley_kwh?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="sunshine_hours" label="日照时数" width="100">
              <template #default="{ row }">{{ row.sunshine_hours?.toFixed(1) }}</template>
            </el-table-column>
          </el-table>
          <div style="margin-top:16px;text-align:right">
            <el-pagination
              v-model:current-page="page"
              :page-size="pageSize"
              :total="total"
              layout="total, prev, pager, next"
              @current-change="loadData"
            />
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { DataLine, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const panelGroups = ref([])
const records = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

const importDate = ref('')
const importPanelGroup = ref(null)
const importKwh = ref(0)
const importing = ref(false)
const filterPanelGroup = ref(null)
const filterDateRange = ref(null)

const loadData = async () => {
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
    }
    if (filterPanelGroup.value) params.panel_group = filterPanelGroup.value
    if (filterDateRange.value && filterDateRange.value[0]) params.date_from = filterDateRange.value[0]
    if (filterDateRange.value && filterDateRange.value[1]) params.date_to = filterDateRange.value[1]
    const data = await api.dailyGeneration.list(params)
    records.value = data.results || data
    total.value = data.count !== undefined ? data.count : (data.length || 0)
  } catch (e) { console.error(e) }
}

const handlePageChange = (p) => {
  page.value = p
  loadData()
}

const handleImport = async () => {
  if (!importDate.value || !importPanelGroup.value) {
    ElMessage.warning('请选择日期和光伏板组')
    return
  }
  importing.value = true
  try {
    await api.importGeneration({
      date: importDate.value,
      panel_group: importPanelGroup.value,
      actual_kwh: importKwh.value,
    })
    await api.calculateRevenue(importDate.value)
    ElMessage.success('数据导入成功，收益已自动计算')
    await loadData()
  } catch (e) { ElMessage.error('导入失败') }
  finally { importing.value = false }
}

onMounted(async () => {
  panelGroups.value = await api.panelGroups.list()
  await loadData()
})
</script>
