import type { TechnicalSummaryResponse } from '../../types'

interface TechnicalIndicatorSummaryProps {
  data: TechnicalSummaryResponse
}

export default function TechnicalIndicatorSummary({ data }: TechnicalIndicatorSummaryProps) {
  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return (
          <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        )
      case 'down':
        return (
          <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        )
      default:
        return (
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
          </svg>
        )
    }
  }

  const getMacdStatusColor = (status: string) => {
    switch (status) {
      case 'bullish_crossover':
      case 'bullish':
        return 'text-success-600 bg-success-50 border-success-200'
      case 'bearish_crossover':
      case 'bearish':
        return 'text-danger-600 bg-danger-50 border-danger-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getMacdStatusLabel = (status: string) => {
    switch (status) {
      case 'bullish_crossover':
        return 'Bullish Crossover'
      case 'bullish':
        return 'Bullish'
      case 'bearish_crossover':
        return 'Bearish Crossover'
      case 'bearish':
        return 'Bearish'
      default:
        return 'Neutral'
    }
  }

  const formatPrice = (value: number | null) => {
    if (value === null) return '-'
    return `$${value.toFixed(2)}`
  }

  return (
    <div className="card card-body">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Technical Summary</h2>

      <div className="grid md:grid-cols-2 gap-6">
        {/* SMA Trends */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide">Moving Averages</h3>

          <div className="space-y-3">
            {/* SMA 20 */}
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div>
                  <span className="font-medium text-gray-900">SMA 20</span>
                  <span className="text-gray-500 ml-2">{formatPrice(data.sma_20)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getDirectionIcon(data.sma_20_direction)}
                <span className={`text-sm font-medium ${
                  data.price_above_sma_20 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {data.price_above_sma_20 ? 'Above' : 'Below'}
                </span>
              </div>
            </div>

            {/* SMA 50 */}
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-orange-500" />
                <div>
                  <span className="font-medium text-gray-900">SMA 50</span>
                  <span className="text-gray-500 ml-2">{formatPrice(data.sma_50)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getDirectionIcon(data.sma_50_direction)}
                <span className={`text-sm font-medium ${
                  data.price_above_sma_50 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {data.price_above_sma_50 ? 'Above' : 'Below'}
                </span>
              </div>
            </div>

            {/* SMA 200 */}
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-purple-500" />
                <div>
                  <span className="font-medium text-gray-900">SMA 200</span>
                  <span className="text-gray-500 ml-2">{formatPrice(data.sma_200)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${
                  data.price_above_sma_200 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {data.price_above_sma_200 ? 'Above' : 'Below'}
                </span>
              </div>
            </div>

            {/* Golden/Death Cross Status */}
            <div className="flex items-center gap-2 mt-2">
              {data.has_golden_cross && (
                <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-success-100 text-success-700 border border-success-200 text-sm font-medium">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                  Golden Cross
                </span>
              )}
              {data.has_death_cross && (
                <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-danger-100 text-danger-700 border border-danger-200 text-sm font-medium">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Death Cross
                </span>
              )}
              {!data.has_golden_cross && !data.has_death_cross && (
                <span className="text-sm text-gray-500">No cross pattern detected</span>
              )}
            </div>
          </div>
        </div>

        {/* MACD Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide">MACD (12, 26, 9)</h3>

          <div className="p-4 bg-gray-50 rounded-lg space-y-4">
            {/* MACD Values */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">MACD Line</p>
                <p className={`font-semibold ${
                  data.macd !== null && data.macd > 0 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {data.macd !== null ? data.macd.toFixed(3) : '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Signal Line</p>
                <p className="font-semibold text-gray-900">
                  {data.macd_signal !== null ? data.macd_signal.toFixed(3) : '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Histogram</p>
                <p className={`font-semibold ${
                  data.macd_histogram !== null && data.macd_histogram > 0 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {data.macd_histogram !== null ? data.macd_histogram.toFixed(3) : '-'}
                </p>
              </div>
            </div>

            {/* MACD Status */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Status:</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getMacdStatusColor(data.macd_status)}`}>
                  {getMacdStatusLabel(data.macd_status)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Histogram:</span>
                <span className="flex items-center gap-1 text-sm font-medium">
                  {data.histogram_direction === 'increasing' ? (
                    <>
                      <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                      <span className="text-success-600">Increasing</span>
                    </>
                  ) : data.histogram_direction === 'decreasing' ? (
                    <>
                      <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                      </svg>
                      <span className="text-danger-600">Decreasing</span>
                    </>
                  ) : (
                    <span className="text-gray-500">Stable</span>
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* Current Price Context */}
          {data.current_price !== null && (
            <div className="p-4 bg-primary-50 rounded-lg border border-primary-200">
              <div className="flex items-center justify-between">
                <span className="text-sm text-primary-700">Current Price</span>
                <span className="text-lg font-bold text-primary-900">${data.current_price.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
