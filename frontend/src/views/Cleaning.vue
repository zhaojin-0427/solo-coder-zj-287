<template>
  <div>
    <el-row :gutter="16" class="stat-row" style="margin-bottom:16px">
      <el-col :xs="12" :sm="6">
        <div class="stat-card" style="cursor:pointer" @click="statusTab = 'pending'">
          <div class="label">待执行计划</div>
          <div class="value" style="color:#f59e0b">{{ summary.pending_count || 0 }}<span class="unit">个</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">近7日待清洁</div>
          <div class="value" style="color:#ef4444">{{ summary.upcoming_7d_count || 0 }}<span class="unit">组</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计恢复发电</div>
          <div class="value" style="color:#22c55e">{{ summary.total_recovered_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="label">累计额外收益</div>
          <div class="value" style="color:#8b5cf6">{{ summary.total_extra_revenue || 0 }}<span class="unit">元</span></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="24">
        <div class="page-card" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 20px">
          <span style="color:#64748b;font-size:14px">状态:</span>
          <el-radio-group v-model="statusTab" @change="loadData" size="default">
            <el-radio-button value="pending">待执行</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
            <el-radio-button value="">全部</el-radio-button>
          </el-radio-group>
          <el-divider direction="vertical" />
          <el-select v-model="filters.panel_group" placeholder="选择板组" clearable style="width:180px" size="default">
            <el-option v-for="pg in panelGroups" :key="'pg-'+pg.id" :label="pg.name" :value="String(pg.id)" />
          </el-select>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:260px" size="default" />
          <el-button type="primary" :icon="Search" @click="loadData" size="default">查询</el-button>
          <el-button @click="resetFilters" size="default">重置</el-button>
          <div style="margin-left:auto">
            <el-button type="success" :icon="Plus" @click="openCreateDialog" size="default">新增计划</el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card">
      <div class="page-card-title">
        <el-icon><Brush /></el-icon> 清洁维护计划列表
      </div>
      <el-table :data="planList" stripe style="width:100%" v-loading="loading">
        <el-table-column prop="plan_name" label="计划名称" width="150" />
        <el-table-column prop="panel_group_name" label="光伏板组" width="150" />
        <el-table-column label="清洁方式" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.cleaning_method_display || methodLabelMap[row.cleaning_method] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预计费用" width="100" align="right">
          <template #default="{ row }">¥{{ row.estimated_cost }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="执行人员" width="100" />
        <el-table-column prop="plan_date" label="计划日期" width="120" />
        <el-table-column prop="actual_date" label="实际完成" width="120" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType[row.status]" effect="dark" size="small">
              {{ row.status_display || statusLabelMap[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="statusTab !== 'pending'" label="有效性" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="effectivenessTagType[row.effectiveness_level]" size="small">
              {{ row.effectiveness_level_display || effectivenessLabelMap[row.effectiveness_level] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="statusTab !== 'pending'" label="恢复发电量" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.recovered_generation_kwh" style="color:#22c55e;font-weight:600">
              +{{ row.recovered_generation_kwh }} kWh
            </span>
            <span v-else style="color:#94a3b8">--</span>
          </template>
        </el-table-column>
        <el-table-column v-if="statusTab !== 'pending'" label="额外收益" width="100" align="right">
          <template #default="{ row }">
            <span v-if="row.extra_revenue" style="color:#8b5cf6;font-weight:600">
              +¥{{ row.extra_revenue }}
            </span>
            <span v-else style="color:#94a3b8">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'pending'" type="warning" link size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.status === 'pending'" type="success" link size="small" @click="openMarkComplete(row)">标记完成</el-button>
            <el-button v-if="row.status === 'completed'" type="info" link size="small" @click="reEvaluate(row)">重新评估</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" link size="small" @click="deletePlan(row)">删除</el-button>
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

    <el-dialog v-model="formDialogVisible" :title="isEditing ? '编辑清洁计划' : '新增清洁计划'" width="560px" destroy-on-close>
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="110px">
        <el-form-item label="计划名称" prop="plan_name">
          <el-input v-model="formData.plan_name" placeholder="请输入计划名称" />
        </el-form-item>
        <el-form-item label="光伏板组" prop="panel_group">
          <el-select v-model="formData.panel_group" placeholder="请选择板组" style="width:100%">
            <el-option v-for="pg in panelGroups" :key="'fpg-'+pg.id" :label="pg.name" :value="pg.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="清洁方式" prop="cleaning_method">
          <el-select v-model="formData.cleaning_method" placeholder="请选择清洁方式" style="width:100%">
            <el-option label="人工清洁" value="manual" />
            <el-option label="水洗清洁" value="water" />
            <el-option label="干洗清洁" value="dry" />
            <el-option label="机器人清洁" value="robot" />
            <el-option label="雨水自洁" value="rain" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计费用" prop="estimated_cost">
          <el-input-number v-model="formData.estimated_cost" :min="0" :precision="2" :step="10" style="width:100%" />
          <span style="color:#94a3b8;font-size:12px;margin-left:8px">元</span>
        </el-form-item>
        <el-form-item label="执行人员" prop="operator">
          <el-input v-model="formData.operator" placeholder="请输入执行人员" />
        </el-form-item>
        <el-form-item label="计划日期" prop="plan_date">
          <el-date-picker v-model="formData.plan_date" type="date" value-format="YYYY-MM-DD" placeholder="选择计划日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.notes" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="markCompleteVisible" title="标记清洁完成" width="480px" destroy-on-close>
      <template v-if="currentPlan">
        <el-descriptions :column="1" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="计划名称">{{ currentPlan.plan_name }}</el-descriptions-item>
          <el-descriptions-item label="板组">{{ currentPlan.panel_group_name }}</el-descriptions-item>
          <el-descriptions-item label="清洁方式">{{ currentPlan.cleaning_method_display || methodLabelMap[currentPlan.cleaning_method] }}</el-descriptions-item>
        </el-descriptions>
        <el-form :model="completeForm" label-width="100px">
          <el-form-item label="实际完成日期">
            <el-date-picker v-model="completeForm.actual_date" type="date" value-format="YYYY-MM-DD" placeholder="选择实际完成日期" style="width:100%" />
          </el-form-item>
          <el-form-item label="实际费用">
            <el-input-number v-model="completeForm.actual_cost" :min="0" :precision="2" :step="10" style="width:100%" />
          </el-form-item>
          <el-form-item label="执行人员">
            <el-input v-model="completeForm.operator" placeholder="执行人员姓名" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="completeForm.notes" type="textarea" :rows="2" placeholder="清洁情况备注" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="markCompleteVisible = false">取消</el-button>
        <el-button type="success" @click="submitMarkComplete">确认完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="清洁计划详情与效果评估" width="780px" destroy-on-close>
      <template v-if="currentPlan">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="计划名称" :span="3">{{ currentPlan.plan_name }}</el-descriptions-item>
          <el-descriptions-item label="光伏板组">{{ currentPlan.panel_group_name }}</el-descriptions-item>
          <el-descriptions-item label="清洁方式">{{ currentPlan.cleaning_method_display || methodLabelMap[currentPlan.cleaning_method] }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType[currentPlan.status]" effect="dark" size="small">
              {{ currentPlan.status_display || statusLabelMap[currentPlan.status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预计费用">¥{{ currentPlan.estimated_cost }}</el-descriptions-item>
          <el-descriptions-item label="实际费用">{{ currentPlan.actual_cost ? '¥'+currentPlan.actual_cost : '--' }}</el-descriptions-item>
          <el-descriptions-item label="执行人员">{{ currentPlan.operator || '--' }}</el-descriptions-item>
          <el-descriptions-item label="计划日期">{{ currentPlan.plan_date }}</el-descriptions-item>
          <el-descriptions-item label="实际完成">{{ currentPlan.actual_date || '--' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="currentPlan.status === 'completed'" style="margin-top:20px">
          <el-divider content-position="left">
            <span style="font-size:15px;font-weight:600">效果评估结果</span>
          </el-divider>

          <el-row :gutter="12" class="stat-row">
            <el-col :xs="12" :sm="6">
              <div class="stat-card" style="padding:14px">
                <div class="label" style="font-size:12px">发电恢复量(30日)</div>
                <div class="value" style="font-size:22px;color:#22c55e">+{{ currentPlan.recovered_generation_kwh }}<span class="unit" style="font-size:12px">kWh</span></div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card" style="padding:14px">
                <div class="label" style="font-size:12px">额外收益(30日)</div>
                <div class="value" style="font-size:22px;color:#8b5cf6">+¥{{ currentPlan.extra_revenue }}</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card" style="padding:14px">
                <div class="label" style="font-size:12px">费用回收天数</div>
                <div class="value" style="font-size:22px;color:#f59e0b">
                  {{ currentPlan.cost_recovery_days < 9999 ? currentPlan.cost_recovery_days + '天' : '--' }}
                </div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card" style="padding:14px">
                <div class="label" style="font-size:12px">有效性等级</div>
                <div class="value" style="font-size:22px">
                  <el-tag :type="effectivenessTagType[currentPlan.effectiveness_level]" effect="dark">
                    {{ currentPlan.effectiveness_level_display || effectivenessLabelMap[currentPlan.effectiveness_level] }}
                  </el-tag>
                </div>
              </div>
            </el-col>
          </el-row>

          <el-descriptions :column="2" border style="margin-top:16px" size="small">
            <el-descriptions-item label="清洁前平均效率">
              <span style="color:#ef4444;font-weight:600">{{ currentPlan.pre_avg_efficiency }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="清洁后平均效率">
              <span style="color:#22c55e;font-weight:600">{{ currentPlan.post_avg_efficiency }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="清洁前平均偏差">
              <span style="color:#ef4444">{{ currentPlan.pre_avg_deviation }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="清洁后平均偏差">
              <span style="color:#22c55e">{{ currentPlan.post_avg_deviation }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="清洁前健康评分">
              <span :style="{color: currentPlan.health_score_before >= 80 ? '#22c55e' : (currentPlan.health_score_before >= 60 ? '#f59e0b' : '#ef4444'), fontWeight:600}">
                {{ currentPlan.health_score_before }}分
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="清洁后健康评分">
              <span :style="{color: currentPlan.health_score_after >= 80 ? '#22c55e' : (currentPlan.health_score_after >= 60 ? '#f59e0b' : '#ef4444'), fontWeight:600}">
                {{ currentPlan.health_score_after }}分
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="连续低发电天数">{{ currentPlan.consecutive_low_days }} 天</el-descriptions-item>
            <el-descriptions-item label="天气日照系数">{{ currentPlan.weather_sunshine_coeff }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="currentPlan.evaluation_detail && currentPlan.evaluation_detail.pre_daily_records" style="margin-top:20px">
            <el-divider content-position="left">
              <span style="font-size:14px;font-weight:600">清洁前后发电效率对比</span>
            </el-divider>
            <v-chart :option="evalChartOption" style="width:100%;height:280px" autoresize />
          </div>
        </div>

        <div v-if="currentPlan.notes" style="margin-top:16px">
          <el-divider content-position="left">
            <span style="font-size:14px;font-weight:600">备注</span>
          </el-divider>
          <div style="padding:12px;background:#f8fafc;border-radius:8px;color:#475569">
            {{ currentPlan.notes }}
          </div>
        </div>
      </template>
      <template #footer>
        <el-button v-if="currentPlan && currentPlan.status === 'completed'" type="info" @click="reEvaluateFromDialog">重新评估</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Brush } from '@element-plus/icons-vue'
import api from '../api'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const statusLabelMap = { pending: '待执行', completed: '已完成', cancelled: '已取消' }
const statusTagType = { pending: 'warning', completed: 'success', cancelled: 'info' }
const methodLabelMap = { manual: '人工清洁', water: '水洗清洁', dry: '干洗清洁', robot: '机器人清洁', rain: '雨水自洁' }
const effectivenessLabelMap = { excellent: '优秀', good: '良好', fair: '一般', poor: '较差', none: '未评估' }
const effectivenessTagType = { excellent: 'success', good: 'primary', fair: 'warning', poor: 'danger', none: 'info' }

const loading = ref(false)
const planList = ref([])
const panelGroups = ref([])
const summary = ref({})
const statusTab = ref('pending')
const filters = reactive({ panel_group: '', date_from: '', date_to: '' })
const dateRange = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)

const formDialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const formData = reactive({
  plan_name: '常规清洁', panel_group: null, cleaning_method: 'manual',
  estimated_cost: 80, operator: '', plan_date: '', notes: ''
})
const formRules = {
  plan_name: [{ required: true, message: '请输入计划名称', trigger: 'blur' }],
  panel_group: [{ required: true, message: '请选择光伏板组', trigger: 'change' }],
  cleaning_method: [{ required: true, message: '请选择清洁方式', trigger: 'change' }],
  plan_date: [{ required: true, message: '请选择计划日期', trigger: 'change' }],
}

const markCompleteVisible = ref(false)
const currentPlan = ref(null)
const completeForm = reactive({ actual_date: '', actual_cost: 0, operator: '', notes: '' })

const detailVisible = ref(false)

const evalChartOption = computed(() => {
  if (!currentPlan.value || !currentPlan.value.evaluation_detail) return {}
  const evalDetail = currentPlan.value.evaluation_detail
  const preData = evalDetail.pre_daily_records || []
  const postData = evalDetail.post_daily_records || []
  const dates = [
    ...preData.map(r => r.date + ' (前)'),
    ...postData.map(r => r.date + ' (后)')
  ]
  const effs = [
    ...preData.map(r => r.efficiency),
    ...postData.map(r => r.efficiency)
  ]
  return {
    tooltip: { trigger: 'axis', formatter: '{b}<br/>效率: {c}%' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 35, fontSize: 10, interval: 0 }
    },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: [{
      type: 'line',
      data: effs,
      smooth: true,
      itemStyle: { color: '#3b82f6' },
      lineStyle: { width: 3 },
      markLine: {
        silent: true,
        data: [
          { yAxis: evalDetail.pre_avg_efficiency, name: '清洁前平均', lineStyle: { color: '#ef4444' }, label: { formatter: '前均' + evalDetail.pre_avg_efficiency + '%' } },
          { yAxis: evalDetail.post_avg_efficiency, name: '清洁后平均', lineStyle: { color: '#22c55e' }, label: { formatter: '后均' + evalDetail.post_avg_efficiency + '%' } }
        ]
      },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(59,130,246,0.3)' },
            { offset: 1, color: 'rgba(59,130,246,0.02)' }
          ]
        }
      }
    }]
  }
})

const loadPanelGroups = async () => {
  try {
    panelGroups.value = await api.panelGroups.list() || []
  } catch (e) {
    console.error('load panel groups failed', e)
  }
}

const loadSummary = async () => {
  try {
    summary.value = await api.cleaningPlans.summary() || {}
  } catch (e) {
    console.error('load summary failed', e)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (statusTab.value) params.status = statusTab.value
    if (filters.panel_group) params.panel_group = filters.panel_group
    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const res = await api.cleaningPlans.list(params)
    planList.value = res.results || res || []
    totalCount.value = res.count || planList.value.length
  } catch (e) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.panel_group = ''
  dateRange.value = []
  currentPage.value = 1
  loadData()
}

const openCreateDialog = () => {
  isEditing.value = false
  editingId.value = null
  Object.assign(formData, {
    plan_name: '常规清洁', panel_group: null, cleaning_method: 'manual',
    estimated_cost: 80, operator: '', plan_date: '', notes: ''
  })
  formDialogVisible.value = true
}

const openEditDialog = (row) => {
  isEditing.value = true
  editingId.value = row.id
  Object.assign(formData, {
    plan_name: row.plan_name,
    panel_group: row.panel_group,
    cleaning_method: row.cleaning_method,
    estimated_cost: row.estimated_cost,
    operator: row.operator,
    plan_date: row.plan_date,
    notes: row.notes || ''
  })
  formDialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (e) { return }
  try {
    if (isEditing.value) {
      await api.cleaningPlans.update(editingId.value, formData)
      ElMessage.success('更新成功')
    } else {
      await api.cleaningPlans.create(formData)
      ElMessage.success('创建成功')
    }
    formDialogVisible.value = false
    loadData()
    loadSummary()
  } catch (e) {
    ElMessage.error('提交失败')
  }
}

const openMarkComplete = (row) => {
  currentPlan.value = row
  Object.assign(completeForm, {
    actual_date: new Date().toISOString().slice(0, 10),
    actual_cost: row.estimated_cost,
    operator: row.operator,
    notes: ''
  })
  markCompleteVisible.value = true
}

const submitMarkComplete = async () => {
  if (!currentPlan.value) return
  try {
    const data = {
      actual_date: completeForm.actual_date,
      actual_cost: completeForm.actual_cost,
      operator: completeForm.operator,
      notes: completeForm.notes,
    }
    await api.cleaningPlans.markCompleted(currentPlan.value.id, data)
    ElMessage.success('标记完成，已自动评估清洁效果')
    markCompleteVisible.value = false
    loadData()
    loadSummary()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const reEvaluate = async (row) => {
  try {
    await api.cleaningPlans.reEvaluate(row.id)
    ElMessage.success('重新评估完成')
    loadData()
  } catch (e) {
    ElMessage.error('评估失败，请确保有足够的发电数据')
  }
}

const reEvaluateFromDialog = async () => {
  if (!currentPlan.value) return
  try {
    const res = await api.cleaningPlans.reEvaluate(currentPlan.value.id)
    currentPlan.value = res
    ElMessage.success('重新评估完成')
  } catch (e) {
    ElMessage.error('评估失败')
  }
}

const deletePlan = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除清洁计划「${row.plan_name}」？`, '确认删除', { type: 'warning' })
    await api.cleaningPlans.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
    loadSummary()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const showDetail = (row) => {
  currentPlan.value = row
  detailVisible.value = true
}

onMounted(() => {
  loadPanelGroups()
  loadSummary()
  loadData()
})
</script>
