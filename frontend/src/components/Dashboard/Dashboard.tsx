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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-medium">Error loading market data</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error occurred'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Market Overview</h2>
        <span className="text-sm text-gray-500">
          {sentiment?.date ? `Last updated: ${sentiment.date}` : ''}
        </span>
      </div>

      {/* Market Indices */}
      <MarketOverview indices={sentiment?.indices} />

      {/* Sentiment Score */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SentimentCard
          title="Market Sentiment"
          score={sentiment?.overall_sentiment}
          bullish={sentiment?.bullish_score}
          bearish={sentiment?.bearish_score}
          hotSectors={sentiment?.hot_sectors}
          negativeSectors={sentiment?.negative_sectors}
          indices={sentiment?.indices}
        />
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Sectors</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-green-600 mb-2">Hot Sectors</h4>
              <ul className="space-y-1">
                {sentiment?.hot_sectors?.map((sector: any, index: number) => (
                  <li key={index} className="text-sm text-gray-600">
                    {sector.name || sector}
                  </li>
                )) || <li className="text-sm text-gray-400">No data</li>}
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-medium text-red-600 mb-2">Negative Sectors</h4>
              <ul className="space-y-1">
                {sentiment?.negative_sectors?.map((sector: any, index: number) => (
                  <li key={index} className="text-sm text-gray-600">
                    {sector.name || sector}
                  </li>
                )) || <li className="text-sm text-gray-400">No data</li>}
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
