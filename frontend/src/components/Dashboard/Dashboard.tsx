import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMarketSentiment, CombinedMarketResponse } from '../../services/api'
import MarketOverview from './MarketOverview'
import SentimentCard from './SentimentCard'
import WebScrapedMarketCard from './WebScrapedMarketCard'

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<'traditional' | 'web-scraped' | 'both'>('both')

  const { data: combinedData, isLoading, error } = useQuery<CombinedMarketResponse>({
    queryKey: ['marketSentiment'],
    queryFn: fetchMarketSentiment,
  })

  const sentiment = combinedData?.traditional
  const webScraped = combinedData?.web_scraped

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
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="inline-flex rounded-lg border border-gray-200 p-1">
            <button
              onClick={() => setViewMode('traditional')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'traditional'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Traditional
            </button>
            <button
              onClick={() => setViewMode('web-scraped')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'web-scraped'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              disabled={!webScraped}
            >
              Web Scraped
            </button>
            <button
              onClick={() => setViewMode('both')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'both'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
              disabled={!webScraped}
            >
              Both
            </button>
          </div>
          {sentiment?.date && (
            <span className="badge badge-neutral">
              Updated: {sentiment.date}
            </span>
          )}
        </div>
      </div>

      {/* Market Indices - always show traditional */}
      <MarketOverview indices={sentiment?.indices} />

      {/* Traditional Analysis */}
      {(viewMode === 'traditional' || viewMode === 'both') && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Traditional Analysis
            <span className="text-sm font-normal text-gray-500 ml-2">
              (Yahoo Finance + Alpha Vantage + Ollama)
            </span>
          </h2>

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

        {/* Combined Sectors Card - Traditional + Web-Scraped */}
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Analysis</h3>

          {/* Combined sectors in heat map style */}
          <div className="space-y-2">
            {/* Trending/Hot Sectors */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-success-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-success-700">Trending Sectors</h4>
              </div>
              <div className="space-y-1.5">
                {/* Traditional hot sectors */}
                {sentiment?.hot_sectors?.map((sector: any, index: number) => (
                  <div key={`trad-${index}`} className="flex items-center justify-between p-2.5 rounded-lg bg-success-50 hover:bg-success-100 transition-colors">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-success-500" />
                      <span className="text-sm font-medium text-gray-800">{sector.name || sector}</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white text-success-700 border border-success-200">
                      Traditional
                    </span>
                  </div>
                ))}
                {/* Web-scraped trending sectors */}
                {webScraped?.trending_sectors?.map((sector: any, index: number) => (
                  <div key={`web-${index}`} className="flex items-center justify-between p-2.5 rounded-lg bg-success-50 hover:bg-success-100 transition-colors border-l-2 border-l-primary-500">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                      <span className="text-sm font-medium text-gray-800">{sector.name || sector}</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white text-primary-700 border border-primary-200">
                      Web-Scraped
                    </span>
                  </div>
                ))}
                {(!sentiment?.hot_sectors?.length && !webScraped?.trending_sectors?.length) && (
                  <p className="text-sm text-gray-400 p-2">No trending sectors</p>
                )}
              </div>
            </div>

            {/* Declining/Negative Sectors */}
            <div className="mt-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-danger-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-danger-700">Declining Sectors</h4>
              </div>
              <div className="space-y-1.5">
                {/* Traditional negative sectors */}
                {sentiment?.negative_sectors?.map((sector: any, index: number) => (
                  <div key={`trad-neg-${index}`} className="flex items-center justify-between p-2.5 rounded-lg bg-danger-50 hover:bg-danger-100 transition-colors">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-danger-500" />
                      <span className="text-sm font-medium text-gray-800">{sector.name || sector}</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white text-danger-700 border border-danger-200">
                      Traditional
                    </span>
                  </div>
                ))}
                {/* Web-scraped declining sectors */}
                {webScraped?.declining_sectors?.map((sector: any, index: number) => (
                  <div key={`web-neg-${index}`} className="flex items-center justify-between p-2.5 rounded-lg bg-danger-50 hover:bg-danger-100 transition-colors border-l-2 border-l-primary-500">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                      <span className="text-sm font-medium text-gray-800">{sector.name || sector}</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white text-primary-700 border border-primary-200">
                      Web-Scraped
                    </span>
                  </div>
                ))}
                {(!sentiment?.negative_sectors?.length && !webScraped?.declining_sectors?.length) && (
                  <p className="text-sm text-gray-400 p-2">No declining sectors</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

          {/* Market Summary with Bullet Points (from web-scraped data) */}
          {webScraped && (
            <div className="card card-body bg-gradient-to-br from-primary-50 to-white border-primary-200">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-8 h-8 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">Market Summary</h3>
                  <p className="text-xs text-primary-600 font-medium">From {webScraped.source_name.replace(/_/g, ' ')}</p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Summary Text */}
                <div className="bg-white rounded-lg p-4 border border-primary-100">
                  <p className="text-sm text-gray-700 leading-relaxed">{webScraped.market_summary}</p>
                </div>

                {/* Key Themes & Events in columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Market Themes */}
                  {webScraped.market_themes && webScraped.market_themes.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-primary-100">
                      <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        Market Themes
                      </h4>
                      <ul className="space-y-1.5">
                        {webScraped.market_themes.map((theme, index) => (
                          <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                            <span className="text-primary-500 mt-1">•</span>
                            <span>{theme}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Key Events */}
                  {webScraped.key_events && webScraped.key_events.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-primary-100">
                      <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        Key Events
                      </h4>
                      <ul className="space-y-1.5">
                        {webScraped.key_events.map((event, index) => (
                          <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                            <span className="text-primary-500 mt-1">•</span>
                            <span>{event}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Split News Card - Traditional + Web-Scraped Summary */}
          <div className="card card-body">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">News & Market Insights</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 divide-x-0 lg:divide-x divide-gray-200">
              {/* Left: Traditional News */}
              <div className="lg:pr-6">
                <div className="flex items-center gap-2 mb-4">
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                  </svg>
                  <h4 className="font-semibold text-gray-900">Traditional News Feed</h4>
                </div>
                <div className="space-y-3">
                  {sentiment?.top_news && sentiment.top_news.length > 0 ? (
                    sentiment.top_news.slice(0, 5).map((item: any, index: number) => (
                      <div key={index} className="pb-3 border-b border-gray-100 last:border-b-0 last:pb-0">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-600 hover:text-primary-800 font-medium text-sm block mb-1 line-clamp-2"
                        >
                          {item.title}
                        </a>
                        <div className="flex items-center text-xs text-gray-500 gap-2">
                          {item.source && <span>{item.source}</span>}
                          {item.published_at && (
                            <>
                              <span>•</span>
                              <span>{new Date(item.published_at).toLocaleDateString()}</span>
                            </>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-400">No news available</p>
                  )}
                </div>
              </div>

              {/* Right: Web-Scraped Market Summary */}
              <div className="lg:pl-6">
                <div className="flex items-center gap-2 mb-4">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  <h4 className="font-semibold text-gray-900">Web-Scraped Summary</h4>
                  {webScraped && (
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-700">
                      {webScraped.source_name.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
                {webScraped ? (
                  <div className="space-y-3">
                    {/* Market Summary */}
                    <div className="bg-primary-50 rounded-lg p-3 border border-primary-100">
                      <p className="text-sm text-gray-700 leading-relaxed">{webScraped.market_summary}</p>
                    </div>

                    {/* Sentiment Scores */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-600">Overall Sentiment</span>
                        <span className="text-xs font-semibold text-gray-900">
                          {((webScraped.overall_sentiment || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-success-500 to-success-600 h-2 rounded-full transition-all"
                          style={{ width: `${(webScraped.overall_sentiment || 0) * 100}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3 mt-3">
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-success-700">Bullish</span>
                            <span className="text-xs font-semibold text-success-900">
                              {((webScraped.bullish_score || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-success-500 h-1.5 rounded-full"
                              style={{ width: `${(webScraped.bullish_score || 0) * 100}%` }}
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-danger-700">Bearish</span>
                            <span className="text-xs font-semibold text-danger-900">
                              {((webScraped.bearish_score || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-danger-500 h-1.5 rounded-full"
                              style={{ width: `${(webScraped.bearish_score || 0) * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Source Link */}
                    <a
                      href={webScraped.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-600 hover:text-primary-800 flex items-center gap-1"
                    >
                      <span>View source</span>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-500 mb-2">No web-scraped data available</p>
                    <p className="text-xs text-gray-400">Trigger a refresh to fetch market data from web sources</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Web-Scraped Analysis */}
      {webScraped && (viewMode === 'web-scraped' || viewMode === 'both') && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Web-Scraped Analysis
            <span className="text-sm font-normal text-gray-500 ml-2">
              ({webScraped.source_name.replace(/_/g, ' ')})
            </span>
          </h2>

          <WebScrapedMarketCard data={webScraped} />
        </div>
      )}
    </div>
  )
}
