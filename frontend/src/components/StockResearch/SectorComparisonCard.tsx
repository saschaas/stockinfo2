interface SectorComparisonData {
  ticker: string
  sector: string
  analysis_date: string
  stock_metrics: Record<string, number | null>
  sector_averages: Record<string, number | null>
  sector_medians: Record<string, number | null>
  percentile_ranks: Record<string, number | null>
  relative_strength: string
  stocks_included: number
  data_freshness: string
  warning?: string
  error?: string
}

interface SectorComparisonCardProps {
  ticker: string
  sectorComparisonData?: SectorComparisonData
}

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  pe_ratio: 'P/E Ratio',
  forward_pe: 'Forward P/E',
  price_to_book: 'Price to Book',
  peg_ratio: 'PEG Ratio',
  debt_to_equity: 'Debt to Equity',
  composite_score: 'Composite Score',
  fundamental_score: 'Fundamental Score',
  technical_score: 'Technical Score',
  competitive_score: 'Competitive Score',
  risk_score: 'Risk Score',
  rsi: 'RSI',
  upside_potential: 'Upside Potential'
}

const METRIC_CATEGORIES = {
  'Valuation Metrics': ['pe_ratio', 'forward_pe', 'price_to_book', 'peg_ratio', 'debt_to_equity'],
  'Analysis Scores': ['composite_score', 'fundamental_score', 'technical_score', 'competitive_score', 'risk_score'],
  'Technical & Performance': ['rsi', 'upside_potential']
}

export default function SectorComparisonCard({ ticker, sectorComparisonData }: SectorComparisonCardProps) {
  if (!sectorComparisonData) {
    return null
  }

  if (sectorComparisonData.error) {
    return (
      <div className="bg-white border rounded-lg p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-2">Sector Comparison</h4>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800">
          {sectorComparisonData.error}
        </div>
      </div>
    )
  }

  const getRelativeStrengthBadge = (strength: string) => {
    const configs: Record<string, { bg: string; text: string; label: string }> = {
      well_above_average: { bg: 'bg-green-100', text: 'text-green-800', label: 'Well Above Average' },
      above_average: { bg: 'bg-green-50', text: 'text-green-700', label: 'Above Average' },
      average: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Average' },
      below_average: { bg: 'bg-orange-50', text: 'text-orange-700', label: 'Below Average' },
      well_below_average: { bg: 'bg-red-100', text: 'text-red-800', label: 'Well Below Average' },
      unknown: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Unknown' }
    }

    const config = configs[strength] || configs.unknown

    return (
      <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </div>
    )
  }

  const getPercentileBadge = (percentile: number | null) => {
    if (percentile === null) return <span className="text-xs text-gray-400">N/A</span>

    let bgColor = 'bg-gray-100 text-gray-700'
    if (percentile >= 75) bgColor = 'bg-green-100 text-green-800'
    else if (percentile >= 50) bgColor = 'bg-blue-100 text-blue-800'
    else if (percentile >= 25) bgColor = 'bg-orange-100 text-orange-800'
    else bgColor = 'bg-red-100 text-red-800'

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${bgColor}`}>
        {percentile.toFixed(0)}th
      </span>
    )
  }

  const getComparisonIndicator = (stockValue: number | null, sectorAvg: number | null, metricName: string) => {
    if (stockValue === null || sectorAvg === null) {
      return <span className="text-xs text-gray-400">N/A</span>
    }

    // For risk_score, lower is better
    const lowerIsBetter = metricName === 'risk_score'
    const diff = stockValue - sectorAvg
    const diffPercent = (diff / sectorAvg) * 100

    let icon = '='
    let color = 'text-gray-600'

    if (Math.abs(diffPercent) < 5) {
      icon = '≈'
      color = 'text-gray-600'
    } else if (lowerIsBetter) {
      if (diff < 0) {
        icon = '▼'
        color = 'text-green-600'
      } else {
        icon = '▲'
        color = 'text-red-600'
      }
    } else {
      if (diff > 0) {
        icon = '▲'
        color = 'text-green-600'
      } else {
        icon = '▼'
        color = 'text-red-600'
      }
    }

    return (
      <span className={`inline-flex items-center text-sm font-medium ${color}`}>
        {icon} {Math.abs(diffPercent).toFixed(1)}%
      </span>
    )
  }

  const formatValue = (value: number | null, metricName: string) => {
    if (value === null) return 'N/A'

    // Format based on typical value ranges
    if (metricName.includes('score')) {
      return value.toFixed(2)
    } else if (metricName === 'upside_potential') {
      return value.toFixed(1) + '%'
    } else {
      return value.toFixed(2)
    }
  }

  return (
    <div className="bg-white border rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="text-lg font-semibold text-gray-900 mb-1">Sector Comparison</h4>
          <p className="text-sm text-gray-600">
            {ticker} vs. {sectorComparisonData.sector} Sector
          </p>
        </div>
        {getRelativeStrengthBadge(sectorComparisonData.relative_strength)}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase">Sector</div>
          <div className="text-lg font-semibold text-gray-900">{sectorComparisonData.sector}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase">Stocks Compared</div>
          <div className="text-lg font-semibold text-gray-900">{sectorComparisonData.stocks_included}</div>
        </div>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase">Data Range</div>
          <div className="text-lg font-semibold text-gray-900">{sectorComparisonData.data_freshness}</div>
        </div>
      </div>

      {/* Warning if any */}
      {sectorComparisonData.warning && (
        <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-yellow-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-yellow-800">{sectorComparisonData.warning}</p>
          </div>
        </div>
      )}

      {/* Comparison Table by Category */}
      {Object.entries(METRIC_CATEGORIES).map(([category, metrics]) => (
        <div key={category} className="mb-6">
          <h5 className="text-sm font-semibold text-gray-900 mb-3">{category}</h5>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Metric
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {ticker}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sector Avg
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    vs Sector
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Percentile
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {metrics.map((metricKey) => {
                  const stockValue = sectorComparisonData.stock_metrics[metricKey]
                  const sectorAvg = sectorComparisonData.sector_averages[metricKey]
                  const percentile = sectorComparisonData.percentile_ranks[metricKey]

                  return (
                    <tr key={metricKey} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {METRIC_DISPLAY_NAMES[metricKey] || metricKey}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {formatValue(stockValue, metricKey)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {formatValue(sectorAvg, metricKey)}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {getComparisonIndicator(stockValue, sectorAvg, metricKey)}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {getPercentileBadge(percentile)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Footer Note */}
      <div className="mt-4 pt-4 border-t text-xs text-gray-500">
        <p className="mb-1">
          <strong>Percentile Rankings:</strong> Shows where {ticker} ranks compared to other stocks in the {sectorComparisonData.sector} sector.
          Higher percentile = better performance (except for Risk Score, where lower is better).
        </p>
        <p>
          <strong>Comparison Indicator:</strong> ▲ = Above sector average, ▼ = Below sector average, ≈ = Close to average (within 5%).
        </p>
      </div>
    </div>
  )
}
