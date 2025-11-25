import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { startStockResearch } from '../../services/api'
import { useResearchStore } from '../../stores/researchStore'
import ProgressTracker from '../ProgressTracker/ProgressTracker'
import DataSourceBadge from '../DataSourceBadge/DataSourceBadge'
import GrowthAnalysisCard from './GrowthAnalysisCard'

export default function StockResearch() {
  const [ticker, setTicker] = useState('')
  const { addJob, jobs } = useResearchStore()

  const mutation = useMutation({
    mutationFn: (ticker: string) => startStockResearch(ticker),
    onSuccess: (data) => {
      addJob({
        id: data.job_id,
        ticker: data.ticker,
        status: 'pending',
        progress: 0,
        currentStep: 'Initializing research...',
      })
      setTicker('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) {
      mutation.mutate(ticker.trim().toUpperCase())
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Stock Research</h2>

      {/* Research Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ticker" className="block text-sm font-medium text-gray-700 mb-1">
              Stock Ticker
            </label>
            <input
              type="text"
              id="ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g., AAPL, MSFT, GOOGL"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              maxLength={10}
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={!ticker.trim() || mutation.isPending}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? 'Starting...' : 'Start Research'}
            </button>
          </div>
        </form>

        {mutation.isError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600 text-sm">
              {mutation.error instanceof Error
                ? mutation.error.message
                : 'Failed to start research'}
            </p>
          </div>
        )}
      </div>

      {/* Active Jobs */}
      {jobs.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Research Jobs</h3>
          {jobs.map((job) => (
            <div key={job.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-lg font-semibold">{job.ticker}</h4>
                  <p className="text-sm text-gray-500">Job ID: {job.id}</p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    job.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : job.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : job.status === 'running'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                </span>
              </div>

              <ProgressTracker
                jobId={job.id}
                progress={job.progress}
                currentStep={job.currentStep}
              />

              {job.error && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-red-600 text-sm font-medium">{job.error}</p>
                  {job.suggestion && (
                    <div className="mt-2">
                      <button className="text-sm text-primary-600 hover:text-primary-800">
                        Get AI Suggestion
                      </button>
                    </div>
                  )}
                </div>
              )}

              {job.result?.data_sources && (
                <div className="mt-4 flex gap-2">
                  {Object.entries(job.result.data_sources).map(([key, value]: [string, any]) => (
                    <DataSourceBadge
                      key={key}
                      source={value.type}
                      label={key}
                    />
                  ))}
                </div>
              )}

              {/* Results Display */}
              {job.status === 'completed' && job.result && (
                <div className="mt-6 border-t pt-6">
                  <h5 className="text-lg font-semibold mb-4">Analysis Results</h5>

                  {/* Recommendation */}
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">Recommendation</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                        job.result.recommendation === 'strong_buy' || job.result.recommendation === 'buy'
                          ? 'bg-green-100 text-green-800'
                          : job.result.recommendation === 'strong_sell' || job.result.recommendation === 'sell'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {job.result.recommendation?.toUpperCase().replace('_', ' ')}
                      </span>
                    </div>
                    {job.result.confidence_score && (
                      <div className="text-sm text-gray-600">
                        Confidence: {(job.result.confidence_score * 100).toFixed(0)}%
                      </div>
                    )}
                  </div>

                  {/* Company Info */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    {job.result.current_price && (
                      <div className="bg-white border rounded-lg p-3">
                        <div className="text-xs text-gray-500">Price</div>
                        <div className="text-lg font-semibold">${job.result.current_price.toFixed(2)}</div>
                      </div>
                    )}
                    {job.result.pe_ratio && (
                      <div className="bg-white border rounded-lg p-3">
                        <div className="text-xs text-gray-500">P/E Ratio</div>
                        <div className="text-lg font-semibold">{job.result.pe_ratio}</div>
                      </div>
                    )}
                    {job.result.rsi && (
                      <div className="bg-white border rounded-lg p-3">
                        <div className="text-xs text-gray-500">RSI (14)</div>
                        <div className="text-lg font-semibold">{job.result.rsi.toFixed(1)}</div>
                      </div>
                    )}
                    {job.result.sma_20 && (
                      <div className="bg-white border rounded-lg p-3">
                        <div className="text-xs text-gray-500">SMA 20</div>
                        <div className="text-lg font-semibold">${job.result.sma_20.toFixed(2)}</div>
                      </div>
                    )}
                  </div>

                  {/* Reasoning */}
                  {job.result.recommendation_reasoning && (
                    <div className="mb-4">
                      <div className="text-sm font-medium text-gray-700 mb-1">Analysis</div>
                      <p className="text-sm text-gray-600">{job.result.recommendation_reasoning}</p>
                    </div>
                  )}

                  {/* Risks & Opportunities */}
                  <div className="grid md:grid-cols-2 gap-4">
                    {job.result.risks && job.result.risks.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-red-700 mb-2">Risks</div>
                        <ul className="text-sm text-gray-600 space-y-1">
                          {job.result.risks.slice(0, 3).map((risk: string, i: number) => (
                            <li key={i} className="flex items-start">
                              <span className="text-red-500 mr-2">•</span>
                              {risk}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {job.result.opportunities && job.result.opportunities.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-green-700 mb-2">Opportunities</div>
                        <ul className="text-sm text-gray-600 space-y-1">
                          {job.result.opportunities.slice(0, 3).map((opp: string, i: number) => (
                            <li key={i} className="flex items-start">
                              <span className="text-green-500 mr-2">•</span>
                              {opp}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Growth Analysis Section */}
                  <div className="mt-8 pt-8 border-t">
                    <GrowthAnalysisCard data={job.result} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
