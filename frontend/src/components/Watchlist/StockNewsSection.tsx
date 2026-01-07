import type { WatchlistNewsItem } from '../../types'

interface StockNewsSectionProps {
  news: WatchlistNewsItem[]
  ticker: string
}

export default function StockNewsSection({ news, ticker }: StockNewsSectionProps) {
  const getSentimentColor = (label: string | undefined) => {
    if (!label) return 'text-gray-500 bg-gray-100'
    const l = label.toLowerCase()
    if (l.includes('bullish') || l.includes('positive') || l === 'positive') {
      return 'text-success-700 bg-success-100'
    }
    if (l.includes('bearish') || l.includes('negative') || l === 'negative') {
      return 'text-danger-700 bg-danger-100'
    }
    return 'text-gray-600 bg-gray-100'
  }

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffHours < 24) {
        return `${diffHours}h ago`
      } else if (diffDays < 7) {
        return `${diffDays}d ago`
      } else {
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        })
      }
    } catch {
      return dateStr
    }
  }

  return (
    <div className="card card-body">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          News <span className="text-gray-500 font-normal">({news.length})</span>
        </h2>
        <span className="text-sm text-gray-500">Last 30 days</span>
      </div>

      {news.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
              />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">No recent news for {ticker}</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
          {news.map((item, index) => (
            <a
              key={index}
              href={item.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
            >
              <h4 className="font-medium text-gray-900 group-hover:text-primary-600 line-clamp-2 mb-2">
                {item.title}
              </h4>
              {item.summary && (
                <p className="text-sm text-gray-600 line-clamp-2 mb-2">{item.summary}</p>
              )}
              <div className="flex items-center gap-3 text-xs">
                {item.source && (
                  <span className="text-gray-500">{item.source}</span>
                )}
                {item.published_at && (
                  <span className="text-gray-400">{formatDate(item.published_at)}</span>
                )}
                {item.sentiment_label && (
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(
                      item.sentiment_label
                    )}`}
                  >
                    {item.sentiment_label}
                  </span>
                )}
                {item.sentiment_score !== undefined && item.sentiment_score !== null && (
                  <span className="text-gray-400">
                    ({item.sentiment_score > 0 ? '+' : ''}{item.sentiment_score.toFixed(2)})
                  </span>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
