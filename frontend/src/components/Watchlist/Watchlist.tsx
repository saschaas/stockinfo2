import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchWatchlist, addToWatchlist, removeFromWatchlist, fetchWatchlistNews, startStockResearch, fetchConfigSettings, updateWatchlistOrder } from '../../services/api'
import type { WatchlistSortBy, WatchlistSortDirection } from '../../services/api'
import type { WatchlistNewsItem, WatchlistItem } from '../../types'

// Market hours utilities (US Eastern Time)
const MARKET_OPEN_HOUR = 9
const MARKET_OPEN_MINUTE = 30
const MARKET_CLOSE_HOUR = 16
const MARKET_CLOSE_MINUTE = 0

function getEasternTimeComponents(): { day: number; hour: number; minute: number } {
  const now = new Date()

  // Get day of week in Eastern Time
  const dayFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short'
  })
  const dayStr = dayFormatter.format(now)
  const dayIndex = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(dayStr)

  // Get hour and minute in Eastern Time
  const timeFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false
  })
  const timeParts = timeFormatter.formatToParts(now)
  const hour = parseInt(timeParts.find(p => p.type === 'hour')?.value || '0')
  const minute = parseInt(timeParts.find(p => p.type === 'minute')?.value || '0')

  return { day: dayIndex, hour, minute }
}

function isMarketOpen(): boolean {
  const { day, hour, minute } = getEasternTimeComponents()

  // Weekend check (0 = Sunday, 6 = Saturday)
  if (day === 0 || day === 6) return false

  // Convert to minutes since midnight for easier comparison
  const currentMinutes = hour * 60 + minute
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

  return currentMinutes >= openMinutes && currentMinutes < closeMinutes
}

function getMillisecondsUntilMarketOpen(): number {
  const { day, hour, minute } = getEasternTimeComponents()

  const currentMinutes = hour * 60 + minute
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

  let minutesUntilOpen = 0

  if (day === 0) {
    // Sunday - wait until Monday 9:30 AM ET
    minutesUntilOpen = (24 * 60 - currentMinutes) + openMinutes
  } else if (day === 6) {
    // Saturday - wait until Monday 9:30 AM ET (2 days)
    minutesUntilOpen = (24 * 60 - currentMinutes) + (24 * 60) + openMinutes
  } else if (currentMinutes >= closeMinutes) {
    // After market close on weekday
    if (day === 5) {
      // Friday after close - wait until Monday 9:30 AM ET (3 days)
      minutesUntilOpen = (24 * 60 - currentMinutes) + (24 * 60 * 2) + openMinutes
    } else {
      // Other weekday after close - wait until tomorrow 9:30 AM ET
      minutesUntilOpen = (24 * 60 - currentMinutes) + openMinutes
    }
  } else if (currentMinutes < openMinutes) {
    // Before market open on weekday - wait until 9:30 AM ET today
    minutesUntilOpen = openMinutes - currentMinutes
  } else {
    // Market is currently open
    minutesUntilOpen = 0
  }

  return minutesUntilOpen * 60 * 1000
}

function formatCountdown(ms: number): string {
  if (ms <= 0) return '00:00:00'

  const totalSeconds = Math.floor(ms / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

export default function Watchlist() {
  const [newTicker, setNewTicker] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [addSuccess, setAddSuccess] = useState<string | null>(null)
  const [newsModal, setNewsModal] = useState<{ itemId: number; ticker: string } | null>(null)
  const [newsItems, setNewsItems] = useState<WatchlistNewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  // Auto-refresh state
  const [isPaused, setIsPaused] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [marketOpen, setMarketOpen] = useState(isMarketOpen())
  const [countdown, setCountdown] = useState<string>('')

  // Stock selection state for batch analysis
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set())
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const navigate = useNavigate()
  const MAX_SELECTION = 5

  // Sorting state
  const [sortBy, setSortBy] = useState<WatchlistSortBy>('custom')
  const [sortDirection, setSortDirection] = useState<WatchlistSortDirection>('asc')

  // Drag-and-drop state
  const [draggedItem, setDraggedItem] = useState<WatchlistItem | null>(null)
  const [dragOverId, setDragOverId] = useState<number | null>(null)

  const queryClient = useQueryClient()

  // Fetch config to get refresh interval
  const { data: configData } = useQuery({
    queryKey: ['configSettings'],
    queryFn: fetchConfigSettings,
  })

  const refreshIntervalMinutes = configData?.settings?.display_preferences?.watchlist_refresh_interval ?? 3

  // Update market status and countdown every second
  useEffect(() => {
    const updateMarketStatus = () => {
      const isOpen = isMarketOpen()
      setMarketOpen(isOpen)

      if (!isOpen) {
        const msUntilOpen = getMillisecondsUntilMarketOpen()
        setCountdown(formatCountdown(msUntilOpen))
      } else {
        setCountdown('')
      }
    }

    updateMarketStatus()
    const interval = setInterval(updateMarketStatus, 1000)

    return () => clearInterval(interval)
  }, [])

  // Calculate refetch interval based on market status and pause state
  const refetchInterval = useMemo(() => {
    if (isPaused || !marketOpen) return false
    return refreshIntervalMinutes * 60 * 1000
  }, [isPaused, marketOpen, refreshIntervalMinutes])

  // Phase 1: Fetch watchlist without news (fast initial load)
  const { data: watchlistBasic, isLoading, error, dataUpdatedAt } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => fetchWatchlist('custom', 'asc', false), // include_news=false
    refetchInterval,
  })

  // Phase 2: Fetch news data in background after initial load
  const { data: watchlistWithNews, isFetching: isLoadingNews } = useQuery({
    queryKey: ['watchlist-news'],
    queryFn: () => fetchWatchlist('custom', 'asc', true), // include_news=true
    enabled: !!watchlistBasic && watchlistBasic.items.length > 0, // Only fetch after basic data loaded
    refetchInterval: refetchInterval || false, // Same refresh interval
    staleTime: 60000, // Consider news data fresh for 1 minute
  })

  // Merge basic data with news data - news data takes priority when available
  const watchlistData = useMemo(() => {
    if (!watchlistBasic) return undefined
    if (!watchlistWithNews) return watchlistBasic

    // Create a map of news data by item id
    const newsMap = new Map(
      watchlistWithNews.items.map(item => [item.id, {
        news_count: item.news_count,
        recent_news_count: item.recent_news_count,
        news_sentiment: item.news_sentiment,
      }])
    )

    // Merge news data into basic data
    return {
      ...watchlistBasic,
      items: watchlistBasic.items.map(item => {
        const newsData = newsMap.get(item.id)
        if (newsData) {
          return { ...item, ...newsData }
        }
        return item
      })
    }
  }, [watchlistBasic, watchlistWithNews])

  // Sort items client-side based on selected sort mode
  const watchlist = useMemo(() => {
    if (!watchlistData) return undefined

    const sortedItems = [...watchlistData.items]

    if (sortBy === 'change') {
      sortedItems.sort((a, b) => {
        const aChange = a.change_pct ?? 0
        const bChange = b.change_pct ?? 0
        return sortDirection === 'desc' ? bChange - aChange : aChange - bChange
      })
    } else if (sortBy === 'custom' && sortDirection === 'desc') {
      sortedItems.reverse()
    }
    // For 'custom' with 'asc', items are already in correct order from API

    return {
      ...watchlistData,
      items: sortedItems
    }
  }, [watchlistData, sortBy, sortDirection])

  // Mutation for updating sort order
  const orderMutation = useMutation({
    mutationFn: updateWatchlistOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist-news'] })
    },
  })

  // Track last update time
  useEffect(() => {
    if (dataUpdatedAt) {
      setLastUpdate(new Date(dataUpdatedAt))
    }
  }, [dataUpdatedAt])

  // Mutation for adding to watchlist
  const addMutation = useMutation({
    mutationFn: addToWatchlist,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist-news'] })
      setNewTicker('')
      setAddError(null)
      setAddSuccess(`${data.ticker} added to watchlist!`)
      setTimeout(() => setAddSuccess(null), 3000)
    },
    onError: (error: any) => {
      setAddError(error.response?.data?.detail || 'Failed to add stock')
      setAddSuccess(null)
    },
  })

  // Mutation for removing from watchlist
  const removeMutation = useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist-news'] })
    },
  })

  // Handle adding a new stock
  const handleAddStock = (e: React.FormEvent) => {
    e.preventDefault()
    if (newTicker.trim()) {
      setAddError(null)
      addMutation.mutate(newTicker.trim().toUpperCase())
    }
  }

  // Handle news modal
  const [newsDaysFetched, setNewsDaysFetched] = useState<number>(30)

  const openNewsModal = async (itemId: number, ticker: string) => {
    setNewsModal({ itemId, ticker })
    setNewsLoading(true)
    try {
      const response = await fetchWatchlistNews(itemId, 50, newsHistoryDays)
      setNewsItems(response.news)
      setNewsDaysFetched(response.days_fetched)
    } catch (error) {
      console.error('Failed to fetch news:', error)
      setNewsItems([])
    } finally {
      setNewsLoading(false)
    }
  }

  const closeNewsModal = () => {
    setNewsModal(null)
    setNewsItems([])
  }

  // Stock selection helper functions
  const toggleTickerSelection = (ticker: string) => {
    setSelectedTickers(prev => {
      const newSet = new Set(prev)
      if (newSet.has(ticker)) {
        newSet.delete(ticker)
      } else if (newSet.size < MAX_SELECTION) {
        newSet.add(ticker)
      }
      return newSet
    })
  }

  const clearSelection = () => setSelectedTickers(new Set())

  const handleBatchAnalysis = async () => {
    if (selectedTickers.size === 0) return

    setIsAnalyzing(true)
    const tickers = Array.from(selectedTickers)

    try {
      const results = []
      const errors = []

      for (const ticker of tickers) {
        try {
          const response = await startStockResearch(ticker, {
            include_peers: true,
            include_technical: true,
            include_ai_analysis: true,
          })
          results.push({ ticker, jobId: response.job_id })
        } catch (error: any) {
          console.error(`Failed to start research for ${ticker}:`, error)
          errors.push({ ticker, error: error.response?.data?.detail || error.message })
        }
      }

      navigate('/research', {
        state: {
          fromWatchlist: true,
          batchJobs: results,
          errors: errors,
        }
      })

      clearSelection()
    } catch (error) {
      console.error('Batch analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Get indicator colors based on aggregated news sentiment (for the badge button)
  const getNewsSentimentIndicatorStyle = (sentiment: string | undefined) => {
    switch (sentiment) {
      case 'bullish':
        return 'bg-success-100 text-success-700 hover:bg-success-200 border border-success-300'
      case 'somewhat_bullish':
        return 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200'
      case 'somewhat_bearish':
        return 'bg-orange-50 text-orange-600 hover:bg-orange-100 border border-orange-200'
      case 'bearish':
        return 'bg-danger-50 text-danger-700 hover:bg-danger-100 border border-danger-300'
      default: // 'neutral' or undefined
        return 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
    }
  }

  // Drag-and-drop handlers for custom ordering
  const handleDragStart = useCallback((e: React.DragEvent<HTMLTableRowElement>, item: WatchlistItem) => {
    if (sortBy !== 'custom') return
    setDraggedItem(item)
    e.dataTransfer.effectAllowed = 'move'
    // Add some visual feedback
    if (e.currentTarget) {
      e.currentTarget.style.opacity = '0.5'
    }
  }, [sortBy])

  const handleDragEnd = useCallback((e: React.DragEvent<HTMLTableRowElement>) => {
    setDraggedItem(null)
    setDragOverId(null)
    if (e.currentTarget) {
      e.currentTarget.style.opacity = '1'
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLTableRowElement>, itemId: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverId(itemId)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOverId(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent<HTMLTableRowElement>, targetItem: WatchlistItem) => {
    e.preventDefault()
    setDragOverId(null)

    if (!draggedItem || draggedItem.id === targetItem.id || !watchlistData?.items) return

    // Calculate new order using the base data (not the sorted view)
    const items = [...watchlistData.items]
    const draggedIndex = items.findIndex(i => i.id === draggedItem.id)
    const targetIndex = items.findIndex(i => i.id === targetItem.id)

    if (draggedIndex === -1 || targetIndex === -1) return

    // Remove dragged item and insert at target position
    const [removed] = items.splice(draggedIndex, 1)
    items.splice(targetIndex, 0, removed)

    // Create new order update with consecutive sort_order values
    const orderUpdate = items.map((item, index) => ({
      id: item.id,
      sort_order: index
    }))

    // Optimistically update the cache
    queryClient.setQueryData(['watchlist'], {
      ...watchlistData,
      items: items.map((item, index) => ({ ...item, sort_order: index }))
    })

    // Save to backend
    orderMutation.mutate({ items: orderUpdate })
  }, [draggedItem, watchlistData, queryClient, orderMutation])

  // Toggle sort direction for change column
  const toggleChangeSorting = useCallback(() => {
    if (sortBy !== 'change') {
      setSortBy('change')
      setSortDirection('desc') // Default to descending for change (highest gains first)
    } else {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    }
  }, [sortBy])

  // Switch to custom ordering
  const switchToCustomOrder = useCallback(() => {
    setSortBy('custom')
    setSortDirection('asc')
  }, [])

  // Get news history days from config
  const newsHistoryDays = configData?.settings?.display_preferences?.news_history_days ?? 30

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
          <p className="text-gray-500 text-sm mt-1">Monitor your stocks with real-time prices and news</p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          {/* Market Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
            marketOpen ? 'bg-success-50 border border-success-200' : 'bg-gray-100 border border-gray-200'
          }`}>
            <div className={`w-2 h-2 rounded-full ${marketOpen ? 'bg-success-500 animate-pulse' : 'bg-gray-400'}`} />
            <span className={`text-sm font-medium ${marketOpen ? 'text-success-700' : 'text-gray-600'}`}>
              {marketOpen ? 'Market Open' : 'Market Closed'}
            </span>
            {!marketOpen && countdown && (
              <span className="text-xs text-gray-500">
                Opens in {countdown}
              </span>
            )}
          </div>

          {/* Last Update Time */}
          {lastUpdate && (
            <div className="text-sm text-gray-500">
              Last update: {lastUpdate.toLocaleTimeString()}
            </div>
          )}

          {/* Auto-Refresh Status */}
          {marketOpen && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span>Auto-refresh: {refreshIntervalMinutes} min</span>
            </div>
          )}

          {/* Pause/Resume Button */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
              isPaused
                ? 'bg-warning-50 border border-warning-200 text-warning-700 hover:bg-warning-100'
                : 'bg-primary-50 border border-primary-200 text-primary-700 hover:bg-primary-100'
            }`}
          >
            {isPaused ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Resume
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Pause
              </>
            )}
          </button>

          {/* Manual Refresh Button */}
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['watchlist'] })
              queryClient.invalidateQueries({ queryKey: ['watchlist-news'] })
            }}
            className="btn-secondary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Now
          </button>
        </div>
      </div>

      {/* News Loading Indicator */}
      {isLoadingNews && watchlistBasic && watchlistBasic.items.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-blue-500" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm text-blue-700">
            Loading news data in background... (this may take up to {Math.ceil(watchlistBasic.items.length * 2.5)} seconds)
          </span>
        </div>
      )}

      {/* Paused Banner */}
      {isPaused && (
        <div className="bg-warning-50 border border-warning-200 rounded-lg p-3 flex items-center gap-3">
          <svg className="w-5 h-5 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm text-warning-700">
            Auto-refresh is paused. Click "Resume" to enable automatic price updates.
          </span>
        </div>
      )}

      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Panel - Add Stock Form */}
        <div className="lg:col-span-1 space-y-4">
          <div className="card card-body">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Stock</h2>
            <form onSubmit={handleAddStock} className="space-y-3">
              <div>
                <input
                  type="text"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                  placeholder="Enter ticker (e.g., AAPL)"
                  className="input w-full"
                  maxLength={10}
                />
              </div>
              <button
                type="submit"
                disabled={!newTicker.trim() || addMutation.isPending}
                className="btn-primary w-full"
              >
                {addMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Adding...
                  </span>
                ) : 'Add to Watchlist'}
              </button>
            </form>

            {addError && (
              <div className="mt-3 p-3 bg-danger-50 border border-danger-100 rounded-lg">
                <p className="text-danger-700 text-sm">{addError}</p>
              </div>
            )}

            {addSuccess && (
              <div className="mt-3 p-3 bg-success-50 border border-success-100 rounded-lg">
                <p className="text-success-700 text-sm">{addSuccess}</p>
              </div>
            )}
          </div>

          {/* Stock List */}
          <div className="card card-body">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              My Watchlist ({watchlist?.total || 0})
            </h2>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="animate-spin h-8 w-8 text-primary-500" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            ) : error ? (
              <div className="text-danger-600 text-sm">Failed to load watchlist</div>
            ) : watchlist?.items.length === 0 ? (
              <div className="text-gray-500 text-sm text-center py-4">
                No stocks in watchlist yet. Add one above!
              </div>
            ) : (
              <div className="space-y-2">
                {watchlist?.items.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                      selectedTickers.has(item.ticker)
                        ? 'border-primary-300 bg-primary-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <button
                      onClick={() => toggleTickerSelection(item.ticker)}
                      className="flex-1 text-left"
                    >
                      <span className="font-semibold text-gray-900">{item.ticker}</span>
                      {item.company_name && (
                        <span className="text-gray-500 text-sm ml-2 truncate">{item.company_name}</span>
                      )}
                    </button>
                    <button
                      onClick={() => removeMutation.mutate(item.id)}
                      className="p-1 text-gray-400 hover:text-danger-500 transition-colors"
                      title="Remove from watchlist"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Stock Details */}
        <div className="lg:col-span-2">
          <div className="card card-body">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Stock Details</h2>
              {/* Sorting Controls */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Sort:</span>
                <button
                  onClick={switchToCustomOrder}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    sortBy === 'custom'
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                  }`}
                >
                  Custom
                </button>
                <button
                  onClick={toggleChangeSorting}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
                    sortBy === 'change'
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                  }`}
                >
                  Change
                  {sortBy === 'change' && (
                    <svg className={`w-4 h-4 transition-transform ${sortDirection === 'desc' ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Custom Order Info */}
            {sortBy === 'custom' && watchlist && watchlist.items.length > 0 && (
              <div className="mb-4 p-2 bg-blue-50 border border-blue-100 rounded-lg">
                <p className="text-sm text-blue-700 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Drag and drop rows to reorder your watchlist
                </p>
              </div>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="animate-spin h-8 w-8 text-primary-500" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            ) : watchlist?.items.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-50 flex items-center justify-center">
                  <svg className="w-8 h-8 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Stocks to Monitor</h3>
                <p className="text-gray-500">Add stocks to your watchlist to see prices and news</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="table-header">
                      {sortBy === 'custom' && <th className="text-center py-3 px-2 w-8"></th>}
                      <th className="text-left py-3 px-4">Ticker</th>
                      <th className="text-left py-3 px-4">Company</th>
                      <th className="text-center py-3 px-4">Momentum</th>
                      <th className="text-right py-3 px-4">Price</th>
                      <th className="text-right py-3 px-4">Change</th>
                      <th className="text-center py-3 px-4">News</th>
                      <th className="text-center py-3 px-4">Select</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist?.items.map((item) => (
                      <tr
                        key={item.id}
                        className={`table-row border-b border-gray-100 ${
                          sortBy === 'custom' ? 'cursor-grab active:cursor-grabbing' : ''
                        } ${dragOverId === item.id ? 'bg-primary-50 border-primary-300' : ''}`}
                        draggable={sortBy === 'custom'}
                        onDragStart={(e) => handleDragStart(e, item)}
                        onDragEnd={handleDragEnd}
                        onDragOver={(e) => handleDragOver(e, item.id)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, item)}
                      >
                        {sortBy === 'custom' && (
                          <td className="py-4 px-2 text-center">
                            <div className="text-gray-400 hover:text-gray-600">
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
                              </svg>
                            </div>
                          </td>
                        )}
                        <td className="py-4 px-4">
                          <Link
                            to={`/watchlist/${item.ticker}`}
                            className="font-semibold text-primary-600 hover:text-primary-800 hover:underline flex items-center gap-2"
                          >
                            {item.ticker}
                            {item.has_triggered_alert && (
                              <span className="w-2 h-2 rounded-full bg-warning-500 animate-pulse" title="Alert triggered" />
                            )}
                          </Link>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-gray-600 truncate max-w-[200px] block">
                            {item.company_name || '-'}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {item.has_golden_cross && (
                              <span
                                className="px-1.5 py-0.5 text-xs font-semibold rounded bg-success-100 text-success-700 border border-success-200"
                                title="Golden Cross (SMA 50 > SMA 200)"
                              >
                                GC
                              </span>
                            )}
                            {item.is_bullish_trend && (
                              <span
                                className="flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-semibold rounded bg-success-100 text-success-700 border border-success-200"
                                title="Bullish Trend (Price > SMA 20 & SMA 50)"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                </svg>
                              </span>
                            )}
                            {!item.has_golden_cross && !item.is_bullish_trend && (
                              <span className="text-gray-400 text-xs">-</span>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right">
                          {item.current_price ? (
                            <span className="font-medium text-gray-900">
                              ${item.current_price.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-4 px-4 text-right">
                          {item.change_pct !== undefined && item.change_pct !== null ? (
                            <div className="flex flex-col items-end">
                              <span className={`font-medium ${item.change_pct >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                                {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                              </span>
                              {item.change_amount !== undefined && (
                                <span className={`text-xs ${item.change_pct >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
                                  {item.change_amount >= 0 ? '+' : ''}${item.change_amount.toFixed(2)}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-4 px-4 text-center">
                          <button
                            onClick={() => openNewsModal(item.id, item.ticker)}
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full transition-colors ${getNewsSentimentIndicatorStyle(item.news_sentiment)}`}
                            title={`${item.recent_news_count} recent news (today/yesterday), ${item.news_count} total - Sentiment: ${item.news_sentiment || 'neutral'}`}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                            </svg>
                            <span className="text-sm font-medium">{item.recent_news_count}</span>
                          </button>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <input
                            type="checkbox"
                            checked={selectedTickers.has(item.ticker)}
                            onChange={() => toggleTickerSelection(item.ticker)}
                            className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Selection Bar */}
          {selectedTickers.size > 0 && (
            <div className="mt-4 card card-body bg-gradient-to-r from-primary-50 to-blue-50">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-gray-700">Selected:</span>
                  {Array.from(selectedTickers).map(ticker => (
                    <span
                      key={ticker}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white border border-primary-200 text-primary-700 text-sm font-medium"
                    >
                      {ticker}
                      <button
                        onClick={() => toggleTickerSelection(ticker)}
                        className="hover:text-danger-500"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={clearSelection}
                    className="text-sm text-gray-600 hover:text-gray-800"
                  >
                    Clear All
                  </button>
                  <button
                    onClick={handleBatchAnalysis}
                    disabled={isAnalyzing}
                    className="btn-primary"
                  >
                    {isAnalyzing ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Analyzing...
                      </span>
                    ) : `Analyze ${selectedTickers.size} Stock${selectedTickers.size > 1 ? 's' : ''}`}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* News Modal */}
      {newsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  News for {newsModal.ticker}
                </h3>
                <p className="text-sm text-gray-500">
                  Showing news from the past {newsDaysFetched} days (sorted by latest)
                </p>
              </div>
              <button
                onClick={closeNewsModal}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {newsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <svg className="animate-spin h-8 w-8 text-primary-500" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
              ) : newsItems.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No news articles found in the past {newsDaysFetched} days
                </div>
              ) : (
                <div className="space-y-4">
                  {newsItems.map((news, index) => {
                    // Format the date nicely
                    const formatNewsDate = (dateStr: string | undefined) => {
                      if (!dateStr) return 'Unknown date'
                      try {
                        // Parse Alpha Vantage format: YYYYMMDDTHHMMSS
                        const year = dateStr.substring(0, 4)
                        const month = dateStr.substring(4, 6)
                        const day = dateStr.substring(6, 8)
                        const hour = dateStr.length > 9 ? dateStr.substring(9, 11) : '00'
                        const minute = dateStr.length > 11 ? dateStr.substring(11, 13) : '00'

                        const date = new Date(`${year}-${month}-${day}T${hour}:${minute}:00`)
                        const today = new Date()
                        const yesterday = new Date(today)
                        yesterday.setDate(yesterday.getDate() - 1)

                        // Check if it's today or yesterday
                        if (date.toDateString() === today.toDateString()) {
                          return `Today at ${date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
                        } else if (date.toDateString() === yesterday.toDateString()) {
                          return `Yesterday at ${date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
                        } else {
                          return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
                        }
                      } catch {
                        return dateStr
                      }
                    }

                    return (
                      <div key={index} className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <a
                          href={news.url || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <h4 className="font-medium text-gray-900 hover:text-primary-600 flex-1">
                              {news.title}
                            </h4>
                            {news.sentiment_label && (
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap ${
                                news.sentiment_label.toLowerCase().includes('bullish') || news.sentiment_label.toLowerCase().includes('positive')
                                  ? 'bg-success-100 text-success-700'
                                  : news.sentiment_label.toLowerCase().includes('bearish') || news.sentiment_label.toLowerCase().includes('negative')
                                  ? 'bg-danger-100 text-danger-700'
                                  : 'bg-gray-100 text-gray-600'
                              }`}>
                                {news.sentiment_label}
                              </span>
                            )}
                          </div>
                          {news.summary && (
                            <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                              {news.summary}
                            </p>
                          )}
                          <div className="flex items-center gap-3 text-xs text-gray-500">
                            <span className="font-medium text-gray-700">{formatNewsDate(news.published_at)}</span>
                            {news.source && (
                              <>
                                <span className="text-gray-300">|</span>
                                <span>{news.source}</span>
                              </>
                            )}
                          </div>
                        </a>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
            <div className="p-4 border-t bg-gray-50">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  {newsItems.length} article{newsItems.length !== 1 ? 's' : ''} found
                  {' - '}
                  <span className="text-gray-600">Adjust the news history days in Configuration tab</span>
                </span>
                <button
                  onClick={closeNewsModal}
                  className="btn-secondary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
