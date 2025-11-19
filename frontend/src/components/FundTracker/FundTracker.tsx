import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchFunds, fetchFundHoldings, fetchFundChanges } from '../../services/api'

export default function FundTracker() {
  const [selectedFund, setSelectedFund] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'holdings' | 'changes'>('holdings')

  const { data: funds, isLoading: fundsLoading } = useQuery({
    queryKey: ['funds'],
    queryFn: () => fetchFunds(),
  })

  const { data: holdings, isLoading: holdingsLoading } = useQuery({
    queryKey: ['fundHoldings', selectedFund],
    queryFn: () => fetchFundHoldings(selectedFund!),
    enabled: !!selectedFund && activeTab === 'holdings',
  })

  const { data: changes, isLoading: changesLoading } = useQuery({
    queryKey: ['fundChanges', selectedFund],
    queryFn: () => fetchFundChanges(selectedFund!),
    enabled: !!selectedFund && activeTab === 'changes',
  })

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
          ) : (
            <div className="space-y-2">
              {funds?.funds?.map((fund: any) => (
                <button
                  key={fund.id}
                  onClick={() => setSelectedFund(fund.id)}
                  className={`w-full text-left px-4 py-2 rounded-lg ${
                    selectedFund === fund.id
                      ? 'bg-primary-100 text-primary-800'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <div className="font-medium text-sm">{fund.name}</div>
                  {fund.ticker && (
                    <div className="text-xs text-gray-500">{fund.ticker}</div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Fund Details */}
        <div className="lg:col-span-2">
          {selectedFund ? (
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
                      <div className="space-y-6">
                        {changes?.new_positions?.length > 0 && (
                          <div>
                            <h4 className="font-medium text-green-600 mb-2">New Positions</h4>
                            <ul className="space-y-1">
                              {changes.new_positions.map((item: any, index: number) => (
                                <li key={index} className="text-sm">
                                  {item.ticker} - ${(item.value / 1000000).toFixed(2)}M
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {changes?.increased?.length > 0 && (
                          <div>
                            <h4 className="font-medium text-blue-600 mb-2">Increased</h4>
                            <ul className="space-y-1">
                              {changes.increased.map((item: any, index: number) => (
                                <li key={index} className="text-sm">
                                  {item.ticker} +{item.shares_change?.toLocaleString()} shares
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {changes?.decreased?.length > 0 && (
                          <div>
                            <h4 className="font-medium text-orange-600 mb-2">Decreased</h4>
                            <ul className="space-y-1">
                              {changes.decreased.map((item: any, index: number) => (
                                <li key={index} className="text-sm">
                                  {item.ticker} {item.shares_change?.toLocaleString()} shares
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {changes?.sold?.length > 0 && (
                          <div>
                            <h4 className="font-medium text-red-600 mb-2">Sold</h4>
                            <ul className="space-y-1">
                              {changes.sold.map((item: any, index: number) => (
                                <li key={index} className="text-sm">{item.ticker}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {!changes?.new_positions?.length &&
                          !changes?.increased?.length &&
                          !changes?.decreased?.length &&
                          !changes?.sold?.length && (
                            <p className="text-gray-500">No recent changes</p>
                          )}
                      </div>
                    )}
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
    </div>
  )
}
