import { useQuery } from '@tanstack/react-query'
import { fetchIndicesHistory } from '../../services/api'
import Sparkline from './Sparkline'

interface IndexData {
  close: number | null
  change_pct: number | null
}

interface MarketOverviewProps {
  indices?: {
    sp500?: IndexData
    nasdaq?: IndexData
    dow?: IndexData
  }
}

export default function MarketOverview({ indices }: MarketOverviewProps) {
  const { data: history } = useQuery({
    queryKey: ['indicesHistory'],
    queryFn: () => fetchIndicesHistory(90),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const indexData = [
    { name: 'S&P 500', key: 'sp500', data: indices?.sp500, history: history?.sp500 },
    { name: 'NASDAQ', key: 'nasdaq', data: indices?.nasdaq, history: history?.nasdaq },
    { name: 'Dow Jones', key: 'dow', data: indices?.dow, history: history?.dow },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {indexData.map((index) => (
        <div key={index.name} className="bg-white rounded-lg shadow p-6 relative overflow-hidden">
          {/* Background sparkline */}
          {index.history && index.history.length > 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Sparkline
                data={index.history}
                width={300}
                height={100}
                className="absolute right-0 bottom-0"
              />
            </div>
          )}

          {/* Content */}
          <div className="relative z-10">
            <h3 className="text-sm font-medium text-gray-500">{index.name}</h3>
            <div className="mt-2">
              <div className="flex items-baseline">
                <p className="text-2xl font-semibold text-gray-900">
                  {index.data?.close?.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }) || 'N/A'}
                </p>
                {index.data?.change_pct != null && (
                  <span
                    className={`ml-2 text-sm font-medium ${
                      index.data.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {index.data.change_pct >= 0 ? '+' : ''}
                    {index.data.change_pct.toFixed(2)}%
                  </span>
                )}
              </div>
              {index.data?.change_pct != null && (
                <p className="text-xs text-gray-400 mt-1">vs previous close</p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
