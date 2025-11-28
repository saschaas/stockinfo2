import { useState } from 'react'
import { getDecisionColor, getRiskColor } from '../../styles/theme'
import type { RiskAssessmentData } from '../../types/risk-assessment'

interface RiskAssessmentCardProps {
  data: RiskAssessmentData
}

export default function RiskAssessmentCard({ data }: RiskAssessmentCardProps) {
  const [showDetails, setShowDetails] = useState(false)

  // Helper function to safely format numbers
  const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === undefined || value === null) return 'N/A'
    const num = typeof value === 'number' ? value : Number(value)
    if (isNaN(num)) return 'N/A'
    return num.toFixed(decimals)
  }

  // Get colors for decision and risk level
  const decisionColor = getDecisionColor(data.investment_decision)
  const riskColor = getRiskColor(data.risk_level)

  // Render subscore bar
  const SubscoreBar = ({ label, value, max, isNegative = false }: { label: string; value: number; max: number; isNegative?: boolean }) => {
    const percentage = Math.min((value / max) * 100, 100)
    const color = isNegative
      ? (value > max * 0.6 ? 'bg-danger-500' : value > max * 0.3 ? 'bg-warning-500' : 'bg-success-500')
      : (value > max * 0.6 ? 'bg-success-500' : value > max * 0.3 ? 'bg-warning-500' : 'bg-danger-500')

    return (
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>{label}</span>
          <span className="font-medium">{safeToFixed(value, 1)}/{max}</span>
        </div>
        <div className="h-2 bg-cream-dark rounded-full overflow-hidden">
          <div
            className={`h-full ${color} rounded-full transition-all duration-300`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      {/* Header - Shows Decision, Risk Level, and Score */}
      <div
        className="px-6 py-4 border-b border-border-warm"
        style={{ backgroundColor: decisionColor.bg + '40' }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Decision Badge */}
            <div
              className="px-4 py-2 rounded-xl font-bold text-lg"
              style={{ backgroundColor: decisionColor.bg, color: decisionColor.text }}
            >
              {data.investment_decision}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Risk Assessment</h3>
              <div className="flex items-center gap-3 mt-1">
                {/* Risk Level Badge */}
                <span
                  className="px-2 py-0.5 rounded-full text-xs font-semibold"
                  style={{ backgroundColor: riskColor.bg, color: riskColor.text }}
                >
                  {data.risk_level.charAt(0).toUpperCase() + data.risk_level.slice(1)} Risk
                </span>
                {/* Risk Score */}
                <span className="text-sm text-gray-600">
                  Score: <span className="font-bold" style={{ color: riskColor.text }}>{safeToFixed(data.risk_score, 0)}</span>/100
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="btn-secondary text-sm"
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
            <svg
              className={`w-4 h-4 ml-2 transition-transform ${showDetails ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Quick Summary - Always Visible */}
      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          {/* Risk/Reward Ratio */}
          <div className="bg-cream rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">Risk/Reward</div>
            <div className={`text-xl font-bold ${data.risk_reward?.is_favorable ? 'text-success-700' : 'text-warning-700'}`}>
              1:{safeToFixed(data.risk_reward?.risk_reward_ratio, 1)}
            </div>
            <div className="text-xs text-gray-500">
              {data.risk_reward?.is_favorable ? 'Favorable' : 'Unfavorable'}
            </div>
          </div>

          {/* MFTA Multiplier */}
          <div className="bg-cream rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">MFTA Alignment</div>
            <div className={`text-xl font-bold ${
              data.mfta_alignment === 'aligned_bullish' ? 'text-success-700' :
              data.mfta_alignment === 'aligned_bearish' ? 'text-danger-700' :
              'text-warning-700'
            }`}>
              {data.mfta_multiplier}x
            </div>
            <div className="text-xs text-gray-500 capitalize">
              {data.mfta_alignment?.replace('_', ' ')}
            </div>
          </div>

          {/* Entry */}
          <div className="bg-cream rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">Entry Price</div>
            <div className="text-xl font-bold text-success-700">
              ${safeToFixed(data.risk_reward?.suggested_entry || data.risk_reward?.nearest_support, 2)}
            </div>
          </div>

          {/* Target */}
          <div className="bg-cream rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">Target Price</div>
            <div className="text-xl font-bold text-primary-700">
              ${safeToFixed(data.risk_reward?.suggested_target, 2)}
            </div>
          </div>
        </div>

        {/* Summary Text */}
        <div className="p-4 bg-primary-50 rounded-xl border border-primary-100">
          <p className="text-sm text-primary-800">{data.summary}</p>
        </div>
      </div>

      {/* Detailed Section (Collapsible) */}
      {showDetails && (
        <div className="px-6 pb-6 space-y-6 border-t border-border-warm pt-6 animate-fade-in">
          {/* Subscore Breakdown */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Positive Scores */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-700 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-success-500"></span>
                Contributing Factors
              </h4>
              <div className="bg-cream rounded-xl p-4">
                <SubscoreBar
                  label="Market Structure"
                  value={data.subscore_breakdown?.market_structure_total || 0}
                  max={100}
                />
                <SubscoreBar
                  label="Momentum"
                  value={data.subscore_breakdown?.momentum_total || 0}
                  max={20}
                />
                <SubscoreBar
                  label="Volume Confirmation"
                  value={data.subscore_breakdown?.volume_total || 0}
                  max={20}
                />
              </div>
            </div>

            {/* Penalty Scores */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-700 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-danger-500"></span>
                Risk Penalties
              </h4>
              <div className="bg-cream rounded-xl p-4">
                <SubscoreBar
                  label="Overextension Penalty"
                  value={data.subscore_breakdown?.overextension_total || 0}
                  max={100}
                  isNegative
                />
                <SubscoreBar
                  label="Volatility Penalty"
                  value={data.subscore_breakdown?.volatility_total || 0}
                  max={100}
                  isNegative
                />
              </div>
            </div>
          </div>

          {/* Trading Levels */}
          {data.risk_reward && (
            <div className="bg-cream rounded-xl p-5">
              <h5 className="font-medium text-gray-700 mb-4">Suggested Trading Levels</h5>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-white rounded-xl p-4 border border-success-200">
                  <div className="text-xs text-gray-500 mb-1">Entry</div>
                  <div className="text-lg font-bold text-success-700">
                    ${safeToFixed(data.risk_reward.suggested_entry || data.risk_reward.nearest_support, 2)}
                  </div>
                  {data.current_price > 0 && (data.risk_reward.suggested_entry || data.risk_reward.nearest_support) && (
                    <div className={`text-xs font-medium ${
                      ((data.risk_reward.suggested_entry || data.risk_reward.nearest_support) - data.current_price) / data.current_price < 0
                        ? 'text-success-600'
                        : 'text-danger-600'
                    }`}>
                      {safeToFixed(((data.risk_reward.suggested_entry || data.risk_reward.nearest_support) - data.current_price) / data.current_price * 100, 1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-400 mt-1">Near Support</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-danger-200">
                  <div className="text-xs text-gray-500 mb-1">Stop Loss</div>
                  <div className="text-lg font-bold text-danger-700">
                    ${safeToFixed(data.risk_reward.suggested_stop, 2)}
                  </div>
                  {data.current_price > 0 && data.risk_reward.suggested_stop > 0 && (
                    <div className="text-xs font-medium text-danger-600">
                      {safeToFixed((data.risk_reward.suggested_stop - data.current_price) / data.current_price * 100, 1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-400 mt-1">2x ATR Below</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-primary-200">
                  <div className="text-xs text-gray-500 mb-1">Target</div>
                  <div className="text-lg font-bold text-primary-700">
                    ${safeToFixed(data.risk_reward.suggested_target, 2)}
                  </div>
                  {data.current_price > 0 && data.risk_reward.suggested_target > 0 && (
                    <div className={`text-xs font-medium ${
                      (data.risk_reward.suggested_target - data.current_price) / data.current_price > 0
                        ? 'text-success-600'
                        : 'text-danger-600'
                    }`}>
                      +{safeToFixed((data.risk_reward.suggested_target - data.current_price) / data.current_price * 100, 1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-400 mt-1">Resistance</div>
                </div>
              </div>
            </div>
          )}

          {/* Position Sizing */}
          {data.position_sizing_suggestion && (
            <div className="bg-primary-50 rounded-xl p-4 border border-primary-100">
              <h5 className="font-medium text-primary-800 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Position Sizing
              </h5>
              <p className="text-sm text-primary-700">{data.position_sizing_suggestion}</p>
            </div>
          )}

          {/* Detailed Analysis */}
          {data.detailed_analysis && (
            <div className="bg-cream rounded-xl p-4 border border-border-warm">
              <h5 className="font-medium text-gray-700 mb-2">Detailed Analysis</h5>
              <p className="text-sm text-gray-600">{data.detailed_analysis}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
