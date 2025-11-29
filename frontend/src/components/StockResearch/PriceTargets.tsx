interface PriceTargetsProps {
  currentPrice: number
  baseTarget: number
  optimisticTarget: number
  pessimisticTarget: number
  upsidePotential: number
}

// Helper to safely convert to number
const safeNumber = (value: unknown, defaultValue: number = 0): number => {
  if (value === undefined || value === null) return defaultValue
  const num = typeof value === 'number' ? value : parseFloat(String(value))
  return isNaN(num) ? defaultValue : num
}

export default function PriceTargets({
  currentPrice: rawCurrentPrice,
  baseTarget: rawBaseTarget,
  optimisticTarget: rawOptimisticTarget,
  pessimisticTarget: rawPessimisticTarget,
  upsidePotential: rawUpsidePotential
}: PriceTargetsProps) {
  // Safely convert all values to numbers
  const currentPrice = safeNumber(rawCurrentPrice)
  const baseTarget = safeNumber(rawBaseTarget)
  const optimisticTarget = safeNumber(rawOptimisticTarget)
  const pessimisticTarget = safeNumber(rawPessimisticTarget)
  const upsidePotential = safeNumber(rawUpsidePotential)

  const maxPrice = Math.max(currentPrice, optimisticTarget) * 1.1
  const minPrice = Math.min(currentPrice, pessimisticTarget) * 0.9

  const getPosition = (price: number) => {
    return ((price - minPrice) / (maxPrice - minPrice)) * 100
  }

  const getUpsideColor = () => {
    if (upsidePotential >= 20) return 'text-green-600'
    if (upsidePotential >= 10) return 'text-blue-600'
    if (upsidePotential >= 0) return 'text-gray-600'
    return 'text-red-600'
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Price Targets</span>
          <span className={`text-lg font-bold ${getUpsideColor()}`}>
            {upsidePotential >= 0 ? '+' : ''}{upsidePotential.toFixed(1)}%
          </span>
        </div>
        <div className="text-xs text-gray-500">Upside to base target</div>
      </div>

      {/* Visual Price Range */}
      <div className="relative h-20 mb-4">
        {/* Background bar */}
        <div className="absolute w-full h-2 bg-gray-200 rounded-full top-1/2 transform -translate-y-1/2"></div>

        {/* Pessimistic Target */}
        <div
          className="absolute transform -translate-x-1/2"
          style={{ left: `${getPosition(pessimisticTarget)}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="absolute top-full mt-1 whitespace-nowrap text-xs text-center transform -translate-x-1/2 left-1/2">
            <div className="text-red-600 font-medium">${pessimisticTarget.toFixed(2)}</div>
            <div className="text-gray-500">Bear</div>
          </div>
        </div>

        {/* Base Target */}
        <div
          className="absolute transform -translate-x-1/2"
          style={{ left: `${getPosition(baseTarget)}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
          <div className="absolute top-full mt-1 whitespace-nowrap text-xs text-center transform -translate-x-1/2 left-1/2">
            <div className="text-blue-600 font-bold">${baseTarget.toFixed(2)}</div>
            <div className="text-gray-500">Base</div>
          </div>
        </div>

        {/* Optimistic Target */}
        <div
          className="absolute transform -translate-x-1/2"
          style={{ left: `${getPosition(optimisticTarget)}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <div className="absolute top-full mt-1 whitespace-nowrap text-xs text-center transform -translate-x-1/2 left-1/2">
            <div className="text-green-600 font-medium">${optimisticTarget.toFixed(2)}</div>
            <div className="text-gray-500">Bull</div>
          </div>
        </div>

        {/* Current Price */}
        <div
          className="absolute transform -translate-x-1/2"
          style={{ left: `${getPosition(currentPrice)}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <div className="w-2 h-8 bg-gray-700 rounded"></div>
          <div className="absolute bottom-full mb-1 whitespace-nowrap text-xs text-center transform -translate-x-1/2 left-1/2">
            <div className="text-gray-900 font-bold">${currentPrice.toFixed(2)}</div>
            <div className="text-gray-500">Current</div>
          </div>
        </div>
      </div>

      {/* Price Target Details */}
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="text-center p-2 bg-red-50 rounded">
          <div className="text-red-600 font-semibold">${pessimisticTarget.toFixed(2)}</div>
          <div className="text-gray-500">Pessimistic</div>
        </div>
        <div className="text-center p-2 bg-gray-50 rounded">
          <div className="text-gray-900 font-bold">${currentPrice.toFixed(2)}</div>
          <div className="text-gray-500">Current</div>
        </div>
        <div className="text-center p-2 bg-blue-50 rounded">
          <div className="text-blue-600 font-bold">${baseTarget.toFixed(2)}</div>
          <div className="text-gray-500">Base</div>
        </div>
        <div className="text-center p-2 bg-green-50 rounded">
          <div className="text-green-600 font-semibold">${optimisticTarget.toFixed(2)}</div>
          <div className="text-gray-500">Optimistic</div>
        </div>
      </div>
    </div>
  )
}
