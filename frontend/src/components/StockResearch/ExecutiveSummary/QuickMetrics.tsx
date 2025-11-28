import type { RiskAssessmentData } from '../../../types/risk-assessment'

interface QuickMetricsProps {
  riskAssessment: RiskAssessmentData
  technicalAnalysis?: {
    overall_signal?: string
    trend_direction?: string
    current_price?: number
  }
  priceTargets?: {
    base?: number
    optimistic?: number
    pessimistic?: number
  }
}

// Helper to format numbers safely
const formatNumber = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return value.toFixed(decimals)
}

// Helper to format currency
const formatCurrency = (value: number | undefined | null): string => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return `$${value.toFixed(2)}`
}

export default function QuickMetrics({ riskAssessment, technicalAnalysis, priceTargets }: QuickMetricsProps) {
  const currentPrice = riskAssessment.current_price
  const targetPrice = priceTargets?.base || riskAssessment.risk_reward?.suggested_target
  const riskReward = riskAssessment.risk_reward

  // Calculate upside percentage
  const upsidePercent = targetPrice && currentPrice
    ? ((targetPrice - currentPrice) / currentPrice * 100)
    : null

  // Get signal color
  const getSignalColor = (signal?: string) => {
    if (!signal) return { bg: 'bg-gray-100', text: 'text-gray-700' }
    const s = signal.toLowerCase()
    if (s.includes('buy') || s.includes('bullish')) return { bg: 'bg-success-50', text: 'text-success-700' }
    if (s.includes('sell') || s.includes('bearish')) return { bg: 'bg-danger-50', text: 'text-danger-700' }
    return { bg: 'bg-warning-50', text: 'text-warning-700' }
  }

  const signalColor = getSignalColor(technicalAnalysis?.overall_signal)

  return (
    <div className="card card-body h-full">
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
        Quick Metrics
      </h3>

      <div className="grid grid-cols-2 gap-4 h-full">
        {/* Current Price */}
        <div className="bg-cream rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Current Price</div>
          <div className="text-xl font-bold text-gray-900">
            {formatCurrency(currentPrice)}
          </div>
        </div>

        {/* Target Price */}
        <div className="bg-cream rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Target Price</div>
          <div className="text-xl font-bold text-gray-900">
            {formatCurrency(targetPrice)}
          </div>
          {upsidePercent !== null && (
            <div className={`text-xs font-medium ${upsidePercent >= 0 ? 'text-success-700' : 'text-danger-700'}`}>
              {upsidePercent >= 0 ? '+' : ''}{formatNumber(upsidePercent, 1)}%
            </div>
          )}
        </div>

        {/* Risk/Reward Ratio */}
        <div className="bg-cream rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Risk/Reward</div>
          <div className={`text-xl font-bold ${
            riskReward?.is_favorable ? 'text-success-700' : 'text-warning-700'
          }`}>
            1:{formatNumber(riskReward?.risk_reward_ratio, 1)}
          </div>
          <div className="text-xs text-gray-500">
            {riskReward?.is_favorable ? 'Favorable' : 'Unfavorable'}
          </div>
        </div>

        {/* Technical Signal */}
        <div className="bg-cream rounded-xl p-4">
          <div className="text-xs text-gray-500 mb-1">Technical Signal</div>
          <div className={`inline-block px-2 py-1 rounded-lg text-sm font-semibold ${signalColor.bg} ${signalColor.text}`}>
            {technicalAnalysis?.overall_signal?.toUpperCase().replace('_', ' ') || 'N/A'}
          </div>
          {technicalAnalysis?.trend_direction && (
            <div className="text-xs text-gray-500 mt-1 capitalize">
              {technicalAnalysis.trend_direction} trend
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
