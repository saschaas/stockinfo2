import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { startStockResearch, fetchAvailableModels } from '../../services/api'
import { useResearchStore } from '../../stores/researchStore'
import JobProgressManager from '../JobProgressManager/JobProgressManager'
import DataSourceBadge from '../DataSourceBadge/DataSourceBadge'
import GrowthAnalysisCard from './GrowthAnalysisCard'
import ValuationAnalysisCard from './ValuationAnalysisCard'
import TechnicalAnalysisChart from './TechnicalAnalysisChart'
import TechnicalIndicatorsPanel from './TechnicalIndicatorsPanel'
import RiskAssessmentCard from './RiskAssessmentCard'
import CollapsibleSection from './CollapsibleSection'
import ResearchSidebar from './ResearchSidebar'
import { InvestmentDecisionCard, QuickMetrics, KeyTakeaways } from './ExecutiveSummary'
import { BullishFactorsCard, BearishFactorsCard } from './DecisionFactors'
import type { RiskAssessmentData } from '../../types/risk-assessment'

// Helper function to safely format numbers
const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === undefined || value === null || typeof value !== 'number' || isNaN(value)) return 'N/A'
  return value.toFixed(decimals)
}

// Convert any signal/score to simplified BUY/HOLD/SELL decision
const getSimplifiedDecision = (signal?: string, score?: number): { label: string; color: string } => {
  // If we have a signal string
  if (signal) {
    const s = signal.toLowerCase()
    if (s.includes('strong_buy') || s.includes('strong buy') || s === 'buy' || s.includes('bullish')) {
      return { label: 'BUY', color: 'badge-success' }
    }
    if (s.includes('strong_sell') || s.includes('strong sell') || s === 'sell' || s.includes('bearish')) {
      return { label: 'SELL', color: 'badge-danger' }
    }
  }

  // If we have a numeric score (0-10 scale)
  if (score !== undefined && score !== null) {
    if (score >= 7) return { label: 'BUY', color: 'badge-success' }
    if (score < 4) return { label: 'SELL', color: 'badge-danger' }
  }

  return { label: 'HOLD', color: 'badge-warning' }
}

// State type for collapsed sections per job
interface CollapsedSections {
  technicalIndicators: boolean
  growthAnalysis: boolean
  valuationAnalysis: boolean
  aiAnalysis: boolean
}

export default function StockResearch() {
  const [ticker, setTicker] = useState('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false)
  const { addJob, jobs, activeJob, setActiveJob } = useResearchStore()

  // Fetch available Ollama models on component mount
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['ollama-models'],
    queryFn: fetchAvailableModels,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
  })

  // Set default model when data loads
  useEffect(() => {
    if (modelsData?.default_model && !selectedModel) {
      // Find the full model name that matches the default
      const defaultModel = modelsData.models.find(
        m => m.name === modelsData.default_model ||
             m.name.startsWith(modelsData.default_model) ||
             m.display_name === modelsData.default_model
      )
      setSelectedModel(defaultModel?.name || modelsData.default_model)
    }
  }, [modelsData, selectedModel])

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
            valuationAnalysis: true,    // Collapsed by default
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

  // Handle batch jobs from Fund Tracker or ETF Tracker
  const location = useLocation()
  useEffect(() => {
    // Check if navigated from Fund Tracker or ETF Tracker with batch jobs
    if ((location.state?.fromFundTracker || location.state?.fromETFTracker) && location.state?.batchJobs) {
      const { batchJobs, errors } = location.state
      const source = location.state?.fromETFTracker ? 'ETF Tracker' : 'Fund Tracker'

      // Add jobs to the research store
      if (batchJobs && batchJobs.length > 0) {
        batchJobs.forEach(({ ticker, jobId }: { ticker: string; jobId: string }) => {
          addJob({
            id: jobId,
            ticker: ticker,
            status: 'pending',
            progress: 0,
            currentStep: 'Initializing research...',
            createdAt: new Date(),
          })
        })
        console.log(`Started analysis for ${batchJobs.length} stocks from ${source}:`, batchJobs.map((j: any) => j.ticker).join(', '))
      }

      // Log errors for failed tickers
      if (errors && errors.length > 0) {
        errors.forEach(({ ticker, error }: { ticker: string; error: string }) => {
          console.error(`Failed to analyze ${ticker}:`, error)
        })
      }

      // Clear navigation state to prevent re-triggering on refresh
      window.history.replaceState({}, document.title)
    }
  }, [location, addJob])

  const mutation = useMutation({
    mutationFn: (ticker: string) => startStockResearch(ticker, {
      llm_model: selectedModel || undefined,
    }),
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
          valuationAnalysis: true,
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

      {/* Main Content Column */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Stock Research</h1>
            <p className="text-gray-500 text-sm mt-1">AI-powered analysis and investment insights</p>
          </div>
        </div>

        {/* Research Form */}
        <div className="card card-body">
          <form onSubmit={handleSubmit} className="flex gap-4">
            <div className="flex-1">
              <label htmlFor="ticker" className="block text-sm font-medium text-gray-700 mb-2">
                Stock Ticker
              </label>
              <input
                type="text"
                id="ticker"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL, MSFT, GOOGL"
                className="input"
                maxLength={10}
              />
            </div>
            <div className="w-48">
              <label htmlFor="llm-model" className="block text-sm font-medium text-gray-700 mb-2">
                AI Model
              </label>
              <select
                id="llm-model"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="input"
                disabled={modelsLoading}
              >
                {modelsLoading ? (
                  <option value="">Loading models...</option>
                ) : modelsData?.error ? (
                  <option value="">Ollama unavailable</option>
                ) : modelsData?.models.length === 0 ? (
                  <option value="">No models found</option>
                ) : (
                  modelsData?.models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.display_name}
                    </option>
                  ))
                )}
              </select>
              {modelsData?.error && (
                <p className="text-xs text-danger-600 mt-1">{modelsData.error}</p>
              )}
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={!ticker.trim() || mutation.isPending}
                className="btn-primary h-[46px] px-8"
              >
                {mutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Starting...
                  </span>
                ) : 'Start Research'}
              </button>
            </div>
          </form>

          {mutation.isError && (
            <div className="mt-4 p-4 bg-danger-50 border border-danger-100 rounded-xl">
              <p className="text-danger-700 text-sm">
                {mutation.error instanceof Error
                  ? mutation.error.message
                  : 'Failed to start research'}
              </p>
            </div>
          )}
        </div>

        {/* Active Job Results */}
        {jobs.length > 0 && activeJobData && (
          <>
            {/* Job Status Card with Company Profile */}
            <div className="card card-body">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-primary-50 flex items-center justify-center">
                    <span className="text-xl font-bold text-primary-600">
                      {activeJobData.ticker.slice(0, 2)}
                    </span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{activeJobData.ticker}</h2>
                    {activeJobData.result?.company_name && (
                      <p className="text-base text-gray-700 font-medium">
                        {activeJobData.result.company_name}
                      </p>
                    )}
                    {(activeJobData.result?.sector || activeJobData.result?.industry) && (
                      <p className="text-sm text-gray-500">
                        {[activeJobData.result.sector, activeJobData.result.industry]
                          .filter(Boolean)
                          .join(' • ')}
                      </p>
                    )}
                  </div>
                </div>
                <span
                  className={`badge ${
                    activeJobData.status === 'completed'
                      ? 'badge-success'
                      : activeJobData.status === 'failed'
                      ? 'badge-danger'
                      : activeJobData.status === 'running'
                      ? 'badge-primary'
                      : 'badge-warning'
                  }`}
                >
                  {activeJobData.status.charAt(0).toUpperCase() + activeJobData.status.slice(1)}
                </span>
              </div>

              {/* Company Description */}
              {activeJobData.result?.description && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Company Overview
                    </h3>
                    <button
                      onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
                      className="text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
                    >
                      {isDescriptionExpanded ? 'Read less' : 'Read more'}
                    </button>
                  </div>
                  <p
                    className={`text-sm text-gray-700 leading-relaxed ${
                      isDescriptionExpanded ? '' : 'line-clamp-2'
                    }`}
                  >
                    {activeJobData.result.description}
                  </p>
                </div>
              )}

              {/* Progress Display */}
              {activeJobData.status !== 'completed' && (
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">{activeJobData.currentStep}</span>
                    <span className="font-medium text-primary-600">{activeJobData.progress}%</span>
                  </div>
                  <div className="progress-bar h-2.5">
                    <div
                      className="progress-fill"
                      style={{ width: `${activeJobData.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {activeJobData.error && (
                <div className="mt-4 p-4 bg-danger-50 border border-danger-100 rounded-xl">
                  <p className="text-danger-700 text-sm font-medium">{activeJobData.error}</p>
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
            </div>

            {/* COMPLETED RESULTS */}
            {activeJobData.status === 'completed' && activeJobData.result && (
              <div className="space-y-6 animate-fade-in">
                {/* LEVEL 1: Executive Summary - 3 column grid */}
                {activeJobData.result.risk_assessment && (
                  <section className="grid lg:grid-cols-3 gap-6">
                    <InvestmentDecisionCard
                      data={activeJobData.result.risk_assessment as RiskAssessmentData}
                    />
                    <QuickMetrics
                      riskAssessment={activeJobData.result.risk_assessment as RiskAssessmentData}
                      technicalAnalysis={activeJobData.result.technical_analysis}
                      priceTargets={activeJobData.result.price_targets}
                    />
                    <KeyTakeaways
                      riskAssessment={activeJobData.result.risk_assessment as RiskAssessmentData}
                      aiSummary={activeJobData.result.ai_summary}
                      keyStrengths={activeJobData.result.key_strengths}
                      keyRisks={activeJobData.result.key_risks}
                    />
                  </section>
                )}

                {/* LEVEL 2: Chart */}
                {activeJobData.result.technical_analysis && (
                  <section>
                    <TechnicalAnalysisChart
                      data={activeJobData.result.technical_analysis}
                      riskAssessment={activeJobData.result.risk_assessment as RiskAssessmentData}
                    />
                  </section>
                )}

                {/* LEVEL 3: Decision Factors - 2 column */}
                {activeJobData.result.risk_assessment && (
                  <section className="grid md:grid-cols-2 gap-6">
                    <BullishFactorsCard
                      bullishFactors={(activeJobData.result.risk_assessment as RiskAssessmentData).bullish_factors}
                      strengths={activeJobData.result.key_strengths}
                      catalysts={activeJobData.result.catalysts}
                      opportunities={activeJobData.result.opportunities}
                    />
                    <BearishFactorsCard
                      bearishFactors={(activeJobData.result.risk_assessment as RiskAssessmentData).bearish_factors}
                      keyRisks={(activeJobData.result.risk_assessment as RiskAssessmentData).key_risks}
                      risks={activeJobData.result.risks}
                    />
                  </section>
                )}

                {/* LEVEL 4: Deep Dive - Collapsible Sections */}
                <section className="space-y-4">
                  {/* Risk Assessment Details */}
                  {activeJobData.result.risk_assessment && (
                    <RiskAssessmentCard data={activeJobData.result.risk_assessment as RiskAssessmentData} />
                  )}

                  {/* Technical Indicators Section */}
                  {activeJobData.result.technical_analysis && (() => {
                    const techDecision = getSimplifiedDecision(activeJobData.result.technical_analysis.overall_signal)
                    return (
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
                          <span className={`badge ${techDecision.color}`}>
                            {techDecision.label}
                          </span>
                        }
                      >
                        <TechnicalIndicatorsPanel data={activeJobData.result.technical_analysis} />
                      </CollapsibleSection>
                    )
                  })()}

                  {/* Growth Analysis Section */}
                  {(activeJobData.result.composite_score !== undefined || activeJobData.result.fundamental_score !== undefined) && (() => {
                    const growthDecision = getSimplifiedDecision(undefined, activeJobData.result.composite_score)
                    return (
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
                          <span className={`badge ${growthDecision.color}`}>
                            {growthDecision.label}
                          </span>
                        }
                      >
                        <GrowthAnalysisCard data={activeJobData.result} ticker={activeJobData.ticker} />
                      </CollapsibleSection>
                    )
                  })()}

                  {/* Valuation Analysis Section */}
                  {activeJobData.result.intrinsic_value !== undefined && activeJobData.result.intrinsic_value > 0 && (() => {
                    const valuationStatus = activeJobData.result.valuation_status?.toLowerCase()
                    const valuationDecision = valuationStatus === 'undervalued'
                      ? { label: 'BUY', color: 'badge-success' }
                      : valuationStatus === 'overvalued'
                      ? { label: 'SELL', color: 'badge-danger' }
                      : { label: 'HOLD', color: 'badge-warning' }
                    return (
                      <CollapsibleSection
                        title="Valuation Analysis"
                        isOpen={!collapsedStates[activeJobData.id]?.valuationAnalysis}
                        onToggle={() => toggleSection(activeJobData.id, 'valuationAnalysis')}
                        icon={
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        }
                        badge={
                          <span className={`badge ${valuationDecision.color}`}>
                            {valuationDecision.label}
                          </span>
                        }
                      >
                        <ValuationAnalysisCard data={activeJobData.result} />
                      </CollapsibleSection>
                    )
                  })()}

                  {/* AI Analysis Section */}
                  {(activeJobData.result.recommendation_reasoning || activeJobData.result.ai_summary || activeJobData.result.risks?.length > 0) && (() => {
                    const aiDecision = getSimplifiedDecision(activeJobData.result.recommendation)
                    return (
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
                          <span className={`badge ${aiDecision.color}`}>
                            {aiDecision.label}
                          </span>
                        }
                      >
                      <div className="space-y-4">
                        {/* Recommendation */}
                        {activeJobData.result.recommendation && (
                          <div className="p-4 bg-cream rounded-xl">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-700">AI Recommendation</span>
                              <span className={`decision-badge ${
                                activeJobData.result.recommendation === 'strong_buy' || activeJobData.result.recommendation === 'buy'
                                  ? 'bg-success-50 text-success-700'
                                  : activeJobData.result.recommendation === 'strong_sell' || activeJobData.result.recommendation === 'sell'
                                  ? 'bg-danger-50 text-danger-700'
                                  : 'bg-warning-50 text-warning-700'
                              }`}>
                                {activeJobData.result.recommendation?.toUpperCase().replace('_', ' ')}
                              </span>
                            </div>
                            {activeJobData.result.confidence_score && (
                              <div className="text-sm text-gray-600">
                                Confidence: <span className="font-semibold">{safeToFixed(activeJobData.result.confidence_score * 100, 0)}%</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Company Info */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {activeJobData.result.current_price && (
                            <div className="bg-cream rounded-xl p-4">
                              <div className="text-xs text-gray-500 mb-1">Price</div>
                              <div className="text-lg font-semibold text-gray-900">${safeToFixed(activeJobData.result.current_price, 2)}</div>
                            </div>
                          )}
                          {activeJobData.result.pe_ratio && (
                            <div className="bg-cream rounded-xl p-4">
                              <div className="text-xs text-gray-500 mb-1">P/E Ratio</div>
                              <div className="text-lg font-semibold text-gray-900">{activeJobData.result.pe_ratio}</div>
                            </div>
                          )}
                          {activeJobData.result.rsi && (
                            <div className="bg-cream rounded-xl p-4">
                              <div className="text-xs text-gray-500 mb-1">RSI (14)</div>
                              <div className="text-lg font-semibold text-gray-900">{safeToFixed(activeJobData.result.rsi, 1)}</div>
                            </div>
                          )}
                          {activeJobData.result.sma_20 && (
                            <div className="bg-cream rounded-xl p-4">
                              <div className="text-xs text-gray-500 mb-1">SMA 20</div>
                              <div className="text-lg font-semibold text-gray-900">${safeToFixed(activeJobData.result.sma_20, 2)}</div>
                            </div>
                          )}
                        </div>

                        {/* Reasoning */}
                        {activeJobData.result.recommendation_reasoning && (
                          <div className="p-4 bg-primary-50 border border-primary-100 rounded-xl">
                            <div className="text-sm font-medium text-primary-800 mb-1">Analysis</div>
                            <p className="text-sm text-primary-700">{activeJobData.result.recommendation_reasoning}</p>
                          </div>
                        )}

                        {/* Risks & Opportunities */}
                        <div className="grid md:grid-cols-2 gap-4">
                          {activeJobData.result.risks && activeJobData.result.risks.length > 0 && (
                            <div className="p-4 bg-danger-50 border border-danger-100 rounded-xl">
                              <div className="text-sm font-medium text-danger-700 mb-2">Risks</div>
                              <ul className="text-sm text-danger-600 space-y-1">
                                {activeJobData.result.risks.slice(0, 5).map((risk: string, i: number) => (
                                  <li key={i} className="flex items-start">
                                    <span className="text-danger-500 mr-2">-</span>
                                    {risk}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {activeJobData.result.opportunities && activeJobData.result.opportunities.length > 0 && (
                            <div className="p-4 bg-success-50 border border-success-100 rounded-xl">
                              <div className="text-sm font-medium text-success-700 mb-2">Opportunities</div>
                              <ul className="text-sm text-success-600 space-y-1">
                                {activeJobData.result.opportunities.slice(0, 5).map((opp: string, i: number) => (
                                  <li key={i} className="flex items-start">
                                    <span className="text-success-500 mr-2">+</span>
                                    {opp}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    </CollapsibleSection>
                    )
                  })()}
                </section>
              </div>
            )}
          </>
        )}

        {/* Empty state when no jobs */}
        {jobs.length === 0 && (
          <div className="card card-body text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-primary-50 flex items-center justify-center">
              <svg
                className="w-10 h-10 text-primary-400"
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
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Start Your First Research</h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Enter a stock ticker in the search box above to get AI-powered analysis, technical indicators, and investment insights.
            </p>
          </div>
        )}

        {/* Empty state when jobs exist but no active job selected */}
        {jobs.length > 0 && !activeJobData && (
          <div className="card card-body text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-primary-50 flex items-center justify-center">
              <svg
                className="w-10 h-10 text-primary-400"
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
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Research Selected</h3>
            <p className="text-gray-500">
              Select a research from the sidebar or start a new search
            </p>
          </div>
        )}
      </div>

      {/* Sidebar Column - Research History */}
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
