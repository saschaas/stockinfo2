import { useMemo } from 'react'
import type { TechnicalAnalysisData } from '../../types/technical-analysis'

interface MACDCardProps {
  data: TechnicalAnalysisData
}

export default function MACDCard({ data }: MACDCardProps) {
  // Helper function to safely format numbers
  const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === undefined || value === null) return 'N/A'
    const num = typeof value === 'number' ? value : Number(value)
    if (isNaN(num)) return 'N/A'
    return num.toFixed(decimals)
  }

  // Get MACD chart data if available
  const chartData = data.chart_data
  const hasChartData = chartData?.indicators?.macd &&
                       chartData?.indicators?.macd_signal &&
                       chartData?.indicators?.macd_histogram &&
                       chartData.indicators.macd.length > 0

  // Calculate MACD analysis
  const analysis = useMemo(() => {
    const macd = data.macd
    const signal = data.macd_signal
    const histogram = data.macd_histogram

    if (macd === undefined || macd === null || isNaN(macd)) {
      return null
    }

    // Trend direction based on MACD position relative to zero
    const trendZone = macd > 0 ? 'bullish' : macd < 0 ? 'bearish' : 'neutral'

    // Momentum strength based on histogram
    const histogramAbs = Math.abs(histogram || 0)
    let momentumStrength: 'weak' | 'moderate' | 'strong' = 'weak'
    if (histogramAbs > 1) momentumStrength = 'strong'
    else if (histogramAbs > 0.3) momentumStrength = 'moderate'

    // Momentum direction
    const momentumDirection = (histogram || 0) > 0 ? 'bullish' : 'bearish'

    // Check for crossover
    const crossover = data.macd_cross

    // Calculate histogram trend (is it growing or shrinking?)
    let histogramTrend: 'growing' | 'shrinking' | 'stable' = 'stable'
    if (hasChartData && chartData.indicators.macd_histogram.length >= 3) {
      const histArr = chartData.indicators.macd_histogram.filter((v: number | null) => v !== null) as number[]
      if (histArr.length >= 3) {
        const recent = histArr.slice(-3)
        const absRecent = recent.map(Math.abs)
        if (absRecent[2] > absRecent[1] && absRecent[1] > absRecent[0]) {
          histogramTrend = 'growing'
        } else if (absRecent[2] < absRecent[1] && absRecent[1] < absRecent[0]) {
          histogramTrend = 'shrinking'
        }
      }
    }

    return {
      trendZone,
      momentumStrength,
      momentumDirection,
      crossover,
      histogramTrend,
      macdValue: macd,
      signalValue: signal,
      histogramValue: histogram,
    }
  }, [data.macd, data.macd_signal, data.macd_histogram, data.macd_cross, hasChartData, chartData])

  // Generate interpretation text
  const getInterpretation = () => {
    if (!analysis) return null

    const parts: string[] = []

    // Trend zone interpretation
    if (analysis.trendZone === 'bullish') {
      parts.push('MACD is above zero, indicating short-term momentum is stronger than long-term - a bullish environment.')
    } else if (analysis.trendZone === 'bearish') {
      parts.push('MACD is below zero, indicating short-term momentum is weaker than long-term - a bearish environment.')
    }

    // Crossover interpretation
    if (analysis.crossover === 'bullish') {
      parts.push('A bullish crossover has occurred (MACD crossed above signal line), suggesting upward momentum shift.')
    } else if (analysis.crossover === 'bearish') {
      parts.push('A bearish crossover has occurred (MACD crossed below signal line), suggesting downward momentum shift.')
    }

    // Histogram trend
    if (analysis.histogramTrend === 'growing') {
      parts.push('Histogram is growing, indicating strengthening momentum.')
    } else if (analysis.histogramTrend === 'shrinking') {
      parts.push('Histogram is shrinking, which may be an early sign of momentum weakening.')
    }

    return parts.join(' ')
  }

  // Mini histogram visualization using last N values
  const renderMiniHistogram = () => {
    if (!hasChartData) return null

    const histArr = chartData.indicators.macd_histogram.slice(-20).filter((v: number | null) => v !== null) as number[]
    if (histArr.length === 0) return null

    const maxAbs = Math.max(...histArr.map(Math.abs), 0.01)
    const barWidth = 100 / histArr.length

    return (
      <div className="mt-3">
        <div className="text-xs text-gray-500 mb-1">Histogram (Last 20 periods)</div>
        <div className="relative h-16 bg-gray-100 rounded overflow-hidden">
          {/* Zero line */}
          <div className="absolute left-0 right-0 top-1/2 h-px bg-gray-400 z-10" />

          {/* Bars */}
          <div className="absolute inset-0 flex items-center">
            {histArr.map((val, idx) => {
              const height = (Math.abs(val) / maxAbs) * 50
              const isPositive = val >= 0

              // Determine if momentum is increasing or decreasing
              const prevVal = idx > 0 ? histArr[idx - 1] : 0
              const isIncreasing = Math.abs(val) > Math.abs(prevVal)

              // Color based on direction and momentum
              let barColor = ''
              if (isPositive) {
                barColor = isIncreasing ? 'bg-green-500' : 'bg-green-300'
              } else {
                barColor = isIncreasing ? 'bg-red-500' : 'bg-red-300'
              }

              return (
                <div
                  key={idx}
                  className="relative"
                  style={{ width: `${barWidth}%`, height: '100%' }}
                >
                  <div
                    className={`absolute left-0.5 right-0.5 ${barColor} transition-all`}
                    style={{
                      height: `${height}%`,
                      top: isPositive ? `${50 - height}%` : '50%',
                    }}
                  />
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // MACD and Signal line visualization
  const renderLineChart = () => {
    if (!hasChartData) return null

    const macdArr = chartData.indicators.macd.slice(-20).filter((v: number | null) => v !== null) as number[]
    const signalArr = chartData.indicators.macd_signal.slice(-20).filter((v: number | null) => v !== null) as number[]

    if (macdArr.length === 0 || signalArr.length === 0) return null

    const allValues = [...macdArr, ...signalArr]
    const minVal = Math.min(...allValues)
    const maxVal = Math.max(...allValues)
    const range = maxVal - minVal || 1

    const width = 280
    const height = 60
    const padding = 4

    const getY = (val: number) => {
      return height - padding - ((val - minVal) / range) * (height - 2 * padding)
    }

    const getX = (idx: number, total: number) => {
      return padding + (idx / (total - 1)) * (width - 2 * padding)
    }

    // Create SVG paths
    const createPath = (arr: number[]) => {
      return arr.map((val, idx) => {
        const x = getX(idx, arr.length)
        const y = getY(val)
        return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`
      }).join(' ')
    }

    const macdPath = createPath(macdArr)
    const signalPath = createPath(signalArr)

    // Zero line Y position
    const zeroY = getY(0)

    return (
      <div className="mt-3">
        <div className="text-xs text-gray-500 mb-1">MACD & Signal Lines (Last 20 periods)</div>
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="bg-gray-100 rounded">
          {/* Zero line if visible */}
          {minVal <= 0 && maxVal >= 0 && (
            <line
              x1={padding}
              y1={zeroY}
              x2={width - padding}
              y2={zeroY}
              stroke="#9ca3af"
              strokeWidth="1"
              strokeDasharray="4,2"
            />
          )}

          {/* Signal line (orange) */}
          <path
            d={signalPath}
            fill="none"
            stroke="#f97316"
            strokeWidth="1.5"
          />

          {/* MACD line (blue) */}
          <path
            d={macdPath}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
          />

          {/* Crossover marker at the end if there's a recent crossover */}
          {analysis?.crossover && (
            <circle
              cx={getX(macdArr.length - 1, macdArr.length)}
              cy={getY(macdArr[macdArr.length - 1])}
              r="4"
              fill={analysis.crossover === 'bullish' ? '#22c55e' : '#ef4444'}
              stroke="white"
              strokeWidth="1"
            />
          )}
        </svg>
        <div className="flex justify-center gap-4 mt-1">
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-blue-500" />
            <span className="text-xs text-gray-500">MACD</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-orange-500" />
            <span className="text-xs text-gray-500">Signal</span>
          </div>
        </div>
      </div>
    )
  }

  // Signal badge color
  const getSignalColor = () => {
    if (!analysis) return 'bg-gray-100 text-gray-700 border-gray-300'

    if (analysis.crossover === 'bullish') {
      return 'bg-green-100 text-green-800 border-green-300'
    } else if (analysis.crossover === 'bearish') {
      return 'bg-red-100 text-red-800 border-red-300'
    } else if (analysis.trendZone === 'bullish') {
      return 'bg-green-50 text-green-700 border-green-200'
    } else if (analysis.trendZone === 'bearish') {
      return 'bg-red-50 text-red-700 border-red-200'
    }
    return 'bg-gray-100 text-gray-700 border-gray-300'
  }

  // Get overall MACD signal
  const getOverallSignal = () => {
    if (!analysis) return 'N/A'

    if (analysis.crossover === 'bullish') return 'BULLISH CROSSOVER'
    if (analysis.crossover === 'bearish') return 'BEARISH CROSSOVER'
    if (analysis.trendZone === 'bullish' && analysis.histogramTrend === 'growing') return 'BULLISH MOMENTUM'
    if (analysis.trendZone === 'bearish' && analysis.histogramTrend === 'growing') return 'BEARISH MOMENTUM'
    if (analysis.histogramTrend === 'shrinking') return 'WEAKENING MOMENTUM'
    return analysis.trendZone.toUpperCase()
  }

  return (
    <div className="bg-gray-50 p-4 rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <h5 className="font-medium text-gray-700">MACD (12, 26, 9)</h5>
        <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalColor()}`}>
          {getOverallSignal()}
        </span>
      </div>

      {/* Current Values */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-white rounded p-2 text-center">
          <div className="text-xs text-gray-500">MACD Line</div>
          <div className={`text-lg font-bold ${(data.macd || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {safeToFixed(data.macd, 2)}
          </div>
        </div>
        <div className="bg-white rounded p-2 text-center">
          <div className="text-xs text-gray-500">Signal Line</div>
          <div className="text-lg font-bold text-orange-500">
            {safeToFixed(data.macd_signal, 2)}
          </div>
        </div>
        <div className="bg-white rounded p-2 text-center">
          <div className="text-xs text-gray-500">Histogram</div>
          <div className={`text-lg font-bold ${(data.macd_histogram || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {safeToFixed(data.macd_histogram, 2)}
          </div>
        </div>
      </div>

      {/* Trend Zone Indicator */}
      {analysis && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-1">Trend Zone</div>
          <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
            {/* Bearish zone */}
            <div className="absolute left-0 w-1/2 h-full bg-red-100" />
            {/* Bullish zone */}
            <div className="absolute right-0 w-1/2 h-full bg-green-100" />
            {/* Zero line */}
            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-400 -translate-x-1/2 z-10" />
            {/* Labels */}
            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-red-600 font-medium">Bearish</div>
            <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-green-600 font-medium">Bullish</div>
            {/* Current position indicator */}
            <div
              className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white shadow-md z-20 transition-all ${
                analysis.trendZone === 'bullish' ? 'bg-green-500' : analysis.trendZone === 'bearish' ? 'bg-red-500' : 'bg-gray-500'
              }`}
              style={{
                left: `${50 + Math.min(Math.max((analysis.macdValue || 0) * 10, -45), 45)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Mini Charts */}
      {renderLineChart()}
      {renderMiniHistogram()}

      {/* Analysis Interpretation */}
      {analysis && (
        <div className="mt-3 p-2 bg-blue-50 rounded border border-blue-100">
          <div className="text-xs font-medium text-blue-800 mb-1">Analysis</div>
          <p className="text-xs text-blue-700">{getInterpretation()}</p>
        </div>
      )}

      {/* Quick Reference */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <div className="grid grid-cols-2 gap-1">
            <div><span className="font-medium">MACD {'>'} 0:</span> Bullish trend</div>
            <div><span className="font-medium">MACD {'<'} 0:</span> Bearish trend</div>
            <div><span className="font-medium">Histogram growing:</span> Momentum increasing</div>
            <div><span className="font-medium">Histogram shrinking:</span> Momentum weakening</div>
          </div>
        </div>
      </div>
    </div>
  )
}
