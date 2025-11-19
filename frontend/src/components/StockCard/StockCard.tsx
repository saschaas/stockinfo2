import { useMemo } from 'react'
import Plot from 'react-plotly.js'
import DataSourceBadge from '../DataSourceBadge/DataSourceBadge'

interface StockCardProps {
  ticker: string
  companyName?: string
  sector?: string
  currentPrice?: number
  priceChange?: number
  recommendation?: string
  confidence?: number
  targetPrice?: number
  peRatio?: number
  rsi?: number
  prices?: Array<{
    date: string
    close: number
  }>
  dataSources?: Record<string, { type: string }>
}

export default function StockCard({
  ticker,
  companyName,
  sector,
  currentPrice,
  priceChange,
  recommendation,
  confidence,
  targetPrice,
  peRatio,
  rsi,
  prices,
  dataSources,
}: StockCardProps) {
  const recommendationStyles = useMemo(() => {
    switch (recommendation) {
      case 'strong_buy':
        return { bg: 'bg-green-100', text: 'text-green-800', label: 'Strong Buy' }
      case 'buy':
        return { bg: 'bg-green-50', text: 'text-green-700', label: 'Buy' }
      case 'hold':
        return { bg: 'bg-yellow-50', text: 'text-yellow-700', label: 'Hold' }
      case 'sell':
        return { bg: 'bg-red-50', text: 'text-red-700', label: 'Sell' }
      case 'strong_sell':
        return { bg: 'bg-red-100', text: 'text-red-800', label: 'Strong Sell' }
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-700', label: 'N/A' }
    }
  }, [recommendation])

  const chartData = useMemo(() => {
    if (!prices || prices.length === 0) return null

    return [
      {
        x: prices.map((p) => p.date),
        y: prices.map((p) => p.close),
        type: 'scatter' as const,
        mode: 'lines' as const,
        line: { color: '#3b82f6', width: 2 },
        fill: 'tozeroy' as const,
        fillcolor: 'rgba(59, 130, 246, 0.1)',
      },
    ]
  }, [prices])

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-xl font-bold text-gray-900">{ticker}</h3>
            {companyName && (
              <p className="text-sm text-gray-500">{companyName}</p>
            )}
            {sector && (
              <p className="text-xs text-gray-400 mt-1">{sector}</p>
            )}
          </div>
          <div className="text-right">
            {currentPrice && (
              <p className="text-2xl font-bold">
                ${currentPrice.toFixed(2)}
              </p>
            )}
            {priceChange != null && (
              <p
                className={`text-sm font-medium ${
                  priceChange >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {priceChange >= 0 ? '+' : ''}
                {(priceChange * 100).toFixed(2)}%
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Price Chart */}
      {chartData && (
        <div className="px-4 py-2">
          <Plot
            data={chartData}
            layout={{
              height: 150,
              margin: { t: 10, r: 10, b: 30, l: 40 },
              xaxis: {
                showgrid: false,
                tickformat: '%b %d',
              },
              yaxis: {
                showgrid: true,
                gridcolor: '#f3f4f6',
                tickprefix: '$',
              },
              showlegend: false,
            }}
            config={{ displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Metrics */}
      <div className="p-6 grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-gray-500 uppercase">P/E Ratio</p>
          <p className="text-lg font-semibold">
            {peRatio ? peRatio.toFixed(2) : 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">RSI (14)</p>
          <p className="text-lg font-semibold">
            {rsi ? rsi.toFixed(1) : 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Target Price</p>
          <p className="text-lg font-semibold">
            {targetPrice ? `$${targetPrice.toFixed(2)}` : 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Confidence</p>
          <p className="text-lg font-semibold">
            {confidence ? `${(confidence * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Recommendation */}
      <div className="px-6 pb-4">
        <div
          className={`rounded-lg p-4 text-center ${recommendationStyles.bg}`}
        >
          <p className="text-xs uppercase text-gray-500 mb-1">Recommendation</p>
          <p className={`text-xl font-bold ${recommendationStyles.text}`}>
            {recommendationStyles.label}
          </p>
        </div>
      </div>

      {/* Data Sources */}
      {dataSources && Object.keys(dataSources).length > 0 && (
        <div className="px-6 pb-4 flex flex-wrap gap-2">
          {Object.entries(dataSources).map(([key, value]) => (
            <DataSourceBadge
              key={key}
              source={value.type}
              label={key}
            />
          ))}
        </div>
      )}
    </div>
  )
}
