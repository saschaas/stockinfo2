import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  fetchWatchlist,
  fetchWatchlistStockDetails,
  fetchCustomLines,
  createCustomLine,
  updateCustomLine,
  deleteCustomLine,
} from '../../services/api'
import type {
  WatchlistLineCreate,
  WatchlistLineUpdate,
} from '../../types'
import InteractiveChart from './InteractiveChart'
import TechnicalIndicatorSummary from './TechnicalIndicatorSummary'
import StockNewsSection from './StockNewsSection'
import CustomLinesList from './CustomLinesList'

export default function WatchlistStockDetails() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()

  // State for line editing
  const [isAddingLine, setIsAddingLine] = useState(false)
  const [newLineType, setNewLineType] = useState<'trend' | 'alert'>('trend')
  const [lineError, setLineError] = useState<string | null>(null)

  // Get watchlist to find item ID for the ticker
  const { data: watchlist } = useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
  })

  const watchlistItem = watchlist?.items.find(
    (item) => item.ticker.toLowerCase() === ticker?.toLowerCase()
  )

  // Fetch stock details
  const {
    data: stockDetails,
    isLoading,
    error,
    refetch: refetchDetails,
  } = useQuery({
    queryKey: ['watchlistStockDetails', watchlistItem?.id],
    queryFn: () => fetchWatchlistStockDetails(watchlistItem!.id),
    enabled: !!watchlistItem?.id,
  })

  // Fetch custom lines separately for easier refresh
  const { data: customLines, refetch: refetchLines } = useQuery({
    queryKey: ['customLines', watchlistItem?.id],
    queryFn: () => fetchCustomLines(watchlistItem!.id),
    enabled: !!watchlistItem?.id,
  })

  // Handle adding a new line from chart interaction
  const handleAddLine = useCallback(
    async (priceLevel: number) => {
      if (!watchlistItem?.id) return

      const name = prompt(
        `Enter name for ${newLineType === 'alert' ? 'alert' : 'trend'} line at $${priceLevel.toFixed(2)}:`
      )
      if (!name) {
        setIsAddingLine(false)
        return
      }

      try {
        const lineData: WatchlistLineCreate = {
          line_type: newLineType,
          name,
          price_level: priceLevel,
          color: newLineType === 'alert' ? '#f97316' : '#8b5cf6',
        }

        await createCustomLine(watchlistItem.id, lineData)
        await refetchLines()
        await refetchDetails()
        setIsAddingLine(false)
        setLineError(null)
      } catch (err: any) {
        setLineError(err.response?.data?.detail || 'Failed to create line')
      }
    },
    [watchlistItem?.id, newLineType, refetchLines, refetchDetails]
  )

  // Handle updating a line (e.g., moving it)
  const handleUpdateLine = useCallback(
    async (lineId: number, updates: WatchlistLineUpdate) => {
      if (!watchlistItem?.id) return

      try {
        await updateCustomLine(watchlistItem.id, lineId, updates)
        await refetchLines()
        await refetchDetails()
        setLineError(null)
      } catch (err: any) {
        setLineError(err.response?.data?.detail || 'Failed to update line')
      }
    },
    [watchlistItem?.id, refetchLines, refetchDetails]
  )

  // Handle deleting a line
  const handleDeleteLine = useCallback(
    async (lineId: number) => {
      if (!watchlistItem?.id) return

      if (!confirm('Are you sure you want to delete this line?')) return

      try {
        await deleteCustomLine(watchlistItem.id, lineId)
        await refetchLines()
        await refetchDetails()
        setLineError(null)
      } catch (err: any) {
        setLineError(err.response?.data?.detail || 'Failed to delete line')
      }
    },
    [watchlistItem?.id, refetchLines, refetchDetails]
  )

  // Handle line price change from chart drag
  const handleLinePriceChange = useCallback(
    async (lineId: number, newPrice: number) => {
      await handleUpdateLine(lineId, { price_level: newPrice })
    },
    [handleUpdateLine]
  )

  if (!ticker) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-gray-500">No ticker specified</p>
          <button onClick={() => navigate('/watchlist')} className="btn-primary mt-4">
            Back to Watchlist
          </button>
        </div>
      </div>
    )
  }

  if (!watchlistItem && !isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-warning-50 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-warning-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Stock Not Found</h2>
          <p className="text-gray-500 mb-4">"{ticker}" is not in your watchlist</p>
          <button onClick={() => navigate('/watchlist')} className="btn-primary">
            Back to Watchlist
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/watchlist')}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Back to Watchlist"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{ticker?.toUpperCase()}</h1>
              {stockDetails?.item.company_name && (
                <span className="text-lg text-gray-600">{stockDetails.item.company_name}</span>
              )}
              {/* Momentum badges */}
              {stockDetails?.item.has_golden_cross && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-success-100 text-success-700 border border-success-200">
                  GC
                </span>
              )}
              {stockDetails?.item.is_bullish_trend && (
                <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-success-100 text-success-700 border border-success-200">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                  Bullish
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-1">Stock Details & Technical Analysis</p>
          </div>
        </div>

        {/* Price and change */}
        {stockDetails?.item && (
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">
              ${stockDetails.item.current_price?.toFixed(2) || '-'}
            </div>
            {stockDetails.item.change_pct !== undefined && stockDetails.item.change_pct !== null && (
              <div
                className={`text-sm font-medium ${
                  stockDetails.item.change_pct >= 0 ? 'text-success-600' : 'text-danger-600'
                }`}
              >
                {stockDetails.item.change_pct >= 0 ? '+' : ''}
                {stockDetails.item.change_pct.toFixed(2)}%
                {stockDetails.item.change_amount !== undefined && (
                  <span className="ml-1">
                    ({stockDetails.item.change_amount >= 0 ? '+' : ''}$
                    {stockDetails.item.change_amount.toFixed(2)})
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error display */}
      {(error || lineError) && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-4">
          <p className="text-danger-700 text-sm">
            {lineError || (error as any)?.message || 'Failed to load stock details'}
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <svg
              className="animate-spin h-12 w-12 text-primary-500 mx-auto mb-4"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p className="text-gray-500">Loading stock details...</p>
          </div>
        </div>
      ) : stockDetails ? (
        <div className="space-y-6">
          {/* Technical Summary */}
          <TechnicalIndicatorSummary data={stockDetails.technical_summary} />

          {/* Chart with line controls */}
          <div className="card card-body">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Price Chart</h2>
              <div className="flex items-center gap-2">
                {isAddingLine ? (
                  <>
                    <span className="text-sm text-gray-600">
                      Click on chart to place {newLineType} line
                    </span>
                    <button
                      onClick={() => setIsAddingLine(false)}
                      className="btn-secondary text-sm px-3 py-1"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setNewLineType('trend')
                        setIsAddingLine(true)
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-purple-300 bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors text-sm"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 4v16m8-8H4"
                        />
                      </svg>
                      Add Trend Line
                    </button>
                    <button
                      onClick={() => {
                        setNewLineType('alert')
                        setIsAddingLine(true)
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-orange-300 bg-orange-50 text-orange-700 hover:bg-orange-100 transition-colors text-sm"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                        />
                      </svg>
                      Add Alert
                    </button>
                  </>
                )}
              </div>
            </div>

            <InteractiveChart
              chartData={stockDetails.chart_data}
              customLines={customLines || stockDetails.custom_lines}
              isAddingLine={isAddingLine}
              newLineType={newLineType}
              onAddLine={handleAddLine}
              onLinePriceChange={handleLinePriceChange}
            />
          </div>

          {/* Two-column layout for lines and news */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Custom Lines */}
            <CustomLinesList
              lines={customLines || stockDetails.custom_lines}
              triggeredAlerts={stockDetails.triggered_alerts_today}
              onUpdateLine={handleUpdateLine}
              onDeleteLine={handleDeleteLine}
            />

            {/* News Section */}
            <StockNewsSection news={stockDetails.news} ticker={ticker} />
          </div>
        </div>
      ) : null}
    </div>
  )
}
