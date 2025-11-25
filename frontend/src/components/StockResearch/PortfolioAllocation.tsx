interface PortfolioAllocationProps {
  allocation: number
  recommendation: string
  confidenceScore: number
}

export default function PortfolioAllocation({ allocation, recommendation, confidenceScore }: PortfolioAllocationProps) {
  const getRecommendationColor = () => {
    const rec = recommendation?.toLowerCase()
    if (rec === 'strong_buy' || rec === 'buy') return 'text-green-700'
    if (rec === 'strong_sell' || rec === 'sell') return 'text-red-700'
    return 'text-yellow-700'
  }

  const getAllocationColor = () => {
    if (allocation >= 8) return 'bg-green-500'
    if (allocation >= 5) return 'bg-blue-500'
    if (allocation >= 3) return 'bg-yellow-500'
    if (allocation > 0) return 'bg-orange-500'
    return 'bg-gray-400'
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">Portfolio Allocation</span>
          <span className={`text-2xl font-bold ${getRecommendationColor()}`}>
            {allocation.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full ${getAllocationColor()} transition-all duration-500`}
            style={{ width: `${Math.min(allocation * 10, 100)}%` }}
          ></div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-600">
        <div>
          <span className="font-medium">Confidence:</span> {confidenceScore?.toFixed(0)}%
        </div>
        <div className={`font-semibold ${getRecommendationColor()}`}>
          {recommendation?.replace('_', ' ').toUpperCase()}
        </div>
      </div>

      <div className="mt-2 pt-2 border-t text-xs text-gray-500">
        <p>Suggested allocation of your portfolio based on analysis confidence and risk assessment.</p>
      </div>
    </div>
  )
}
