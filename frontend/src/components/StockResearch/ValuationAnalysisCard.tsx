/**
 * ValuationAnalysisCard - Displays comprehensive company valuation analysis
 *
 * Shows:
 * - Company classification and reasoning
 * - Intrinsic value with range
 * - Margin of safety and valuation status
 * - WACC/Cost of Equity breakdown
 * - Valuation method results with weights
 * - Sensitivity analysis
 */

interface ValuationMethod {
  method: string
  weight: number
  fair_value: number
  confidence: number
}

interface MethodResult {
  fair_value: number
  weight: number
  confidence: number
  description?: string
  data_quality?: string
  assumptions?: Record<string, any>
}

interface ValuationData {
  // Company Classification
  valuation_company_type?: string
  valuation_classification_confidence?: number
  valuation_classification_reasons?: string[]

  // Intrinsic Value
  intrinsic_value?: number
  intrinsic_value_low?: number
  intrinsic_value_high?: number
  margin_of_safety?: number
  valuation_status?: string
  current_price?: number

  // Discount Rates
  valuation_wacc?: number
  valuation_cost_of_equity?: number
  valuation_risk_free_rate?: number

  // Method Details
  valuation_methods_used?: ValuationMethod[]
  valuation_primary_method?: string
  valuation_method_results?: Record<string, MethodResult>

  // Quality
  valuation_confidence?: number
  valuation_data_quality?: string
}

interface ValuationAnalysisCardProps {
  data: ValuationData
}

// Format company type for display
const formatCompanyType = (type?: string): string => {
  if (!type) return 'Not Classified'
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Format method name for display
const formatMethodName = (method: string): string => {
  const methodNames: Record<string, string> = {
    dcf_fcff: 'DCF (FCFF)',
    dcf_fcfe: 'DCF (FCFE)',
    ddm_gordon: 'Gordon Growth DDM',
    ddm_two_stage: 'Two-Stage DDM',
    ddm_h_model: 'H-Model DDM',
    relative_pe: 'P/E Multiple',
    relative_pb: 'P/B Multiple',
    relative_ps: 'P/S Multiple',
    relative_ev_ebitda: 'EV/EBITDA',
    relative_ev_revenue: 'EV/Revenue',
    asset_book_value: 'Book Value',
    asset_nav: 'Net Asset Value',
    asset_liquidation: 'Liquidation Value',
    growth_rule_40: 'Rule of 40',
    growth_ev_arr: 'EV/ARR',
  }
  return methodNames[method] || method
}

// Get valuation status color
const getStatusColor = (status?: string): string => {
  switch (status?.toLowerCase()) {
    case 'undervalued':
      return 'text-success-600 bg-success-50'
    case 'overvalued':
      return 'text-danger-600 bg-danger-50'
    case 'fairly_valued':
    case 'fairly valued':
      return 'text-warning-600 bg-warning-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}

// Format percentage
const formatPercent = (value?: number): string => {
  if (value === undefined || value === null) return 'N/A'
  return `${(value * 100).toFixed(2)}%`
}

// Format currency
const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null || isNaN(value)) return 'N/A'
  return `$${value.toFixed(2)}`
}

export default function ValuationAnalysisCard({ data }: ValuationAnalysisCardProps) {
  // Check if we have valuation data
  const hasValuation = data.intrinsic_value !== undefined && data.intrinsic_value > 0

  if (!hasValuation) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
        <p className="font-medium mb-1">Valuation Analysis Not Available</p>
        <p className="text-xs text-blue-600">
          Intrinsic value calculation requires sufficient financial data.
          Run a new analysis with a stock that has complete financial information.
        </p>
      </div>
    )
  }

  const marginOfSafety = data.margin_of_safety ?? 0
  const currentPrice = data.current_price ?? 0
  const intrinsicValue = data.intrinsic_value ?? 0
  const upside = currentPrice > 0 ? ((intrinsicValue - currentPrice) / currentPrice) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Header with Intrinsic Value Summary */}
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-sm font-medium text-primary-600 mb-1">Intrinsic Value</h4>
            <div className="text-3xl font-bold text-primary-900">
              {formatCurrency(data.intrinsic_value)}
            </div>
            <div className="text-sm text-primary-700 mt-1">
              Range: {formatCurrency(data.intrinsic_value_low)} - {formatCurrency(data.intrinsic_value_high)}
            </div>
          </div>
          <div className="text-right">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(data.valuation_status)}`}>
              {data.valuation_status?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
            </span>
            <div className="text-sm text-primary-600 mt-2">
              Current: {formatCurrency(currentPrice)}
            </div>
          </div>
        </div>

        {/* Margin of Safety / Upside */}
        <div className="mt-4 pt-4 border-t border-primary-200">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-primary-600 mb-1">Margin of Safety</div>
              <div className={`text-lg font-semibold ${marginOfSafety > 0 ? 'text-success-600' : 'text-danger-600'}`}>
                {(marginOfSafety * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-primary-600 mb-1">Upside Potential</div>
              <div className={`text-lg font-semibold ${upside > 0 ? 'text-success-600' : 'text-danger-600'}`}>
                {upside > 0 ? '+' : ''}{upside.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Company Classification */}
      {data.valuation_company_type && (
        <div className="bg-cream rounded-xl p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h5 className="text-sm font-semibold text-gray-900">Company Classification</h5>
              <div className="text-lg font-medium text-gray-800 mt-1">
                {formatCompanyType(data.valuation_company_type)}
              </div>
            </div>
            {data.valuation_classification_confidence !== undefined && (
              <div className="text-right">
                <div className="text-xs text-gray-500">Confidence</div>
                <div className="text-sm font-medium text-gray-700">
                  {(data.valuation_classification_confidence * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>
          {data.valuation_classification_reasons && data.valuation_classification_reasons.length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-gray-500 mb-1">Classification Reasons:</div>
              <ul className="text-sm text-gray-700 space-y-1">
                {data.valuation_classification_reasons.slice(0, 3).map((reason, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-primary-500 mr-2">•</span>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Discount Rates */}
      {(data.valuation_wacc || data.valuation_cost_of_equity) && (
        <div className="bg-gray-50 rounded-xl p-4">
          <h5 className="text-sm font-semibold text-gray-900 mb-3">Discount Rates</h5>
          <div className="grid grid-cols-3 gap-4">
            {data.valuation_risk_free_rate !== undefined && (
              <div>
                <div className="text-xs text-gray-500">Risk-Free Rate</div>
                <div className="text-lg font-semibold text-gray-900">
                  {formatPercent(data.valuation_risk_free_rate)}
                </div>
              </div>
            )}
            {data.valuation_cost_of_equity !== undefined && (
              <div>
                <div className="text-xs text-gray-500">Cost of Equity</div>
                <div className="text-lg font-semibold text-gray-900">
                  {formatPercent(data.valuation_cost_of_equity)}
                </div>
              </div>
            )}
            {data.valuation_wacc !== undefined && (
              <div>
                <div className="text-xs text-gray-500">WACC</div>
                <div className="text-lg font-semibold text-gray-900">
                  {formatPercent(data.valuation_wacc)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Valuation Methods Breakdown */}
      {data.valuation_methods_used && data.valuation_methods_used.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h5 className="text-sm font-semibold text-gray-900">Valuation Methods</h5>
            {data.valuation_primary_method && (
              <span className="text-xs text-gray-500">
                Primary: {formatMethodName(data.valuation_primary_method)}
              </span>
            )}
          </div>
          <div className="space-y-3">
            {data.valuation_methods_used.map((method, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div className="flex items-center space-x-3">
                  <div className="w-20">
                    <div
                      className="h-2 bg-primary-500 rounded-full"
                      style={{ width: `${method.weight * 100}%` }}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      {(method.weight * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {formatMethodName(method.method)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-900">
                    {formatCurrency(method.fair_value)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(method.confidence * 100).toFixed(0)}% confidence
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Quality Indicator */}
      {data.valuation_data_quality && (
        <div className="flex items-center justify-between text-sm text-gray-500 pt-2 border-t border-gray-100">
          <span>Data Quality: </span>
          <span className={`font-medium ${
            data.valuation_data_quality === 'high' ? 'text-success-600' :
            data.valuation_data_quality === 'medium' ? 'text-warning-600' :
            'text-danger-600'
          }`}>
            {data.valuation_data_quality.charAt(0).toUpperCase() + data.valuation_data_quality.slice(1)}
          </span>
          {data.valuation_confidence !== undefined && (
            <span className="ml-4">
              Overall Confidence: <span className="font-medium">{data.valuation_confidence.toFixed(0)}%</span>
            </span>
          )}
        </div>
      )}
    </div>
  )
}
