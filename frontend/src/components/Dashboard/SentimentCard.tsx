interface SentimentCardProps {
  title: string
  score?: number | null
  bullish?: number | null
  bearish?: number | null
}

export default function SentimentCard({
  title,
  score,
  bullish,
  bearish,
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

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>

      <div className="flex items-center justify-center mb-6">
        <div className="text-center">
          <p className={`text-4xl font-bold ${getSentimentColor(score)}`}>
            {score != null ? `${(score * 100).toFixed(0)}%` : 'N/A'}
          </p>
          <p className="text-sm text-gray-500 mt-1">{getSentimentLabel(score)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
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
    </div>
  )
}
