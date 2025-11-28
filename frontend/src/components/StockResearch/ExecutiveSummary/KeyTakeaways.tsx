import { useState } from 'react'
import { getDecisionColor } from '../../../styles/theme'
import type { RiskAssessmentData } from '../../../types/risk-assessment'

interface KeyTakeawaysProps {
  riskAssessment: RiskAssessmentData
  aiSummary?: string
  keyStrengths?: string[]
  keyRisks?: string[]
}

export default function KeyTakeaways({
  riskAssessment,
  aiSummary,
  keyStrengths,
  keyRisks,
}: KeyTakeawaysProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Use the investment_decision from risk_assessment as the source of truth
  const decision = riskAssessment.investment_decision
  const decisionColor = getDecisionColor(decision)

  // Get the summary text - prefer aiSummary, fallback to riskAssessment.summary
  const summaryText = aiSummary || riskAssessment.summary

  // Check if text is long enough to need expansion
  const isLongText = summaryText && summaryText.length > 150

  // Combine and prioritize takeaways
  const takeaways: { text: string; type: 'positive' | 'negative' | 'neutral' }[] = []

  // Add top bullish factors
  if (riskAssessment.bullish_factors?.length > 0) {
    riskAssessment.bullish_factors.slice(0, 2).forEach(factor => {
      takeaways.push({ text: factor, type: 'positive' })
    })
  }

  // Add top bearish factors / risks
  const risks = keyRisks || riskAssessment.key_risks || riskAssessment.bearish_factors || []
  if (risks.length > 0) {
    risks.slice(0, 2).forEach(risk => {
      takeaways.push({ text: risk, type: 'negative' })
    })
  }

  // Add key strengths
  if (keyStrengths?.length) {
    keyStrengths.slice(0, 1).forEach(strength => {
      if (!takeaways.some(t => t.text === strength)) {
        takeaways.push({ text: strength, type: 'positive' })
      }
    })
  }

  // Limit to 5 takeaways
  const displayTakeaways = takeaways.slice(0, 5)

  return (
    <div className="card card-body h-full flex flex-col">
      {/* Header with Decision Badge */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
          Key Takeaways
        </h3>
        {/* Show the decision from risk_assessment for consistency */}
        <span
          className="px-2 py-0.5 rounded-full text-xs font-semibold"
          style={{ backgroundColor: decisionColor.bg, color: decisionColor.text }}
        >
          {decision}
        </span>
      </div>

      {/* Summary Section - Expandable */}
      {summaryText && (
        <div
          className="bg-primary-50 rounded-xl p-3 mb-4 border border-primary-100 cursor-pointer transition-all"
          onClick={() => isLongText && setIsExpanded(!isExpanded)}
        >
          <p className={`text-sm text-primary-800 ${!isExpanded && isLongText ? 'line-clamp-3' : ''}`}>
            {summaryText}
          </p>
          {isLongText && (
            <button
              className="text-xs text-primary-600 font-medium mt-2 hover:text-primary-700 flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation()
                setIsExpanded(!isExpanded)
              }}
            >
              {isExpanded ? (
                <>
                  Show less
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </>
              ) : (
                <>
                  Read more
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Bullet points */}
      <ul className="flex-1 space-y-2">
        {displayTakeaways.map((takeaway, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs ${
              takeaway.type === 'positive'
                ? 'bg-success-50 text-success-700'
                : takeaway.type === 'negative'
                ? 'bg-danger-50 text-danger-700'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {takeaway.type === 'positive' ? '+' : takeaway.type === 'negative' ? '!' : '•'}
            </span>
            <span className="text-sm text-gray-700">
              {takeaway.text}
            </span>
          </li>
        ))}
      </ul>

      {/* Empty state */}
      {displayTakeaways.length === 0 && !summaryText && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          No key takeaways available
        </div>
      )}
    </div>
  )
}
