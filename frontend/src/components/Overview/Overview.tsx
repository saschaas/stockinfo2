import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchDataSourcesHealth,
  DataSourcesResponse,
  fetchScrapedWebsites,
  ScrapedWebsite,
} from '../../services/api'

// Human-readable names for data sources and categories
const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  alpha_vantage: 'Alpha Vantage',
  yahoo_finance: 'Yahoo Finance',
  sec_edgar: 'SEC EDGAR',
  ollama: 'Ollama LLM',
  openfigi: 'OpenFIGI',
  web_scraping: 'Web Scraping',
  database: 'PostgreSQL',
  redis: 'Redis Cache',
  celery: 'Celery Workers',
  nordvpn: 'NordVPN',
  // Data use categories
  dashboard_sentiment: 'Dashboard Sentiment',
  hot_stocks: 'Hot Stocks',
  hot_sectors: 'Hot Sectors',
  bad_sectors: 'Bad Sectors',
  analyst_ratings: 'Analyst Ratings',
  news: 'News',
  etf_holdings: 'ETF Holdings',
  etf_holding_changes: 'ETF Holding Changes',
  fund_holdings: 'Fund Holdings',
  fund_holding_changes: 'Fund Holding Changes',
}

// Icons for different source types
const SourceTypeIcon = ({ type }: { type: string }) => {
  if (type === 'api') {
    return (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    )
  }
  if (type === 'service') {
    return (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    )
  }
  // infrastructure
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
    </svg>
  )
}

// Status badge component
const StatusBadge = ({ status }: { status: string }) => {
  const styles = {
    healthy: 'bg-success-100 text-success-700 border-success-200',
    degraded: 'bg-warning-100 text-warning-700 border-warning-200',
    unhealthy: 'bg-danger-100 text-danger-700 border-danger-200',
    unknown: 'bg-gray-100 text-gray-700 border-gray-200',
  }

  const icons = {
    healthy: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    degraded: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    unhealthy: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    unknown: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${styles[status as keyof typeof styles] || styles.unknown}`}>
      {icons[status as keyof typeof icons] || icons.unknown}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

// Data flow arrow component
const FlowArrow = () => (
  <div className="flex items-center justify-center px-2">
    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
    </svg>
  </div>
)

// Tab flow row component
const TabFlowRow = ({
  tabName,
  dataTypes,
  sources
}: {
  tabName: string
  dataTypes: Array<{ name: string; primary: string; fallback: string | null }>
  sources: Record<string, { status: string; description: string; type: string; message: string }>
}) => {
  return (
    <div className="flex flex-col gap-3 p-4 bg-gray-50 rounded-xl">
      {/* Tab Name Header */}
      <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
        <div className="w-8 h-8 rounded-lg bg-primary-100 flex items-center justify-center">
          <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-gray-900">{tabName}</h3>
      </div>

      {/* Data Types Flow */}
      <div className="space-y-2">
        {dataTypes.map((dataType, idx) => {
          const primarySource = sources[dataType.primary]
          const fallbackSource = dataType.fallback ? sources[dataType.fallback] : null
          const isPrimaryUnavailable = primarySource?.status === 'unhealthy'
          const usingFallback = isPrimaryUnavailable && fallbackSource?.status === 'healthy'

          return (
            <div key={idx} className="flex items-center gap-2 flex-wrap">
              {/* Data Type */}
              <div className="flex-shrink-0 px-3 py-1.5 bg-white border border-gray-200 rounded-lg">
                <span className="text-xs font-medium text-gray-700">{dataType.name}</span>
              </div>

              <FlowArrow />

              {/* Primary Source */}
              <div className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
                isPrimaryUnavailable
                  ? 'bg-danger-50 border-danger-200'
                  : 'bg-white border-gray-200'
              }`}>
                <SourceTypeIcon type={primarySource?.type || 'api'} />
                <span className={`text-xs font-medium ${isPrimaryUnavailable ? 'text-danger-700 line-through' : 'text-gray-700'}`}>
                  {SOURCE_DISPLAY_NAMES[dataType.primary] || dataType.primary}
                </span>
                <StatusBadge status={primarySource?.status || 'unknown'} />
              </div>

              {/* Fallback Source (if exists) */}
              {dataType.fallback && (
                <>
                  <div className="flex items-center px-1">
                    <span className="text-xs text-gray-400 italic">fallback</span>
                    <svg className="w-4 h-4 text-gray-300 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </div>
                  <div className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
                    usingFallback
                      ? 'bg-warning-50 border-warning-200 ring-2 ring-warning-300'
                      : 'bg-gray-100 border-gray-200'
                  }`}>
                    <SourceTypeIcon type={fallbackSource?.type || 'api'} />
                    <span className={`text-xs font-medium ${usingFallback ? 'text-warning-700' : 'text-gray-500'}`}>
                      {SOURCE_DISPLAY_NAMES[dataType.fallback] || dataType.fallback}
                    </span>
                    {usingFallback && <span className="text-xs text-warning-600">(active)</span>}
                  </div>
                </>
              )}

              {/* No fallback warning */}
              {!dataType.fallback && isPrimaryUnavailable && (
                <span className="text-xs text-danger-600 italic">No fallback available</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Warning banner component
const WarningBanner = ({ warnings }: {
  warnings: DataSourcesResponse['warnings']
}) => {
  if (warnings.length === 0) return null

  return (
    <div className="space-y-3">
      {warnings.map((warning, idx) => (
        <div key={idx} className="card card-body bg-danger-50 border-danger-200">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-danger-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-danger-800">
                {SOURCE_DISPLAY_NAMES[warning.source] || warning.source_name} Unavailable
              </h4>
              <p className="text-sm text-danger-700 mt-1">{warning.message}</p>

              {warning.affected.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-danger-800 mb-2">Affected Features:</p>
                  <ul className="space-y-1">
                    {warning.affected.map((affected, affIdx) => (
                      <li key={affIdx} className="flex items-center gap-2 text-xs text-danger-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-danger-400" />
                        <span className="font-medium">{affected.tab}</span>
                        <span className="text-danger-500">-</span>
                        <span>{affected.data_type}</span>
                        {affected.fallback && (
                          <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
                            affected.fallback_available
                              ? 'bg-warning-100 text-warning-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {affected.fallback_available
                              ? `Using ${SOURCE_DISPLAY_NAMES[affected.fallback] || affected.fallback}`
                              : `Fallback ${SOURCE_DISPLAY_NAMES[affected.fallback] || affected.fallback} also unavailable`
                            }
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Source status card for the summary grid
const SourceStatusCard = ({
  sourceId,
  source
}: {
  sourceId: string
  source: { status: string; description: string; type: string; message: string }
}) => {
  const statusStyles = {
    healthy: 'border-success-200 bg-success-50',
    degraded: 'border-warning-200 bg-warning-50',
    unhealthy: 'border-danger-200 bg-danger-50',
    unknown: 'border-gray-200 bg-gray-50',
  }

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg border ${statusStyles[source.status as keyof typeof statusStyles] || statusStyles.unknown}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
        source.status === 'healthy' ? 'bg-success-100 text-success-600' :
        source.status === 'degraded' ? 'bg-warning-100 text-warning-600' :
        source.status === 'unhealthy' ? 'bg-danger-100 text-danger-600' :
        'bg-gray-100 text-gray-600'
      }`}>
        <SourceTypeIcon type={source.type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">
            {SOURCE_DISPLAY_NAMES[sourceId] || sourceId}
          </span>
          <StatusBadge status={source.status} />
        </div>
        <p className="text-xs text-gray-600 truncate" title={source.description}>
          {source.description}
        </p>
      </div>
    </div>
  )
}

// Scraped Websites Card Component
const ScrapedWebsitesCard = ({ websites }: { websites: ScrapedWebsite[] }) => {
  if (!websites || websites.length === 0) {
    return (
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Web Scraping Sources</h2>
            <p className="text-sm text-gray-500">Custom websites configured for data scraping</p>
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 text-center">
          <p className="text-sm text-gray-500">No custom websites configured yet.</p>
          <p className="text-xs text-gray-400 mt-1">Go to Configuration to add websites for scraping.</p>
        </div>
      </div>
    )
  }

  // Group websites by data_use categories (websites can appear in multiple categories)
  const groupedWebsites = websites.reduce((acc, website) => {
    // Use data_use_list if available, otherwise parse data_use
    const categories = website.data_use_list || website.data_use.split(',').map(s => s.trim())
    categories.forEach(cat => {
      const displayName = SOURCE_DISPLAY_NAMES[cat] || cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      if (!acc[displayName]) acc[displayName] = []
      // Avoid duplicates
      if (!acc[displayName].some(w => w.key === website.key)) {
        acc[displayName].push(website)
      }
    })
    return acc
  }, {} as Record<string, ScrapedWebsite[]>)

  return (
    <div className="card card-body bg-white">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Web Scraping Sources</h2>
          <p className="text-sm text-gray-500">{websites.length} custom website(s) configured for data scraping</p>
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(groupedWebsites).map(([category, categoryWebsites]) => (
          <div key={category} className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">{category}</span>
              <span className="text-gray-400 text-xs font-normal">({categoryWebsites.length} source{categoryWebsites.length !== 1 ? 's' : ''})</span>
            </h3>
            <div className="space-y-2">
              {categoryWebsites.map((website) => (
                <div
                  key={website.key}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    website.is_active
                      ? website.last_test_success
                        ? 'bg-success-50 border-success-200'
                        : website.last_test_success === false
                        ? 'bg-danger-50 border-danger-200'
                        : 'bg-white border-gray-200'
                      : 'bg-gray-100 border-gray-300'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{website.name}</span>
                      {!website.is_active && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">Inactive</span>
                      )}
                      {website.last_test_success === true && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-success-100 text-success-700 flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Verified
                        </span>
                      )}
                      {website.last_test_success === false && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-danger-100 text-danger-700 flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          Failed
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">{website.url}</p>
                    {website.description && (
                      <p className="text-xs text-gray-400 mt-1 italic">{website.description}</p>
                    )}
                  </div>
                  {website.last_test_at && (
                    <div className="text-right text-xs text-gray-400">
                      <div>Last tested:</div>
                      <div>{new Date(website.last_test_at).toLocaleDateString()}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Overview() {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dataSourcesHealth'],
    queryFn: fetchDataSourcesHealth,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Fetch scraped websites
  const { data: scrapedWebsites } = useQuery<ScrapedWebsite[]>({
    queryKey: ['scrapedWebsites'],
    queryFn: () => fetchScrapedWebsites(),
  })

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center animate-pulse">
          <svg className="w-6 h-6 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="card card-body bg-danger-50 border-danger-200">
        <p className="text-danger-700">Failed to load data sources information</p>
      </div>
    )
  }

  const checkedAt = new Date(data.checked_at).toLocaleString()

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Sources Overview</h1>
          <p className="text-gray-500 text-sm mt-1">
            View data flow and source status for each application tab
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-500">Last checked: {checkedAt}</span>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg
              className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isRefreshing ? 'Refreshing...' : 'Refresh Status'}
          </button>
        </div>
      </div>

      {/* Warnings Section */}
      {data.warnings.length > 0 && (
        <WarningBanner warnings={data.warnings} />
      )}

      {/* All Sources Status Grid */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">All Data Sources</h2>
            <p className="text-sm text-gray-500">Current status of all connected services and APIs</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(data.sources).map(([sourceId, source]) => (
            <SourceStatusCard key={sourceId} sourceId={sourceId} source={source} />
          ))}
        </div>
      </div>

      {/* Web Scraping Sources */}
      <ScrapedWebsitesCard websites={scrapedWebsites || []} />

      {/* Tab Data Flow Diagram */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Data Flow by Tab</h2>
            <p className="text-sm text-gray-500">See which data sources power each application tab</p>
          </div>
        </div>

        <div className="space-y-4">
          {Object.entries(data.tabs).map(([tabName, tabInfo]) => (
            <TabFlowRow
              key={tabName}
              tabName={tabName}
              dataTypes={tabInfo.data_types}
              sources={data.sources}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="card card-body bg-gray-50 border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Legend</h3>
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <StatusBadge status="healthy" />
            <span className="text-gray-600">Service is operational</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status="degraded" />
            <span className="text-gray-600">Service has issues but functional</span>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status="unhealthy" />
            <span className="text-gray-600">Service is unavailable</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 bg-warning-100 text-warning-700 rounded text-xs">fallback (active)</span>
            <span className="text-gray-600">Using fallback source</span>
          </div>
        </div>
      </div>
    </div>
  )
}
