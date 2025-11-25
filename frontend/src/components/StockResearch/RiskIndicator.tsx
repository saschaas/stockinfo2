interface RiskIndicatorProps {
  riskLevel: string
  riskScore: number
}

export default function RiskIndicator({ riskLevel, riskScore }: RiskIndicatorProps) {
  const getRiskColor = () => {
    switch (riskLevel?.toLowerCase()) {
      case 'low':
        return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300', fill: 'bg-green-500' }
      case 'moderate':
        return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300', fill: 'bg-yellow-500' }
      case 'high':
        return { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300', fill: 'bg-orange-500' }
      case 'very high':
        return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', fill: 'bg-red-500' }
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300', fill: 'bg-gray-500' }
    }
  }

  const colors = getRiskColor()
  const riskPercentage = (riskScore / 10) * 100

  return (
    <div className={`p-4 rounded-lg border ${colors.border} ${colors.bg}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Risk Level</span>
        <span className={`px-2 py-1 rounded text-xs font-bold ${colors.text}`}>
          {riskLevel?.toUpperCase()}
        </span>
      </div>

      {/* Risk Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
        <div
          className={`h-2 rounded-full ${colors.fill} transition-all duration-500`}
          style={{ width: `${riskPercentage}%` }}
        ></div>
      </div>

      <div className="flex justify-between text-xs text-gray-600">
        <span>Risk Score: {riskScore.toFixed(1)}/10</span>
        <span>{riskPercentage.toFixed(0)}%</span>
      </div>
    </div>
  )
}
