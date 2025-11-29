/**
 * TypeScript interfaces for Risk Assessment data
 */

export interface SubscoreBreakdown {
  // Market Structure (40% weight)
  support_proximity_score: number  // 0-40
  resistance_distance_score: number  // 0-40
  trend_alignment_score: number  // 0-20
  market_structure_total: number  // 0-100

  // Momentum (20% weight)
  macd_momentum_score: number  // 0-10
  rsi_direction_score: number  // 0-10
  momentum_total: number  // 0-20

  // Overextension Penalty (15% weight, negative)
  rsi_overbought_penalty: number  // 0-100
  bollinger_penalty: number  // 0-100
  ema_distance_penalty: number  // 0-100
  overextension_total: number  // 0-100

  // Volatility Penalty (15% weight, negative)
  atr_volatility_penalty: number  // 0-100
  stop_distance_penalty: number  // 0-100
  volatility_total: number  // 0-100

  // Volume Confirmation (20% weight)
  volume_ratio_score: number  // 0-20
  volume_total: number  // 0-20
}

export interface RiskRewardAnalysis {
  current_price: number
  nearest_support: number
  nearest_resistance: number
  risk_distance_pct: number  // Distance to support (%)
  reward_distance_pct: number  // Distance to resistance (%)
  risk_reward_ratio: number
  is_favorable: boolean  // True if reward >= 2x risk
  suggested_entry: number | null
  suggested_stop: number
  suggested_target: number
}

export interface RiskAssessmentData {
  ticker: string
  assessment_date: string
  current_price: number

  // Main Risk Score (0-100, higher = lower risk)
  risk_score: number
  risk_level: 'low' | 'medium' | 'elevated' | 'high'

  // Weighted subscores (final contribution)
  market_structure_weighted: number  // 0-40
  momentum_weighted: number  // 0-20
  overextension_penalty_weighted: number  // 0-15 (negative impact)
  volatility_penalty_weighted: number  // 0-15 (negative impact)
  volume_confirmation_weighted: number  // 0-20

  // Raw subscores
  subscore_breakdown: SubscoreBreakdown

  // MFTA (Multi-Timeframe Analysis)
  mfta_multiplier: number  // 0.5, 0.8, 1.0, 1.2
  mfta_alignment: 'aligned_bullish' | 'aligned_bearish' | 'mixed' | 'neutral'
  pre_mfta_score: number  // Score before MFTA adjustment

  // Risk/Reward Analysis
  risk_reward: RiskRewardAnalysis

  // Investment Decision
  investment_decision: 'BUY' | 'HOLD' | 'AVOID' | 'SELL'
  decision_confidence: number  // 0-100
  entry_quality: 'excellent' | 'good' | 'fair' | 'poor'
  decision_composite_score: number  // 0-100 - final weighted composite
  decision_components: {  // Individual factor contributions
    risk_score_component: number
    growth_score_component: number
    technical_score_component: number
    rr_score_component: number
    pre_mfta_composite: number
    mfta_multiplier: number
    final_composite: number
  }

  // Key Factors Summary
  bullish_factors: string[]
  bearish_factors: string[]
  key_risks: string[]

  // Detailed Analysis
  summary: string  // 2-3 sentence summary
  detailed_analysis: string  // Full analysis

  // Position Sizing
  position_sizing_suggestion: string

  // Data Sources
  data_sources: Record<string, { type: string; name: string } | null>
}

// Helper type for the complete research result that includes risk assessment
export interface ResearchResultWithRiskAssessment {
  ticker: string
  risk_assessment?: RiskAssessmentData
  technical_analysis?: Record<string, unknown>
  // ... other fields
}
