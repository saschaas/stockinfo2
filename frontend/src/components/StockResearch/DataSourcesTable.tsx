interface DataSource {
  type: string
  name: string
}

interface DataSourcesTableProps {
  dataSources?: Record<string, DataSource>
  missingCategories?: string[]
  completenessScore?: number
  sectorComparisonAvailable?: boolean
}

export default function DataSourcesTable({
  dataSources,
  missingCategories,
  completenessScore,
  sectorComparisonAvailable
}: DataSourcesTableProps) {
  if (!dataSources) {
    return null
  }

  // Map data categories to their respective fields
  const dataMapping = [
    {
      category: 'Stock Information',
      fields: ['Ticker', 'Company Name', 'Sector', 'Industry', 'Market Cap'],
      source: dataSources.stock_info,
      available: !!dataSources.stock_info,
      note: null
    },
    {
      category: 'Price Data',
      fields: ['Current Price', 'Historical Prices'],
      source: dataSources.stock_info,
      available: !!dataSources.stock_info,
      note: null
    },
    {
      category: 'Technical Indicators',
      fields: ['RSI', 'SMA 20', 'SMA 50', 'MACD', 'Bollinger Bands'],
      source: dataSources.technical,
      available: !!dataSources.technical,
      note: null
    },
    {
      category: 'Fundamental Metrics',
      fields: ['P/E Ratio', 'Revenue', 'EPS', 'Profit Margin', 'ROE'],
      source: dataSources.fundamentals,
      available: !!dataSources.fundamentals,
      note: null
    },
    {
      category: 'Financial Data',
      fields: ['Balance Sheet', 'Income Statement', 'Cash Flow'],
      source: dataSources.fundamentals,
      available: !!dataSources.fundamentals,
      note: null
    },
    {
      category: 'Analyst Coverage',
      fields: ['Analyst Recommendations', 'Target Prices', 'Upgrades/Downgrades'],
      source: dataSources.stock_info,
      available: !!dataSources.stock_info,
      note: 'Available when analysts cover the stock'
    },
    {
      category: 'Peer Comparison',
      fields: ['Sector Averages', 'Percentile Rankings', 'Valuation Metrics', 'Performance Comparison'],
      source: sectorComparisonAvailable ? { type: 'analysis', name: 'sector_comparison' } : null,
      available: !!sectorComparisonAvailable,
      note: sectorComparisonAvailable ? 'Comparison with sector peers based on recent analyses' : 'Not available from current data sources'
    },
    {
      category: 'Growth Analysis',
      fields: ['Multi-Factor Scoring', 'Price Targets', 'Risk Assessment', 'Portfolio Allocation'],
      source: dataSources.growth_analysis,
      available: !!dataSources.growth_analysis,
      note: null
    },
    {
      category: 'AI Analysis',
      fields: ['Recommendation', 'Investment Thesis', 'Key Insights', 'Risk/Opportunity Analysis'],
      source: dataSources.ai_analysis,
      available: !!dataSources.ai_analysis,
      note: null
    }
  ]

  // Get unique sources
  const sources = Object.values(dataSources).reduce((acc, source) => {
    if (!acc.some(s => s.name === source.name && s.type === source.type)) {
      acc.push(source)
    }
    return acc
  }, [] as DataSource[])

  const getSourceBadge = (source: DataSource) => {
    const isAPI = source.type === 'api'
    const isAnalysis = source.type === 'analysis'
    const bgColor = isAPI ? 'bg-blue-100 text-blue-800' : isAnalysis ? 'bg-teal-100 text-teal-800' : 'bg-purple-100 text-purple-800'
    const icon = isAPI ? '🌐' : isAnalysis ? '📊' : '🤖'

    return (
      <div className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${bgColor}`}>
        <span className="mr-1">{icon}</span>
        {source.name.replace(/_/g, ' ').toUpperCase()}
      </div>
    )
  }

  return (
    <div className="bg-white border rounded-lg p-6">
      <h4 className="text-lg font-semibold text-gray-900 mb-4">Data Sources & Coverage</h4>

      {/* Data Completeness Summary */}
      {completenessScore !== undefined && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Data Completeness</span>
            <span className={`text-lg font-bold ${
              completenessScore >= 80 ? 'text-green-600' :
              completenessScore >= 60 ? 'text-yellow-600' :
              completenessScore >= 40 ? 'text-orange-600' : 'text-red-600'
            }`}>
              {completenessScore.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                completenessScore >= 80 ? 'bg-green-500' :
                completenessScore >= 60 ? 'bg-yellow-500' :
                completenessScore >= 40 ? 'bg-orange-500' : 'bg-red-500'
              }`}
              style={{ width: `${completenessScore}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Sources Used */}
      <div className="mb-6">
        <h5 className="text-sm font-semibold text-gray-900 mb-3">Sources Used</h5>
        <div className="flex flex-wrap gap-2">
          {sources.map((source, idx) => (
            <div key={idx}>
              {getSourceBadge(source)}
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-4 text-xs text-gray-600">
          <div className="flex items-center">
            <span className="mr-1">🌐</span>
            <span>Direct API</span>
          </div>
          <div className="flex items-center">
            <span className="mr-1">📊</span>
            <span>Analysis</span>
          </div>
          <div className="flex items-center">
            <span className="mr-1">🤖</span>
            <span>AI Analysis</span>
          </div>
        </div>
      </div>

      {/* Data Coverage Table */}
      <div className="mb-6">
        <h5 className="text-sm font-semibold text-gray-900 mb-3">Data Coverage by Category</h5>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data Category
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fields Included
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dataMapping.map((item, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {item.category}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    <div className="space-y-1">
                      {item.fields.map((field, fidx) => (
                        <div key={fidx} className="text-xs">• {field}</div>
                      ))}
                    </div>
                    {item.note && (
                      <div className="mt-2 text-xs italic text-gray-500">
                        {item.note}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {item.available && item.source ? (
                      getSourceBadge(item.source)
                    ) : (
                      <span className="text-xs text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {item.available ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ✓ Available
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        ✗ Not Available
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Missing Data Categories */}
      {missingCategories && missingCategories.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-yellow-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h5 className="text-sm font-semibold text-yellow-900 mb-2">Missing Data Categories</h5>
              <ul className="text-sm text-yellow-800 space-y-1">
                {missingCategories.map((category, idx) => (
                  <li key={idx}>• {category}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-yellow-700">
                These data points were not available from our sources at the time of analysis.
                This may affect the completeness and accuracy of the investment recommendation.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Data Sources Legend */}
      <div className="mt-6 pt-4 border-t text-xs text-gray-500">
        <p className="font-medium mb-2">Data Source Information:</p>
        <ul className="space-y-1">
          <li>• <strong>Yahoo Finance</strong> - Stock prices, technical indicators, basic company info</li>
          <li>• <strong>Alpha Vantage</strong> - Fundamental data, financial statements</li>
          <li>• <strong>Sector Comparison</strong> - Peer analysis using historical stock data from database</li>
          <li>• <strong>Ollama (AI)</strong> - Stock analysis, recommendations, sentiment analysis</li>
          <li>• <strong>Growth Analysis Agent (AI)</strong> - Multi-factor scoring, price targets, risk assessment</li>
        </ul>
        <p className="mt-3 text-xs">
          Last updated: {new Date().toLocaleString()}
        </p>
      </div>
    </div>
  )
}
