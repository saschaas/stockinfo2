import { useQuery } from '@tanstack/react-query'
import { fetchMarketSentiment } from '../../services/api'
import MarketOverview from './MarketOverview'
import SentimentCard from './SentimentCard'
import TopNews from './TopNews'

export default function Dashboard() {
  const { data: sentiment, isLoading, error } = useQuery({
    queryKey: ['marketSentiment'],
    queryFn: fetchMarketSentiment,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center animate-pulse">
          <svg className="w-6 h-6 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card card-body bg-danger-50 border-danger-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-danger-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-danger-800 font-medium">Error loading market data</h3>
            <p className="text-danger-600 text-sm mt-1">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Market overview and sentiment analysis</p>
        </div>
        {sentiment?.date && (
          <span className="badge badge-neutral">
            Updated: {sentiment.date}
          </span>
        )}
      </div>

      {/* Market Indices */}
      <MarketOverview indices={sentiment?.indices} />

      {/* Sentiment & Sectors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SentimentCard
          title="Market Sentiment"
          score={sentiment?.overall_sentiment}
          bullish={sentiment?.bullish_score}
          bearish={sentiment?.bearish_score}
          hotSectors={sentiment?.hot_sectors}
          negativeSectors={sentiment?.negative_sectors}
          indices={sentiment?.indices}
        />

        {/* Sectors Card */}
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Analysis</h3>
          <div className="grid grid-cols-2 gap-6">
            {/* Hot Sectors */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-success-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-success-700">Hot Sectors</h4>
              </div>
              <ul className="space-y-2">
                {sentiment?.hot_sectors?.map((sector: any, index: number) => (
                  <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-success-500" />
                    {sector.name || sector}
                  </li>
                )) || (
                  <li className="text-sm text-gray-400">No data available</li>
                )}
              </ul>
            </div>

            {/* Negative Sectors */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-danger-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-danger-700">Lagging Sectors</h4>
              </div>
              <ul className="space-y-2">
                {sentiment?.negative_sectors?.map((sector: any, index: number) => (
                  <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-danger-500" />
                    {sector.name || sector}
                  </li>
                )) || (
                  <li className="text-sm text-gray-400">No data available</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Top News */}
      <TopNews news={sentiment?.top_news || []} />
    </div>
  )
}
