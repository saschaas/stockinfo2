import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { startStockResearch } from '../../services/api'
import { useResearchStore } from '../../stores/researchStore'
import ProgressTracker from '../ProgressTracker/ProgressTracker'
import DataSourceBadge from '../DataSourceBadge/DataSourceBadge'

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
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
