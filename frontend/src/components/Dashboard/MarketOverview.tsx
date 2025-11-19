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
  const indexData = [
    { name: 'S&P 500', data: indices?.sp500 },
    { name: 'NASDAQ', data: indices?.nasdaq },
    { name: 'Dow Jones', data: indices?.dow },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {indexData.map((index) => (
        <div key={index.name} className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">{index.name}</h3>
          <div className="mt-2 flex items-baseline">
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
                {(index.data.change_pct * 100).toFixed(2)}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
