import { useState } from 'react'
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

  // Get risk level color
  const getRiskLevelColor = () => {
    switch (data.risk_level) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'elevated':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  // Get decision color
  const getDecisionColor = () => {
    switch (data.investment_decision) {
      case 'BUY':
        return 'bg-green-500 text-white'
      case 'HOLD':
        return 'bg-yellow-500 text-white'
      case 'AVOID':
        return 'bg-orange-500 text-white'
      case 'SELL':
        return 'bg-red-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  // Get entry quality color
  const getEntryQualityColor = () => {
    switch (data.entry_quality) {
      case 'excellent':
        return 'text-green-600'
      case 'good':
        return 'text-green-500'
      case 'fair':
        return 'text-yellow-600'
      case 'poor':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  // Get score gauge color
  const getScoreGaugeColor = (score: number) => {
    if (score >= 80) return '#22c55e' // green-500
    if (score >= 60) return '#eab308' // yellow-500
    if (score >= 40) return '#f97316' // orange-500
    return '#ef4444' // red-500
  }

  // Render score gauge
  const ScoreGauge = () => {
    const score = data.risk_score
    const color = getScoreGaugeColor(score)

    return (
      <div className="relative w-32 h-16 mx-auto">
        {/* Background arc */}
        <svg viewBox="0 0 100 50" className="w-full h-full">
          {/* Background track */}
          <path
            d="M 5 50 A 45 45 0 0 1 95 50"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="10"
            strokeLinecap="round"
          />
          {/* Score arc */}
          <path
            d="M 5 50 A 45 45 0 0 1 95 50"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${(score / 100) * 141.37} 141.37`}
          />
          {/* Score text */}
          <text x="50" y="45" textAnchor="middle" className="text-2xl font-bold" fill={color}>
            {Math.round(score)}
          </text>
        </svg>
      </div>
    )
  }

  // Render subscore bar
  const SubscoreBar = ({ label, value, max, isNegative = false }: { label: string; value: number; max: number; isNegative?: boolean }) => {
    const percentage = Math.min((value / max) * 100, 100)
    const color = isNegative
      ? (value > max * 0.6 ? 'bg-red-500' : value > max * 0.3 ? 'bg-orange-500' : 'bg-green-500')
      : (value > max * 0.6 ? 'bg-green-500' : value > max * 0.3 ? 'bg-yellow-500' : 'bg-red-500')

    return (
      <div className="mb-2">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>{label}</span>
          <span>{safeToFixed(value, 1)}/{max}</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${color} transition-all`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Risk Assessment
        </h3>
      </div>

      {/* Summary Section (Always Visible) */}
      <div className="p-6">
        <div className="flex flex-col md:flex-row gap-6">
          {/* Score Gauge */}
          <div className="flex flex-col items-center">
            <ScoreGauge />
            <span className={`mt-2 px-3 py-1 rounded-full text-sm font-medium border ${getRiskLevelColor()}`}>
              {data.risk_level.charAt(0).toUpperCase() + data.risk_level.slice(1)} Risk
            </span>
          </div>

          {/* Decision & Key Metrics */}
          <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Investment Decision */}
            <div className="col-span-2 bg-gray-50 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">Investment Decision</div>
              <div className="flex items-center gap-3">
                <span className={`px-4 py-2 rounded-lg text-lg font-bold ${getDecisionColor()}`}>
                  {data.investment_decision}
                </span>
                <div>
                  <div className="text-sm text-gray-600">
                    Confidence: <span className="font-semibold">{safeToFixed(data.decision_confidence, 0)}%</span>
                  </div>
                  <div className={`text-sm ${getEntryQualityColor()}`}>
                    Entry Quality: <span className="font-semibold capitalize">{data.entry_quality}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk/Reward Ratio */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">Risk/Reward</div>
              <div className={`text-xl font-bold ${data.risk_reward?.is_favorable ? 'text-green-600' : 'text-orange-600'}`}>
                1:{safeToFixed(data.risk_reward?.risk_reward_ratio, 1)}
              </div>
              <div className="text-xs text-gray-500">
                {data.risk_reward?.is_favorable ? 'Favorable' : 'Unfavorable'}
              </div>
            </div>

            {/* MFTA Multiplier */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-xs text-gray-500 mb-1">MFTA Alignment</div>
              <div className={`text-xl font-bold ${
                data.mfta_alignment === 'aligned_bullish' ? 'text-green-600' :
                data.mfta_alignment === 'aligned_bearish' ? 'text-red-600' :
                'text-yellow-600'
              }`}>
                {data.mfta_multiplier}x
              </div>
              <div className="text-xs text-gray-500 capitalize">
                {data.mfta_alignment?.replace('_', ' ')}
              </div>
            </div>
          </div>
        </div>

        {/* Summary Text */}
        <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
          <p className="text-sm text-blue-800">{data.summary}</p>
        </div>

        {/* Toggle Details Button */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="mt-4 w-full flex items-center justify-center gap-2 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
        >
          <svg
            className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          {showDetails ? 'Hide Detailed Analysis' : 'Show Detailed Analysis'}
        </button>
      </div>

      {/* Detailed Section (Collapsible) */}
      {showDetails && (
        <div className="px-6 pb-6 space-y-6 border-t border-gray-200 pt-6">
          {/* Subscore Breakdown */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Positive Scores */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-700 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                Contributing Factors
              </h4>
              <div className="bg-gray-50 rounded-lg p-4">
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
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                Risk Penalties
              </h4>
              <div className="bg-gray-50 rounded-lg p-4">
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

          {/* Key Factors */}
          <div className="grid md:grid-cols-3 gap-4">
            {/* Bullish Factors */}
            {data.bullish_factors && data.bullish_factors.length > 0 && (
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <h5 className="font-medium text-green-800 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Bullish Factors
                </h5>
                <ul className="text-sm text-green-700 space-y-1">
                  {data.bullish_factors.slice(0, 5).map((factor, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Bearish Factors */}
            {data.bearish_factors && data.bearish_factors.length > 0 && (
              <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                <h5 className="font-medium text-red-800 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Bearish Factors
                </h5>
                <ul className="text-sm text-red-700 space-y-1">
                  {data.bearish_factors.slice(0, 5).map((factor, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">-</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Key Risks */}
            {data.key_risks && data.key_risks.length > 0 && (
              <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                <h5 className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Key Risks
                </h5>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {data.key_risks.slice(0, 5).map((risk, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-yellow-500 mt-0.5">!</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Trading Levels */}
          {data.risk_reward && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-gray-700 mb-3">Suggested Trading Levels</h5>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-white rounded-lg p-3 border border-green-200">
                  <div className="text-xs text-gray-500 mb-1">Entry</div>
                  <div className="text-lg font-bold text-green-600">
                    ${safeToFixed(data.risk_reward.suggested_entry || data.risk_reward.nearest_support, 2)}
                  </div>
                  {data.current_price > 0 && (
                    <div className={`text-xs font-medium ${
                      ((data.risk_reward.suggested_entry || data.risk_reward.nearest_support) - data.current_price) / data.current_price < 0
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      {(((data.risk_reward.suggested_entry || data.risk_reward.nearest_support) - data.current_price) / data.current_price * 100).toFixed(1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-500">Near Support</div>
                </div>
                <div className="bg-white rounded-lg p-3 border border-red-200">
                  <div className="text-xs text-gray-500 mb-1">Stop Loss</div>
                  <div className="text-lg font-bold text-red-600">
                    ${safeToFixed(data.risk_reward.suggested_stop, 2)}
                  </div>
                  {data.current_price > 0 && data.risk_reward.suggested_stop > 0 && (
                    <div className="text-xs font-medium text-red-600">
                      {((data.risk_reward.suggested_stop - data.current_price) / data.current_price * 100).toFixed(1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-500">2x ATR Below</div>
                </div>
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-500 mb-1">Target</div>
                  <div className="text-lg font-bold text-blue-600">
                    ${safeToFixed(data.risk_reward.suggested_target, 2)}
                  </div>
                  {data.current_price > 0 && data.risk_reward.suggested_target > 0 && (
                    <div className={`text-xs font-medium ${
                      (data.risk_reward.suggested_target - data.current_price) / data.current_price > 0
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      +{((data.risk_reward.suggested_target - data.current_price) / data.current_price * 100).toFixed(1)}%
                    </div>
                  )}
                  <div className="text-xs text-gray-500">Resistance</div>
                </div>
              </div>
            </div>
          )}

          {/* Position Sizing */}
          {data.position_sizing_suggestion && (
            <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <h5 className="font-medium text-purple-800 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Position Sizing
              </h5>
              <p className="text-sm text-purple-700">{data.position_sizing_suggestion}</p>
            </div>
          )}

          {/* Detailed Analysis */}
          {data.detailed_analysis && (
            <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
              <h5 className="font-medium text-indigo-800 mb-2">Detailed Analysis</h5>
              <p className="text-sm text-indigo-700">{data.detailed_analysis}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
