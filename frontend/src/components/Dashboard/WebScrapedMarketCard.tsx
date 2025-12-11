import { WebScrapedMarketDataResponse } from '../../services/api'

interface Props {
  data: WebScrapedMarketDataResponse
}

export default function WebScrapedMarketCard({ data }: Props) {
  const sentimentColor = (score?: number) => {
    if (!score) return 'text-gray-500'
    if (score >= 0.6) return 'text-success-600'
    if (score <= 0.4) return 'text-danger-600'
    return 'text-warning-600'
  }

  const sentimentLabel = (score?: number) => {
    if (!score) return 'Neutral'
    if (score >= 0.7) return 'Very Bullish'
    if (score >= 0.6) return 'Bullish'
    if (score <= 0.3) return 'Very Bearish'
    if (score <= 0.4) return 'Bearish'
    return 'Neutral'
  }

  return (
    <div className="space-y-6">
      {/* Market Summary */}
      <div className="card card-body">
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Market Summary</h3>
          <a
            href={data.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            View Source
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>

        {data.market_summary && (
          <p className="text-gray-700 leading-relaxed">{data.market_summary}</p>
        )}

        {data.confidence_score !== undefined && data.confidence_score !== null && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Data Confidence:</span>
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden max-w-xs">
                <div
                  className="h-full bg-primary-500"
                  style={{ width: `${data.confidence_score * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium text-gray-700">
                {(data.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Sentiment & Sectors Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Scores */}
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Analysis</h3>

          <div className="space-y-4">
            {/* Overall Sentiment */}
            {data.overall_sentiment !== undefined && data.overall_sentiment !== null && (
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-600">Overall</span>
                  <span className={`text-lg font-bold ${sentimentColor(data.overall_sentiment)}`}>
                    {sentimentLabel(data.overall_sentiment)}
                  </span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-danger-500 via-warning-400 to-success-500"
                    style={{ width: `${(data.overall_sentiment || 0.5) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Bullish Score */}
            {data.bullish_score !== undefined && data.bullish_score !== null && (
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-gray-600">Bullish</span>
                  <span className="text-sm font-medium text-success-600">
                    {(data.bullish_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-success-500"
                    style={{ width: `${data.bullish_score * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Bearish Score */}
            {data.bearish_score !== undefined && data.bearish_score !== null && (
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-gray-600">Bearish</span>
                  <span className="text-sm font-medium text-danger-600">
                    {(data.bearish_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-danger-500"
                    style={{ width: `${data.bearish_score * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sectors */}
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Analysis</h3>
          <div className="grid grid-cols-2 gap-6">
            {/* Trending Sectors */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-success-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-success-700">Trending</h4>
              </div>
              <ul className="space-y-2">
                {data.trending_sectors && data.trending_sectors.length > 0 ? (
                  data.trending_sectors.map((sector, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-success-500" />
                      {typeof sector === 'string' ? sector : sector.name}
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-gray-400">No data</li>
                )}
              </ul>
            </div>

            {/* Declining Sectors */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-danger-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-danger-700">Declining</h4>
              </div>
              <ul className="space-y-2">
                {data.declining_sectors && data.declining_sectors.length > 0 ? (
                  data.declining_sectors.map((sector, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-danger-500" />
                      {typeof sector === 'string' ? sector : sector.name}
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-gray-400">No data</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Market Themes & Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Themes */}
        {data.market_themes && data.market_themes.length > 0 && (
          <div className="card card-body">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Market Themes</h3>
            <ul className="space-y-2">
              {data.market_themes.map((theme, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-1.5" />
                  {theme}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key Events */}
        {data.key_events && data.key_events.length > 0 && (
          <div className="card card-body">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Events</h3>
            <ul className="space-y-2">
              {data.key_events.map((event, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-warning-500 mt-1.5" />
                  {event}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Metadata Footer */}
      <div className="card card-body bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            {data.scraping_model && (
              <span>Extraction: {data.scraping_model}</span>
            )}
            {data.analysis_model && (
              <span>Analysis: {data.analysis_model}</span>
            )}
          </div>
          <span>Updated: {data.date}</span>
        </div>
      </div>
    </div>
  )
}
