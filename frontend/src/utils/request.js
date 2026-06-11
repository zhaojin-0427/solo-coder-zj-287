// 构建分页查询参数
export const buildPaginationParams = (page = 1, pageSize = 20, extra = {}) => {
  const params = {
    page,
    page_size: pageSize,
    ...extra
  }
  // 移除空值参数
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null || params[key] === undefined) {
      delete params[key]
    }
  })
  return params
}

// 构建日期范围参数
export const buildDateRangeParams = (dateRange, startKey = 'date_from', endKey = 'date_to') => {
  const params = {}
  if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
    params[startKey] = dateRange[0]
    params[endKey] = dateRange[1]
  }
  return params
}

// 解析分页响应
export const parsePagedResponse = (response) => {
  if (response && response.results) {
    return {
      list: response.results,
      total: response.count,
      page: response.page || 1,
      pageSize: response.page_size || 20,
      totalPages: response.num_pages || 1
    }
  }
  const list = Array.isArray(response) ? response : []
  return {
    list,
    total: list.length,
    page: 1,
    pageSize: list.length || 20,
    totalPages: 1
  }
}

// 从分页响应中提取列表数据
export const extractListData = (response) => {
  if (response && response.results) {
    return response.results
  }
  return Array.isArray(response) ? response : []
}

// 从分页响应中提取总数
export const extractTotalCount = (response) => {
  if (response && response.count != null) {
    return response.count
  }
  if (Array.isArray(response)) {
    return response.length
  }
  return 0
}
