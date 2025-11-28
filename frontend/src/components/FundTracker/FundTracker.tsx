import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchFunds, fetchFundHoldings, fetchFundChanges, fetchAggregatedHoldings, fetchAggregatedChanges, addFund, removeFund, validateFund, searchFunds } from '../../services/api'

interface SearchResult {
  cik: string
  name: string
  ticker: string | null
  has_13f_filings: boolean
  is_recommended: boolean
  latest_filing_date: string | null
}

export default function FundTracker() {
  const [selectedFund, setSelectedFund] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'holdings' | 'changes' | 'new' | 'sold'>('holdings')
  const [newFundCik, setNewFundCik] = useState('')
  const [newFundName, setNewFundName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [addSuccess, setAddSuccess] = useState<string | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const hasValidated = useRef(false)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [modalFunds, setModalFunds] = useState<{ ticker: string; companyName: string; fundNames: string[] } | null>(null)

  const queryClient = useQueryClient()

  const handleFundCountClick = (ticker: string, companyName: string, fundNames: string[]) => {
    setModalFunds({ ticker, companyName, fundNames })
  }

  const closeModal = () => {
    setModalFunds(null)
  }

  const { data: funds, isLoading: fundsLoading, error: fundsError } = useQuery({
    queryKey: ['funds'],
    queryFn: () => fetchFunds(),
  })

  const { data: holdings, isLoading: holdingsLoading } = useQuery({
    queryKey: ['fundHoldings', selectedFund],
    queryFn: () => selectedFund === 0 ? fetchAggregatedHoldings() : fetchFundHoldings(selectedFund!),
    enabled: selectedFund !== null && activeTab === 'holdings',
  })

  const { data: changes, isLoading: changesLoading } = useQuery({
    queryKey: ['fundChanges', selectedFund],
    queryFn: () => selectedFund === 0 ? fetchAggregatedChanges() : fetchFundChanges(selectedFund!),
    enabled: selectedFund !== null && (activeTab === 'changes' || activeTab === 'new' || activeTab === 'sold'),
  })

  // Mutation for removing a fund
  const removeFundMutation = useMutation({
    mutationFn: removeFund,
    onSuccess: (_data, fundId) => {
      queryClient.invalidateQueries({ queryKey: ['funds'] })
      if (selectedFund === fundId) {
        setSelectedFund(null)
      }
    },
  })

  // Mutation for adding a fund
  const addFundMutation = useMutation({
    mutationFn: ({ cik, name }: { cik: string; name?: string }) => addFund(cik, name),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['funds'] })
      setNewFundCik('')
      setNewFundName('')
      setAddError(null)
      setAddSuccess(`Fund "${data.name}" added successfully!`)
      setTimeout(() => setAddSuccess(null), 5000)
    },
    onError: (error: any) => {
      setAddError(error.response?.data?.detail || 'Failed to add fund')
      setAddSuccess(null)
    },
  })

  // Validate all funds on startup and remove invalid ones
  useEffect(() => {
    const validateAllFunds = async () => {
      if (!funds?.funds || funds.funds.length === 0 || hasValidated.current) return

      hasValidated.current = true
      const invalidFundIds: number[] = []

      for (const fund of funds.funds) {
        if (fund.cik) {
          try {
            const validation = await validateFund(fund.cik, fund.name)
            if (!validation.is_valid) {
              console.warn(`Invalid fund detected: ${fund.name} (${fund.cik}) - ${validation.error}`)
              invalidFundIds.push(fund.id)
            }
          } catch (error) {
            console.error(`Error validating fund ${fund.name}:`, error)
          }
        }
      }

      if (invalidFundIds.length > 0) {
        console.log(`Removing ${invalidFundIds.length} invalid funds...`)
        for (const fundId of invalidFundIds) {
          try {
            await removeFund(fundId)
          } catch (error) {
            console.error(`Error removing fund ${fundId}:`, error)
          }
        }
        queryClient.invalidateQueries({ queryKey: ['funds'] })
      }
    }

    validateAllFunds()
  }, [funds, queryClient])

  // Handle search input with debouncing
  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    if (value.length < 2) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }
    setIsSearching(true)
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await searchFunds(value)
        setSearchResults(results.results || [])
        setShowSearchResults(true)
      } catch (error) {
        console.error('Search failed:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    }, 300)
  }

  const handleSelectSearchResult = (result: SearchResult) => {
    setNewFundCik(result.cik)
    setNewFundName(result.name)
    setSearchQuery('')
    setSearchResults([])
    setShowSearchResults(false)
  }

  const handleAddFund = async () => {
    if (!newFundCik.trim()) {
      setAddError('Please enter a CIK or search for a fund')
      return
    }
    setAddError(null)
    setAddSuccess(null)
    setIsValidating(true)

    try {
      const validation = await validateFund(newFundCik.trim(), newFundName.trim() || undefined)
      if (!validation.is_valid) {
        setAddError(validation.error || 'Validation failed')
        setIsValidating(false)
        return
      }
      if (validation.fund_type === 'etf') {
        setAddError('ETFs are not supported. Please add only investment funds that file 13F forms.')
        setIsValidating(false)
        return
      }
      await addFundMutation.mutateAsync({
        cik: newFundCik.trim(),
        name: newFundName.trim() || validation.name || undefined,
      })
    } catch (error: any) {
      setAddError(error.response?.data?.detail || error.message || 'Failed to add fund')
    } finally {
      setIsValidating(false)
    }
  }

  const handleRemoveFund = (fundId: number, fundName: string) => {
    if (confirm(`Are you sure you want to remove "${fundName}" from the tracked list?`)) {
      removeFundMutation.mutate(fundId)
    }
  }

  const tabs = [
    { id: 'holdings', label: 'Holdings' },
    { id: 'changes', label: 'Recent Changes' },
    { id: 'new', label: 'New Positions' },
    { id: 'sold', label: 'Sold Positions' },
  ] as const

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Fund Tracker</h1>
        <p className="text-gray-500 text-sm mt-1">Track institutional fund holdings and changes</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fund List */}
        <div className="card card-body">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Tracked Funds</h3>

          {fundsLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-cream-dark rounded-xl animate-pulse" />
              ))}
            </div>
          ) : fundsError ? (
            <div className="p-4 bg-danger-50 text-danger-700 rounded-xl text-sm">Error loading funds</div>
          ) : (
            <>
              <div className="space-y-2 mb-6">
                {/* ALL FUNDS aggregated view */}
                <button
                  onClick={() => setSelectedFund(0)}
                  className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all ${
                    selectedFund === 0
                      ? 'bg-primary-50 border-primary-500 text-primary-800'
                      : 'border-border-warm hover:bg-cream hover:border-border-warm-dark'
                  }`}
                >
                  <div className="font-bold text-sm">ALL FUNDS</div>
                  <div className="text-xs text-gray-500">Combined holdings across all funds</div>
                </button>

                {/* Individual funds */}
                {funds?.funds?.map((fund: any) => (
                  <div
                    key={fund.id}
                    className={`flex items-center justify-between px-4 py-3 rounded-xl transition-all ${
                      selectedFund === fund.id
                        ? 'bg-primary-50 border border-primary-200'
                        : 'hover:bg-cream border border-transparent'
                    }`}
                  >
                    <button
                      onClick={() => setSelectedFund(fund.id)}
                      className="flex-1 text-left"
                    >
                      <div className="font-medium text-sm text-gray-900">{fund.name}</div>
                      {fund.ticker && (
                        <div className="text-xs text-gray-500">{fund.ticker}</div>
                      )}
                    </button>
                    <button
                      onClick={() => handleRemoveFund(fund.id, fund.name)}
                      className="ml-2 p-1.5 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                      title="Remove fund"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>

              {/* Add Fund Form */}
              <div className="border-t border-border-warm pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Add New Fund</h4>

                {addError && (
                  <div className="mb-3 p-3 bg-danger-50 border border-danger-100 rounded-xl text-sm text-danger-700">
                    {addError}
                  </div>
                )}
                {addSuccess && (
                  <div className="mb-3 p-3 bg-success-50 border border-success-100 rounded-xl text-sm text-success-700">
                    {addSuccess}
                  </div>
                )}

                <div className="space-y-3">
                  {/* Search Input */}
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search funds (e.g., FMR, Fidelity)"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      className="input"
                    />
                    {isSearching && (
                      <div className="absolute right-3 top-3 text-gray-400 text-xs">Searching...</div>
                    )}

                    {/* Search Results Dropdown */}
                    {showSearchResults && searchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border border-border-warm rounded-xl shadow-card max-h-64 overflow-y-auto">
                        {searchResults.map((result) => (
                          <button
                            key={result.cik}
                            onClick={() => handleSelectSearchResult(result)}
                            className={`w-full text-left px-4 py-3 hover:bg-cream border-b border-border-warm last:border-b-0 transition-colors ${
                              result.is_recommended ? 'bg-success-50' : ''
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm text-gray-900">{result.name}</span>
                              {result.is_recommended && (
                                <span className="badge badge-success text-xs">Recommended</span>
                              )}
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5">
                              CIK: {result.cik}
                              {result.ticker && ` • ${result.ticker}`}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <input
                    type="text"
                    placeholder="CIK (auto-filled)"
                    value={newFundCik}
                    readOnly
                    className="input bg-cream"
                  />
                  <input
                    type="text"
                    placeholder="Fund Name (auto-filled)"
                    value={newFundName}
                    readOnly
                    className="input bg-cream"
                  />
                  <button
                    onClick={handleAddFund}
                    disabled={isValidating || addFundMutation.isPending || !newFundCik}
                    className="btn-primary w-full"
                  >
                    {isValidating || addFundMutation.isPending ? 'Adding...' : 'Add Fund'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Fund Details */}
        <div className="lg:col-span-2">
          {selectedFund !== null ? (
            <div className="card overflow-hidden">
              {/* Tabs */}
              <div className="border-b border-border-warm bg-cream">
                <nav className="flex -mb-px">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-6 py-4 text-sm font-medium transition-colors ${
                        activeTab === tab.id
                          ? 'border-b-2 border-primary-500 text-primary-600 bg-white'
                          : 'text-gray-500 hover:text-gray-700 hover:bg-cream-dark'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              <div className="p-6">
                {/* Holdings Tab */}
                {activeTab === 'holdings' && (
                  <>
                    {holdingsLoading ? (
                      <div className="space-y-3">
                        {[...Array(10)].map((_, i) => (
                          <div key={i} className="h-10 bg-cream-dark rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : holdings?.holdings?.length > 0 ? (
                      <>
                        <div className="mb-4 badge badge-neutral">
                          Filing Date: {holdings.filing_date}
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="table-header text-left">
                                <th className="px-4 py-3 rounded-l-lg">Ticker</th>
                                <th className="px-4 py-3">Company</th>
                                <th className="px-4 py-3 text-right">Shares</th>
                                <th className="px-4 py-3 text-right">Value</th>
                                <th className="px-4 py-3 text-right">%</th>
                                {selectedFund === 0 && <th className="px-4 py-3 text-right rounded-r-lg">Funds</th>}
                              </tr>
                            </thead>
                            <tbody>
                              {holdings.holdings.map((holding: any, index: number) => (
                                <tr key={index} className="table-row">
                                  <td className="px-4 py-3 font-semibold text-gray-900">{holding.ticker}</td>
                                  <td className="px-4 py-3 text-sm text-gray-600">{holding.company_name}</td>
                                  <td className="px-4 py-3 text-right text-sm font-mono">{holding.shares.toLocaleString()}</td>
                                  <td className="px-4 py-3 text-right text-sm font-mono">${(holding.value / 1000000).toFixed(2)}M</td>
                                  <td className="px-4 py-3 text-right text-sm">{holding.percentage?.toFixed(2)}%</td>
                                  {selectedFund === 0 && (
                                    <td className="px-4 py-3 text-right">
                                      <button
                                        onClick={() => handleFundCountClick(holding.ticker, holding.company_name, holding.fund_names || [])}
                                        className="font-medium text-primary-600 hover:text-primary-700"
                                      >
                                        {holding.fund_count}
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : (
                      <p className="text-gray-500 text-center py-8">No holdings data available</p>
                    )}
                  </>
                )}

                {/* Changes Tab */}
                {activeTab === 'changes' && (
                  <>
                    {changesLoading ? (
                      <div className="space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-16 bg-cream-dark rounded-xl animate-pulse" />
                        ))}
                      </div>
                    ) : (
                      <div>
                        {changes?.filing_date && (
                          <div className="mb-4 badge badge-neutral">Filing Date: {changes.filing_date}</div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Top Bought */}
                          <div>
                            <h4 className="font-semibold text-success-700 mb-3 flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success-500" />
                              Top 10 Bought
                            </h4>
                            {(() => {
                              const bought = [...(changes?.new_positions || []), ...(changes?.increased || [])]
                                .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                                .slice(0, 10);
                              return bought.length > 0 ? (
                                <div className="space-y-2">
                                  {bought.map((item: any, index: number) => (
                                    <div key={index} className="bg-success-50 p-3 rounded-xl border border-success-100">
                                      <div className="font-medium text-sm text-gray-900">{item.company_name || item.ticker}</div>
                                      <div className="flex justify-between items-center mt-1">
                                        <div className="text-xs text-success-700">+${(item.value_change / 1000000).toFixed(2)}M</div>
                                        <div className="text-xs text-gray-500">{item.percentage?.toFixed(2)}%</div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : <p className="text-sm text-gray-500">No positions bought</p>;
                            })()}
                          </div>
                          {/* Top Sold */}
                          <div>
                            <h4 className="font-semibold text-danger-700 mb-3 flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-danger-500" />
                              Top 10 Sold
                            </h4>
                            {(() => {
                              const sold = [...(changes?.decreased || []), ...(changes?.sold || [])]
                                .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                                .slice(0, 10);
                              return sold.length > 0 ? (
                                <div className="space-y-2">
                                  {sold.map((item: any, index: number) => (
                                    <div key={index} className="bg-danger-50 p-3 rounded-xl border border-danger-100">
                                      <div className="font-medium text-sm text-gray-900">{item.company_name || item.ticker}</div>
                                      <div className="flex justify-between items-center mt-1">
                                        <div className="text-xs text-danger-700">${(item.value_change / 1000000).toFixed(2)}M</div>
                                        <div className="text-xs text-gray-500">{item.percentage?.toFixed(2)}%</div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : <p className="text-sm text-gray-500">No positions sold</p>;
                            })()}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* New Positions Tab */}
                {activeTab === 'new' && (
                  <>
                    {changesLoading ? (
                      <div className="space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-10 bg-cream-dark rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : changes?.new_positions?.length > 0 ? (
                      <>
                        {changes?.filing_date && (
                          <div className="mb-4 badge badge-neutral">Filing Date: {changes.filing_date}</div>
                        )}
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="table-header text-left">
                                <th className="px-4 py-3 rounded-l-lg">Ticker</th>
                                <th className="px-4 py-3">Company</th>
                                <th className="px-4 py-3 text-right">Value</th>
                                <th className="px-4 py-3 text-right rounded-r-lg">%</th>
                              </tr>
                            </thead>
                            <tbody>
                              {changes.new_positions
                                .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                                .map((item: any, index: number) => (
                                <tr key={index} className="table-row">
                                  <td className="px-4 py-3 font-semibold text-gray-900">{item.ticker}</td>
                                  <td className="px-4 py-3 text-sm text-gray-600">{item.company_name || '-'}</td>
                                  <td className="px-4 py-3 text-right text-sm text-success-700">+${(item.value / 1000000).toFixed(2)}M</td>
                                  <td className="px-4 py-3 text-right text-sm">{item.percentage?.toFixed(2)}%</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : (
                      <p className="text-gray-500 text-center py-8">No new positions</p>
                    )}
                  </>
                )}

                {/* Sold Positions Tab */}
                {activeTab === 'sold' && (
                  <>
                    {changesLoading ? (
                      <div className="space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-10 bg-cream-dark rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : (() => {
                      const soldPositions = [...(changes?.decreased || []), ...(changes?.sold || [])]
                        .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0));
                      return soldPositions.length > 0 ? (
                        <>
                          {changes?.filing_date && (
                            <div className="mb-4 badge badge-neutral">Filing Date: {changes.filing_date}</div>
                          )}
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="table-header text-left">
                                  <th className="px-4 py-3 rounded-l-lg">Ticker</th>
                                  <th className="px-4 py-3">Company</th>
                                  <th className="px-4 py-3 text-right">Value Change</th>
                                  <th className="px-4 py-3 text-right rounded-r-lg">%</th>
                                </tr>
                              </thead>
                              <tbody>
                                {soldPositions.map((item: any, index: number) => (
                                  <tr key={index} className="table-row">
                                    <td className="px-4 py-3 font-semibold text-gray-900">{item.ticker}</td>
                                    <td className="px-4 py-3 text-sm text-gray-600">{item.company_name || '-'}</td>
                                    <td className="px-4 py-3 text-right text-sm text-danger-700">${(item.value_change / 1000000).toFixed(2)}M</td>
                                    <td className="px-4 py-3 text-right text-sm">{item.percentage?.toFixed(2)}%</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      ) : (
                        <p className="text-gray-500 text-center py-8">No sold positions</p>
                      );
                    })()}
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="card card-body text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-50 flex items-center justify-center">
                <svg className="w-8 h-8 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Select a Fund</h3>
              <p className="text-gray-500">Choose a fund from the list to view holdings and changes</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {modalFunds && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={closeModal}>
          <div className="card card-body max-w-md w-full m-4 animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{modalFunds.ticker}</h3>
                <p className="text-sm text-gray-500">{modalFunds.companyName}</p>
              </div>
              <button onClick={closeModal} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-cream">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Held by {modalFunds.fundNames.length} fund{modalFunds.fundNames.length !== 1 ? 's' : ''}:
              </h4>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {modalFunds.fundNames.map((fundName, index) => (
                  <div key={index} className="px-3 py-2 bg-cream rounded-lg text-sm text-gray-800">
                    {fundName}
                  </div>
                ))}
              </div>
            </div>
            <button onClick={closeModal} className="btn-primary w-full">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
