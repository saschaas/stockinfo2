// Market types
export interface IndexData {
  close: number | null
  change_pct: number | null
}

export interface MarketSentiment {
  date: string
  indices?: {
    sp500?: IndexData
    nasdaq?: IndexData
    dow?: IndexData
  }
  overall_sentiment?: number | null
  bullish_score?: number | null
  bearish_score?: number | null
  hot_sectors?: any[]
  negative_sectors?: any[]
  top_news?: NewsItem[]
  message?: string
}

export interface NewsItem {
  title: string
  source?: string
  url?: string
  published_at?: string
  sentiment?: number
}

// Stock types
export interface StockAnalysis {
  ticker: string
  analysis_date: string
  company_name?: string
  sector?: string
  industry?: string
  pe_ratio?: number
  forward_pe?: number
  peg_ratio?: number
  price_to_book?: number
  debt_to_equity?: number
  market_cap?: number
  rsi?: number
  macd?: number
  macd_signal?: number
  sma_20?: number
  sma_50?: number
  sma_200?: number
  bollinger_upper?: number
  bollinger_lower?: number
  current_price?: number
  target_price_6m?: number
  price_change_1d?: number
  price_change_1w?: number
  price_change_1m?: number
  price_change_ytd?: number
  fund_ownership?: FundOwnership[]
  total_fund_shares?: number
  recommendation?: string
  confidence_score?: number
  recommendation_reasoning?: string
  risks?: string[]
  opportunities?: string[]
  peer_comparison?: any
  data_sources?: Record<string, DataSource>
}

export interface PriceData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// Fund types
export interface Fund {
  id: number
  name: string
  ticker?: string
  cik?: string
  category: string
  priority: number
}

export interface FundHolding {
  ticker: string
  company_name?: string
  shares: number
  value: number
  percentage?: number
  change_type?: string
  shares_change?: number
}

export interface FundOwnership {
  fund_name: string
  shares: number
  value: number
  percentage: number
}

// Data source types
export interface DataSource {
  type: 'api' | 'ai' | 'web'
  name: string
  timestamp: string
  cached: boolean
}

// Research job types
export interface ResearchJob {
  id: string
  ticker: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  currentStep: string
  result?: StockAnalysis
  error?: string
  suggestion?: string
}

// WebSocket message types
export interface WSProgressMessage {
  type: 'progress'
  job_id: string
  progress: number
  current_step: string
  status: string
}

export interface WSCompleteMessage {
  type: 'complete'
  job_id: string
  result: any
}

export interface WSErrorMessage {
  type: 'error'
  job_id: string
  error: string
  suggestion?: string
}

export interface WSNotificationMessage {
  type: 'notification'
  notification_type: 'info' | 'warning' | 'error' | 'success'
  message: string
  data?: any
}

export type WSMessage =
  | WSProgressMessage
  | WSCompleteMessage
  | WSErrorMessage
  | WSNotificationMessage

// Watchlist types
export interface WatchlistItem {
  id: number
  ticker: string
  company_name?: string
  added_at: string
  sort_order: number  // Custom sort order for user-defined ordering
  current_price?: number
  previous_close?: number
  change_amount?: number
  change_pct?: number
  news_count: number
  recent_news_count: number  // News from today and yesterday (for table display)
  news_sentiment?: string  // Aggregated sentiment: "bullish", "somewhat_bullish", "somewhat_bearish", "bearish", "neutral"
  // Momentum indicators
  has_golden_cross?: boolean
  is_bullish_trend?: boolean
  sma_20?: number
  sma_50?: number
  sma_200?: number
  // Alert status
  has_triggered_alert?: boolean
}

// Watchlist Order types
export interface WatchlistOrderItem {
  id: number
  sort_order: number
}

export interface WatchlistOrderUpdate {
  items: WatchlistOrderItem[]
}

export interface WatchlistResponse {
  total: number
  items: WatchlistItem[]
}

export interface WatchlistNewsItem {
  title: string
  url?: string
  source?: string
  published_at?: string
  summary?: string
  sentiment_score?: number
  sentiment_label?: string
}

export interface WatchlistNewsResponse {
  ticker: string
  news: WatchlistNewsItem[]
  total: number
  days_fetched: number  // Number of days of news fetched
}

// Watchlist Custom Lines types
export interface WatchlistLineCreate {
  line_type: 'trend' | 'alert'
  name: string
  price_level: number
  color?: string
}

export interface WatchlistLineUpdate {
  name?: string
  price_level?: number
  color?: string
  is_active?: boolean
}

export interface WatchlistLineResponse {
  id: number
  watchlist_item_id: number
  line_type: string
  name: string
  price_level: number
  color: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// Technical Analysis Summary types
export interface TechnicalSummaryResponse {
  ticker: string
  current_price: number | null
  // SMA Trends
  sma_20: number | null
  sma_50: number | null
  sma_200: number | null
  price_above_sma_20: boolean
  price_above_sma_50: boolean
  price_above_sma_200: boolean
  sma_20_direction: string
  sma_50_direction: string
  // MACD
  macd: number | null
  macd_signal: number | null
  macd_histogram: number | null
  macd_status: string
  histogram_direction: string
  // Golden cross status
  has_golden_cross: boolean
  has_death_cross: boolean
}

// Chart Data types
export interface ChartDataResponse {
  ticker: string
  company_name?: string
  dates: string[]
  ohlcv: {
    open: number[]
    high: number[]
    low: number[]
    close: number[]
    volume: number[]
  }
  moving_averages: {
    sma_20: (number | null)[]
    sma_50: (number | null)[]
    sma_200: (number | null)[]
  }
  support_levels: number[]
  resistance_levels: number[]
  custom_lines: WatchlistLineResponse[]
  entry_level?: number
  stop_loss?: number
  target_price?: number
}

// Alert types
export interface TriggeredAlertResponse {
  id: number
  line_id: number
  line_name: string
  ticker: string
  price_level: number
  triggered_price: number
  direction: string
  triggered_at: string
  notified: boolean
  dismissed: boolean
}

export interface TriggeredAlertsResponse {
  alerts: TriggeredAlertResponse[]
  total: number
}

// Stock Details Response
export interface WatchlistStockDetailsResponse {
  item: WatchlistItem
  technical_summary: TechnicalSummaryResponse
  chart_data: ChartDataResponse
  custom_lines: WatchlistLineResponse[]
  triggered_alerts_today: TriggeredAlertResponse[]
  news: WatchlistNewsItem[]
}
