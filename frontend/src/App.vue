<template>
  <div class="app-container">
    <el-container>
      <el-aside width="220px" class="app-aside">
        <div class="logo-section">
          <el-icon :size="28" color="#f59e0b"><Sunny /></el-icon>
          <span class="logo-text">光伏监测平台</span>
        </div>
        <el-menu
          :default-active="currentRoute"
          class="app-menu"
          background-color="#1e293b"
          text-color="#94a3b8"
          active-text-color="#f59e0b"
          router
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <span>发电监控看板</span>
          </el-menu-item>
          <el-menu-item index="/cleaning">
            <el-icon><Brush /></el-icon>
            <span>清洁维护</span>
          </el-menu-item>
          <el-menu-item index="/storage">
            <el-icon><Lightning /></el-icon>
            <span>储能管理</span>
          </el-menu-item>
          <el-menu-item index="/alerts">
            <el-icon><Bell /></el-icon>
            <span>告警中心</span>
          </el-menu-item>
          <el-menu-item index="/inverters">
            <el-icon><Cpu /></el-icon>
            <span>逆变器管理</span>
          </el-menu-item>
          <el-menu-item index="/generation">
            <el-icon><DataLine /></el-icon>
            <span>发电数据</span>
          </el-menu-item>
          <el-menu-item index="/revenue">
            <el-icon><Wallet /></el-icon>
            <span>收益明细</span>
          </el-menu-item>
          <el-menu-item index="/payback">
            <el-icon><Timer /></el-icon>
            <span>回本预测</span>
          </el-menu-item>
          <el-menu-item index="/statistics">
            <el-icon><TrendCharts /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="app-header">
          <div class="header-left">
            <h2>{{ currentTitle }}</h2>
          </div>
          <div class="header-right">
            <el-button type="warning" :icon="Sunny" @click="handleSeedDemo" :loading="seeding" size="small">
              生成演示数据
            </el-button>
          </div>
        </el-header>
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Sunny, Monitor, Cpu, DataLine, Wallet, Timer, TrendCharts, Bell, Lightning, Brush } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from './api'

const route = useRoute()
const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')
const seeding = ref(false)

const handleSeedDemo = async () => {
  seeding.value = true
  try {
    await api.seedDemo()
    ElMessage.success('演示数据生成成功！')
    window.location.reload()
  } catch (e) {
    ElMessage.error('生成演示数据失败')
  } finally {
    seeding.value = false
  }
}
</script>

<style>
* { 
  margin: 0; 
  padding: 0; 
  box-sizing: border-box; 
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
  -webkit-writing-mode: horizontal-tb !important;
}
html, body, #app { 
  height: 100%; 
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; 
  writing-mode: horizontal-tb !important;
}

.app-container { height: 100vh; width: 100vw; }
.el-container { height: 100%; width: 100%; display: flex; flex-direction: row; }
.el-container .el-container { flex-direction: column; }

.app-aside {
  background: #1e293b;
  overflow-y: auto;
  border-right: 1px solid #334155;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid #334155;
}

.logo-text {
  color: #f59e0b;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
}

.app-menu {
  border-right: none !important;
}

.app-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
  font-size: 14px;
}

.app-menu .el-menu-item:hover {
  background-color: #334155 !important;
}

.app-menu .el-menu-item.is-active {
  background-color: #334155 !important;
  border-right: 3px solid #f59e0b;
}

.app-header {
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  padding: 0 24px;
  height: 60px !important;
}

.header-left h2 {
  font-size: 18px;
  color: #1e293b;
  font-weight: 600;
}

.app-main {
  background: #f1f5f9;
  padding: 20px;
  overflow-y: auto;
  width: 100%;
  min-width: 0;
}

.el-row {
  width: 100% !important;
  display: flex !important;
  flex-wrap: wrap !important;
  min-width: 0 !important;
}

.el-col {
  min-width: 0 !important;
  flex-shrink: 0 !important;
}

.stat-row .el-col {
  padding: 0 8px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: transform 0.2s, box-shadow 0.2s;
  min-width: 140px;
  width: 100%;
  display: block;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.stat-card .label {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 8px;
}

.stat-card .value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}

.stat-card .unit {
  font-size: 14px;
  font-weight: 400;
  color: #94a3b8;
  margin-left: 4px;
}

.page-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  margin-bottom: 20px;
}

.page-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.el-table th.el-table__cell {
  background-color: #f8fafc !important;
  color: #475569;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 350px;
}

.stat-card .label,
.stat-card .value,
.stat-card .unit {
  white-space: nowrap !important;
  overflow: visible !important;
  display: block !important;
  width: auto !important;
}

.el-table th.el-table__cell .cell,
.el-table td.el-table__cell .cell {
  white-space: nowrap !important;
  writing-mode: horizontal-tb !important;
}

.page-card-title {
  white-space: nowrap !important;
}
</style>
