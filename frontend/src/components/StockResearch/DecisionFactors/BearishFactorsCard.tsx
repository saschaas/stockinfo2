interface BearishFactorsCardProps {
  bearishFactors?: string[]
  keyRisks?: string[]
  risks?: string[]
  concerns?: string[]
}

export default function BearishFactorsCard({
  bearishFactors = [],
  keyRisks = [],
  risks = [],
  concerns = [],
}: BearishFactorsCardProps) {
  // Combine all negative factors, prioritizing key risks
  const allFactors: { text: string; category: string }[] = []

  keyRisks.forEach(f => allFactors.push({ text: f, category: 'Key Risk' }))
  bearishFactors.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Bearish' })
    }
  })
  risks.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Risk' })
    }
  })
  concerns.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Concern' })
    }
  })

  // Limit to top 6
  const displayFactors = allFactors.slice(0, 6)

  if (displayFactors.length === 0) {
    return (
      <div className="card card-body h-full">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-xl bg-danger-50 flex items-center justify-center">
            <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">Why Be Cautious</h3>
        </div>
        <p className="text-gray-500 text-sm">No significant risk factors identified</p>
      </div>
    )
  }

  return (
    <div className="card card-body h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-danger-50 flex items-center justify-center">
          <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Why Be Cautious</h3>
        <span className="ml-auto badge badge-danger">
          {displayFactors.length} risk{displayFactors.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Factors List */}
      <ul className="space-y-3">
        {displayFactors.map((factor, index) => (
          <li key={index} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-danger-50 text-danger-700 flex items-center justify-center text-sm font-medium">
              !
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700">{factor.text}</p>
              {factor.category !== 'Bearish' && factor.category !== 'Risk' && (
                <span className="text-xs text-gray-400">{factor.category}</span>
              )}
            </div>
          </li>
        ))}
      </ul>

      {/* Show more indicator if truncated */}
      {allFactors.length > 6 && (
        <p className="mt-3 text-xs text-gray-400 text-center">
          +{allFactors.length - 6} more risks in detailed analysis
        </p>
      )}
    </div>
  )
}
