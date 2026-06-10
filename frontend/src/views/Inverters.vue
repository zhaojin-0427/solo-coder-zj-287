<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
              <el-icon><Cpu /></el-icon> 逆变器管理
            </div>
            <el-button type="primary" @click="showDialog()" :icon="Plus" size="small">新增逆变器</el-button>
          </div>
          <el-table :data="inverters" stripe style="width:100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="brand" label="品牌" width="140" />
            <el-table-column prop="model" label="型号" width="180" />
            <el-table-column prop="rated_power" label="额定功率(kW)" width="120" />
            <el-table-column prop="efficiency" label="效率(%)" width="100" />
            <el-table-column prop="api_endpoint" label="API端点" min-width="200" show-overflow-tooltip />
            <el-table-column prop="panel_group_count" label="关联组数" width="100" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="showDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-card-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
              <el-icon><Sunny /></el-icon> 光伏板组管理
            </div>
            <el-button type="primary" @click="showPanelDialog()" :icon="Plus" size="small">新增光伏板组</el-button>
          </div>
          <el-table :data="panelGroups" stripe style="width:100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="名称" width="160" />
            <el-table-column prop="capacity_kw" label="容量(kW)" width="100" />
            <el-table-column prop="install_angle" label="安装角度(°)" width="110" />
            <el-table-column prop="azimuth" label="方位角(°)" width="100" />
            <el-table-column prop="inverter_name" label="逆变器" width="180" />
            <el-table-column prop="grid_date" label="并网日期" width="120" />
            <el-table-column prop="location" label="地区" width="80" />
            <el-table-column prop="total_generation" label="总发电(kWh)" width="120">
              <template #default="{ row }">{{ row.total_generation?.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column prop="days_online" label="在线天数" width="100" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="showPanelDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeletePanel(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="editingItem ? '编辑逆变器' : '新增逆变器'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="品牌">
          <el-input v-model="form.brand" placeholder="如: 华为、阳光电源" />
        </el-form-item>
        <el-form-item label="型号">
          <el-input v-model="form.model" placeholder="如: SUN2000-6KTL" />
        </el-form-item>
        <el-form-item label="额定功率(kW)">
          <el-input-number v-model="form.rated_power" :min="0" :precision="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="效率(%)">
          <el-input-number v-model="form.efficiency" :min="80" :max="100" :precision="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="API端点">
          <el-input v-model="form.api_endpoint" placeholder="逆变器监控API地址（选填）" />
        </el-form-item>
        <el-form-item label="API密钥">
          <el-input v-model="form.api_key" placeholder="API访问密钥（选填）" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveInverter" :loading="saving">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="panelDialogVisible" :title="editingPanel ? '编辑光伏板组' : '新增光伏板组'" width="550px">
      <el-form :model="panelForm" label-width="110px">
        <el-form-item label="名称">
          <el-input v-model="panelForm.name" placeholder="如: 屋顶南侧A组" />
        </el-form-item>
        <el-form-item label="装机容量(kW)">
          <el-input-number v-model="panelForm.capacity_kw" :min="0.1" :precision="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="安装角度(°)">
          <el-input-number v-model="panelForm.install_angle" :min="0" :max="90" :precision="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="方位角(°)">
          <el-input-number v-model="panelForm.azimuth" :min="0" :max="360" :precision="0" style="width:100%" />
          <div style="color:#94a3b8;font-size:12px;margin-top:4px">180°=正南, 135°=东南, 225°=西南</div>
        </el-form-item>
        <el-form-item label="逆变器">
          <el-select v-model="panelForm.inverter" placeholder="选择逆变器" clearable style="width:100%">
            <el-option v-for="inv in inverters" :key="inv.id" :label="`${inv.brand} ${inv.model}`" :value="inv.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="并网日期">
          <el-date-picker v-model="panelForm.grid_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="地区">
          <el-input v-model="panelForm.location" placeholder="如: 上海" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="panelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePanel" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Cpu, Sunny, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const inverters = ref([])
const panelGroups = ref([])
const dialogVisible = ref(false)
const panelDialogVisible = ref(false)
const editingItem = ref(null)
const editingPanel = ref(null)
const saving = ref(false)

const defaultForm = { brand: '', model: '', rated_power: 5, efficiency: 98, api_endpoint: '', api_key: '' }
const form = ref({ ...defaultForm })

const defaultPanelForm = { name: '', capacity_kw: 5, install_angle: 30, azimuth: 180, inverter: null, grid_date: '', location: '' }
const panelForm = ref({ ...defaultPanelForm })

const loadData = async () => {
  try {
    inverters.value = await api.inverters.list()
    panelGroups.value = await api.panelGroups.list()
  } catch (e) { console.error(e) }
}

const showDialog = (item = null) => {
  editingItem.value = item
  form.value = item ? { ...item } : { ...defaultForm }
  dialogVisible.value = true
}

const showPanelDialog = (item = null) => {
  editingPanel.value = item
  panelForm.value = item ? { ...item, inverter: item.inverter } : { ...defaultPanelForm }
  panelDialogVisible.value = true
}

const saveInverter = async () => {
  saving.value = true
  try {
    if (editingItem.value) {
      await api.inverters.update(editingItem.value.id, form.value)
    } else {
      await api.inverters.create(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await loadData()
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const savePanel = async () => {
  saving.value = true
  try {
    if (editingPanel.value) {
      await api.panelGroups.update(editingPanel.value.id, panelForm.value)
    } else {
      await api.panelGroups.create(panelForm.value)
    }
    ElMessage.success('保存成功')
    panelDialogVisible.value = false
    await loadData()
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此逆变器？', '提示', { type: 'warning' })
    await api.inverters.delete(id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {}
}

const handleDeletePanel = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此光伏板组？', '提示', { type: 'warning' })
    await api.panelGroups.delete(id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {}
}

onMounted(loadData)
</script>
