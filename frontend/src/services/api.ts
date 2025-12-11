import axios from 'axios'

// Use relative URL to go through nginx proxy (works with both normal and host networking)
// In production/deployment, nginx proxies /api/* to backend:8000/api/*
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

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

export async function refreshWebScrapedMarket(
  websiteKey?: string,
  scrapingModel?: string,
  analysisModel?: string
): Promise<{ status: string; job_id: string; message: string }> {
  const params = new URLSearchParams()
  if (websiteKey) params.append('website_key', websiteKey)
  if (scrapingModel) params.append('scraping_model', scrapingModel)
  if (analysisModel) params.append('analysis_model', analysisModel)

  const { data } = await api.post(`/market/sentiment/refresh-web-scraped?${params.toString()}`)
  return data
}

export async function getMarketScrapingConfig(): Promise<{
  available_websites: Record<string, { name: string; url: string }>
}> {
  const { data } = await api.get('/market/scraping-config')
  return data
}

export async function setMarketScrapingConfig(
  websiteKey: string,
  scrapingModel?: string,
  analysisModel?: string
): Promise<{ status: string; message: string }> {
  const { data } = await api.post('/market/scraping-config', {
    website_key: websiteKey,
    scraping_model: scrapingModel,
    analysis_model: analysisModel,
  })
  return data
}

export async function fetchIndicesHistory(days: number = 90) {
  const { data } = await api.get('/market/indices/history', {
    params: { days },
  })
  return data
}

// Type definitions for market data
export interface CombinedMarketResponse {
  traditional: MarketSentimentResponse
  web_scraped?: WebScrapedMarketDataResponse
}

export interface MarketSentimentResponse {
  date: string
  indices?: {
    sp500: { close: number | null; change_pct: number | null }
    nasdaq: { close: number | null; change_pct: number | null }
    dow: { close: number | null; change_pct: number | null }
  }
  overall_sentiment?: number
  bullish_score?: number
  bearish_score?: number
  hot_sectors: Array<{ name: string }>
  negative_sectors: Array<{ name: string }>
  top_news: Array<any>
  message?: string
}

export interface WebScrapedMarketDataResponse {
  date: string
  source_url: string
  source_name: string
  market_summary?: string
  overall_sentiment?: number
  bullish_score?: number
  bearish_score?: number
  trending_sectors: Array<{ name: string }>
  declining_sectors: Array<{ name: string }>
  market_themes: string[]
  key_events: string[]
  confidence_score?: number
  scraping_model?: string
  analysis_model?: string
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
  llm_model?: string
}) {
  const { data } = await api.post('/stocks/research', {
    ticker,
    ...options,
  })
  return data
}

// Ollama models endpoint
export interface OllamaModel {
  name: string
  display_name: string
  size: number
  modified_at: string
}

export interface OllamaModelsResponse {
  models: OllamaModel[]
  default_model: string
  default_available: boolean
  error?: string
}

export async function fetchAvailableModels(): Promise<OllamaModelsResponse> {
  const { data } = await api.get('/stocks/models/available')
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

export async function fetchSectorComparison(ticker: string, lookbackDays: number = 180) {
  const { data} = await api.get(`/stocks/${ticker}/sector-comparison`, {
    params: { lookback_days: lookbackDays },
  })
  return data
}

export async function startTechnicalAnalysis(ticker: string, period: string = '6mo') {
  const { data } = await api.post(`/stocks/${ticker}/technical-analysis`, {
    ticker,
    period,
  })
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

export async function fetchAggregatedHoldings(limit: number = 50) {
  const { data } = await api.get('/funds/aggregate/holdings', {
    params: { limit },
  })
  return data
}

export async function fetchAggregatedChanges() {
  const { data } = await api.get('/funds/aggregate/changes')
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
