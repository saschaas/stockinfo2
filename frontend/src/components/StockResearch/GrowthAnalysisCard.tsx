import DataQualityBadge from './DataQualityBadge'
import RiskIndicator from './RiskIndicator'
import PortfolioAllocation from './PortfolioAllocation'
import PriceTargets from './PriceTargets'
import KeyInsights from './KeyInsights'
import ScoringBreakdown from './ScoringBreakdown'
import DataSourcesTable from './DataSourcesTable'

interface GrowthAnalysisData {
  // Scoring
  composite_score?: number
  fundamental_score?: number
  sentiment_score?: number
  technical_score?: number
  competitive_score?: number
  risk_score?: number

  // Recommendation
  recommendation?: string
  confidence_score?: number
  portfolio_allocation?: number

  // Price Targets
  current_price?: number
  price_target_base?: number
  price_target_optimistic?: number
  price_target_pessimistic?: number
  upside_potential?: number

  // Risk
  risk_level?: string

  // Insights
  key_strengths?: string[]
  key_risks?: string[]
  catalyst_points?: string[]
  monitoring_points?: string[]

  // AI Analysis
  ai_summary?: string
  ai_reasoning?: string

  // Data Quality
  data_completeness_score?: number
  missing_data_categories?: string[]

  // Data Sources
  data_sources?: Record<string, { type: string; name: string }>
}

interface GrowthAnalysisCardProps {
  data: GrowthAnalysisData
}

export default function GrowthAnalysisCard({ data }: GrowthAnalysisCardProps) {
  // Check if we have growth analysis data
  const hasGrowthAnalysis = data.composite_score !== undefined && data.composite_score !== null

  if (!hasGrowthAnalysis) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-medium mb-1">Growth Analysis Not Available</p>
        <p className="text-xs text-blue-600">
          This analysis was performed before the growth analysis agent was implemented.
          Run a new analysis to see comprehensive multi-factor scoring and insights.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-xl font-bold text-gray-900 mb-2">Growth Stock Analysis</h4>
          {data.ai_summary && (
            <p className="text-sm text-gray-700 leading-relaxed">{data.ai_summary}</p>
          )}
        </div>
        {data.data_completeness_score !== undefined && (
          <DataQualityBadge
            completenessScore={data.data_completeness_score}
            missingCategories={data.missing_data_categories}
          />
        )}
      </div>

      {/* AI Detailed Reasoning */}
      {data.ai_reasoning && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h5 className="text-sm font-semibold text-gray-900 mb-2">Investment Thesis</h5>
          <p className="text-sm text-gray-700 leading-relaxed">{data.ai_reasoning}</p>
        </div>
      )}

      {/* Top Metrics Row */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Portfolio Allocation */}
        {data.portfolio_allocation !== undefined && data.recommendation && data.confidence_score !== undefined && (
          <PortfolioAllocation
            allocation={data.portfolio_allocation}
            recommendation={data.recommendation}
            confidenceScore={data.confidence_score}
          />
        )}

        {/* Risk Indicator */}
        {data.risk_level && data.risk_score !== undefined && (
          <RiskIndicator
            riskLevel={data.risk_level}
            riskScore={data.risk_score}
          />
        )}
      </div>

      {/* Price Targets */}
      {data.current_price !== undefined &&
       data.price_target_base !== undefined &&
       data.price_target_optimistic !== undefined &&
       data.price_target_pessimistic !== undefined &&
       data.upside_potential !== undefined && (
        <PriceTargets
          currentPrice={data.current_price}
          baseTarget={data.price_target_base}
          optimisticTarget={data.price_target_optimistic}
          pessimisticTarget={data.price_target_pessimistic}
          upsidePotential={data.upside_potential}
        />
      )}

      {/* Scoring Breakdown */}
      {data.composite_score !== undefined &&
       data.fundamental_score !== undefined &&
       data.sentiment_score !== undefined &&
       data.technical_score !== undefined &&
       data.competitive_score !== undefined && (
        <ScoringBreakdown
          compositeScore={data.composite_score}
          fundamentalScore={data.fundamental_score}
          sentimentScore={data.sentiment_score}
          technicalScore={data.technical_score}
          competitiveScore={data.competitive_score}
          riskAdjustedScore={data.risk_score !== undefined ? 10 - data.risk_score : 5}
        />
      )}

      {/* Key Insights */}
      <KeyInsights
        strengths={data.key_strengths}
        risks={data.key_risks}
        catalysts={data.catalyst_points}
        monitoringPoints={data.monitoring_points}
      />

      {/* Data Sources & Coverage */}
      <DataSourcesTable
        dataSources={data.data_sources}
        missingCategories={data.missing_data_categories}
        completenessScore={data.data_completeness_score}
      />
    </div>
  )
}
