<template>
  <div>
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">电池组数</div>
          <div class="value" style="color:#8b5cf6">{{ summary.battery_count || 0 }}<span class="unit">组</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">总储能容量</div>
          <div class="value" style="color:#3b82f6">{{ summary.total_capacity_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">今日充电量</div>
          <div class="value" style="color:#06b6d4">{{ summary.today_charge_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">今日放电量</div>
          <div class="value" style="color:#f97316">{{ summary.today_discharge_kwh || 0 }}<span class="unit">kWh</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">今日储能增益</div>
          <div class="value" :style="{color: (summary.today_storage_profit || 0) >= 0 ? '#22c55e' : '#ef4444'}">{{ summary.today_storage_profit || 0 }}<span class="unit">元</span></div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6" :md="4">
        <div class="stat-card">
          <div class="label">本月储能增益</div>
          <div class="value" :style="{color: (summary.month_storage_profit || 0) >= 0 ? '#f59e0b' : '#ef4444'}">{{ summary.month_storage_profit || 0 }}<span class="unit">元</span></div>
        </div>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab" style="margin-top:16px">
      <el-tab-pane label="电池档案管理" name="batteries">
        <div class="page-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div class="page-card-title" style="margin-bottom:0">
              <el-icon><Lightning /></el-icon> 储能电池档案
            </div>
            <el-button type="primary" :icon="Plus" @click="openBatteryDialog()">新增电池</el-button>
          </div>
          <el-table :data="batteries" stripe style="width: 100%" v-loading="loadingBatteries">
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column label="品牌/型号" min-width="160">
              <template #default="{ row }">
                <div>{{ row.brand || '-' }} {{ row.model || '' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="capacity_kwh" label="容量(kWh)" width="100" align="center" />
            <el-table-column label="最大充放功率(kW)" width="160" align="center">
              <template #default="{ row }">
                <span>充 {{ row.max_charge_power_kw }} / 放 {{ row.max_discharge_power_kw }}</span>
              </template>
            </el-table-column>
            <el-table-column label="充放电效率" width="120" align="center">
              <template #default="{ row }">
                <span>充{{ row.charge_efficiency }}%/放{{ row.discharge_efficiency }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="SOC范围" width="120" align="center">
              <template #default="{ row }">
                <span>{{ row.soc_lower_limit }}%~{{ row.soc_upper_limit }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="current_soc" label="当前SOC" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="socTagType(row.current_soc)" size="small">{{ row.current_soc }}%</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status_display" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ row.status_display }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enable_date" label="启用日期" width="120" />
            <el-table-column label="关联板组" min-width="140">
              <template #default="{ row }">
                <div style="font-size:12px;color:#64748b">{{ (row.panel_group_names || []).join('、') || '-' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openBatteryDialog(row)">编辑</el-button>
                <el-button type="success" link size="small" @click="openRecalcDialog(row)">重算调度</el-button>
                <el-popconfirm title="确定删除该电池档案？" @confirm="deleteBattery(row.id)">
                  <template #reference>
                    <el-button type="danger" link size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="调度计划列表" name="schedules">
        <div class="page-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:12px">
            <div class="page-card-title" style="margin-bottom:0">
              <el-icon><Calendar /></el-icon> 充放电调度计划
            </div>
            <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
              <el-select v-model="filterBatteryId" placeholder="选择电池" clearable style="width:180px" size="default">
                <el-option v-for="b in batteries" :key="b.id" :label="b.name" :value="b.id" />
              </el-select>
              <el-date-picker
                v-model="filterDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                size="default"
              />
              <el-button type="primary" :icon="Search" @click="loadSchedules">查询</el-button>
              <el-button :icon="Refresh" @click="openGlobalRecalcDialog">批量重算</el-button>
            </div>
          </div>
          <el-table :data="schedules" stripe style="width: 100%" v-loading="loadingSchedules">
            <el-table-column prop="date" label="日期" width="110" />
            <el-table-column prop="battery_name" label="电池" min-width="130" />
            <el-table-column label="SOC变化" width="160" align="center">
              <template #default="{ row }">
                <span style="color:#3b82f6">{{ row.initial_soc }}%</span>
                <span style="margin:0 4px;color:#94a3b8">→</span>
                <span style="color:#8b5cf6">{{ row.final_soc }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="charge_kwh" label="充电量(kWh)" width="110" align="center">
              <template #default="{ row }">
                <span style="color:#06b6d4">{{ Number(row.charge_kwh).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="discharge_kwh" label="放电量(kWh)" width="110" align="center">
              <template #default="{ row }">
                <span style="color:#f97316">{{ Number(row.discharge_kwh).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="reduced_curtailment_kwh" label="弃光减少(kWh)" width="120" align="center">
              <template #default="{ row }">
                <span style="color:#22c55e">{{ Number(row.reduced_curtailment_kwh).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="peak_discharge_saving" label="峰时节省(元)" width="110" align="center">
              <template #default="{ row }">
                <span style="color:#22c55e">+{{ Number(row.peak_discharge_saving).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="valley_charge_cost" label="谷时成本(元)" width="110" align="center">
              <template #default="{ row }">
                <span style="color:#ef4444">-{{ Number(row.valley_charge_cost).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="grid_income_change" label="上网收益变化" width="120" align="center">
              <template #default="{ row }">
                <span :style="{color: Number(row.grid_income_change) >= 0 ? '#22c55e' : '#ef4444'}">
                  {{ Number(row.grid_income_change) >= 0 ? '+' : '' }}{{ Number(row.grid_income_change).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="total_profit_diff" label="总收益差额(元)" width="130" align="center" fixed="right">
              <template #default="{ row }">
                <span :style="{color: Number(row.total_profit_diff) >= 0 ? '#f59e0b' : '#ef4444', fontWeight:600}">
                  {{ Number(row.total_profit_diff) >= 0 ? '+' : '' }}{{ Number(row.total_profit_diff).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="viewScheduleDetail(row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top:16px;display:flex;justify-content:flex-end">
            <el-pagination
              v-model:current-page="schedulePage"
              v-model:page-size="schedulePageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="scheduleTotal"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadSchedules"
              @current-change="loadSchedules"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="调度详情分析" name="detail">
        <div class="page-card">
          <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap">
            <el-select v-model="detailBatteryId" placeholder="选择电池" style="width:200px" @change="loadDetailData">
              <el-option v-for="b in batteries" :key="b.id" :label="b.name" :value="b.id" />
            </el-select>
            <el-date-picker
              v-model="detailDate"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width:180px"
              @change="loadDetailData"
            />
            <el-button type="primary" :icon="View" @click="loadDetailData">查看</el-button>
          </div>
          <el-row :gutter="16" class="stat-row" v-if="selectedSchedule">
            <el-col :xs="12" :sm="6">
              <div class="stat-card">
                <div class="label">初始SOC</div>
                <div class="value" style="color:#3b82f6">{{ selectedSchedule.initial_soc }}<span class="unit">%</span></div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card">
                <div class="label">结束SOC</div>
                <div class="value" style="color:#8b5cf6">{{ selectedSchedule.final_soc }}<span class="unit">%</span></div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card">
                <div class="label">总充电量</div>
                <div class="value" style="color:#06b6d4">{{ Number(selectedSchedule.charge_kwh).toFixed(2) }}<span class="unit">kWh</span></div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-card">
                <div class="label">总放电量</div>
                <div class="value" style="color:#f97316">{{ Number(selectedSchedule.discharge_kwh).toFixed(2) }}<span class="unit">kWh</span></div>
              </div>
            </el-col>
          </el-row>
        </div>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="14">
            <div class="page-card">
              <div class="page-card-title">
                <el-icon><TrendCharts /></el-icon> 24小时SOC变化曲线
              </div>
              <v-chart :option="socCurveOption" :key="socChartKey" class="chart-container" autoresize />
            </div>
          </el-col>
          <el-col :span="10">
            <div class="page-card">
              <div class="page-card-title">
                <el-icon><DataLine /></el-icon> 24小时充放电明细
              </div>
              <v-chart :option="chargeDischargeOption" :key="cdChartKey" class="chart-container" autoresize />
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <div class="page-card">
              <div class="page-card-title">
                <el-icon><PieChart /></el-icon> 收益构成分析
              </div>
              <v-chart :option="profitPieOption" :key="pieChartKey" class="chart-container" autoresize />
            </div>
          </el-col>
          <el-col :span="12">
            <div class="page-card">
              <div class="page-card-title">
                <el-icon><Wallet /></el-icon> 小时级充放电与收益明细
              </div>
              <div style="max-height:350px;overflow:auto">
                <el-table :data="hourlyDetailList" stripe size="small">
                  <el-table-column prop="hour" label="小时" width="60" align="center">
                    <template #default="{ row }">{{ row.hour }}:00</template>
                  </el-table-column>
                  <el-table-column prop="price_type" label="时段" width="70" align="center">
                    <template #default="{ row }">
                      <el-tag v-if="row.price_type==='peak'" type="danger" size="small">峰</el-tag>
                      <el-tag v-else-if="row.price_type==='valley'" type="success" size="small">谷</el-tag>
                      <el-tag v-else type="warning" size="small">平</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="动作" width="110" align="center">
                    <template #default="{ row }">
                      <span v-if="row.action==='charge_solar'" style="color:#06b6d4">光→充</span>
                      <span v-else-if="row.action==='charge_grid_valley'" style="color:#22c55e">谷电充电</span>
                      <span v-else-if="row.action==='discharge'" style="color:#f97316">放电</span>
                      <span v-else style="color:#94a3b8">待机</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="charge_kwh" label="充电(kWh)" width="85" align="center">
                    <template #default="{ row }"><span v-if="row.charge_kwh>0" style="color:#06b6d4">{{ Number(row.charge_kwh).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column prop="discharge_kwh" label="放电(kWh)" width="85" align="center">
                    <template #default="{ row }"><span v-if="row.discharge_kwh>0" style="color:#f97316">{{ Number(row.discharge_kwh).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column prop="soc_pct" label="SOC(%)" width="70" align="center" />
                </el-table>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="batteryDialogVisible" :title="editingBattery ? '编辑储能电池' : '新增储能电池'" width="680px">
      <el-form :model="batteryForm" label-width="130px" :rules="batteryRules" ref="batteryFormRef">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="电池名称" prop="name">
              <el-input v-model="batteryForm.name" placeholder="例如：家庭储能主电池" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-input v-model="batteryForm.brand" placeholder="例如：宁德时代" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="型号">
              <el-input v-model="batteryForm.model" placeholder="例如：EVE-10kWh" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="额定容量(kWh)" prop="capacity_kwh">
              <el-input-number v-model="batteryForm.capacity_kwh" :min="0.1" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大充电功率(kW)" prop="max_charge_power_kw">
              <el-input-number v-model="batteryForm.max_charge_power_kw" :min="0.1" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大放电功率(kW)" prop="max_discharge_power_kw">
              <el-input-number v-model="batteryForm.max_discharge_power_kw" :min="0.1" :step="0.5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="充电效率(%)" prop="charge_efficiency">
              <el-input-number v-model="batteryForm.charge_efficiency" :min="50" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="放电效率(%)" prop="discharge_efficiency">
              <el-input-number v-model="batteryForm.discharge_efficiency" :min="50" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SOC上限(%)" prop="soc_upper_limit">
              <el-input-number v-model="batteryForm.soc_upper_limit" :min="50" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SOC下限(%)" prop="soc_lower_limit">
              <el-input-number v-model="batteryForm.soc_lower_limit" :min="0" :max="50" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用日期" prop="enable_date">
              <el-date-picker v-model="batteryForm.enable_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前SOC(%)">
              <el-input-number v-model="batteryForm.current_soc" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备状态">
              <el-select v-model="batteryForm.status" style="width:100%">
                <el-option label="正常" value="normal" />
                <el-option label="告警" value="warning" />
                <el-option label="维护中" value="maintenance" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="关联光伏板组">
              <el-select v-model="batteryForm.panel_group_ids" multiple placeholder="选择关联的光伏板组" style="width:100%">
                <el-option v-for="pg in panelGroups" :key="pg.id" :label="pg.name" :value="pg.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24" v-if="batteryForm.status === 'warning'">
            <el-form-item label="告警说明">
              <el-input v-model="batteryForm.warning_message" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="batteryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBattery">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="recalcDialogVisible" title="重新计算调度计划" width="500px">
      <el-form label-width="100px">
        <el-form-item label="电池">{{ recalcBattery?.name || '全部电池' }}</el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="recalcDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recalcDialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Refresh" :loading="recalculating" @click="executeRecalc">执行计算</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, View, Lightning, Calendar, DataLine, TrendCharts, PieChart, Wallet } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart as PieChartType } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent, TitleComponent } from 'echarts/components'
import api from '../api'
import { BATTERY_STATUS_LABELS, BATTERY_STATUS_TAG_TYPES, getSocColor, getSocTagType, getProfitColor, THEME_COLORS } from '../utils/constants'
import { formatKwh, formatMoney, formatHour, formatMonthDay } from '../utils/format'
import { createLineChart, createBarChart, createPieChart, createEmptyChart } from '../utils/charts'
import { extractListData, extractTotalCount, buildPaginationParams, buildDateRangeParams } from '../utils/request'

use([CanvasRenderer, BarChart, LineChart, PieChartType, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent, TitleComponent])

const activeTab = ref('batteries')
const loadingBatteries = ref(false)
const loadingSchedules = ref(false)
const batteries = ref([])
const panelGroups = ref([])
const schedules = ref([])
const schedulePage = ref(1)
const schedulePageSize = ref(20)
const scheduleTotal = ref(0)
const filterBatteryId = ref('')
const filterDateRange = ref([])
const summary = ref({})
const selectedSchedule = ref(null)
const detailBatteryId = ref(null)
const detailDate = ref(new Date().toISOString().slice(0, 10))
const socChartKey = ref(0)
const cdChartKey = ref(0)
const pieChartKey = ref(0)

const batteryDialogVisible = ref(false)
const editingBattery = ref(null)
const batteryFormRef = ref(null)
const batteryForm = reactive({
  name: '', brand: '', model: '', capacity_kwh: 10,
  max_charge_power_kw: 3, max_discharge_power_kw: 3,
  charge_efficiency: 95, discharge_efficiency: 95,
  soc_upper_limit: 90, soc_lower_limit: 15,
  enable_date: '', current_soc: 50, status: 'normal',
  warning_message: '', panel_group_ids: []
})
const batteryRules = {
  name: [{ required: true, message: '请输入电池名称', trigger: 'blur' }],
  capacity_kwh: [{ required: true, message: '请输入容量', trigger: 'change' }],
  enable_date: [{ required: true, message: '请选择启用日期', trigger: 'change' }],
}

const recalcDialogVisible = ref(false)
const recalcBattery = ref(null)
const recalcDateRange = ref([])
const recalculating = ref(false)

const socTagType = getSocTagType
const statusTagType = (s) => BATTERY_STATUS_TAG_TYPES[s] || 'info'

const hourlyDetailList = computed(() => {
  if (!selectedSchedule.value?.hourly_detail) return []
  return Object.values(selectedSchedule.value.hourly_detail).sort((a, b) => a.hour - b.hour)
})

const socCurveOption = computed(() => {
  if (!selectedSchedule.value?.hourly_soc) {
    return createEmptyChart()
  }
  const hours = Array.from({ length: 24 }, (_, i) => formatHour(i))
  const socs = selectedSchedule.value.hourly_soc
  const battery = selectedSchedule.value?.battery
    ? batteries.value.find(b => b.id === selectedSchedule.value.battery)
    : null
  return createLineChart({
    xData: hours,
    yAxisName: '%',
    yMin: 0,
    yMax: 100,
    lineColor: THEME_COLORS.purple,
    areaStyle: true,
    areaColor: THEME_COLORS.purple,
    xAxis: { axisLabel: { fontSize: 10 } },
    series: {
      data: socs,
      markLine: {
        silent: true,
        data: [
          { yAxis: battery?.soc_upper_limit || 90, label: { formatter: 'SOC上限' }, lineStyle: { color: THEME_COLORS.success, type: 'dashed' } },
          { yAxis: battery?.soc_lower_limit || 15, label: { formatter: 'SOC下限' }, lineStyle: { color: THEME_COLORS.danger, type: 'dashed' } }
        ]
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (p) => `${p[0].name}<br/>SOC: ${p[0].value}%`
    }
  })
})

const chargeDischargeOption = computed(() => {
  if (!selectedSchedule.value?.hourly_charge_discharge) {
    return createEmptyChart()
  }
  const hours = Array.from({ length: 24 }, (_, i) => formatHour(i))
  const data = selectedSchedule.value.hourly_charge_discharge
  const maxVal = Math.max(...data.map(Math.abs))
  return createBarChart({
    xData: hours,
    yAxisName: 'kWh',
    xAxis: { axisLabel: { fontSize: 10 } },
    series: {
      data,
      barWidth: '60%',
      itemStyle: {
        color: (params) => params.value >= 0 ? THEME_COLORS.info : THEME_COLORS.orange
      },
      label: {
        show: maxVal > 2,
        position: 'top',
        fontSize: 9,
        formatter: (p) => {
          if (Math.abs(p.value) < 0.5) return ''
          return Math.abs(p.value).toFixed(1)
        }
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const v = p[0].value
        return `${p[0].name}<br/>${v >= 0 ? '充电' : '放电'}: ${Math.abs(v).toFixed(3)} kWh`
      }
    }
  })
})

const profitPieOption = computed(() => {
  if (!selectedSchedule.value) {
    return createEmptyChart()
  }
  const peakSaving = Number(selectedSchedule.value.peak_discharge_saving || 0)
  const incomeChange = Number(selectedSchedule.value.grid_income_change || 0)
  const valleyCost = Number(selectedSchedule.value.valley_charge_cost || 0)
  const otherGain = Math.max(0, Number(selectedSchedule.value.total_profit_diff || 0) - peakSaving - incomeChange + valleyCost)
  return createPieChart({
    data: [
      { value: Math.max(0, peakSaving), name: '峰时放电节省', itemStyle: { color: THEME_COLORS.success } },
      { value: Math.max(0, incomeChange), name: '上网收益提升', itemStyle: { color: THEME_COLORS.primary } },
      { value: Math.max(0, otherGain), name: '其他增益', itemStyle: { color: THEME_COLORS.purple } },
      { value: valleyCost, name: '谷电成本(抵扣)', itemStyle: { color: THEME_COLORS.orange } },
    ].filter(d => d.value > 0),
    legend: { bottom: 0, orient: 'horizontal' },
    label: { formatter: '{b}\n¥{c}' },
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' }
  })
})

const loadSummary = async () => {
  try {
    summary.value = await api.storageSummary()
  } catch (e) { console.error(e) }
}

const loadBatteries = async () => {
  loadingBatteries.value = true
  try {
    batteries.value = await api.storageBatteries.list()
    if (batteries.value.length > 0 && !detailBatteryId.value) {
      detailBatteryId.value = batteries.value[0].id
    }
  } catch (e) { console.error(e) }
  finally { loadingBatteries.value = false }
}

const loadPanelGroups = async () => {
  try {
    panelGroups.value = extractListData(await api.panelGroups.list())
  } catch (e) { console.error(e) }
}

const loadSchedules = async () => {
  loadingSchedules.value = true
  try {
    const params = buildPaginationParams(schedulePage.value, schedulePageSize.value, {
      battery: filterBatteryId.value || '',
      ...buildDateRangeParams(filterDateRange.value)
    })
    const res = await api.storageSchedules.list(params)
    schedules.value = extractListData(res)
    scheduleTotal.value = extractTotalCount(res)
  } catch (e) { console.error(e) }
  finally { loadingSchedules.value = false }
}

const loadDetailData = async () => {
  if (!detailBatteryId.value || !detailDate.value) return
  try {
    const params = { battery: detailBatteryId.value, date_from: detailDate.value, date_to: detailDate.value }
    const res = await api.storageSchedules.list(params)
    const list = res.results || res
    if (list && list.length > 0) {
      selectedSchedule.value = { ...list[0] }
      socChartKey.value++
      cdChartKey.value++
      pieChartKey.value++
    } else {
      selectedSchedule.value = null
      ElMessage.warning('该日期暂无调度记录，可点击"批量重算"生成')
    }
  } catch (e) { console.error(e) }
}

const openBatteryDialog = (row = null) => {
  editingBattery.value = row
  if (row) {
    Object.assign(batteryForm, {
      name: row.name, brand: row.brand, model: row.model,
      capacity_kwh: row.capacity_kwh,
      max_charge_power_kw: row.max_charge_power_kw,
      max_discharge_power_kw: row.max_discharge_power_kw,
      charge_efficiency: row.charge_efficiency,
      discharge_efficiency: row.discharge_efficiency,
      soc_upper_limit: row.soc_upper_limit,
      soc_lower_limit: row.soc_lower_limit,
      enable_date: row.enable_date,
      current_soc: row.current_soc,
      status: row.status,
      warning_message: row.warning_message || '',
      panel_group_ids: row.panel_groups || []
    })
  } else {
    Object.assign(batteryForm, {
      name: '', brand: '', model: '', capacity_kwh: 10,
      max_charge_power_kw: 3, max_discharge_power_kw: 3,
      charge_efficiency: 95, discharge_efficiency: 95,
      soc_upper_limit: 90, soc_lower_limit: 15,
      enable_date: new Date().toISOString().slice(0, 10),
      current_soc: 50, status: 'normal',
      warning_message: '', panel_group_ids: []
    })
  }
  batteryDialogVisible.value = true
}

const saveBattery = async () => {
  if (!batteryFormRef.value) return
  try {
    await batteryFormRef.value.validate()
  } catch { return }
  try {
    const payload = { ...batteryForm }
    delete payload.panel_group_ids
    if (editingBattery.value) {
      await api.storageBatteries.update(editingBattery.value.id, payload)
      if (batteryForm.panel_group_ids.length >= 0) {
        await api.storageBatteries.update(editingBattery.value.id, { ...payload, panel_groups: batteryForm.panel_group_ids })
      }
      ElMessage.success('更新成功')
    } else {
      const created = await api.storageBatteries.create({ ...payload, panel_groups: batteryForm.panel_group_ids })
      if (batteryForm.panel_group_ids.length > 0 && created?.id) {
        await api.storageBatteries.update(created.id, { panel_groups: batteryForm.panel_group_ids })
      }
      ElMessage.success('新增成功')
    }
    batteryDialogVisible.value = false
    await loadBatteries()
    await loadSummary()
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败')
  }
}

const deleteBattery = async (id) => {
  try {
    await api.storageBatteries.delete(id)
    ElMessage.success('删除成功')
    await loadBatteries()
    await loadSummary()
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败')
  }
}

const openRecalcDialog = (battery) => {
  recalcBattery.value = battery
  const today = new Date()
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000)
  recalcDateRange.value = [sevenDaysAgo.toISOString().slice(0, 10), today.toISOString().slice(0, 10)]
  recalcDialogVisible.value = true
}

const openGlobalRecalcDialog = () => {
  recalcBattery.value = null
  const today = new Date()
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000)
  recalcDateRange.value = [sevenDaysAgo.toISOString().slice(0, 10), today.toISOString().slice(0, 10)]
  recalcDialogVisible.value = true
}

const executeRecalc = async () => {
  if (!recalcDateRange.value?.[0] || !recalcDateRange.value?.[1]) {
    ElMessage.warning('请选择日期范围')
    return
  }
  recalculating.value = true
  try {
    const payload = {
      date_from: recalcDateRange.value[0],
      date_to: recalcDateRange.value[1]
    }
    if (recalcBattery.value) {
      await api.storageBatteries.recalculate(recalcBattery.value.id, payload.date_from, payload.date_to)
    } else {
      await api.calculateStorage(payload)
    }
    ElMessage.success('调度计算完成')
    recalcDialogVisible.value = false
    await Promise.all([loadSchedules(), loadSummary(), loadDetailData()])
  } catch (e) {
    console.error(e)
    ElMessage.error('计算失败')
  } finally {
    recalculating.value = false
  }
}

const viewScheduleDetail = (row) => {
  activeTab.value = 'detail'
  detailBatteryId.value = row.battery
  detailDate.value = row.date
  setTimeout(() => loadDetailData(), 100)
}

watch([activeTab, detailBatteryId, detailDate], () => {
  if (activeTab.value === 'detail' && detailBatteryId.value && detailDate.value) {
    loadDetailData()
  }
})

onMounted(async () => {
  await Promise.all([loadBatteries(), loadPanelGroups(), loadSummary(), loadSchedules()])
})
</script>
