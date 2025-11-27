import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { startStockResearch } from '../../services/api'
import { useResearchStore } from '../../stores/researchStore'
import JobProgressManager from '../JobProgressManager/JobProgressManager'
import DataSourceBadge from '../DataSourceBadge/DataSourceBadge'
import GrowthAnalysisCard from './GrowthAnalysisCard'
import TechnicalAnalysisChart from './TechnicalAnalysisChart'
import TechnicalIndicatorsPanel from './TechnicalIndicatorsPanel'
import RiskAssessmentCard from './RiskAssessmentCard'
import CollapsibleSection from './CollapsibleSection'
import ResearchSidebar from './ResearchSidebar'
import type { RiskAssessmentData } from '../../types/risk-assessment'

// Helper function to safely format numbers
const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === undefined || value === null || typeof value !== 'number' || isNaN(value)) return 'N/A'
  return value.toFixed(decimals)
}

// State type for collapsed sections per job
interface CollapsedSections {
  technicalIndicators: boolean
  growthAnalysis: boolean
  aiAnalysis: boolean
}

export default function StockResearch() {
  const [ticker, setTicker] = useState('')
  const { addJob, jobs, activeJob, setActiveJob } = useResearchStore()

  // Track collapsed state per job
  const [collapsedStates, setCollapsedStates] = useState<Record<string, CollapsedSections>>({})

  // Initialize collapsed state for new jobs
  useEffect(() => {
    jobs.forEach(job => {
      if (!collapsedStates[job.id]) {
        setCollapsedStates(prev => ({
          ...prev,
          [job.id]: {
            technicalIndicators: true,  // Collapsed by default
            growthAnalysis: true,       // Collapsed by default
            aiAnalysis: true,           // Collapsed by default
          }
        }))
      }
    })
  }, [jobs, collapsedStates])

  const toggleSection = (jobId: string, section: keyof CollapsedSections) => {
    setCollapsedStates(prev => ({
      ...prev,
      [jobId]: {
        ...prev[jobId],
        [section]: !prev[jobId]?.[section]
      }
    }))
  }

  const mutation = useMutation({
    mutationFn: (ticker: string) => startStockResearch(ticker),
    onSuccess: (data) => {
      addJob({
        id: data.job_id,
        ticker: data.ticker,
        status: 'pending',
        progress: 0,
        currentStep: 'Initializing research...',
        createdAt: new Date(),
      })
      setTicker('')

      // Reset all sections to collapsed for the new job
      setCollapsedStates(prev => ({
        ...prev,
        [data.job_id]: {
          technicalIndicators: true,
          growthAnalysis: true,
          aiAnalysis: true,
        }
      }))
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) {
      mutation.mutate(ticker.trim().toUpperCase())
    }
  }

  // Get the active job object
  const activeJobData = jobs.find(job => job.id === activeJob)

  // Handler for selecting a job from sidebar
  const handleSelectJob = (jobId: string) => {
    setActiveJob(jobId)
  }

  // Check if sidebar should be shown (only when there are other jobs besides active)
  const sidebarJobs = jobs.filter((job) => job.id !== activeJob)
  const showSidebar = sidebarJobs.length > 0

  return (
    <div className="flex gap-6">
      {/* JobProgressManager handles WebSocket connections for ALL running jobs */}
      <JobProgressManager />

      {/* Main Content Column - fixed width to maintain consistent size with or without sidebar */}
      <div className="w-full max-w-6xl space-y-6">
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

        {/* Active Job Results */}
        {jobs.length > 0 && activeJobData && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-lg font-semibold">{activeJobData.ticker}</h4>
                <p className="text-sm text-gray-500">Job ID: {activeJobData.id}</p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  activeJobData.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : activeJobData.status === 'failed'
                    ? 'bg-red-100 text-red-800'
                    : activeJobData.status === 'running'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {activeJobData.status.charAt(0).toUpperCase() + activeJobData.status.slice(1)}
              </span>
            </div>

            {/* Progress Display */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">{activeJobData.currentStep}</span>
                <span className="font-medium">{activeJobData.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${activeJobData.progress}%` }}
                ></div>
              </div>
            </div>

            {activeJobData.error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-600 text-sm font-medium">{activeJobData.error}</p>
                {activeJobData.suggestion && (
                  <div className="mt-2">
                    <button className="text-sm text-primary-600 hover:text-primary-800">
                      Get AI Suggestion
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeJobData.result?.data_sources && (
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(activeJobData.result.data_sources).map(([key, value]: [string, any]) => (
                  value && (
                    <DataSourceBadge
                      key={key}
                      source={value.type}
                      label={key}
                    />
                  )
                ))}
              </div>
            )}

            {/* COMPLETED RESULTS */}
            {activeJobData.status === 'completed' && activeJobData.result && (
              <div className="mt-6 space-y-6">
                {/* 1. CHART - Always visible at top */}
                {activeJobData.result.technical_analysis && (
                  <TechnicalAnalysisChart
                    data={activeJobData.result.technical_analysis}
                    riskAssessment={activeJobData.result.risk_assessment as RiskAssessmentData}
                  />
                )}

                {/* 2. RISK ASSESSMENT - High-level summary below chart */}
                {activeJobData.result.risk_assessment && (
                  <RiskAssessmentCard data={activeJobData.result.risk_assessment as RiskAssessmentData} />
                )}

                {/* 3. COLLAPSIBLE SECTIONS - Rest of the analysis */}
                <div className="space-y-4">
                  {/* Technical Indicators Section */}
                  {activeJobData.result.technical_analysis && (
                    <CollapsibleSection
                      title="Technical Indicators"
                      isOpen={!collapsedStates[activeJobData.id]?.technicalIndicators}
                      onToggle={() => toggleSection(activeJobData.id, 'technicalIndicators')}
                      icon={
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                      }
                      badge={
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          activeJobData.result.technical_analysis.overall_signal === 'strong_buy' || activeJobData.result.technical_analysis.overall_signal === 'buy'
                            ? 'bg-green-100 text-green-800'
                            : activeJobData.result.technical_analysis.overall_signal === 'strong_sell' || activeJobData.result.technical_analysis.overall_signal === 'sell'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {activeJobData.result.technical_analysis.overall_signal?.toUpperCase().replace('_', ' ')}
                        </span>
                      }
                    >
                      <TechnicalIndicatorsPanel data={activeJobData.result.technical_analysis} />
                    </CollapsibleSection>
                  )}

                  {/* Growth Analysis Section */}
                  {(activeJobData.result.composite_score !== undefined || activeJobData.result.fundamental_score !== undefined) && (
                    <CollapsibleSection
                      title="Growth Analysis"
                      isOpen={!collapsedStates[activeJobData.id]?.growthAnalysis}
                      onToggle={() => toggleSection(activeJobData.id, 'growthAnalysis')}
                      icon={
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                      }
                      badge={
                        activeJobData.result.composite_score !== undefined && (
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            activeJobData.result.composite_score >= 7
                              ? 'bg-green-100 text-green-800'
                              : activeJobData.result.composite_score >= 5
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            Score: {safeToFixed(activeJobData.result.composite_score, 1)}/10
                          </span>
                        )
                      }
                    >
                      <GrowthAnalysisCard data={activeJobData.result} ticker={activeJobData.ticker} />
                    </CollapsibleSection>
                  )}

                  {/* AI Analysis Section */}
                  {(activeJobData.result.recommendation_reasoning || activeJobData.result.ai_summary || activeJobData.result.risks?.length > 0) && (
                    <CollapsibleSection
                      title="AI Analysis"
                      isOpen={!collapsedStates[activeJobData.id]?.aiAnalysis}
                      onToggle={() => toggleSection(activeJobData.id, 'aiAnalysis')}
                      icon={
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                      }
                      badge={
                        activeJobData.result.recommendation && (
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            activeJobData.result.recommendation === 'strong_buy' || activeJobData.result.recommendation === 'buy'
                              ? 'bg-green-100 text-green-800'
                              : activeJobData.result.recommendation === 'strong_sell' || activeJobData.result.recommendation === 'sell'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {activeJobData.result.recommendation?.toUpperCase().replace('_', ' ')}
                          </span>
                        )
                      }
                    >
                      <div className="space-y-4">
                        {/* Recommendation */}
                        {activeJobData.result.recommendation && (
                          <div className="p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">AI Recommendation</span>
                              <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                                activeJobData.result.recommendation === 'strong_buy' || activeJobData.result.recommendation === 'buy'
                                  ? 'bg-green-100 text-green-800'
                                  : activeJobData.result.recommendation === 'strong_sell' || activeJobData.result.recommendation === 'sell'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {activeJobData.result.recommendation?.toUpperCase().replace('_', ' ')}
                              </span>
                            </div>
                            {activeJobData.result.confidence_score && (
                              <div className="text-sm text-gray-600">
                                Confidence: {safeToFixed(activeJobData.result.confidence_score * 100, 0)}%
                              </div>
                            )}
                          </div>
                        )}

                        {/* Company Info */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {activeJobData.result.current_price && (
                            <div className="bg-white border rounded-lg p-3">
                              <div className="text-xs text-gray-500">Price</div>
                              <div className="text-lg font-semibold">${safeToFixed(activeJobData.result.current_price, 2)}</div>
                            </div>
                          )}
                          {activeJobData.result.pe_ratio && (
                            <div className="bg-white border rounded-lg p-3">
                              <div className="text-xs text-gray-500">P/E Ratio</div>
                              <div className="text-lg font-semibold">{activeJobData.result.pe_ratio}</div>
                            </div>
                          )}
                          {activeJobData.result.rsi && (
                            <div className="bg-white border rounded-lg p-3">
                              <div className="text-xs text-gray-500">RSI (14)</div>
                              <div className="text-lg font-semibold">{safeToFixed(activeJobData.result.rsi, 1)}</div>
                            </div>
                          )}
                          {activeJobData.result.sma_20 && (
                            <div className="bg-white border rounded-lg p-3">
                              <div className="text-xs text-gray-500">SMA 20</div>
                              <div className="text-lg font-semibold">${safeToFixed(activeJobData.result.sma_20, 2)}</div>
                            </div>
                          )}
                        </div>

                        {/* Reasoning */}
                        {activeJobData.result.recommendation_reasoning && (
                          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                            <div className="text-sm font-medium text-blue-800 mb-1">Analysis</div>
                            <p className="text-sm text-blue-700">{activeJobData.result.recommendation_reasoning}</p>
                          </div>
                        )}

                        {/* Risks & Opportunities */}
                        <div className="grid md:grid-cols-2 gap-4">
                          {activeJobData.result.risks && activeJobData.result.risks.length > 0 && (
                            <div className="p-4 bg-red-50 border border-red-100 rounded-lg">
                              <div className="text-sm font-medium text-red-700 mb-2">Risks</div>
                              <ul className="text-sm text-red-600 space-y-1">
                                {activeJobData.result.risks.slice(0, 5).map((risk: string, i: number) => (
                                  <li key={i} className="flex items-start">
                                    <span className="text-red-500 mr-2">-</span>
                                    {risk}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {activeJobData.result.opportunities && activeJobData.result.opportunities.length > 0 && (
                            <div className="p-4 bg-green-50 border border-green-100 rounded-lg">
                              <div className="text-sm font-medium text-green-700 mb-2">Opportunities</div>
                              <ul className="text-sm text-green-600 space-y-1">
                                {activeJobData.result.opportunities.slice(0, 5).map((opp: string, i: number) => (
                                  <li key={i} className="flex items-start">
                                    <span className="text-green-500 mr-2">+</span>
                                    {opp}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    </CollapsibleSection>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty state when no jobs */}
        {jobs.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg
              className="w-16 h-16 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start Your First Research</h3>
            <p className="text-gray-500">
              Enter a stock ticker in the search box above to begin analyzing
            </p>
          </div>
        )}

        {/* Empty state when jobs exist but no active job selected */}
        {jobs.length > 0 && !activeJobData && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg
              className="w-16 h-16 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Research Selected</h3>
            <p className="text-gray-500">
              Select a research from the sidebar or start a new search
            </p>
          </div>
        )}
      </div>

      {/* Sidebar Column - Research History (Right Side, Separate Column) */}
      {showSidebar && (
        <ResearchSidebar
          jobs={jobs}
          activeJobId={activeJob}
          onSelectJob={handleSelectJob}
        />
      )}
    </div>
  )
}
