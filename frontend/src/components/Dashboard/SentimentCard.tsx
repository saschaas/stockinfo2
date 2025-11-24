interface SentimentCardProps {
  title: string
  score?: number | null
  bullish?: number | null
  bearish?: number | null
  hotSectors?: Array<{ name: string }>
  negativeSectors?: Array<{ name: string }>
  indices?: {
    sp500?: { change_pct: number | null }
    nasdaq?: { change_pct: number | null }
    dow?: { change_pct: number | null }
  }
}

export default function SentimentCard({
  title,
  score,
  bullish,
  bearish,
  hotSectors = [],
  negativeSectors = [],
  indices,
}: SentimentCardProps) {
  const getSentimentColor = (value: number | null | undefined) => {
    if (value == null) return 'text-gray-500'
    if (value >= 0.6) return 'text-green-600'
    if (value >= 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getSentimentLabel = (value: number | null | undefined) => {
    if (value == null) return 'No Data'
    if (value >= 0.7) return 'Very Bullish'
    if (value >= 0.55) return 'Bullish'
    if (value >= 0.45) return 'Neutral'
    if (value >= 0.3) return 'Bearish'
    return 'Very Bearish'
  }

  // Generate positive bullet points
  const positivePoints = []
  if (indices?.sp500?.change_pct && indices.sp500.change_pct > 0) {
    positivePoints.push('Major indices trending up')
  }
  if (hotSectors.length > 0) {
    positivePoints.push(`${hotSectors[0].name} sector leading`)
  }
  if (bullish && bullish > 0.6) {
    positivePoints.push('Strong bullish signals')
  }

  // Generate negative bullet points
  const negativePoints = []
  if (indices?.sp500?.change_pct && indices.sp500.change_pct < 0) {
    negativePoints.push('Market indices declining')
  }
  if (negativeSectors.length > 0) {
    negativePoints.push(`${negativeSectors[0].name} under pressure`)
  }
  if (bearish && bearish > 0.4) {
    negativePoints.push('Elevated bearish sentiment')
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>

      <div className="flex items-center justify-center mb-4">
        <div className="text-center">
          <p className={`text-4xl font-bold ${getSentimentColor(score)}`}>
            {score != null ? `${(score * 100).toFixed(0)}%` : 'N/A'}
          </p>
          <p className="text-sm text-gray-500 mt-1">{getSentimentLabel(score)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <p className="text-sm text-green-600 font-medium">Bullish</p>
          <p className="text-lg font-semibold text-green-700">
            {bullish != null ? `${(bullish * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <p className="text-sm text-red-600 font-medium">Bearish</p>
          <p className="text-lg font-semibold text-red-700">
            {bearish != null ? `${(bearish * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Compact bullet points */}
      <div className="grid grid-cols-2 gap-3 text-xs border-t pt-3">
        <div>
          <p className="font-medium text-green-700 mb-1.5">✓ Positive</p>
          {positivePoints.length > 0 ? (
            <ul className="space-y-0.5">
              {positivePoints.slice(0, 3).map((point, idx) => (
                <li key={idx} className="text-gray-600">• {point}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">No strong signals</p>
          )}
        </div>
        <div>
          <p className="font-medium text-red-700 mb-1.5">✗ Negative</p>
          {negativePoints.length > 0 ? (
            <ul className="space-y-0.5">
              {negativePoints.slice(0, 3).map((point, idx) => (
                <li key={idx} className="text-gray-600">• {point}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">No major concerns</p>
          )}
        </div>
      </div>
    </div>
  )
}
