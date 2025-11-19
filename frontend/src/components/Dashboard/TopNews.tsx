interface NewsItem {
  title: string
  source?: string
  url?: string
  published_at?: string
  sentiment?: number
}

interface TopNewsProps {
  news: NewsItem[]
}

export default function TopNews({ news }: TopNewsProps) {
  if (!news || news.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Top News</h3>
        <p className="text-gray-500 text-sm">No news available</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Top News</h3>
      <div className="space-y-4">
        {news.map((item, index) => (
          <div
            key={index}
            className="border-b border-gray-200 pb-4 last:border-b-0 last:pb-0"
          >
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-800 font-medium"
            >
              {item.title}
            </a>
            <div className="flex items-center mt-1 text-sm text-gray-500">
              {item.source && <span>{item.source}</span>}
              {item.published_at && (
                <>
                  <span className="mx-2">•</span>
                  <span>{new Date(item.published_at).toLocaleDateString()}</span>
                </>
              )}
              {item.sentiment != null && (
                <>
                  <span className="mx-2">•</span>
                  <span
                    className={
                      item.sentiment >= 0.5
                        ? 'text-green-600'
                        : item.sentiment <= -0.5
                        ? 'text-red-600'
                        : 'text-gray-600'
                    }
                  >
                    {item.sentiment >= 0.5
                      ? 'Positive'
                      : item.sentiment <= -0.5
                      ? 'Negative'
                      : 'Neutral'}
                  </span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
