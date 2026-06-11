// 金额格式化
export const formatMoney = (value, decimals = 2) => {
  if (value == null || isNaN(value)) return '0'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

export const formatMoneyWithSymbol = (value, decimals = 2) => {
  return `¥${formatMoney(value, decimals)}`
}

// 带正负号的金额格式化
export const formatSignedMoney = (value, decimals = 2) => {
  const num = Number(value) || 0
  const sign = num >= 0 ? '+' : ''
  return `${sign}¥${formatMoney(Math.abs(num), decimals)}`
}

// 电量格式化
export const formatKwh = (value, decimals = 2) => {
  if (value == null || isNaN(value)) return '0'
  return Number(value).toFixed(decimals)
}

export const formatKwhWithUnit = (value, decimals = 2) => {
  return `${formatKwh(value, decimals)} kWh`
}

// 带正负号的电量格式化
export const formatSignedKwh = (value, decimals = 2) => {
  const num = Number(value) || 0
  const sign = num >= 0 ? '+' : ''
  return `${sign}${formatKwh(Math.abs(num), decimals)} kWh`
}

// 百分比格式化
export const formatPercent = (value, decimals = 1) => {
  if (value == null || isNaN(value)) return '0'
  return Number(value).toFixed(decimals)
}

export const formatPercentWithUnit = (value, decimals = 1) => {
  return `${formatPercent(value, decimals)}%`
}

// 日期格式化
export const formatDate = (date, format = 'YYYY-MM-DD') => {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
}

// 数字千分位格式化
export const formatNumber = (value, decimals = 0) => {
  if (value == null || isNaN(value)) return '0'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

// 截取日期月日部分（用于图表X轴）
export const formatMonthDay = (dateStr) => {
  if (!dateStr) return ''
  if (dateStr.length >= 10) {
    return dateStr.slice(5)
  }
  return dateStr
}

// 小时格式化
export const formatHour = (hour) => {
  return `${hour}:00`
}
