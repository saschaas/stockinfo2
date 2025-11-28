interface BullishFactorsCardProps {
  bullishFactors?: string[]
  strengths?: string[]
  catalysts?: string[]
  opportunities?: string[]
}

export default function BullishFactorsCard({
  bullishFactors = [],
  strengths = [],
  catalysts = [],
  opportunities = [],
}: BullishFactorsCardProps) {
  // Combine all positive factors, prioritizing bullish factors
  const allFactors: { text: string; category: string }[] = []

  bullishFactors.forEach(f => allFactors.push({ text: f, category: 'Bullish' }))
  strengths.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Strength' })
    }
  })
  catalysts.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Catalyst' })
    }
  })
  opportunities.forEach(f => {
    if (!allFactors.some(af => af.text === f)) {
      allFactors.push({ text: f, category: 'Opportunity' })
    }
  })

  // Limit to top 6
  const displayFactors = allFactors.slice(0, 6)

  if (displayFactors.length === 0) {
    return (
      <div className="card card-body h-full">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-xl bg-success-50 flex items-center justify-center">
            <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">Why Buy</h3>
        </div>
        <p className="text-gray-500 text-sm">No bullish factors identified</p>
      </div>
    )
  }

  return (
    <div className="card card-body h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-success-50 flex items-center justify-center">
          <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Why Buy</h3>
        <span className="ml-auto badge badge-success">
          {displayFactors.length} factor{displayFactors.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Factors List */}
      <ul className="space-y-3">
        {displayFactors.map((factor, index) => (
          <li key={index} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-success-50 text-success-700 flex items-center justify-center text-sm font-medium">
              +
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700">{factor.text}</p>
              {factor.category !== 'Bullish' && (
                <span className="text-xs text-gray-400">{factor.category}</span>
              )}
            </div>
          </li>
        ))}
      </ul>

      {/* Show more indicator if truncated */}
      {allFactors.length > 6 && (
        <p className="mt-3 text-xs text-gray-400 text-center">
          +{allFactors.length - 6} more factors in detailed analysis
        </p>
      )}
    </div>
  )
}
