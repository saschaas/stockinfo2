import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchHealthStatus } from '../../services/api'

interface HealthCheck {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  message: string
}

export default function DataSourceHealth() {
  const [isExpanded, setIsExpanded] = useState(false)

  const { data: healthData, isLoading } = useQuery({
    queryKey: ['healthStatus'],
    queryFn: fetchHealthStatus,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (isLoading || !healthData) {
    return null
  }

  const allChecks = healthData.checks || []

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-success-500'
      case 'degraded':
        return 'bg-warning-500'
      case 'unhealthy':
        return 'bg-danger-500'
      default:
        return 'bg-gray-500'
    }
  }

  const healthyCount = allChecks.filter((c: HealthCheck) => c.status === 'healthy').length
  const degradedCount = allChecks.filter((c: HealthCheck) => c.status === 'degraded').length
  const unhealthyCount = allChecks.filter((c: HealthCheck) => c.status === 'unhealthy').length

  return (
    <div className="card card-body bg-white">
      {/* Compact Header - Always Visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between hover:bg-gray-50 -m-4 p-4 rounded-lg transition-colors"
      >
        <div className="flex items-center gap-3">
          <svg
            className="w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
          <span className="text-sm font-medium text-gray-700">Data Sources</span>

          {/* Compact Status List */}
          <div className="flex items-center gap-2 flex-wrap">
            {allChecks.map((check: HealthCheck, index: number) => (
              <div key={index} className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${getStatusDot(check.status)}`} />
                <span className="text-xs text-gray-600">{check.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Summary + Expand Icon */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            {healthyCount > 0 && (
              <span className="text-success-600 font-medium">{healthyCount} healthy</span>
            )}
            {degradedCount > 0 && (
              <span className="text-warning-600 font-medium">{degradedCount} degraded</span>
            )}
            {unhealthyCount > 0 && (
              <span className="text-danger-600 font-medium">{unhealthyCount} unhealthy</span>
            )}
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {allChecks.map((check: HealthCheck, index: number) => (
              <div
                key={index}
                className={`flex items-center gap-3 p-3 rounded-lg border ${
                  check.status === 'healthy'
                    ? 'border-success-200 bg-success-50'
                    : check.status === 'degraded'
                    ? 'border-warning-200 bg-warning-50'
                    : 'border-danger-200 bg-danger-50'
                }`}
              >
                <div className="flex-shrink-0">
                  <span className={`inline-block w-3 h-3 rounded-full ${getStatusDot(check.status)}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900">{check.name}</div>
                  <p className="text-xs text-gray-600 truncate" title={check.message}>
                    {check.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
