import { getDecisionColor } from '../../../styles/theme'
import type { RiskAssessmentData } from '../../../types/risk-assessment'

interface TechnicalAnalysisData {
  overall_signal?: string
  trend_direction?: string
  rsi?: number
  macd_signal?: string
}

interface InvestmentDecisionCardProps {
  data: RiskAssessmentData
  technicalAnalysis?: TechnicalAnalysisData
  growthScore?: number
  aiRecommendation?: string
  aiConfidence?: number
}

// Helper to safely format numbers
const safeToFixed = (value: number | undefined | null, decimals: number = 0): string => {
  if (value === undefined || value === null || typeof value !== 'number' || isNaN(value)) return 'N/A'
  return value.toFixed(decimals)
}

// Convert signal strings to normalized scores (0-100)
const getSignalScore = (signal?: string): number => {
  if (!signal) return 50
  const s = signal.toLowerCase()
  if (s.includes('strong_buy') || s.includes('strong buy')) return 90
  if (s.includes('buy') || s.includes('bullish')) return 75
  if (s.includes('strong_sell') || s.includes('strong sell')) return 10
  if (s.includes('sell') || s.includes('bearish')) return 25
  return 50 // neutral/hold
}

// Get color based on score
const getScoreColor = (score: number): { fill: string; text: string; bg: string } => {
  if (score >= 70) return { fill: '#22c55e', text: 'text-success-700', bg: 'bg-success-50' }
  if (score >= 50) return { fill: '#eab308', text: 'text-warning-700', bg: 'bg-warning-50' }
  if (score >= 30) return { fill: '#f97316', text: 'text-warning-700', bg: 'bg-warning-50' }
  return { fill: '#ef4444', text: 'text-danger-700', bg: 'bg-danger-50' }
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
  technicalAnalysis,
  growthScore,
  aiRecommendation,
}: InvestmentDecisionCardProps) {
  const decisionColor = getDecisionColor(data.investment_decision)

  // Calculate individual factor scores (normalized to 0-100)

  // 1. Technical Analysis Score (from overall_signal)
  const technicalScore = getSignalScore(technicalAnalysis?.overall_signal)
  const technicalLabel = technicalAnalysis?.overall_signal?.toUpperCase().replace('_', ' ') || 'N/A'

  // 2. Risk Assessment Score (already 0-100, higher = better)
  const riskScore = data.risk_score || 50

  // 3. Growth Analysis Score (0-10 scale, convert to 0-100)
  const growthNormalized = growthScore !== undefined ? growthScore * 10 : 50

  // 4. AI Analysis Score (from recommendation)
  const aiScore = aiRecommendation ? getSignalScore(aiRecommendation) : 50
  const aiLabel = aiRecommendation?.toUpperCase().replace('_', ' ') || 'N/A'

  // Calculate weighted composite (for display - the actual decision is from backend)
  // This shows users how factors contributed
  const compositeScore = (
    technicalScore * 0.30 +  // 30% technical
    riskScore * 0.35 +       // 35% risk
    growthNormalized * 0.20 + // 20% growth
    aiScore * 0.15           // 15% AI
  )

  // Icons for each factor
  const icons = {
    technical: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
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
    ai: (
      <svg className="w-3.5 h-3.5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    )
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

      {/* Factor Breakdown */}
      <div className="flex-1 space-y-2.5 mt-2">
        <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1">
          Decision Factors
        </div>

        <FactorIndicator
          label="Technical"
          score={technicalScore}
          icon={icons.technical}
          subtitle={technicalLabel}
        />

        <FactorIndicator
          label="Risk Assessment"
          score={riskScore}
          icon={icons.risk}
          subtitle={data.risk_level ? `${data.risk_level.charAt(0).toUpperCase() + data.risk_level.slice(1)} Risk` : undefined}
        />

        <FactorIndicator
          label="Growth"
          score={growthNormalized}
          icon={icons.growth}
          subtitle={growthScore !== undefined ? `${safeToFixed(growthScore, 1)}/10` : undefined}
        />

        <FactorIndicator
          label="AI Analysis"
          score={aiScore}
          icon={icons.ai}
          subtitle={aiLabel}
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
