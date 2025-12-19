import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useMutation } from '@tanstack/react-query'
import {
  fetchMarketSentiment,
  refreshMarketSentiment,
  refreshCategoryData,
  fetchScrapedCategoryData,
  startStockResearch,
  CombinedMarketResponse,
  ScrapedCategoryDataResponse,
  ScrapedStockData
} from '../../services/api'
import { useResearchStore } from '../../stores/researchStore'
import MarketOverview from './MarketOverview'
import SentimentCard from './SentimentCard'
import DataSourceHealth from './DataSourceHealth'

// Categories to refresh on Dashboard
const DASHBOARD_CATEGORIES = ['news', 'top_gainers', 'top_losers', 'dashboard_sentiment'] as const

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<'traditional' | 'web-scraped' | 'both'>('both')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshStatus, setRefreshStatus] = useState<string>('')
  const hasAutoRefreshed = useRef(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addJob } = useResearchStore()

  const { data: combinedData, isLoading, error, refetch } = useQuery<CombinedMarketResponse>({
    queryKey: ['marketSentiment'],
    queryFn: fetchMarketSentiment,
  })

  // Mutation to start stock research
  const researchMutation = useMutation({
    mutationFn: (ticker: string) => startStockResearch(ticker),
    onSuccess: (data) => {
      // Add job to research store
      addJob({
        id: data.job_id,
        ticker: data.ticker,
        status: 'pending',
        progress: 0,
        currentStep: 'Initializing research...',
        createdAt: new Date(),
      })
      // Navigate to Stock Research tab
      navigate('/research')
    },
  })

  // Handler to research a stock from Top Movers
  const handleResearchStock = (ticker: string) => {
    if (ticker && ticker !== 'N/A') {
      researchMutation.mutate(ticker.toUpperCase())
    }
  }

  // Fetch category-specific scraped data (Top Gainers)
  const { data: topGainersData } = useQuery<ScrapedCategoryDataResponse>({
    queryKey: ['scrapedCategoryData', 'top_gainers'],
    queryFn: () => fetchScrapedCategoryData('top_gainers', 1),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Fetch category-specific scraped data (Top Losers)
  const { data: topLosersData } = useQuery<ScrapedCategoryDataResponse>({
    queryKey: ['scrapedCategoryData', 'top_losers'],
    queryFn: () => fetchScrapedCategoryData('top_losers', 1),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Fetch category-specific scraped data (News)
  const { data: newsData } = useQuery<ScrapedCategoryDataResponse>({
    queryKey: ['scrapedCategoryData', 'news'],
    queryFn: () => fetchScrapedCategoryData('news', 1),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Helper to format percentage change with color
  const formatChangePercent = (change: number | undefined) => {
    if (change === undefined || change === null) return { text: 'N/A', className: 'text-gray-500' }
    const isPositive = change >= 0
    return {
      text: `${isPositive ? '+' : ''}${change.toFixed(2)}%`,
      className: isPositive ? 'text-success-600' : 'text-danger-600'
    }
  }

  // Helper to determine news item data source
  const getNewsSource = (item: any): 'alpha_vantage' | 'yahoo' | 'unknown' => {
    // Alpha Vantage news has 'published_at' and 'overall_sentiment_label' fields
    if (item.published_at && item.overall_sentiment_label) return 'alpha_vantage'
    // Yahoo scraped news doesn't have 'published_at' - it's the main differentiator
    if (!item.published_at) return 'yahoo'
    return 'unknown'
  }

  // Helper to normalize sentiment to category
  const getSentimentCategory = (item: any): 'positive' | 'negative' | 'neutral' => {
    const sentiment = item.sentiment || item.overall_sentiment_label || ''
    const sentimentLower = sentiment.toLowerCase()
    if (sentimentLower.includes('bullish') || sentimentLower === 'positive') return 'positive'
    if (sentimentLower.includes('bearish') || sentimentLower === 'negative') return 'negative'
    return 'neutral'
  }

  // Helper to generate search URL for items without links
  const getNewsUrl = (item: any): string | null => {
    if (item.url && item.url !== '#') return item.url
    // Generate a Google News search URL for items without direct links
    const title = item.title || item.headline || item.name
    if (title) {
      return `https://news.google.com/search?q=${encodeURIComponent(title)}`
    }
    return null
  }

  // Helper to get source display name
  const getSourceDisplayName = (item: any): string => {
    const dataSource = getNewsSource(item)
    // For Alpha Vantage, show the actual news source (e.g., "MarketBeat")
    if (dataSource === 'alpha_vantage' && item.source) return item.source
    // For Yahoo scraped, the summary field often contains the source name
    if (dataSource === 'yahoo' && item.summary && !item.summary.includes(' ')) return item.summary
    return dataSource === 'alpha_vantage' ? 'Alpha Vantage' : dataSource === 'yahoo' ? 'Yahoo Finance' : 'Unknown'
  }

  // Process and organize news data
  const processedNews = (() => {
    if (!newsData?.data || newsData.data.length === 0) return { positive: [], negative: [], neutral: [], all: [] }

    const sources = newsData.sources || []
    const sourceCount = sources.length || 1
    const itemsPerSource = Math.ceil(30 / sourceCount)

    // Separate items by source
    const alphaVantageItems = newsData.data.filter((item: any) => getNewsSource(item) === 'alpha_vantage')
    const yahooItems = newsData.data.filter((item: any) => getNewsSource(item) === 'yahoo')

    // Take even distribution from each source
    const selectedItems: any[] = []
    const avCount = Math.min(alphaVantageItems.length, itemsPerSource)
    const yhCount = Math.min(yahooItems.length, 30 - avCount)

    selectedItems.push(...alphaVantageItems.slice(0, avCount))
    selectedItems.push(...yahooItems.slice(0, yhCount))

    // Fill remaining slots if needed
    if (selectedItems.length < 30) {
      const remaining = 30 - selectedItems.length
      const moreAv = alphaVantageItems.slice(avCount, avCount + remaining)
      selectedItems.push(...moreAv)
    }

    // Categorize by sentiment
    const positive = selectedItems.filter(item => getSentimentCategory(item) === 'positive')
    const negative = selectedItems.filter(item => getSentimentCategory(item) === 'negative')
    const neutral = selectedItems.filter(item => getSentimentCategory(item) === 'neutral')

    return { positive, negative, neutral, all: selectedItems.slice(0, 30) }
  })()

  // State for news sentiment filter
  const [newsFilter, setNewsFilter] = useState<'all' | 'positive' | 'negative' | 'neutral'>('all')

  // Function to refresh all Dashboard data sources
  const handleRefresh = async (showStatus = true) => {
    setIsRefreshing(true)
    if (showStatus) setRefreshStatus('Starting refresh...')

    try {
      // Trigger traditional market sentiment refresh
      if (showStatus) setRefreshStatus('Refreshing market sentiment...')
      await refreshMarketSentiment()

      // Trigger refresh for each Dashboard category (this scrapes web sources)
      const categoryPromises = DASHBOARD_CATEGORIES.map(async (category) => {
        try {
          if (showStatus) setRefreshStatus(`Refreshing ${category.replace('_', ' ')}...`)
          await refreshCategoryData(category)
        } catch (err) {
          console.warn(`Failed to refresh category ${category}:`, err)
        }
      })

      await Promise.all(categoryPromises)

      if (showStatus) setRefreshStatus('Waiting for data to process...')

      // Wait for background tasks to complete, then refetch all queries
      setTimeout(() => {
        refetch()
        // Invalidate category data queries to refetch fresh data
        queryClient.invalidateQueries({ queryKey: ['scrapedCategoryData'] })
        setIsRefreshing(false)
        setRefreshStatus('')
      }, 5000)
    } catch (err) {
      console.error('Failed to refresh market data:', err)
      setIsRefreshing(false)
      setRefreshStatus('')
    }
  }

  // Auto-refresh on first load
  useEffect(() => {
    if (!hasAutoRefreshed.current && !isLoading) {
      hasAutoRefreshed.current = true
      // Trigger a background refresh without blocking the UI
      // Use a small delay to let the initial data load first
      const timer = setTimeout(() => {
        handleRefresh(false) // Don't show status for auto-refresh
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [isLoading])

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
      {/* Data Source Health Status */}
      <DataSourceHealth />

      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Market overview and sentiment analysis</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Refresh Button */}
          <button
            onClick={() => handleRefresh(true)}
            disabled={isRefreshing}
            className="btn btn-primary-outline flex items-center gap-2"
            title="Refresh all data sources (including web-scraped)"
          >
            <svg
              className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {isRefreshing ? (refreshStatus || 'Refreshing...') : 'Refresh'}
          </button>

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

      {/* Top Movers - from category-specific scraped data */}
      {(topGainersData?.data?.length || topLosersData?.data?.length) ? (
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Movers</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Gainers */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-success-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-success-700">Top Gainers</h4>
                {topGainersData?.sources && topGainersData.sources.length > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-700 ml-auto">
                    {topGainersData.sources.length} source{topGainersData.sources.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                {topGainersData?.data && topGainersData.data.length > 0 ? (
                  topGainersData.data.slice(0, 10).map((stock: ScrapedStockData, index: number) => {
                    const change = formatChangePercent(stock.change_pct)
                    return (
                      <button
                        key={`gainer-${index}`}
                        onClick={() => handleResearchStock(stock.ticker || '')}
                        disabled={!stock.ticker || stock.ticker === 'N/A' || researchMutation.isPending}
                        className="w-full flex items-center justify-between p-2.5 rounded-lg bg-success-50 hover:bg-success-100 transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 text-left"
                        title={`Research ${stock.ticker}`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-xs font-bold text-success-700 bg-success-200 px-2 py-0.5 rounded">
                            {stock.ticker || 'N/A'}
                          </span>
                          <span className="text-sm text-gray-700 truncate">
                            {stock.name || stock.ticker}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          {stock.price && (
                            <span className="text-sm text-gray-600">${stock.price.toFixed(2)}</span>
                          )}
                          <span className={`text-sm font-bold ${change.className}`}>
                            {change.text}
                          </span>
                        </div>
                      </button>
                    )
                  })
                ) : (
                  <div className="text-center py-6 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">No top gainers data available</p>
                    {topGainersData?.has_configured_sources === false ? (
                      <p className="text-xs text-gray-400 mt-1">
                        No sources configured. <a href="#" onClick={(e) => { e.preventDefault(); window.location.hash = '#configuration'; }} className="text-primary-600 hover:text-primary-700 underline">Configure sources</a> in Settings.
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400 mt-1">Refresh to fetch data from configured sources</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Top Losers */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-danger-50 flex items-center justify-center">
                  <svg className="w-4 h-4 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-danger-700">Top Losers</h4>
                {topLosersData?.sources && topLosersData.sources.length > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-700 ml-auto">
                    {topLosersData.sources.length} source{topLosersData.sources.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div className="space-y-2">
                {topLosersData?.data && topLosersData.data.length > 0 ? (
                  topLosersData.data.slice(0, 10).map((stock: ScrapedStockData, index: number) => {
                    const change = formatChangePercent(stock.change_pct)
                    return (
                      <button
                        key={`loser-${index}`}
                        onClick={() => handleResearchStock(stock.ticker || '')}
                        disabled={!stock.ticker || stock.ticker === 'N/A' || researchMutation.isPending}
                        className="w-full flex items-center justify-between p-2.5 rounded-lg bg-danger-50 hover:bg-danger-100 transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 text-left"
                        title={`Research ${stock.ticker}`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-xs font-bold text-danger-700 bg-danger-200 px-2 py-0.5 rounded">
                            {stock.ticker || 'N/A'}
                          </span>
                          <span className="text-sm text-gray-700 truncate">
                            {stock.name || stock.ticker}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          {stock.price && (
                            <span className="text-sm text-gray-600">${stock.price.toFixed(2)}</span>
                          )}
                          <span className={`text-sm font-bold ${change.className}`}>
                            {change.text}
                          </span>
                        </div>
                      </button>
                    )
                  })
                ) : (
                  <div className="text-center py-6 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">No top losers data available</p>
                    {topLosersData?.has_configured_sources === false ? (
                      <p className="text-xs text-gray-400 mt-1">
                        No sources configured. <a href="#" onClick={(e) => { e.preventDefault(); window.location.hash = '#configuration'; }} className="text-primary-600 hover:text-primary-700 underline">Configure sources</a> in Settings.
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400 mt-1">Refresh to fetch data from configured sources</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

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
                  <a
                    href={webScraped.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1"
                  >
                    From {webScraped.source_name.replace(/_/g, ' ')}
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
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

          {/* News Feed Card */}
          <div className="card card-body">
            {/* Header with title and source links */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900">News Feed</h3>
                <span className="text-xs text-gray-400">
                  ({processedNews.all.length} articles)
                </span>
              </div>
              {/* Show source attribution */}
              {newsData?.sources && newsData.sources.length > 0 && (
                <div className="flex items-center gap-2">
                  {newsData.sources.map((source, idx) => (
                    <a
                      key={idx}
                      href={source.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${
                        source.source_key.includes('alpha')
                          ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                          : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                      }`}
                    >
                      {source.source_key.includes('alpha') ? 'Alpha Vantage' : 'Yahoo Finance'}
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Sentiment Filter Tabs */}
            <div className="flex items-center gap-2 mb-4 border-b border-gray-200 pb-3">
              <button
                onClick={() => setNewsFilter('all')}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  newsFilter === 'all'
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                All ({processedNews.all.length})
              </button>
              <button
                onClick={() => setNewsFilter('positive')}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                  newsFilter === 'positive'
                    ? 'bg-green-600 text-white'
                    : 'bg-green-50 text-green-700 hover:bg-green-100'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                Positive ({processedNews.positive.length})
              </button>
              <button
                onClick={() => setNewsFilter('negative')}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                  newsFilter === 'negative'
                    ? 'bg-red-600 text-white'
                    : 'bg-red-50 text-red-700 hover:bg-red-100'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
                Negative ({processedNews.negative.length})
              </button>
              <button
                onClick={() => setNewsFilter('neutral')}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                  newsFilter === 'neutral'
                    ? 'bg-gray-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
                Neutral ({processedNews.neutral.length})
              </button>
            </div>

            {/* News Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {processedNews[newsFilter].length > 0 ? (
                processedNews[newsFilter].map((item: any, index: number) => {
                  const newsUrl = getNewsUrl(item)
                  const dataSource = getNewsSource(item)
                  const sourceName = getSourceDisplayName(item)
                  const sentimentCategory = getSentimentCategory(item)
                  const isSearchUrl = newsUrl?.includes('news.google.com')

                  return (
                    <div
                      key={index}
                      className={`p-3 rounded-lg hover:shadow-md transition-all border-l-4 ${
                        sentimentCategory === 'positive'
                          ? 'bg-green-50 border-green-400'
                          : sentimentCategory === 'negative'
                          ? 'bg-red-50 border-red-400'
                          : 'bg-gray-50 border-gray-300'
                      }`}
                    >
                      {/* Title with link */}
                      <a
                        href={newsUrl || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`font-medium text-sm block mb-2 line-clamp-2 ${
                          newsUrl
                            ? 'text-primary-600 hover:text-primary-800'
                            : 'text-gray-800 cursor-default'
                        }`}
                        title={isSearchUrl ? 'Opens Google News search (no direct link available)' : 'Open article'}
                      >
                        {item.title || item.headline || item.name || 'Untitled'}
                        {isSearchUrl && (
                          <svg className="w-3 h-3 inline-block ml-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                        )}
                      </a>

                      {/* Meta info row */}
                      <div className="flex items-center text-xs gap-2 flex-wrap">
                        {/* Data source badge */}
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          dataSource === 'alpha_vantage'
                            ? 'bg-blue-100 text-blue-700'
                            : dataSource === 'yahoo'
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {dataSource === 'alpha_vantage' ? 'AV' : dataSource === 'yahoo' ? 'YF' : '?'}
                        </span>

                        {/* News source (e.g., MarketBeat, Reuters) */}
                        <span className="text-gray-600">{sourceName}</span>

                        {/* Date if available */}
                        {item.published_at && (
                          <>
                            <span className="text-gray-300">•</span>
                            <span className="text-gray-500">
                              {new Date(item.published_at.replace('T', ' ')).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </>
                        )}

                        {/* Sentiment label */}
                        <span className={`ml-auto px-1.5 py-0.5 rounded text-xs ${
                          sentimentCategory === 'positive'
                            ? 'bg-green-200 text-green-800'
                            : sentimentCategory === 'negative'
                            ? 'bg-red-200 text-red-800'
                            : 'bg-gray-200 text-gray-700'
                        }`}>
                          {sentimentCategory === 'positive' ? 'Bullish' : sentimentCategory === 'negative' ? 'Bearish' : 'Neutral'}
                        </span>
                      </div>

                      {/* Tickers if available */}
                      {item.tickers && item.tickers.length > 0 && (
                        <div className="flex items-center gap-1 mt-2 flex-wrap">
                          {item.tickers.slice(0, 3).map((ticker: string, tidx: number) => (
                            <span key={tidx} className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-mono">
                              ${ticker}
                            </span>
                          ))}
                          {item.tickers.length > 3 && (
                            <span className="text-xs text-gray-400">+{item.tickers.length - 3}</span>
                          )}
                        </div>
                      )}
                      {item.ticker_sentiment && item.ticker_sentiment.length > 0 && (
                        <div className="flex items-center gap-1 mt-2 flex-wrap">
                          {item.ticker_sentiment.slice(0, 3).map((ts: any, tidx: number) => (
                            <span key={tidx} className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-mono">
                              ${ts.ticker}
                            </span>
                          ))}
                          {item.ticker_sentiment.length > 3 && (
                            <span className="text-xs text-gray-400">+{item.ticker_sentiment.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              ) : (
                <div className="col-span-3 text-center py-6 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">
                    {newsFilter === 'all' ? 'No news available' : `No ${newsFilter} news available`}
                  </p>
                  {!newsData?.has_configured_sources && (
                    <p className="text-xs text-gray-400 mt-1">
                      Configure a "news" data source in <a href="#" onClick={(e) => { e.preventDefault(); window.location.hash = '#configuration'; }} className="text-primary-600 hover:text-primary-700 underline">Settings</a>
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
