import { getDecisionColor } from '../../../styles/theme'
import type { RiskAssessmentData } from '../../../types/risk-assessment'

interface InvestmentDecisionCardProps {
  data: RiskAssessmentData
}

// Helper to safely convert to number
const safeNumber = (value: unknown, defaultValue: number = 50): number => {
  if (value === undefined || value === null) return defaultValue
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  return isNaN(num) ? defaultValue : num
}

// Helper to safely format numbers
const safeToFixed = (value: unknown, decimals: number = 0): string => {
  const num = safeNumber(value, NaN)
  if (isNaN(num)) return 'N/A'
  return num.toFixed(decimals)
}

// Get color based on score (0-100)
const getScoreColor = (score: number): { fill: string; text: string; bg: string } => {
  if (score >= 65) return { fill: '#22c55e', text: 'text-success-700', bg: 'bg-success-50' }
  if (score >= 45) return { fill: '#eab308', text: 'text-warning-700', bg: 'bg-warning-50' }
  if (score >= 30) return { fill: '#f97316', text: 'text-warning-700', bg: 'bg-warning-50' }
  return { fill: '#ef4444', text: 'text-danger-700', bg: 'bg-danger-50' }
}

// Get label for score level
const getScoreLabel = (score: number): string => {
  if (score >= 75) return 'Strong'
  if (score >= 60) return 'Good'
  if (score >= 45) return 'Moderate'
  if (score >= 30) return 'Weak'
  return 'Poor'
}


// Factor indicator component
interface FactorIndicatorProps {
  label: string
  score: number
  icon: React.ReactNode
  subtitle?: string
}

function FactorIndicator({ label, score, icon, subtitle }: FactorIndicatorProps) {
  const color = getScoreColor(score)
  const barWidth = Math.max(5, Math.min(100, score))

  return (
    <div className="flex items-center gap-2">
      <div className={`w-7 h-7 rounded-lg ${color.bg} flex items-center justify-center flex-shrink-0`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-xs font-medium text-gray-700 truncate">{label}</span>
          <span className={`text-xs font-bold ${color.text}`}>{safeToFixed(score)}</span>
        </div>
        <div className="h-1.5 bg-cream-dark rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${barWidth}%`, backgroundColor: color.fill }}
          />
        </div>
        {subtitle && (
          <span className="text-[10px] text-gray-400">{subtitle}</span>
        )}
      </div>
    </div>
  )
}

export default function InvestmentDecisionCard({
  data,
}: InvestmentDecisionCardProps) {
  const decisionColor = getDecisionColor(data.investment_decision)

  // Use backend-calculated scores for consistency
  const components = data.decision_components || {}

  // Individual factor scores from backend (all normalized to 0-100)
  // Use safeNumber to handle any type issues
  const riskScore = safeNumber(components.risk_score_component, safeNumber(data.risk_score, 50))
  const growthScore = safeNumber(components.growth_score_component, 50)
  const technicalScore = safeNumber(components.technical_score_component, 50)
  const rrScore = safeNumber(components.rr_score_component, 50)

  // Use backend's composite score for the ring display
  const compositeScore = safeNumber(data.decision_composite_score, safeNumber(components.final_composite, 50))

  // Icons for each factor
  const icons = {
    risk: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    growth: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    technical: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
    rr: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
  }

  return (
    <div className="card card-body h-full flex flex-col">
      {/* Header with Decision */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Investment Decision
          </h3>
          <div
            className="decision-badge text-xl"
            style={{ backgroundColor: decisionColor.bg, color: decisionColor.text }}
          >
            {data.investment_decision}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">Confidence</div>
          <div className="text-lg font-bold text-gray-900">
            {safeToFixed(data.decision_confidence)}%
          </div>
        </div>
      </div>

      {/* Composite Score Ring */}
      <div className="flex items-center justify-center py-2">
        <div className="relative w-24 h-24">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke="#E8E0D8"
              strokeWidth="10"
            />
            {/* Score arc */}
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke={getScoreColor(compositeScore).fill}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${(compositeScore / 100) * 251.33} 251.33`}
              className="transition-all duration-700"
            />
          </svg>
          {/* Center content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-gray-900">{safeToFixed(compositeScore)}</span>
            <span className="text-[10px] text-gray-500 uppercase">Score</span>
          </div>
        </div>
      </div>

      {/* Factor Breakdown - Shows how each component contributed to the decision */}
      <div className="flex-1 space-y-2.5 mt-2">
        <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1">
          Decision Factors (weighted)
        </div>

        <FactorIndicator
          label="Risk Assessment"
          score={riskScore}
          icon={icons.risk}
          subtitle={`${getScoreLabel(riskScore)} (35%)`}
        />

        <FactorIndicator
          label="Growth Potential"
          score={growthScore}
          icon={icons.growth}
          subtitle={`${getScoreLabel(growthScore)} (25%)`}
        />

        <FactorIndicator
          label="Technical Signals"
          score={technicalScore}
          icon={icons.technical}
          subtitle={`${getScoreLabel(technicalScore)} (25%)`}
        />

        <FactorIndicator
          label="Risk/Reward"
          score={rrScore}
          icon={icons.rr}
          subtitle={`${getScoreLabel(rrScore)} (15%)`}
        />
      </div>

      {/* Entry Quality Footer */}
      <div className="pt-3 mt-2 border-t border-border-warm">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">Entry Quality</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            data.entry_quality === 'excellent' ? 'bg-success-50 text-success-700' :
            data.entry_quality === 'good' ? 'bg-success-50 text-success-600' :
            data.entry_quality === 'fair' ? 'bg-warning-50 text-warning-700' :
            'bg-danger-50 text-danger-700'
          }`}>
            {data.entry_quality?.charAt(0).toUpperCase() + data.entry_quality?.slice(1)}
          </span>
        </div>
      </div>
    </div>
  )
}
