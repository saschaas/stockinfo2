import type { TechnicalAnalysisData } from '../../types/technical-analysis'
import MACDCard from './MACDCard'

interface TechnicalIndicatorsPanelProps {
  data: TechnicalAnalysisData
}

export default function TechnicalIndicatorsPanel({ data }: TechnicalIndicatorsPanelProps) {
  // Helper functions
  const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === undefined || value === null) return 'N/A'
    const num = typeof value === 'number' ? value : Number(value)
    if (isNaN(num)) return 'N/A'
    return num.toFixed(decimals)
  }

  // Format volume in millions
  const formatVolume = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return 'N/A'
    const num = typeof value === 'number' ? value : Number(value)
    if (isNaN(num)) return 'N/A'
    return (num / 1000000).toFixed(2) + 'M'
  }

  const getSignalBadgeColor = (signal: string) => {
    switch (signal?.toLowerCase()) {
      case 'bullish':
      case 'oversold':
      case 'rising':
      case 'high':
      case 'very_high':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'bearish':
      case 'overbought':
      case 'falling':
      case 'low':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'neutral':
      case 'normal':
      case 'moderate':
        return 'bg-gray-100 text-gray-800 border-gray-300'
      case 'strong':
      case 'very_strong':
        return 'bg-purple-100 text-purple-800 border-purple-300'
      case 'weak':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300'
    }
  }

  const formatSignal = (signal: string) => {
    if (!signal) return 'N/A'
    return signal.replace(/_/g, ' ').toUpperCase()
  }

  // RSI Gauge Component
  const RSIGauge = ({ value }: { value: number | undefined }) => {
    if (value === undefined || value === null || isNaN(value)) {
      return <div className="text-center text-gray-500">RSI data not available</div>
    }

    const percentage = (value / 100) * 100
    let color = 'bg-yellow-500'
    if (value < 25) color = 'bg-green-500'
    else if (value > 75) color = 'bg-red-500'

    return (
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-gray-600">
          <span>0</span>
          <span className="font-semibold">RSI</span>
          <span>100</span>
        </div>
        <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
          {/* Zones */}
          <div className="absolute inset-0 flex">
            <div className="w-1/4 bg-green-100" />
            <div className="w-1/2 bg-gray-100" />
            <div className="w-1/4 bg-red-100" />
          </div>
          {/* Threshold lines */}
          <div className="absolute left-1/4 top-0 bottom-0 w-px bg-green-400" />
          <div className="absolute left-3/4 top-0 bottom-0 w-px bg-red-400" />
          {/* Value bar */}
          <div
            className={`absolute top-0 bottom-0 left-0 ${color} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
          {/* Value indicator */}
          <div
            className="absolute top-0 bottom-0 w-1 bg-gray-900 shadow-lg transition-all duration-500"
            style={{ left: `calc(${percentage}% - 2px)` }}
          />
        </div>
        <div className="text-center">
          <span className="text-2xl font-bold text-gray-900">{safeToFixed(value, 1)}</span>
          <span className={`ml-2 px-2 py-1 rounded text-xs font-medium border ${getSignalBadgeColor(data.rsi_signal)}`}>
            {formatSignal(data.rsi_signal)}
          </span>
        </div>
      </div>
    )
  }

  // Score Card Component
  const ScoreCard = ({ title, score, maxScore = 10 }: { title: string; score: number | undefined; maxScore?: number }) => {
    if (score === undefined || score === null || isNaN(score)) {
      return (
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <h4 className="text-sm font-medium text-gray-600 mb-2">{title}</h4>
          <div className="text-center text-gray-500">N/A</div>
        </div>
      )
    }

    const percentage = (score / maxScore) * 100
    let color = 'bg-yellow-500'
    if (percentage >= 70) color = 'bg-green-500'
    else if (percentage < 40) color = 'bg-red-500'

    return (
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <h4 className="text-sm font-medium text-gray-600 mb-2">{title}</h4>
        <div className="flex items-end justify-between mb-2">
          <span className="text-3xl font-bold text-gray-900">{safeToFixed(score, 1)}</span>
          <span className="text-sm text-gray-500">/ {maxScore}</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${color} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
      <h3 className="text-2xl font-bold text-gray-900">Technical Indicators</h3>

      {/* Score Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <ScoreCard title="Trend Score" score={data.trend_score} />
        <ScoreCard title="Momentum Score" score={data.momentum_score} />
        <ScoreCard title="Volatility Score" score={data.volatility_score} />
        <ScoreCard title="Volume Score" score={data.volume_score} />
      </div>

      {/* Momentum Indicators */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Momentum Indicators</h4>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* RSI Gauge */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-3">Relative Strength Index (RSI)</h5>
            <RSIGauge value={data.rsi} />
            <p className="text-xs text-gray-600 mt-2">
              Growth stock thresholds: Oversold &lt; 25, Overbought &gt; 75
            </p>
          </div>

          {/* MACD */}
          <MACDCard data={data} />

          {/* Rate of Change (ROC) */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-3">Rate of Change (ROC)</h5>
            <div className="space-y-3">
              <div className="text-center">
                <span className={`text-3xl font-bold ${data.roc >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {data.roc > 0 ? '+' : ''}{safeToFixed(data.roc, 2)}%
                </span>
              </div>
              <div className="text-center">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalBadgeColor(data.roc_signal)}`}>
                  {formatSignal(data.roc_signal)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trend Indicators */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Trend Indicators</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-2">Moving Averages</h5>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">SMA 20:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">${safeToFixed(data.sma_20, 2)}</span>
                  <span className={`text-xs ${data.price_above_sma_20 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.price_above_sma_20 ? '↑' : '↓'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">SMA 50:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">${safeToFixed(data.sma_50, 2)}</span>
                  <span className={`text-xs ${data.price_above_sma_50 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.price_above_sma_50 ? '↑' : '↓'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">SMA 200:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">${safeToFixed(data.sma_200, 2)}</span>
                  <span className={`text-xs ${data.price_above_sma_200 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.price_above_sma_200 ? '↑' : '↓'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-2">ADX (Trend Strength)</h5>
            <div className="text-center mb-2">
              <span className="text-3xl font-bold text-gray-900">{safeToFixed(data.adx, 1)}</span>
            </div>
            <div className="text-center">
              <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalBadgeColor(data.adx_signal)}`}>
                {formatSignal(data.adx_signal)}
              </span>
            </div>
            <p className="text-xs text-gray-600 mt-2 text-center">
              ADX &gt; 25 = Strong Trend
            </p>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-2">Trend Signals</h5>
            <div className="space-y-2">
              {data.golden_cross && (
                <div className="flex items-center gap-2">
                  <span className="text-green-600">✓</span>
                  <span className="text-sm font-medium text-green-700">Golden Cross</span>
                </div>
              )}
              {data.death_cross && (
                <div className="flex items-center gap-2">
                  <span className="text-red-600">✗</span>
                  <span className="text-sm font-medium text-red-700">Death Cross</span>
                </div>
              )}
              {!data.golden_cross && !data.death_cross && (
                <div className="text-sm text-gray-500">No cross signals</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Volume Indicators */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Volume Indicators</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-3">Volume Analysis</h5>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Current:</span>
                <span className="font-semibold text-gray-900">{formatVolume(data.current_volume)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">20-Day Avg:</span>
                <span className="font-semibold text-gray-900">{formatVolume(data.avg_volume_20d)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Ratio:</span>
                <span className={`font-semibold ${(data.volume_ratio ?? 0) > 1.5 ? 'text-green-600' : (data.volume_ratio ?? 0) < 0.5 ? 'text-red-600' : 'text-gray-900'}`}>
                  {safeToFixed(data.volume_ratio, 2)}x
                </span>
              </div>
              <div className="mt-2 pt-2 border-t border-gray-300">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalBadgeColor(data.volume_signal)}`}>
                  {formatSignal(data.volume_signal)} VOLUME
                </span>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium text-gray-700 mb-3">OBV (On-Balance Volume)</h5>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">OBV:</span>
                <span className="font-semibold text-gray-900">{formatVolume(data.obv)}</span>
              </div>
              <div className="mt-2">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalBadgeColor(data.obv_trend)}`}>
                  {formatSignal(data.obv_trend)} TREND
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-2">
                OBV confirms price movements through volume accumulation
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Support/Resistance Summary */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Support & Resistance Levels</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <h5 className="font-medium text-red-900 mb-3">Resistance Levels</h5>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-red-700">R3:</span>
                <span className="font-semibold text-red-900">${safeToFixed(data.resistance_3, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-red-700">R2:</span>
                <span className="font-semibold text-red-900">${safeToFixed(data.resistance_2, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-red-700">R1:</span>
                <span className="font-semibold text-red-900">${safeToFixed(data.resistance_1, 2)}</span>
              </div>
            </div>
          </div>

          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h5 className="font-medium text-green-900 mb-3">Support Levels</h5>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-green-700">S1:</span>
                <span className="font-semibold text-green-900">${safeToFixed(data.support_1, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-green-700">S2:</span>
                <span className="font-semibold text-green-900">${safeToFixed(data.support_2, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-green-700">S3:</span>
                <span className="font-semibold text-green-900">${safeToFixed(data.support_3, 2)}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 p-3 bg-gray-100 rounded">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-700">Pivot Point:</span>
            <span className="text-lg font-bold text-gray-900">${safeToFixed(data.pivot, 2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
