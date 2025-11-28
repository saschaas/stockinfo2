interface DataQualityBadgeProps {
  completenessScore: number
  missingCategories?: string[]
}

export default function DataQualityBadge({ completenessScore, missingCategories }: DataQualityBadgeProps) {
  const getColor = () => {
    if (completenessScore >= 90) return 'bg-green-100 text-green-800 border-green-200'
    if (completenessScore >= 70) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    if (completenessScore >= 50) return 'bg-orange-100 text-orange-800 border-orange-200'
    return 'bg-red-100 text-red-800 border-red-200'
  }

  const getQualityLabel = () => {
    if (completenessScore >= 90) return 'Excellent'
    if (completenessScore >= 70) return 'Good'
    if (completenessScore >= 50) return 'Moderate'
    return 'Limited'
  }

  // Safe number formatting
  const formatScore = (score: number | undefined | null): string => {
    if (score === undefined || score === null || typeof score !== 'number' || isNaN(score)) return 'N/A'
    return score.toFixed(0)
  }

  return (
    <div className="inline-flex items-center gap-2">
      <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getColor()}`}>
        Data Quality: {getQualityLabel()} ({formatScore(completenessScore)}%)
      </div>
      {missingCategories && missingCategories.length > 0 && (
        <div className="group relative">
          <span className="text-xs text-gray-500 cursor-help">
            ⓘ
          </span>
          <div className="absolute z-10 invisible group-hover:visible bg-gray-900 text-white text-xs rounded-lg py-2 px-3 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48">
            <div className="font-semibold mb-1">Missing Data:</div>
            <ul className="space-y-1">
              {missingCategories.map((cat, idx) => (
                <li key={idx}>• {cat}</li>
              ))}
            </ul>
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
              <div className="border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
