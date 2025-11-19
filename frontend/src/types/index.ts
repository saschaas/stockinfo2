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
