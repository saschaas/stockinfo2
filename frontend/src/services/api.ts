import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Market endpoints
export async function fetchMarketSentiment() {
  const { data } = await api.get('/market/sentiment')
  return data
}

export async function fetchMarketSentimentHistory(days: number = 7) {
  const { data } = await api.get('/market/sentiment/history', {
    params: { days },
  })
  return data
}

export async function refreshMarketSentiment() {
  const { data } = await api.post('/market/sentiment/refresh')
  return data
}

// Stock endpoints
export async function fetchStockAnalysis(ticker: string) {
  const { data } = await api.get(`/stocks/${ticker}`)
  return data
}

export async function fetchStockPrices(ticker: string, days: number = 30) {
  const { data } = await api.get(`/stocks/${ticker}/prices`, {
    params: { days },
  })
  return data
}

export async function startStockResearch(ticker: string, options?: {
  include_peers?: boolean
  include_technical?: boolean
  include_ai_analysis?: boolean
}) {
  const { data } = await api.post('/stocks/research', {
    ticker,
    ...options,
  })
  return data
}

export async function fetchStockPeers(ticker: string, limit: number = 5) {
  const { data } = await api.get(`/stocks/${ticker}/peers`, {
    params: { limit },
  })
  return data
}

export async function fetchFundOwnership(ticker: string) {
  const { data } = await api.get(`/stocks/${ticker}/fund-ownership`)
  return data
}

// Fund endpoints
export async function fetchFunds(category?: string, activeOnly: boolean = true, fundsOnly: boolean = true) {
  const { data } = await api.get('/funds', {
    params: { category, active_only: activeOnly, funds_only: fundsOnly },
  })
  return data
}

export async function fetchFundHoldings(fundId: number, limit: number = 50) {
  const { data } = await api.get(`/funds/${fundId}/holdings`, {
    params: { limit },
  })
  return data
}

export async function fetchFundChanges(fundId: number) {
  const { data } = await api.get(`/funds/${fundId}/changes`)
  return data
}

export async function refreshFundHoldings() {
  const { data } = await api.post('/funds/refresh')
  return data
}

export async function searchFunds(query: string, limit: number = 5) {
  const { data } = await api.get('/funds/search', {
    params: { query, limit },
  })
  return data
}

export async function validateFund(cik: string, name?: string) {
  const { data } = await api.get(`/funds/validate/${cik}`, {
    params: name ? { name } : {},
  })
  return data
}

export async function addFund(cik: string, name?: string, category: string = 'general') {
  const { data } = await api.post('/funds', {
    cik,
    name,
    category,
  })
  return data
}

export async function removeFund(fundId: number) {
  const { data } = await api.delete(`/funds/${fundId}`)
  return data
}

// Report endpoints
export async function getStockReport(ticker: string, format: 'html' | 'pdf' = 'html') {
  const { data } = await api.get(`/reports/stock/${ticker}`, {
    params: { format },
    responseType: format === 'pdf' ? 'blob' : 'text',
  })
  return data
}

export async function getMarketReport(format: 'html' | 'pdf' = 'html') {
  const { data } = await api.get('/reports/market', {
    params: { format },
    responseType: format === 'pdf' ? 'blob' : 'text',
  })
  return data
}

// Health check
export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}

export default api
