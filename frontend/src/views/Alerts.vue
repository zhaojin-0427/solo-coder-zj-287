<template>
  <div>
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="24">
        <div class="page-card" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 20px">
          <span style="color:#64748b;font-size:14px">筛选:</span>
          <el-select v-model="filters.anomaly_level" placeholder="告警等级" clearable style="width:130px" size="default">
            <el-option label="严重" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
            <el-option label="正常" value="normal" />
          </el-select>
          <el-select v-model="filters.device_type" placeholder="设备类型" clearable style="width:130px" size="default" @change="onDeviceTypeChange">
            <el-option label="光伏板组" value="panel_group" />
            <el-option label="逆变器" value="inverter" />
          </el-select>
          <el-select v-model="filters.device_id" placeholder="选择设备" clearable style="width:180px" size="default" :disabled="!filters.device_type">
            <el-option v-if="filters.device_type === 'panel_group'" v-for="pg in panelGroups" :key="'pg-'+pg.id" :label="pg.name" :value="String(pg.id)" />
            <el-option v-if="filters.device_type === 'inverter'" v-for="inv in inverters" :key="'inv-'+inv.id" :label="inv.brand+' '+inv.model" :value="String(inv.id)" />
          </el-select>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:260px" size="default" />
          <el-switch v-model="showHandled" active-text="已处理" inactive-text="未处理" style="margin-left:8px" />
          <el-button type="primary" :icon="Search" @click="loadData" size="default">查询</el-button>
          <el-button @click="resetFilters" size="default">重置</el-button>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stat-row" style="margin-bottom:16px">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">未处理告警</div>
          <div class="value" style="color:#ef4444">{{ alertSummaryData.unhandled_count }}<span class="unit">条</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">最高告警等级</div>
          <div class="value" :style="{color: levelColorMap[alertSummaryData.highest_level] || '#22c55e'}">{{ levelLabelMap[alertSummaryData.highest_level] || '正常' }}</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">严重告警</div>
          <div class="value" style="color:#dc2626">{{ alertSummaryData.level_counts?.critical || 0 }}<span class="unit">条</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">高级告警</div>
          <div class="value" style="color:#f59e0b">{{ alertSummaryData.level_counts?.high || 0 }}<span class="unit">条</span></div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card">
      <div class="page-card-title">
        <el-icon><Bell /></el-icon> 告警列表
      </div>
      <el-table :data="alertList" stripe style="width:100%" v-loading="loading">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="device_display_name" label="设备名称" width="180" />
        <el-table-column label="告警等级" width="100">
          <template #default="{ row }">
            <el-tag :type="levelTagType[row.anomaly_level]" effect="dark" size="small">
              {{ levelLabelMap[row.anomaly_level] || row.anomaly_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="异常类型" width="140">
          <template #default="{ row }">
            {{ row.anomaly_type_display || row.anomaly_type }}
          </template>
        </el-table-column>
        <el-table-column prop="health_score" label="健康评分" width="100">
          <template #default="{ row }">
            <span :style="{color: row.health_score >= 90 ? '#22c55e' : row.health_score >= 70 ? '#f59e0b' : '#ef4444', fontWeight: 600}">
              {{ row.health_score }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="possible_cause" label="可能原因" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.anomaly_level === 'normal'" type="success" size="small">正常</el-tag>
            <el-tag v-else :type="row.is_handled ? 'info' : 'danger'" size="small">
              {{ row.is_handled ? '已处理' : '未处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
            <el-button v-if="!row.is_handled && row.anomaly_level !== 'normal'" type="success" link size="small" @click="markHandled(row)">标记已处理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex;justify-content:flex-end;margin-top:16px">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="totalCount"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="告警详情" width="600px" destroy-on-close>
      <template v-if="currentAlert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="日期">{{ currentAlert.date }}</el-descriptions-item>
          <el-descriptions-item label="设备名称">{{ currentAlert.device_display_name }}</el-descriptions-item>
          <el-descriptions-item label="设备类型">{{ currentAlert.device_type === 'panel_group' ? '光伏板组' : '逆变器' }}</el-descriptions-item>
          <el-descriptions-item label="健康评分">
            <span :style="{color: currentAlert.health_score >= 90 ? '#22c55e' : currentAlert.health_score >= 70 ? '#f59e0b' : '#ef4444', fontWeight: 600}">
              {{ currentAlert.health_score }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="告警等级">
            <el-tag :type="levelTagType[currentAlert.anomaly_level]" effect="dark" size="small">
              {{ levelLabelMap[currentAlert.anomaly_level] || currentAlert.anomaly_level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="异常类型">{{ currentAlert.anomaly_type_display || currentAlert.anomaly_type }}</el-descriptions-item>
          <el-descriptions-item label="偏差率">{{ currentAlert.deviation_rate }}%</el-descriptions-item>
          <el-descriptions-item label="逆变器效率">{{ currentAlert.inverter_efficiency }}%</el-descriptions-item>
          <el-descriptions-item label="连续低发电天数">{{ currentAlert.consecutive_low_days }} 天</el-descriptions-item>
          <el-descriptions-item label="并网运行天数">{{ currentAlert.grid_days }} 天</el-descriptions-item>
          <el-descriptions-item label="峰谷比">{{ currentAlert.peak_valley_ratio }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag v-if="currentAlert.anomaly_level === 'normal'" type="success" size="small">正常</el-tag>
            <el-tag v-else :type="currentAlert.is_handled ? 'info' : 'danger'" size="small">
              {{ currentAlert.is_handled ? '已处理' : '未处理' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="可能原因" :span="2">
            <div style="white-space:pre-wrap">{{ currentAlert.possible_cause }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="处理建议" :span="2">
            <div style="white-space:pre-wrap">{{ currentAlert.handling_suggestion }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button v-if="currentAlert && !currentAlert.is_handled && currentAlert.anomaly_level !== 'normal'" type="success" @click="markHandledFromDialog">标记已处理</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Bell, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { ALERT_LEVEL_LABELS, ALERT_LEVEL_COLORS, ALERT_LEVEL_TAG_TYPES, getHealthColor } from '../utils/constants'
import { extractListData, extractTotalCount, buildPaginationParams, buildDateRangeParams } from '../utils/request'

const levelLabelMap = ALERT_LEVEL_LABELS
const levelColorMap = ALERT_LEVEL_COLORS
const levelTagType = ALERT_LEVEL_TAG_TYPES

const loading = ref(false)
const alertList = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const filters = ref({
  anomaly_level: '',
  device_type: '',
  device_id: '',
})
const dateRange = ref(null)
const showHandled = ref(false)

const panelGroups = ref([])
const inverters = ref([])

const onDeviceTypeChange = () => {
  filters.value.device_id = ''
}

const alertSummaryData = ref({
  unhandled_count: 0,
  highest_level: 'normal',
  level_counts: {},
})

const detailVisible = ref(false)
const currentAlert = ref(null)

const loadDevices = async () => {
  try {
    const [pgRes, invRes] = await Promise.all([api.panelGroups.list(), api.inverters.list()])
    panelGroups.value = extractListData(pgRes)
    inverters.value = extractListData(invRes)
  } catch (e) { console.error(e) }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = buildPaginationParams(currentPage.value, pageSize.value, {
      anomaly_level: filters.value.anomaly_level || '',
      device_type: filters.value.device_type || '',
      device_id: filters.value.device_id || '',
      is_handled: showHandled.value ? 'true' : 'false',
      ...buildDateRangeParams(dateRange.value)
    })

    const res = await api.healthDiagnosis.list(params)
    alertList.value = extractListData(res)
    totalCount.value = extractTotalCount(res)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadSummary = async () => {
  try {
    alertSummaryData.value = await api.alertSummary()
  } catch (e) { console.error(e) }
}

const resetFilters = () => {
  filters.value = { anomaly_level: '', device_type: '', device_id: '' }
  dateRange.value = null
  showHandled.value = false
  currentPage.value = 1
  loadData()
  loadSummary()
}

const showDetail = (row) => {
  currentAlert.value = row
  detailVisible.value = true
}

const markHandled = async (row) => {
  try {
    await ElMessageBox.confirm('确认将该告警标记为已处理？', '确认', { type: 'warning' })
    await api.healthDiagnosis.markHandled(row.id)
    ElMessage.success('已标记为已处理')
    loadData()
    loadSummary()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const markHandledFromDialog = async () => {
  if (!currentAlert.value) return
  try {
    await api.healthDiagnosis.markHandled(currentAlert.value.id)
    ElMessage.success('已标记为已处理')
    detailVisible.value = false
    loadData()
    loadSummary()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadDevices()
  loadData()
  loadSummary()
})
</script>

<style scoped>
</style>
