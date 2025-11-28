/**
 * TypeScript interfaces for Technical Analysis data
 */

export interface TechnicalAnalysisData {
  ticker: string
  analysis_date: string
  current_price: number

  // Trend Analysis
  trend_direction: 'bullish' | 'bearish' | 'neutral'
  trend_strength_score: number
  sma_20: number
  sma_50: number
  sma_200: number
  adx: number
  adx_signal: 'weak' | 'moderate' | 'strong' | 'very_strong'
  price_above_sma_20: boolean
  price_above_sma_50: boolean
  price_above_sma_200: boolean
  golden_cross: boolean
  death_cross: boolean

  // Momentum Analysis
  rsi: number
  rsi_signal: 'oversold' | 'neutral' | 'overbought'
  rsi_weighted_signal: string  // Trend-context adjusted signal
  rsi_weight: number  // Weight applied based on trend context
  macd: number
  macd_signal: number
  macd_histogram: number
  macd_cross?: 'bullish' | 'bearish' | null
  stoch_k: number
  stoch_d: number
  stoch_signal: 'oversold' | 'neutral' | 'overbought'
  roc: number
  roc_signal: 'bullish' | 'neutral' | 'bearish'
  momentum_score: number

  // Volatility Analysis
  bb_upper: number
  bb_middle: number
  bb_lower: number
  bb_width: number
  bb_signal: 'squeeze' | 'breakout_upper' | 'breakout_lower' | 'neutral'
  price_position: 'above_upper' | 'upper' | 'middle' | 'lower' | 'below_lower'
  atr: number
  atr_percent: number
  volatility_level: 'low' | 'moderate' | 'high' | 'very_high'
  volatility_score: number

  // Volume Analysis
  current_volume: number
  avg_volume_20d: number
  volume_ratio: number
  volume_signal: 'low' | 'normal' | 'high' | 'very_high'
  obv: number
  obv_trend: 'rising' | 'falling' | 'neutral'
  volume_score: number

  // Support/Resistance
  pivot: number
  resistance_1: number
  resistance_2: number
  resistance_3: number
  support_1: number
  support_2: number
  support_3: number
  support_levels: number[]
  resistance_levels: number[]
  nearest_support?: number | null
  nearest_resistance?: number | null
  support_distance_pct: number
  resistance_distance_pct: number

  // Chart Patterns
  patterns: string[]
  trend_channel?: 'ascending' | 'descending' | 'horizontal' | null
  consolidation: boolean
  breakout_signal?: 'bullish' | 'bearish' | null

  // Overall Scoring
  trend_score: number
  price_action_score?: number  // Support/Resistance based entry quality score (0-10)
  composite_technical_score: number
  overall_signal: 'strong_buy' | 'buy' | 'neutral' | 'sell' | 'strong_sell'
  signal_confidence: number

  // Multi-timeframe Analysis
  multi_timeframe: MultiTimeframeAnalysis

  // Beta Analysis
  beta_analysis: BetaAnalysis

  // Entry Analysis (comprehensive entry point evaluation)
  entry_analysis?: EntryAnalysis

  // Chart Data
  chart_data: ChartData

  // Data Sources
  data_sources: Record<string, { type: string; name: string }>
}

export interface TimeframeAnalysis {
  timeframe: string  // "daily", "60min", "5min"
  trend_direction: 'bullish' | 'bearish' | 'neutral'
  trend_strength: number
  ema_200_trend: string
  momentum_signal: string
  entry_signal?: string | null
}

export interface MultiTimeframeAnalysis {
  primary_trend: TimeframeAnalysis | null  // Daily
  confirmation_trend: TimeframeAnalysis | null  // 60-min
  execution_trend: TimeframeAnalysis | null  // 5-min
  trend_alignment: 'aligned_bullish' | 'aligned_bearish' | 'mixed'
  signal_quality: 'high' | 'medium' | 'low'
  recommended_action: string
  confidence: number
}

export interface BetaAnalysis {
  beta: number
  benchmark: string
  correlation: number
  alpha: number
  r_squared: number
  volatility_vs_market: 'low' | 'below_average' | 'average' | 'above_average' | 'high'
  risk_profile: 'conservative' | 'moderate' | 'aggressive' | 'very_aggressive'
}

export interface EntryAnalysis {
  // Range Position (0-100%): 0% = at support, 100% = at resistance
  range_position_pct: number
  range_position_zone: 'discount' | 'neutral' | 'premium'

  // Confluence Score (0-10): Weighted sum of confirming factors
  confluence_score: number
  confluence_factors: string[]

  // Stop-Loss Levels
  suggested_stop_loss: number
  stop_loss_type: 'support' | 'atr' | 'swing_low'
  stop_loss_distance_pct: number

  // Take Profit / Target
  suggested_target: number
  target_distance_pct: number

  // Risk/Reward Calculation
  risk_reward_ratio: number
  risk_reward_quality: 'excellent' | 'good' | 'acceptable' | 'poor'

  // Entry Quality Assessment
  is_good_entry: boolean
  entry_quality: 'excellent' | 'good' | 'acceptable' | 'poor'
  entry_quality_score: number  // 0-100

  // Suggested Entry Points
  suggested_entry_price: number
  suggested_entry_zone_low: number
  suggested_entry_zone_high: number
  wait_for_pullback: boolean

  // Analysis Reasoning
  entry_reasoning: string
  warning_signals: string[]
}

export interface ChartData {
  dates: string[]
  ohlcv: {
    open: number[]
    high: number[]
    low: number[]
    close: number[]
    volume: number[]
  }
  moving_averages: {
    sma_20: number[]
    sma_50: number[]
    sma_200: number[]
  }
  bollinger_bands: {
    upper: number[]
    middle: number[]
    lower: number[]
  }
  support_resistance: {
    support_levels: number[]
    resistance_levels: number[]
    pivot: number
  }
  indicators: {
    rsi: number[]
    macd: number[]
    macd_signal: number[]
    macd_histogram: number[]
  }
}

export interface TechnicalAnalysisJob {
  job_id: string
  ticker: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  message: string
  result?: TechnicalAnalysisData
}
