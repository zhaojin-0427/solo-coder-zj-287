// 告警等级相关映射
export const ALERT_LEVEL_LABELS = {
  normal: '正常',
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重'
}

export const ALERT_LEVEL_COLORS = {
  normal: '#22c55e',
  low: '#3b82f6',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444'
}

export const ALERT_LEVEL_TAG_TYPES = {
  normal: 'success',
  low: '',
  medium: 'warning',
  high: 'warning',
  critical: 'danger'
}

// 储能电池状态映射
export const BATTERY_STATUS_LABELS = {
  normal: '正常',
  warning: '告警',
  maintenance: '维护中'
}

export const BATTERY_STATUS_TAG_TYPES = {
  normal: 'success',
  warning: 'warning',
  maintenance: 'info'
}

// 储能SOC相关
export const SOC_COLORS = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#ef4444',
  empty: '#64748b'
}

export const getSocColor = (soc) => {
  if (soc === '--' || soc == null || soc === 0) return SOC_COLORS.empty
  if (soc >= 60) return SOC_COLORS.high
  if (soc >= 30) return SOC_COLORS.medium
  return SOC_COLORS.low
}

export const getSocTagType = (soc) => {
  if (soc >= 60) return 'success'
  if (soc >= 30) return 'warning'
  return 'danger'
}

// 清洁计划状态映射
export const CLEANING_STATUS_LABELS = {
  pending: '待执行',
  completed: '已完成',
  cancelled: '已取消'
}

export const CLEANING_STATUS_TAG_TYPES = {
  pending: 'warning',
  completed: 'success',
  cancelled: 'info'
}

// 清洁方式映射
export const CLEANING_METHOD_LABELS = {
  manual: '人工清洁',
  water: '水洗清洁',
  dry: '干洗清洁',
  robot: '机器人清洁',
  rain: '雨水自洁'
}

// 清洁有效性等级映射
export const EFFECTIVENESS_LABELS = {
  excellent: '优秀',
  good: '良好',
  fair: '一般',
  poor: '较差',
  none: '未评估'
}

export const EFFECTIVENESS_TAG_TYPES = {
  excellent: 'success',
  good: 'primary',
  fair: 'warning',
  poor: 'danger',
  none: 'info'
}

// 健康评分颜色
export const getHealthColor = (score) => {
  if (score === '--' || score == null) return '#64748b'
  if (score >= 90) return '#22c55e'
  if (score >= 70) return '#f59e0b'
  return '#ef4444'
}

// 收益颜色（正绿负红）
export const getProfitColor = (value) => {
  return (value || 0) >= 0 ? '#22c55e' : '#ef4444'
}

// 主题色板
export const THEME_COLORS = {
  primary: '#3b82f6',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  purple: '#8b5cf6',
  orange: '#f97316',
  pink: '#ec4899',
  teal: '#14b8a6',
  indigo: '#6366f1',
  lime: '#84cc16',
  sky: '#0ea5e9'
}

export const CHART_COLOR_PALETTE = [
  '#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4',
  '#ef4444', '#ec4899', '#14b8a6', '#f97316', '#6366f1',
  '#84cc16', '#0ea5e9'
]
