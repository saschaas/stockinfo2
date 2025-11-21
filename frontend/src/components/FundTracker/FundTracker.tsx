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

      // Validate all funds first
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

      // Remove all invalid funds
      if (invalidFundIds.length > 0) {
        console.log(`Removing ${invalidFundIds.length} invalid funds...`)
        for (const fundId of invalidFundIds) {
          try {
            await removeFund(fundId)
            console.log(`Removed fund ID ${fundId}`)
          } catch (error) {
            console.error(`Error removing fund ${fundId}:`, error)
          }
        }
        // Refresh the funds list after all removals
        queryClient.invalidateQueries({ queryKey: ['funds'] })
      }
    }

    validateAllFunds()
  }, [funds, queryClient])

  // Handle search input with debouncing
  const handleSearchChange = (value: string) => {
    setSearchQuery(value)

    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    // Don't search if query is too short
    if (value.length < 2) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    // Debounce search
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

  // Handle selecting a search result
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
      // Validate first
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

      // If validation passed, add the fund
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

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Fund Tracker</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fund List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Tracked Funds</h3>

          {fundsLoading ? (
            <div className="animate-pulse space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-gray-200 rounded"></div>
              ))}
            </div>
          ) : fundsError ? (
            <div className="text-red-600 text-sm">Error loading funds</div>
          ) : (
            <>
              <div className="space-y-2 mb-6">
                {/* ALL FUNDS aggregated view */}
                <div
                  className={`flex items-center justify-between px-4 py-2 rounded-lg border-2 ${
                    selectedFund === 0
                      ? 'bg-primary-100 text-primary-800 border-primary-500'
                      : 'hover:bg-gray-100 border-gray-300'
                  }`}
                >
                  <button
                    onClick={() => setSelectedFund(0)}
                    className="flex-1 text-left"
                  >
                    <div className="font-bold text-sm">ALL FUNDS</div>
                    <div className="text-xs text-gray-500">Combined holdings across all funds</div>
                  </button>
                </div>

                {/* Individual funds */}
                {funds?.funds?.map((fund: any) => (
                  <div
                    key={fund.id}
                    className={`flex items-center justify-between px-4 py-2 rounded-lg ${
                      selectedFund === fund.id
                        ? 'bg-primary-100 text-primary-800'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <button
                      onClick={() => setSelectedFund(fund.id)}
                      className="flex-1 text-left"
                    >
                      <div className="font-medium text-sm">{fund.name}</div>
                      {fund.ticker && (
                        <div className="text-xs text-gray-500">{fund.ticker}</div>
                      )}
                    </button>
                    <button
                      onClick={() => handleRemoveFund(fund.id, fund.name)}
                      className="ml-2 p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
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
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Add New Fund</h4>

                {addError && (
                  <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                    {addError}
                  </div>
                )}

                {addSuccess && (
                  <div className="mb-3 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                    {addSuccess}
                  </div>
                )}

                <div className="space-y-2">
                  {/* Search Input */}
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search funds (e.g., FMR, Fidelity, or CIK)"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    {isSearching && (
                      <div className="absolute right-3 top-2.5 text-gray-400 text-xs">
                        Searching...
                      </div>
                    )}

                    {/* Search Results Dropdown */}
                    {showSearchResults && searchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                        {searchResults.map((result) => (
                          <div
                            key={result.cik}
                            onClick={() => handleSelectSearchResult(result)}
                            className={`px-3 py-2 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                              result.is_recommended ? 'bg-green-50' : ''
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="font-medium text-sm text-gray-900">
                                  {result.name}
                                  {result.is_recommended && (
                                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                      ✓ Recommended
                                    </span>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500 mt-0.5">
                                  CIK: {result.cik}
                                  {result.ticker && ` • Ticker: ${result.ticker}`}
                                  {result.has_13f_filings && result.latest_filing_date && (
                                    <span> • Latest filing: {result.latest_filing_date}</span>
                                  )}
                                </div>
                                {!result.has_13f_filings && (
                                  <div className="text-xs text-orange-600 mt-0.5">
                                    ⚠ No 13F filings found
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* CIK and Name Inputs (Auto-filled from search) */}
                  <input
                    type="text"
                    placeholder="CIK (auto-filled from search)"
                    value={newFundCik}
                    onChange={(e) => setNewFundCik(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-gray-50"
                    readOnly
                  />
                  <input
                    type="text"
                    placeholder="Fund Name (auto-filled from search)"
                    value={newFundName}
                    onChange={(e) => setNewFundName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-gray-50"
                    readOnly
                  />
                  <button
                    onClick={handleAddFund}
                    disabled={isValidating || addFundMutation.isPending || !newFundCik}
                    className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
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
            <div className="bg-white rounded-lg shadow">
              {/* Tabs */}
              <div className="border-b border-gray-200">
                <nav className="flex -mb-px">
                  <button
                    onClick={() => setActiveTab('holdings')}
                    className={`px-6 py-3 text-sm font-medium ${
                      activeTab === 'holdings'
                        ? 'border-b-2 border-primary-500 text-primary-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Holdings
                  </button>
                  <button
                    onClick={() => setActiveTab('changes')}
                    className={`px-6 py-3 text-sm font-medium ${
                      activeTab === 'changes'
                        ? 'border-b-2 border-primary-500 text-primary-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Recent Changes
                  </button>
                  <button
                    onClick={() => setActiveTab('new')}
                    className={`px-6 py-3 text-sm font-medium ${
                      activeTab === 'new'
                        ? 'border-b-2 border-primary-500 text-primary-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    New Stocks
                  </button>
                  <button
                    onClick={() => setActiveTab('sold')}
                    className={`px-6 py-3 text-sm font-medium ${
                      activeTab === 'sold'
                        ? 'border-b-2 border-primary-500 text-primary-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Sold Stocks
                  </button>
                </nav>
              </div>

              <div className="p-6">
                {activeTab === 'holdings' && (
                  <>
                    {holdingsLoading ? (
                      <div className="animate-pulse space-y-3">
                        {[...Array(10)].map((_, i) => (
                          <div key={i} className="h-8 bg-gray-200 rounded"></div>
                        ))}
                      </div>
                    ) : holdings?.holdings?.length > 0 ? (
                      <>
                        <div className="mb-4 text-sm text-gray-500">
                          Filing Date: {holdings.filing_date}
                        </div>
                        <table className="w-full">
                          <thead>
                            <tr className="text-left text-sm text-gray-500">
                              <th className="pb-2">Ticker</th>
                              <th className="pb-2">Company</th>
                              <th className="pb-2 text-right">Shares</th>
                              <th className="pb-2 text-right">Value</th>
                              <th className="pb-2 text-right">%</th>
                              {selectedFund === 0 && <th className="pb-2 text-right">Funds</th>}
                            </tr>
                          </thead>
                          <tbody>
                            {holdings.holdings.map((holding: any, index: number) => (
                              <tr key={index} className="border-t border-gray-100">
                                <td className="py-2 font-medium">{holding.ticker}</td>
                                <td className="py-2 text-sm text-gray-600">
                                  {holding.company_name}
                                </td>
                                <td className="py-2 text-right text-sm">
                                  {holding.shares.toLocaleString()}
                                </td>
                                <td className="py-2 text-right text-sm">
                                  ${(holding.value / 1000000).toFixed(2)}M
                                </td>
                                <td className="py-2 text-right text-sm">
                                  {holding.percentage?.toFixed(2)}%
                                </td>
                                {selectedFund === 0 && (
                                  <td className="py-2 text-right text-sm">
                                    <button
                                      onClick={() => handleFundCountClick(holding.ticker, holding.company_name, holding.fund_names || [])}
                                      className="font-medium text-primary-600 hover:text-primary-800 hover:underline cursor-pointer"
                                      title="Click to see which funds hold this position"
                                    >
                                      {holding.fund_count}
                                    </button>
                                  </td>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    ) : (
                      <p className="text-gray-500">No holdings data available</p>
                    )}
                  </>
                )}

                {activeTab === 'changes' && (
                  <>
                    {changesLoading ? (
                      <div className="animate-pulse space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-8 bg-gray-200 rounded"></div>
                        ))}
                      </div>
                    ) : (
                      <div>
                        {changes?.filing_date && (
                          <div className="mb-4 text-sm text-gray-500">
                            Filing Date: {changes.filing_date}
                          </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Top 10 Bought */}
                          <div>
                            <h4 className="font-medium text-green-600 mb-3">Top 10 Bought</h4>
                            {(() => {
                              const bought = [
                                ...(changes?.new_positions || []),
                                ...(changes?.increased || [])
                              ]
                                .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                                .slice(0, 10);

                              return bought.length > 0 ? (
                                <div className="space-y-2">
                                  {bought.map((item: any, index: number) => (
                                    <div key={index} className="bg-green-50 p-3 rounded border border-green-200">
                                      <div className="font-medium text-sm">{item.company_name || item.ticker}</div>
                                      <div className="flex justify-between items-start mt-1">
                                        <div>
                                          <div className="text-xs text-gray-600">{item.ticker}</div>
                                          <div className="text-xs text-green-700">
                                            +${(item.value_change / 1000000).toFixed(2)}M
                                          </div>
                                        </div>
                                        <div className="text-right">
                                          <div className="text-xs text-gray-600">
                                            {item.percentage?.toFixed(2)}% of fund
                                          </div>
                                          {selectedFund === 0 && item.fund_count && (
                                            <button
                                              onClick={() => handleFundCountClick(item.ticker, item.company_name, item.fund_names || [])}
                                              className="text-xs font-medium text-primary-600 hover:text-primary-800 hover:underline cursor-pointer"
                                              title="Click to see which funds hold this position"
                                            >
                                              {item.fund_count} fund{item.fund_count !== 1 ? 's' : ''}
                                            </button>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-sm text-gray-500">No positions bought</p>
                              );
                            })()}
                          </div>

                          {/* Top 10 Sold */}
                          <div>
                            <h4 className="font-medium text-red-600 mb-3">Top 10 Sold</h4>
                            {(() => {
                              const sold = [
                                ...(changes?.decreased || []),
                                ...(changes?.sold || [])
                              ]
                                .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                                .slice(0, 10);

                              return sold.length > 0 ? (
                                <div className="space-y-2">
                                  {sold.map((item: any, index: number) => (
                                    <div key={index} className="bg-red-50 p-3 rounded border border-red-200">
                                      <div className="font-medium text-sm">{item.company_name || item.ticker}</div>
                                      <div className="flex justify-between items-start mt-1">
                                        <div>
                                          <div className="text-xs text-gray-600">{item.ticker}</div>
                                          <div className="text-xs text-red-700">
                                            ${(item.value_change / 1000000).toFixed(2)}M
                                          </div>
                                        </div>
                                        <div className="text-right">
                                          <div className="text-xs text-gray-600">
                                            {item.percentage?.toFixed(2)}% of fund
                                          </div>
                                          {selectedFund === 0 && item.fund_count && (
                                            <button
                                              onClick={() => handleFundCountClick(item.ticker, item.company_name, item.fund_names || [])}
                                              className="text-xs font-medium text-primary-600 hover:text-primary-800 hover:underline cursor-pointer"
                                              title="Click to see which funds hold this position"
                                            >
                                              {item.fund_count} fund{item.fund_count !== 1 ? 's' : ''}
                                            </button>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-sm text-gray-500">No positions sold</p>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {activeTab === 'new' && (
                  <>
                    {changesLoading ? (
                      <div className="animate-pulse space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-8 bg-gray-200 rounded"></div>
                        ))}
                      </div>
                    ) : changes?.new_positions?.length > 0 ? (
                      <>
                        {changes?.filing_date && (
                          <div className="mb-4 text-sm text-gray-500">
                            Filing Date: {changes.filing_date}
                          </div>
                        )}
                        <table className="w-full">
                          <thead>
                            <tr className="text-left text-sm text-gray-500">
                              <th className="pb-2">Ticker</th>
                              <th className="pb-2">Company</th>
                              <th className="pb-2 text-right">Value</th>
                              <th className="pb-2 text-right">% of Fund</th>
                              {selectedFund === 0 && <th className="pb-2 text-right">Funds</th>}
                            </tr>
                          </thead>
                          <tbody>
                            {changes.new_positions
                              .sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0))
                              .map((item: any, index: number) => (
                              <tr key={index} className="border-t border-gray-100">
                                <td className="py-2 font-medium">{item.ticker}</td>
                                <td className="py-2 text-sm text-gray-600">
                                  {item.company_name || '-'}
                                </td>
                                <td className="py-2 text-right text-sm text-green-600">
                                  +${(item.value / 1000000).toFixed(2)}M
                                </td>
                                <td className="py-2 text-right text-sm">
                                  {item.percentage?.toFixed(2)}%
                                </td>
                                {selectedFund === 0 && (
                                  <td className="py-2 text-right text-sm">
                                    <button
                                      onClick={() => handleFundCountClick(item.ticker, item.company_name, item.fund_names || [])}
                                      className="font-medium text-primary-600 hover:text-primary-800 hover:underline cursor-pointer"
                                      title="Click to see which funds hold this position"
                                    >
                                      {item.fund_count}
                                    </button>
                                  </td>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    ) : (
                      <p className="text-gray-500">No new positions</p>
                    )}
                  </>
                )}

                {activeTab === 'sold' && (
                  <>
                    {changesLoading ? (
                      <div className="animate-pulse space-y-3">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="h-8 bg-gray-200 rounded"></div>
                        ))}
                      </div>
                    ) : (() => {
                      const soldPositions = [
                        ...(changes?.decreased || []),
                        ...(changes?.sold || [])
                      ].sort((a: any, b: any) => (b.percentage || 0) - (a.percentage || 0));

                      return soldPositions.length > 0 ? (
                        <>
                          {changes?.filing_date && (
                            <div className="mb-4 text-sm text-gray-500">
                              Filing Date: {changes.filing_date}
                            </div>
                          )}
                          <table className="w-full">
                            <thead>
                              <tr className="text-left text-sm text-gray-500">
                                <th className="pb-2">Ticker</th>
                                <th className="pb-2">Company</th>
                                <th className="pb-2 text-right">Value Change</th>
                                <th className="pb-2 text-right">% of Fund</th>
                                {selectedFund === 0 && <th className="pb-2 text-right">Funds</th>}
                              </tr>
                            </thead>
                            <tbody>
                              {soldPositions.map((item: any, index: number) => (
                                <tr key={index} className="border-t border-gray-100">
                                  <td className="py-2 font-medium">{item.ticker}</td>
                                  <td className="py-2 text-sm text-gray-600">
                                    {item.company_name || '-'}
                                  </td>
                                  <td className="py-2 text-right text-sm text-red-600">
                                    ${(item.value_change / 1000000).toFixed(2)}M
                                  </td>
                                  <td className="py-2 text-right text-sm">
                                    {item.percentage?.toFixed(2)}%
                                  </td>
                                  {selectedFund === 0 && (
                                    <td className="py-2 text-right text-sm">
                                      <button
                                        onClick={() => handleFundCountClick(item.ticker, item.company_name, item.fund_names || [])}
                                        className="font-medium text-primary-600 hover:text-primary-800 hover:underline cursor-pointer"
                                        title="Click to see which funds hold this position"
                                      >
                                        {item.fund_count}
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </>
                      ) : (
                        <p className="text-gray-500">No sold or decreased positions</p>
                      );
                    })()}
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
              Select a fund to view details
            </div>
          )}
        </div>
      </div>

      {/* Modal for showing which funds hold a position */}
      {modalFunds && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={closeModal}>
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{modalFunds.ticker}</h3>
                  <p className="text-sm text-gray-600">{modalFunds.companyName}</p>
                </div>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                  title="Close"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Held by {modalFunds.fundNames.length} fund{modalFunds.fundNames.length !== 1 ? 's' : ''}:
                </h4>
                <div className="space-y-1 max-h-96 overflow-y-auto">
                  {modalFunds.fundNames.map((fundName, index) => (
                    <div key={index} className="px-3 py-2 bg-gray-50 rounded text-sm text-gray-800">
                      {fundName}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={closeModal}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
