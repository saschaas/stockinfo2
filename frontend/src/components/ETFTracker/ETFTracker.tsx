import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchETFs,
  fetchETFHoldings,
  fetchETFChanges,
  fetchAggregatedETFHoldings,
  fetchAggregatedETFChanges,
  addETF,
  removeETF,
  refreshETFHoldings,
  startStockResearch,
  ETFCreateData,
} from '../../services/api'
import { useETFNotificationStore } from '../../stores/etfNotificationStore'

export default function ETFTracker() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // State
  const [selectedETF, setSelectedETF] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'holdings' | 'changes' | 'new' | 'sold'>('holdings')

  // Add ETF form state
  const [showAddForm, setShowAddForm] = useState(false)
  const [newETFName, setNewETFName] = useState('')
  const [newETFTicker, setNewETFTicker] = useState('')
  const [newETFUrl, setNewETFUrl] = useState('')
  const [newETFCommand, setNewETFCommand] = useState('')
  const [newETFDescription, setNewETFDescription] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [addSuccess, setAddSuccess] = useState<string | null>(null)

  // Stock selection for batch analysis
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set())
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const MAX_SELECTION = 5

  // Helper to check if ticker is valid for stock research
  const isValidTicker = (ticker: string | null | undefined): boolean => {
    if (!ticker) return false
    // Check it's not a CUSIP (9 alphanumeric characters)
    if (ticker.length === 9 && /^[A-Z0-9]{9}$/i.test(ticker)) return false
    // Valid tickers are typically 1-5 characters
    return ticker.length >= 1 && ticker.length <= 5
  }

  // Refresh status
  const [refreshStatus, setRefreshStatus] = useState<'idle' | 'refreshing' | 'success' | 'error'>('idle')
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null)

  // Notification store
  const { updatedETFIds, clearETFUpdate, checkForUpdates } = useETFNotificationStore()

  // Modal for showing ETFs holding a stock
  const [modalETFs, setModalETFs] = useState<{ ticker: string; companyName: string; etfNames: string[] } | null>(null)

  // Queries
  const { data: etfs, isLoading: etfsLoading, error: etfsError } = useQuery({
    queryKey: ['etfs'],
    queryFn: () => fetchETFs(),
  })

  const { data: holdings, isLoading: holdingsLoading } = useQuery({
    queryKey: ['etfHoldings', selectedETF],
    queryFn: () => selectedETF === 0
      ? fetchAggregatedETFHoldings()
      : fetchETFHoldings(selectedETF!),
    enabled: selectedETF !== null && activeTab === 'holdings',
  })

  const { data: changes, isLoading: changesLoading } = useQuery({
    queryKey: ['etfChanges', selectedETF],
    queryFn: () => selectedETF === 0
      ? fetchAggregatedETFChanges()
      : fetchETFChanges(selectedETF!),
    enabled: selectedETF !== null && (activeTab === 'changes' || activeTab === 'new' || activeTab === 'sold'),
  })

  // Mutations
  const removeETFMutation = useMutation({
    mutationFn: removeETF,
    onSuccess: (_data, etfId) => {
      queryClient.invalidateQueries({ queryKey: ['etfs'] })
      if (selectedETF === etfId) setSelectedETF(null)
    },
  })

  const addETFMutation = useMutation({
    mutationFn: (data: ETFCreateData) => addETF(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['etfs'] })
      setAddSuccess(`ETF "${data.name}" added successfully!`)
      setShowAddForm(false)
      resetAddForm()
      setTimeout(() => setAddSuccess(null), 5000)
    },
    onError: (error: any) => {
      setAddError(error.response?.data?.detail || error.message || 'Failed to add ETF')
    },
  })

  const refreshMutation = useMutation({
    mutationFn: refreshETFHoldings,
    onMutate: () => {
      setRefreshStatus('refreshing')
      setRefreshMessage('Checking for new ETF holdings data...')
    },
    onSuccess: (data) => {
      setRefreshMessage(data.message || 'Refresh started successfully')
      setTimeout(() => {
        setRefreshStatus('success')
        queryClient.invalidateQueries({ queryKey: ['etfs'] })
        queryClient.invalidateQueries({ queryKey: ['etfHoldings'] })
        queryClient.invalidateQueries({ queryKey: ['etfChanges'] })
        checkForUpdates()
      }, 3000)
      setTimeout(() => {
        setRefreshStatus('idle')
        setRefreshMessage(null)
      }, 8000)
    },
    onError: (error: any) => {
      setRefreshStatus('error')
      setRefreshMessage(error.response?.data?.detail || 'Refresh failed')
      setTimeout(() => {
        setRefreshStatus('idle')
        setRefreshMessage(null)
      }, 5000)
    },
  })

  // Select first ETF on load
  useEffect(() => {
    if (etfs && etfs.etfs.length > 0 && selectedETF === null) {
      setSelectedETF(0) // Start with "ALL ETFs"
    }
  }, [etfs, selectedETF])

  // Handle ETF selection
  const handleSelectETF = (etfId: number) => {
    setSelectedETF(etfId)
    if (etfId !== 0 && updatedETFIds.has(etfId)) {
      clearETFUpdate(etfId)
    }
  }

  // Reset add form
  const resetAddForm = () => {
    setNewETFName('')
    setNewETFTicker('')
    setNewETFUrl('')
    setNewETFCommand('')
    setNewETFDescription('')
    setAddError(null)
  }

  // Handle add ETF
  const handleAddETF = () => {
    if (!newETFName.trim() || !newETFTicker.trim() || !newETFUrl.trim() || !newETFCommand.trim()) {
      setAddError('Please fill in all required fields')
      return
    }

    addETFMutation.mutate({
      name: newETFName.trim(),
      ticker: newETFTicker.trim().toUpperCase(),
      url: newETFUrl.trim(),
      agent_command: newETFCommand.trim(),
      description: newETFDescription.trim() || undefined,
    })
  }

  // Handle ticker selection
  const handleTickerClick = (ticker: string) => {
    if (!ticker || ticker.length > 10) return // Skip invalid tickers

    if (selectedTickers.has(ticker)) {
      const newSet = new Set(selectedTickers)
      newSet.delete(ticker)
      setSelectedTickers(newSet)
    } else if (selectedTickers.size < MAX_SELECTION) {
      setSelectedTickers(new Set([...selectedTickers, ticker]))
    }
  }

  // Handle ETF count click (show modal)
  const handleETFCountClick = (ticker: string, companyName: string, etfNames: string[]) => {
    setModalETFs({ ticker, companyName, etfNames })
  }

  // Navigate to stock research with selected tickers
  const handleAnalyzeStocks = async () => {
    if (selectedTickers.size === 0) return

    setIsAnalyzing(true)
    const tickers = Array.from(selectedTickers)

    try {
      // Start research jobs for each ticker sequentially
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

      // Navigate to Stock Research with job IDs
      navigate('/research', {
        state: {
          fromETFTracker: true,
          batchJobs: results,
          errors: errors,
        }
      })

      setSelectedTickers(new Set())
    } catch (error) {
      console.error('Batch analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Render loading state
  if (etfsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  // Render error state
  if (etfsError) {
    return (
      <div className="card card-body bg-danger-50 border-danger-200">
        <p className="text-danger-700">Failed to load ETFs. Please try again later.</p>
      </div>
    )
  }

  const etfList = etfs?.etfs || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ETF Tracker</h1>
          <p className="text-sm text-gray-500 mt-1">
            Track holdings and changes across ETFs
          </p>
        </div>

        <div className="flex items-center gap-3">
          {refreshMessage && (
            <span className={`text-sm ${refreshStatus === 'error' ? 'text-danger-600' : 'text-gray-600'}`}>
              {refreshMessage}
            </span>
          )}
          <button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshStatus === 'refreshing'}
            className={`btn ${refreshStatus === 'refreshing' ? 'btn-secondary' : 'btn-primary'} flex items-center gap-2`}
          >
            {refreshStatus === 'refreshing' ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Refreshing...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh Holdings
              </>
            )}
          </button>
        </div>
      </div>

      {/* Success message */}
      {addSuccess && (
        <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-lg">
          {addSuccess}
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel - ETF list */}
        <div className="card card-body">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">ETFs</h2>

          {/* ALL ETFs button */}
          <button
            onClick={() => handleSelectETF(0)}
            className={`w-full text-left px-4 py-3 rounded-xl mb-2 transition-all ${
              selectedETF === 0
                ? 'bg-primary-50 border-2 border-primary-200 text-primary-700'
                : 'hover:bg-cream border border-transparent'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">ALL ETFs</span>
              <span className="text-sm text-gray-500">{etfList.length} ETFs</span>
            </div>
          </button>

          <hr className="my-3 border-border-warm" />

          {/* Individual ETFs */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {etfList.map((etf) => {
              const hasUpdate = updatedETFIds.has(etf.id)
              return (
                <div
                  key={etf.id}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer transition-all ${
                    selectedETF === etf.id
                      ? 'bg-primary-50 border-2 border-primary-200'
                      : 'hover:bg-cream border border-transparent'
                  }`}
                  onClick={() => handleSelectETF(etf.id)}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{etf.ticker}</span>
                    {hasUpdate && (
                      <span className="relative flex h-2 w-2" title="New data available">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 truncate max-w-[120px]">{etf.name}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (confirm(`Remove ${etf.ticker} from tracking?`)) {
                          removeETFMutation.mutate(etf.id)
                        }
                      }}
                      className="p-1 text-gray-400 hover:text-danger-600 transition-colors"
                      title="Remove ETF"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          <hr className="my-4 border-border-warm" />

          {/* Add ETF section */}
          <div>
            {!showAddForm ? (
              <button
                onClick={() => setShowAddForm(true)}
                className="btn btn-secondary w-full"
              >
                + Add New ETF
              </button>
            ) : (
              <div className="space-y-3">
                <h3 className="font-medium text-gray-900">Add New ETF</h3>

                {addError && (
                  <div className="text-sm text-danger-600 bg-danger-50 p-2 rounded">
                    {addError}
                  </div>
                )}

                <input
                  type="text"
                  placeholder="Name (e.g., ARK Innovation ETF)"
                  value={newETFName}
                  onChange={(e) => setNewETFName(e.target.value)}
                  className="w-full px-3 py-2 border border-border-warm rounded-lg text-sm"
                />

                <input
                  type="text"
                  placeholder="Ticker (e.g., ARKK)"
                  value={newETFTicker}
                  onChange={(e) => setNewETFTicker(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border border-border-warm rounded-lg text-sm"
                />

                <input
                  type="text"
                  placeholder="Holdings page URL"
                  value={newETFUrl}
                  onChange={(e) => setNewETFUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-border-warm rounded-lg text-sm"
                />

                <textarea
                  placeholder="Agent command (instructions for data extraction)"
                  value={newETFCommand}
                  onChange={(e) => setNewETFCommand(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-border-warm rounded-lg text-sm"
                />

                <textarea
                  placeholder="Description (optional)"
                  value={newETFDescription}
                  onChange={(e) => setNewETFDescription(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-border-warm rounded-lg text-sm"
                />

                <div className="flex gap-2">
                  <button
                    onClick={handleAddETF}
                    disabled={addETFMutation.isPending}
                    className="btn btn-primary flex-1"
                  >
                    {addETFMutation.isPending ? 'Adding...' : 'Add ETF'}
                  </button>
                  <button
                    onClick={() => {
                      setShowAddForm(false)
                      resetAddForm()
                    }}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right panel - Holdings/Changes */}
        <div className="lg:col-span-2">
          {selectedETF === null ? (
            <div className="card card-body text-center text-gray-500">
              Select an ETF to view holdings
            </div>
          ) : (
            <div className="card card-body">
              {/* Tabs */}
              <div className="flex gap-2 mb-4 border-b border-border-warm pb-4">
                {(['holdings', 'changes', 'new', 'sold'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:bg-cream'
                    }`}
                  >
                    {tab === 'holdings' && 'Holdings'}
                    {tab === 'changes' && 'Recent Changes'}
                    {tab === 'new' && 'New Positions'}
                    {tab === 'sold' && 'Sold Positions'}
                  </button>
                ))}
              </div>

              {/* Stock selection bar */}
              {selectedTickers.size > 0 && (
                <div className="sticky top-0 z-10 bg-primary-50 border border-primary-200 rounded-xl p-3 mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-primary-700">
                      Selected ({selectedTickers.size}/{MAX_SELECTION}):
                    </span>
                    {Array.from(selectedTickers).map((ticker) => (
                      <span
                        key={ticker}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded-lg text-sm"
                      >
                        {ticker}
                        <button
                          onClick={() => handleTickerClick(ticker)}
                          className="hover:text-primary-900"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedTickers(new Set())}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Clear All
                    </button>
                    <button
                      onClick={handleAnalyzeStocks}
                      disabled={isAnalyzing}
                      className="btn btn-primary text-sm flex items-center gap-2"
                    >
                      {isAnalyzing ? (
                        <>
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Analyzing...
                        </>
                      ) : (
                        `Analyze ${selectedTickers.size} Stock${selectedTickers.size > 1 ? 's' : ''}`
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Holdings tab */}
              {activeTab === 'holdings' && (
                <div>
                  {holdingsLoading ? (
                    <div className="flex justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                    </div>
                  ) : holdings && holdings.holdings.length > 0 ? (
                    <>
                      <div className="text-sm text-gray-500 mb-3">
                        {holdings.holding_date && `Data as of ${holdings.holding_date}`}
                        {' | '}
                        Total Value: ${(holdings.total_value / 1000000).toFixed(2)}M
                      </div>
                      <table className="w-full">
                        <thead>
                          <tr className="table-header">
                            <th className="text-left">Ticker</th>
                            <th className="text-left">Company</th>
                            <th className="text-right">Weight %</th>
                            <th className="text-right">Value</th>
                            {selectedETF === 0 && <th className="text-right">ETFs</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {holdings.holdings.map((holding, idx) => (
                            <tr key={idx} className="table-row">
                              <td>
                                <button
                                  onClick={() => holding.ticker && handleTickerClick(holding.ticker)}
                                  className={`font-semibold ${
                                    selectedTickers.has(holding.ticker || '')
                                      ? 'text-primary-600'
                                      : 'text-gray-900 hover:text-primary-600'
                                  }`}
                                  disabled={!holding.ticker || selectedTickers.size >= MAX_SELECTION && !selectedTickers.has(holding.ticker || '')}
                                >
                                  {holding.ticker || 'N/A'}
                                </button>
                              </td>
                              <td className="text-gray-600 truncate max-w-[200px]">
                                {holding.company_name || '-'}
                              </td>
                              <td className="text-right">
                                {holding.weight_pct != null ? `${holding.weight_pct.toFixed(2)}%` : '-'}
                              </td>
                              <td className="text-right">
                                {holding.market_value != null
                                  ? `$${(holding.market_value / 1000000).toFixed(2)}M`
                                  : '-'}
                              </td>
                              {selectedETF === 0 && (
                                <td className="text-right">
                                  <button
                                    onClick={() => handleETFCountClick(
                                      holding.ticker || '',
                                      holding.company_name || '',
                                      holding.etf_names || []
                                    )}
                                    className="text-primary-600 hover:text-primary-800 font-medium"
                                  >
                                    {holding.etf_count || 0}
                                  </button>
                                </td>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  ) : (
                    <p className="text-center text-gray-500 py-8">No holdings data available</p>
                  )}
                </div>
              )}

              {/* Changes tabs */}
              {(activeTab === 'changes' || activeTab === 'new' || activeTab === 'sold') && (
                <div>
                  {changesLoading ? (
                    <div className="flex justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                    </div>
                  ) : changes ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {activeTab === 'changes' && (
                        <>
                          {/* Top Bought */}
                          <div className="bg-success-50 rounded-xl p-4 border border-success-100">
                            <h4 className="font-semibold text-success-700 mb-3 flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success-500" />
                              Top 10 Bought
                            </h4>
                            {(() => {
                              const bought = [...(changes?.new_positions || []), ...(changes?.increased || [])]
                                .sort((a: any, b: any) => (b.weight_pct || 0) - (a.weight_pct || 0))
                                .slice(0, 10);
                              return bought.length > 0 ? (
                                <div className="space-y-2">
                                  {bought.map((item: any, index: number) => {
                                    const validTicker = item.ticker
                                    const isValid = isValidTicker(validTicker)
                                    return (
                                      <div key={index} className="bg-white/50 p-3 rounded-xl border border-success-100">
                                        <div className="font-medium text-sm">
                                          {isValid ? (
                                            <span
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleTickerClick(validTicker);
                                              }}
                                              className={`cursor-pointer transition-colors ${
                                                selectedTickers.has(validTicker)
                                                  ? 'text-primary-600 font-semibold underline'
                                                  : 'text-gray-900 hover:text-primary-500 hover:underline'
                                              }`}
                                            >
                                              <span className="text-primary-600 font-bold mr-1">{validTicker}</span>
                                              {item.company_name}
                                            </span>
                                          ) : (
                                            <span className="text-gray-900">
                                              {item.company_name || item.ticker}
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex justify-between items-center mt-1">
                                          <div className="text-xs text-success-700">
                                            {item.market_value ? `$${(item.market_value / 1000000).toFixed(2)}M` : 'New'}
                                          </div>
                                          <div className="text-xs text-gray-600 font-medium">
                                            {item.weight_pct?.toFixed(2)}%
                                          </div>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              ) : <p className="text-sm text-gray-500">No positions bought</p>;
                            })()}
                          </div>

                          {/* Top Sold */}
                          <div className="bg-danger-50 rounded-xl p-4 border border-danger-100">
                            <h4 className="font-semibold text-danger-700 mb-3 flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-danger-500" />
                              Top 10 Sold
                            </h4>
                            {(() => {
                              const sold = [...(changes?.decreased || []), ...(changes?.sold || [])]
                                .sort((a: any, b: any) => (b.weight_pct || 0) - (a.weight_pct || 0))
                                .slice(0, 10);
                              return sold.length > 0 ? (
                                <div className="space-y-2">
                                  {sold.map((item: any, index: number) => {
                                    const validTicker = item.ticker
                                    const isValid = isValidTicker(validTicker)
                                    return (
                                      <div key={index} className="bg-white/50 p-3 rounded-xl border border-danger-100">
                                        <div className="font-medium text-sm">
                                          {isValid ? (
                                            <span
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleTickerClick(validTicker);
                                              }}
                                              className={`cursor-pointer transition-colors ${
                                                selectedTickers.has(validTicker)
                                                  ? 'text-primary-600 font-semibold underline'
                                                  : 'text-gray-900 hover:text-primary-500 hover:underline'
                                              }`}
                                            >
                                              <span className="text-primary-600 font-bold mr-1">{validTicker}</span>
                                              {item.company_name}
                                            </span>
                                          ) : (
                                            <span className="text-gray-900">
                                              {item.company_name || item.ticker}
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex justify-between items-center mt-1">
                                          <div className="text-xs text-danger-700">
                                            {item.market_value ? `$${(item.market_value / 1000000).toFixed(2)}M` : 'Sold'}
                                          </div>
                                          <div className="text-xs text-gray-600 font-medium">
                                            {item.weight_pct?.toFixed(2)}%
                                          </div>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              ) : <p className="text-sm text-gray-500">No sold positions</p>;
                            })()}
                          </div>
                        </>
                      )}

                      {activeTab === 'new' && (
                        <div className="md:col-span-2">
                          <h3 className="font-semibold text-success-700 mb-3">New Positions</h3>
                          {changes.new_positions.length > 0 ? (
                            <table className="w-full">
                              <thead>
                                <tr className="table-header">
                                  <th className="text-left">Ticker</th>
                                  <th className="text-left">Company</th>
                                  <th className="text-right">Value</th>
                                  <th className="text-right">Weight %</th>
                                </tr>
                              </thead>
                              <tbody>
                                {changes.new_positions
                                  .sort((a: any, b: any) => (b.weight_pct || 0) - (a.weight_pct || 0))
                                  .map((pos: any, idx: number) => {
                                    const isValid = isValidTicker(pos.ticker)
                                    return (
                                      <tr key={idx} className="table-row bg-success-50">
                                        <td className="font-semibold">
                                          {isValid ? (
                                            <span
                                              onClick={() => handleTickerClick(pos.ticker)}
                                              className={`cursor-pointer transition-colors ${
                                                selectedTickers.has(pos.ticker)
                                                  ? 'text-primary-600 underline'
                                                  : 'text-primary-600 hover:text-primary-700 hover:underline'
                                              }`}
                                            >
                                              {pos.ticker}
                                            </span>
                                          ) : pos.ticker}
                                        </td>
                                        <td className="text-gray-600">{pos.company_name || '-'}</td>
                                        <td className="text-right text-success-600">
                                          {pos.market_value ? `$${(pos.market_value / 1000000).toFixed(2)}M` : '-'}
                                        </td>
                                        <td className="text-right">{pos.weight_pct?.toFixed(2) || '-'}%</td>
                                      </tr>
                                    )
                                  })}
                              </tbody>
                            </table>
                          ) : (
                            <p className="text-center text-gray-500 py-4">No new positions</p>
                          )}
                        </div>
                      )}

                      {activeTab === 'sold' && (
                        <div className="md:col-span-2">
                          <h3 className="font-semibold text-danger-700 mb-3">Sold Positions</h3>
                          {changes.sold.length > 0 ? (
                            <table className="w-full">
                              <thead>
                                <tr className="table-header">
                                  <th className="text-left">Ticker</th>
                                  <th className="text-left">Company</th>
                                  <th className="text-right">Value</th>
                                  <th className="text-right">Weight %</th>
                                </tr>
                              </thead>
                              <tbody>
                                {changes.sold
                                  .sort((a: any, b: any) => (b.weight_pct || 0) - (a.weight_pct || 0))
                                  .map((pos: any, idx: number) => {
                                    const isValid = isValidTicker(pos.ticker)
                                    return (
                                      <tr key={idx} className="table-row bg-danger-50">
                                        <td className="font-semibold">
                                          {isValid ? (
                                            <span
                                              onClick={() => handleTickerClick(pos.ticker)}
                                              className={`cursor-pointer transition-colors ${
                                                selectedTickers.has(pos.ticker)
                                                  ? 'text-primary-600 underline'
                                                  : 'text-primary-600 hover:text-primary-700 hover:underline'
                                              }`}
                                            >
                                              {pos.ticker}
                                            </span>
                                          ) : pos.ticker}
                                        </td>
                                        <td className="text-gray-600">{pos.company_name || '-'}</td>
                                        <td className="text-right text-danger-600">
                                          {pos.market_value ? `$${(pos.market_value / 1000000).toFixed(2)}M` : '-'}
                                        </td>
                                        <td className="text-right">{pos.weight_pct?.toFixed(2) || '-'}%</td>
                                      </tr>
                                    )
                                  })}
                              </tbody>
                            </table>
                          ) : (
                            <p className="text-center text-gray-500 py-4">No sold positions</p>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 py-8">No changes data available</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Floating batch analysis button */}
      {selectedTickers.size > 0 && (
        <div className="fixed bottom-6 right-6 z-40">
          <button
            onClick={handleAnalyzeStocks}
            disabled={isAnalyzing}
            className="btn btn-primary shadow-lg hover:shadow-xl transition-all flex items-center gap-2 px-6 py-3 rounded-full"
          >
            {isAnalyzing ? (
              <>
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analyzing...
              </>
            ) : (
              <>
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                Analyze {selectedTickers.size} Stock{selectedTickers.size > 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}

      {/* Modal for ETF list */}
      {modalETFs && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lg">{modalETFs.ticker}</h3>
                <p className="text-sm text-gray-500">{modalETFs.companyName}</p>
              </div>
              <button
                onClick={() => setModalETFs(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-3">Held by {modalETFs.etfNames.length} ETF(s):</p>
            <ul className="space-y-2">
              {modalETFs.etfNames.map((name, idx) => (
                <li key={idx} className="text-sm bg-cream px-3 py-2 rounded-lg">
                  {name}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
