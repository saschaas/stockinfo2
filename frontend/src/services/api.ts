import axios from 'axios'

// Construct API URL based on current page URL (works with both normal and host networking)
// This allows API calls to work when accessing via IP address or domain
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  // Use current page's host and protocol to construct full origin
  const protocol = window.location.protocol
  const host = window.location.host // includes port if present
  return `${protocol}//${host}`
}

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to set baseURL dynamically on each request
api.interceptors.request.use(
  (config) => {
    // Set baseURL on every request to ensure it uses current window location
    const baseURL = `${getApiBaseUrl()}/api/v1`
    config.baseURL = baseURL

    // Don't add trailing slashes - they cause redirects that lose the port
    // FastAPI will accept URLs without trailing slashes just fine

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Health check endpoint
export async function fetchHealthStatus() {
  const { data } = await api.get('/health')
  return data
}

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

// Scraped category data types
export interface ScrapedStockData {
  ticker: string
  name?: string
  price?: number
  change_pct: number
  change_abs?: number
  volume?: number
  reason?: string
  sentiment?: string
}

export interface ScrapedCategorySource {
  source_key: string
  source_url: string
  date: string
  scraping_model?: string
}

export interface ScrapedCategoryDataResponse {
  success: boolean
  category: string
  category_display: string
  date_range: {
    start: string
    end: string
  }
  sources: ScrapedCategorySource[]
  data: ScrapedStockData[]
  count: number
  error?: string
  configured_sources?: string[] | null
  has_configured_sources?: boolean
}

export interface ScrapedCategorySummary {
  category: string
  display_name: string
  source_count: number
  date: string
}

export interface ScrapedCategoriesResponse {
  success: boolean
  date: string
  categories: ScrapedCategorySummary[]
}

// Fetch scraped data for a specific category (e.g., top_gainers, top_losers)
export async function fetchScrapedCategoryData(
  category: string,
  days: number = 1
): Promise<ScrapedCategoryDataResponse> {
  const { data } = await api.get(`/market/scraped-data/${category}`, {
    params: { days },
  })
  return data
}

// Fetch summary of all available scraped categories
export async function fetchScrapedCategories(): Promise<ScrapedCategoriesResponse> {
  const { data } = await api.get('/market/scraped-data')
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

// Fund updates/notifications types
export interface FundUpdateInfo {
  fund_id: number
  fund_name: string
  latest_filing_date: string | null
  last_data_update: string | null
  has_new_data: boolean
}

export interface FundUpdatesResponse {
  funds: FundUpdateInfo[]
  has_any_updates: boolean
  checked_at: string
}

export async function checkFundUpdates(since?: string): Promise<FundUpdatesResponse> {
  const { data } = await api.get('/funds/updates', {
    params: since ? { since } : {},
  })
  return data
}

// ETF endpoints
export interface ETFInfo {
  id: number
  name: string
  ticker: string
  url: string
  agent_command: string
  description: string | null
  category: string
  priority: number
  is_active: boolean
  last_scrape_at: string | null
  last_scrape_success: boolean | null
  last_scrape_error: string | null
  created_at: string
  updated_at: string
}

export interface ETFListResponse {
  total: number
  etfs: Array<{
    id: number
    name: string
    ticker: string
    url: string
    category: string
    priority: number
    is_active: boolean
    last_scrape_at: string | null
    last_scrape_success: boolean | null
  }>
}

export interface ETFHoldingsResponse {
  etf_id: number
  etf_name: string
  holding_date: string | null
  holdings: Array<{
    ticker: string
    company_name: string | null
    cusip: string | null
    shares: number | null
    market_value: number | null
    weight_pct: number | null
    change_type: string | null
    shares_change: number | null
    weight_change: number | null
    etf_count?: number
    etf_names?: string[]
  }>
  total_value: number
}

export interface ETFChangesResponse {
  etf_id: number
  etf_name: string
  holding_date: string | null
  new_positions: Array<any>
  increased: Array<any>
  decreased: Array<any>
  sold: Array<any>
}

export interface ETFUpdateInfo {
  etf_id: number
  etf_name: string
  ticker: string
  latest_holding_date: string | null
  last_data_update: string | null
  has_new_data: boolean
}

export interface ETFUpdatesResponse {
  etfs: ETFUpdateInfo[]
  has_any_updates: boolean
  checked_at: string
}

export interface ETFCreateData {
  name: string
  ticker: string
  url: string
  agent_command: string
  description?: string
  category?: string
}

export interface ETFUpdateData {
  name?: string
  url?: string
  agent_command?: string
  description?: string
  category?: string
  is_active?: boolean
}

export async function fetchETFs(category?: string, activeOnly: boolean = true): Promise<ETFListResponse> {
  const { data } = await api.get('/etfs/', {
    params: { category, active_only: activeOnly },
  })
  return data
}

export async function fetchETFHoldings(etfId: number, limit: number = 50): Promise<ETFHoldingsResponse> {
  const { data } = await api.get(`/etfs/${etfId}/holdings`, {
    params: { limit },
  })
  return data
}

export async function fetchETFChanges(etfId: number): Promise<ETFChangesResponse> {
  const { data } = await api.get(`/etfs/${etfId}/changes`)
  return data
}

export async function fetchAggregatedETFHoldings(limit: number = 50): Promise<ETFHoldingsResponse> {
  const { data } = await api.get('/etfs/aggregate/holdings', {
    params: { limit },
  })
  return data
}

export async function fetchAggregatedETFChanges(): Promise<ETFChangesResponse> {
  const { data } = await api.get('/etfs/aggregate/changes')
  return data
}

export async function checkETFUpdates(since?: string): Promise<ETFUpdatesResponse> {
  const { data } = await api.get('/etfs/updates', {
    params: since ? { since } : {},
  })
  return data
}

export async function addETF(data: ETFCreateData): Promise<ETFInfo> {
  const { data: response } = await api.post('/etfs/', data)
  return response
}

export async function updateETF(etfId: number, data: ETFUpdateData): Promise<ETFInfo> {
  const { data: response } = await api.put(`/etfs/${etfId}`, data)
  return response
}

export async function removeETF(etfId: number) {
  const { data } = await api.delete(`/etfs/${etfId}`)
  return data
}

export async function refreshETFHoldings() {
  const { data } = await api.post('/etfs/refresh')
  return data
}

export async function refreshSingleETF(etfId: number) {
  const { data } = await api.post(`/etfs/${etfId}/refresh`)
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

// Data sources overview types
export interface DataSourceInfo {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  description: string
  type: 'api' | 'service' | 'infrastructure'
  message: string
}

export interface DataTypeMapping {
  name: string
  primary: string
  fallback: string | null
}

export interface TabMapping {
  data_types: DataTypeMapping[]
}

export interface AffectedTab {
  tab: string
  data_type: string
  fallback: string | null
  fallback_available: boolean
}

export interface DataSourceWarning {
  source: string
  source_name: string
  message: string
  affected: AffectedTab[]
}

export interface DataSourcesResponse {
  sources: Record<string, DataSourceInfo>
  tabs: Record<string, TabMapping>
  warnings: DataSourceWarning[]
  checked_at: string
}

// Data sources overview endpoint
export async function fetchDataSourcesHealth(): Promise<DataSourcesResponse> {
  const { data } = await api.get('/health/data-sources')
  return data
}

// Configuration types
export interface AIModelSettings {
  default_model?: string
  stock_research_model?: string
  market_sentiment_model?: string
  web_scraping_model?: string
  temperature?: number
  max_tokens?: number
}

export interface DisplayPreferences {
  research_history_items?: number
  fund_recent_changes_items?: number
  holdings_per_fund?: number
  peers_in_comparison?: number
}

export interface WebsiteInfo {
  name: string
  url: string
}

export interface MarketScrapingSettings {
  website_key?: string
  scraping_model?: string
  analysis_model?: string
  custom_websites?: Record<string, WebsiteInfo>
}

export interface ConfigSettings {
  ai_models: AIModelSettings
  display_preferences: DisplayPreferences
  market_scraping: MarketScrapingSettings
}

export interface VPNStatus {
  enabled: boolean
  connected: boolean
  location: string | null
  message: string
}

export interface ConfigResponse {
  settings: ConfigSettings
  has_alpha_vantage_key: boolean
  has_fmp_key: boolean
  has_sec_user_agent: boolean
  vpn_status?: VPNStatus
}

export interface TestAPIKeyRequest {
  provider: string
  api_key: string
}

export interface TestAPIKeyResponse {
  valid: boolean
  message: string
  provider: string
}

// Configuration endpoints
export async function fetchConfigSettings(): Promise<ConfigResponse> {
  const { data } = await api.get('/config/settings')
  return data
}

export async function updateConfigSettings(settings: ConfigSettings): Promise<{ status: string; message: string }> {
  const { data } = await api.put('/config/settings', settings)
  return data
}

export async function testAPIKey(request: TestAPIKeyRequest): Promise<TestAPIKeyResponse> {
  const { data } = await api.post('/config/test-api-key', request)
  return data
}

// Scraped Websites types
export interface DataUseCategory {
  value: string
  label: string
  description: string
}

export interface DataTemplate {
  description: string
  template: Record<string, any>
}

export interface ScrapedWebsite {
  id: number
  key: string
  name: string
  url: string
  description?: string
  data_use: string  // Comma-separated for storage
  data_use_list: string[]  // List of categories
  data_use_display: string
  extraction_template?: Record<string, any>
  is_active: boolean
  last_test_at?: string
  last_test_result?: Record<string, any>
  last_test_success?: boolean
  created_at: string
  updated_at: string
}

export interface ScrapedWebsiteCreate {
  key: string
  name: string
  url: string
  description?: string
  data_use: string | string[]  // Can be single string or array
  extraction_template?: Record<string, any>
}

export interface ScrapedWebsiteUpdate {
  name?: string
  url?: string
  description?: string
  data_use?: string | string[]  // Can be single string or array
  extraction_template?: Record<string, any>
  is_active?: boolean
}

export interface ScrapedWebsiteTestRequest {
  url: string
  description?: string
  data_use: string | string[]  // Can be single string or array
}

export interface ScrapedWebsiteTestResponse {
  success: boolean
  scraped_data?: Record<string, any>
  error?: string
  response_time_ms: number
  extraction_prompt_used: string
}

export interface DataUseCategoriesResponse {
  categories: DataUseCategory[]
  templates: Record<string, DataTemplate>
}

// Scraped Websites endpoints
export async function fetchDataUseCategories(): Promise<DataUseCategoriesResponse> {
  const { data } = await api.get('/websites/categories')
  return data
}

export async function fetchScrapedWebsites(dataUse?: string, isActive?: boolean): Promise<ScrapedWebsite[]> {
  const params: Record<string, any> = {}
  if (dataUse) params.data_use = dataUse
  if (isActive !== undefined) params.is_active = isActive
  const { data } = await api.get('/websites', { params })
  return data
}

export async function fetchScrapedWebsite(key: string): Promise<ScrapedWebsite> {
  const { data } = await api.get(`/websites/${key}`)
  return data
}

export async function createScrapedWebsite(website: ScrapedWebsiteCreate): Promise<ScrapedWebsite> {
  const { data } = await api.post('/websites', website)
  return data
}

export async function updateScrapedWebsite(key: string, website: ScrapedWebsiteUpdate): Promise<ScrapedWebsite> {
  const { data } = await api.put(`/websites/${key}`, website)
  return data
}

export async function deleteScrapedWebsite(key: string): Promise<void> {
  await api.delete(`/websites/${key}`)
}

export async function testScrapeWebsite(request: ScrapedWebsiteTestRequest): Promise<ScrapedWebsiteTestResponse> {
  const { data } = await api.post('/websites/test', request)
  return data
}

export async function testExistingWebsite(key: string): Promise<ScrapedWebsiteTestResponse> {
  const { data } = await api.post(`/websites/${key}/test`)
  return data
}

// Category mapping types
export interface CategorySource {
  key: string
  name: string
  url: string
}

export interface CategoryInfo {
  category: string
  display_name: string
  selected_sources: string[]
  available_sources: CategorySource[]
}

export interface CategoryMappingsResponse {
  categories: CategoryInfo[]
  mappings: Record<string, string[]>
}

// Category mapping endpoints
export async function fetchCategoryMappings(): Promise<CategoryMappingsResponse> {
  const { data } = await api.get('/config/category-mappings')
  return data
}

export async function updateCategoryMappings(
  mappings: Record<string, string[]>
): Promise<{ status: string; message: string; mappings: Record<string, string[]> }> {
  const { data } = await api.put('/config/category-mappings', mappings)
  return data
}

export async function refreshCategoryData(
  category: string
): Promise<{ status: string; message: string; jobs: Array<{ source_key: string; job_id: string }> }> {
  const { data } = await api.post(`/config/refresh-category/${category}`)
  return data
}

export default api
