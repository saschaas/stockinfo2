interface KeyInsightsProps {
  strengths?: string[]
  risks?: string[]
  catalysts?: string[]
  monitoringPoints?: string[]
}

export default function KeyInsights({ strengths, risks, catalysts, monitoringPoints }: KeyInsightsProps) {
  return (
    <div className="grid md:grid-cols-2 gap-4">
      {/* Key Strengths */}
      {strengths && strengths.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center mb-3">
            <svg className="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <h4 className="text-sm font-semibold text-green-900">Key Strengths</h4>
          </div>
          <ul className="space-y-2">
            {strengths.map((strength, idx) => (
              <li key={idx} className="flex items-start text-sm text-green-800">
                <span className="text-green-600 mr-2 flex-shrink-0">✓</span>
                <span>{strength}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Key Risks */}
      {risks && risks.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center mb-3">
            <svg className="w-5 h-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <h4 className="text-sm font-semibold text-red-900">Key Risks</h4>
          </div>
          <ul className="space-y-2">
            {risks.map((risk, idx) => (
              <li key={idx} className="flex items-start text-sm text-red-800">
                <span className="text-red-600 mr-2 flex-shrink-0">⚠</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Catalyst Points */}
      {catalysts && catalysts.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center mb-3">
            <svg className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
            </svg>
            <h4 className="text-sm font-semibold text-blue-900">Catalysts</h4>
          </div>
          <ul className="space-y-2">
            {catalysts.map((catalyst, idx) => (
              <li key={idx} className="flex items-start text-sm text-blue-800">
                <span className="text-blue-600 mr-2 flex-shrink-0">▲</span>
                <span>{catalyst}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Monitoring Points */}
      {monitoringPoints && monitoringPoints.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center mb-3">
            <svg className="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
            </svg>
            <h4 className="text-sm font-semibold text-yellow-900">Monitor</h4>
          </div>
          <ul className="space-y-2">
            {monitoringPoints.map((point, idx) => (
              <li key={idx} className="flex items-start text-sm text-yellow-800">
                <span className="text-yellow-600 mr-2 flex-shrink-0">👁</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
