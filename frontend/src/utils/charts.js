import { CHART_COLOR_PALETTE, THEME_COLORS } from './constants'

const defaultGrid = {
  left: '3%',
  right: '4%',
  bottom: '3%',
  containLabel: true
}

const defaultTooltip = {
  trigger: 'axis'
}

// 创建线性渐变颜色
export const createLinearGradient = (color, opacityStart = 0.3, opacityEnd = 0.02) => {
  return {
    type: 'linear',
    x: 0, y: 0, x2: 0, y2: 1,
    colorStops: [
      { offset: 0, color: hexToRgba(color, opacityStart) },
      { offset: 1, color: hexToRgba(color, opacityEnd) }
    ]
  }
}

// hex颜色转rgba
const hexToRgba = (hex, alpha = 1) => {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

// 基础折线图配置
export const createLineChart = (options = {}) => {
  const {
    xData = [],
    series = [],
    yAxisName = '',
    yMin = null,
    yMax = null,
    tooltip = {},
    grid = {},
    legend = null,
    smooth = true,
    showSymbol = false,
    areaStyle = false,
    areaColor = null,
    lineColor = THEME_COLORS.primary,
    lineWidth = 3,
    markLine = null,
    label = null
  } = options

  const seriesConfig = Array.isArray(series) && series.length > 0
    ? series.map(s => ({
        type: 'line',
        smooth,
        showSymbol,
        ...s,
        lineStyle: { width: s.lineWidth || lineWidth, ...s.lineStyle },
        areaStyle: s.areaStyle || (areaStyle ? createLinearGradient(s.color || lineColor) : undefined),
        markLine: s.markLine || markLine,
        label: s.label || label
      }))
    : [{
        type: 'line',
        data: series.data || [],
        smooth,
        showSymbol,
        itemStyle: { color: lineColor },
        lineStyle: { width: lineWidth },
        areaStyle: areaStyle ? createLinearGradient(areaColor || lineColor) : undefined,
        markLine,
        label
      }]

  return {
    tooltip: { ...defaultTooltip, ...tooltip },
    legend: legend || (seriesConfig.length > 1 ? { top: 0 } : null),
    grid: { ...defaultGrid, ...grid },
    xAxis: {
      type: 'category',
      data: xData,
      ...options.xAxis
    },
    yAxis: {
      type: 'value',
      name: yAxisName,
      min: yMin,
      max: yMax,
      ...options.yAxis
    },
    series: seriesConfig
  }
}

// 基础柱状图配置
export const createBarChart = (options = {}) => {
  const {
    xData = [],
    series = [],
    yAxisName = '',
    yMin = null,
    yMax = null,
    tooltip = {},
    grid = {},
    legend = null,
    barWidth = null,
    itemStyle = {},
    label = null,
    markLine = null,
    color = null,
    colorByIndex = false
  } = options

  const seriesConfig = Array.isArray(series) && series.length > 0
    ? series.map((s, idx) => ({
        type: 'bar',
        ...s,
        barWidth: s.barWidth || barWidth,
        itemStyle: s.itemStyle || itemStyle || (
          colorByIndex
            ? { color: (params) => CHART_COLOR_PALETTE[params.dataIndex % CHART_COLOR_PALETTE.length] }
            : { color: s.color || color }
        ),
        label: s.label || label,
        markLine: s.markLine || markLine
      }))
    : [{
        type: 'bar',
        data: series.data || [],
        barWidth,
        itemStyle: itemStyle || (
          colorByIndex
            ? { color: (params) => CHART_COLOR_PALETTE[params.dataIndex % CHART_COLOR_PALETTE.length] }
            : { color }
        ),
        label,
        markLine
      }]

  return {
    tooltip: { ...defaultTooltip, ...tooltip },
    legend: legend || (seriesConfig.length > 1 ? { top: 0 } : null),
    grid: { ...defaultGrid, ...grid },
    xAxis: {
      type: 'category',
      data: xData,
      ...options.xAxis
    },
    yAxis: {
      type: 'value',
      name: yAxisName,
      min: yMin,
      max: yMax,
      ...options.yAxis
    },
    series: seriesConfig
  }
}

// 基础饼图配置
export const createPieChart = (options = {}) => {
  const {
    data = [],
    tooltip = {},
    legend = { bottom: 0 },
    radius = ['40%', '70%'],
    center = ['50%', '45%'],
    label = { formatter: '{b}\n{d}%' },
    emphasis = { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' } },
    colors = CHART_COLOR_PALETTE
  } = options

  const coloredData = data.map((item, idx) => ({
    ...item,
    itemStyle: item.itemStyle || { color: colors[idx % colors.length] }
  }))

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', ...tooltip },
    legend,
    series: [{
      type: 'pie',
      radius,
      center,
      data: coloredData,
      label,
      emphasis
    }]
  }
}

// 双Y轴图表配置
export const createDualAxisChart = (options = {}) => {
  const {
    xData = [],
    leftSeries = [],
    rightSeries = [],
    leftYAxisName = '',
    rightYAxisName = '',
    leftYMin = null,
    leftYMax = null,
    rightYMin = null,
    rightYMax = null,
    tooltip = { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid = {},
    legend = { top: 0 }
  } = options

  const leftSeriesConfig = leftSeries.map(s => ({
    ...s,
    yAxisIndex: 0,
    itemStyle: s.itemStyle || { color: s.color }
  }))

  const rightSeriesConfig = rightSeries.map(s => ({
    ...s,
    yAxisIndex: 1,
    itemStyle: s.itemStyle || { color: s.color }
  }))

  return {
    tooltip,
    legend,
    grid: { ...defaultGrid, ...grid },
    xAxis: {
      type: 'category',
      data: xData,
      ...options.xAxis
    },
    yAxis: [
      {
        type: 'value',
        name: leftYAxisName,
        position: 'left',
        min: leftYMin,
        max: leftYMax,
        ...options.leftYAxis
      },
      {
        type: 'value',
        name: rightYAxisName,
        position: 'right',
        min: rightYMin,
        max: rightYMax,
        ...options.rightYAxis
      }
    ],
    series: [...leftSeriesConfig, ...rightSeriesConfig]
  }
}

// 创建空数据图表占位
export const createEmptyChart = (text = '暂无数据') => {
  return {
    title: {
      text,
      left: 'center',
      top: 'center',
      textStyle: { color: '#94a3b8', fontSize: 14 }
    }
  }
}

// 水平柱状图（排行榜类）
export const createHorizontalBarChart = (options = {}) => {
  const {
    yData = [],
    series = [],
    xAxisNames = [''],
    tooltip = { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid = {},
    legend = { top: 0 },
    label = null
  } = options

  const seriesConfig = series.map((s, idx) => ({
    type: 'bar',
    xAxisIndex: idx,
    ...s,
    label: s.label || label
  }))

  const xAxisConfig = xAxisNames.map((name, idx) => ({
    type: 'value',
    name,
    position: idx === 0 ? 'bottom' : 'top',
    ...(options.xAxis && options.xAxis[idx])
  }))

  return {
    tooltip,
    legend,
    grid: { ...defaultGrid, ...grid },
    xAxis: xAxisConfig,
    yAxis: {
      type: 'category',
      data: yData,
      ...options.yAxis
    },
    series: seriesConfig
  }
}
