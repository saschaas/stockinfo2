import type { ResearchJob } from '../../stores/researchStore'

interface ResearchSidebarProps {
  jobs: ResearchJob[]
  activeJobId: string | null
  onSelectJob: (jobId: string) => void
}

// Format date for display
const formatDate = (date: Date): string => {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date)
}

// Get status badge styling
const getStatusBadge = (status: ResearchJob['status']) => {
  switch (status) {
    case 'completed':
      return {
        bg: 'bg-success-50',
        text: 'text-success-700',
        dot: 'bg-success-500',
        label: 'Completed',
      }
    case 'running':
      return {
        bg: 'bg-primary-50',
        text: 'text-primary-700',
        dot: 'bg-primary-500',
        label: 'Running',
      }
    case 'pending':
      return {
        bg: 'bg-warning-50',
        text: 'text-warning-700',
        dot: 'bg-warning-500',
        label: 'Pending',
      }
    case 'failed':
      return {
        bg: 'bg-danger-50',
        text: 'text-danger-700',
        dot: 'bg-danger-500',
        label: 'Failed',
      }
    default:
      return {
        bg: 'bg-gray-100',
        text: 'text-gray-700',
        dot: 'bg-gray-500',
        label: 'Unknown',
      }
  }
}

export default function ResearchSidebar({
  jobs,
  activeJobId,
  onSelectJob,
}: ResearchSidebarProps) {
  // Filter out active job and sort by createdAt (most recent first)
  const sidebarJobs = jobs
    .filter((job) => job.id !== activeJobId)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())

  if (sidebarJobs.length === 0) {
    return null
  }

  return (
    <div className="w-72 flex-shrink-0">
      <div className="card overflow-hidden sticky top-6">
        {/* Header */}
        <div className="bg-cream-dark px-5 py-4 border-b border-border-warm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-primary-100 flex items-center justify-center">
              <svg
                className="w-4 h-4 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Research History</h3>
              <p className="text-xs text-gray-500">
                {sidebarJobs.length} previous {sidebarJobs.length === 1 ? 'search' : 'searches'}
              </p>
            </div>
          </div>
        </div>

        {/* Job List */}
        <div className="divide-y divide-border-warm max-h-[calc(100vh-250px)] overflow-y-auto">
          {sidebarJobs.map((job) => {
            const statusBadge = getStatusBadge(job.status)
            const isInProgress = job.status === 'pending' || job.status === 'running'

            return (
              <button
                key={job.id}
                onClick={() => onSelectJob(job.id)}
                className="w-full text-left px-5 py-4 hover:bg-cream transition-colors focus:outline-none focus:bg-cream group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Ticker */}
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900 text-lg group-hover:text-primary-600 transition-colors">
                        {job.ticker}
                      </span>
                      {/* Status Badge */}
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge.bg} ${statusBadge.text}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
                        {statusBadge.label}
                      </span>
                    </div>

                    {/* Date */}
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDate(new Date(job.createdAt))}
                    </p>

                    {/* Progress bar for in-progress jobs */}
                    {isInProgress && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span className="truncate max-w-[160px]">{job.currentStep}</span>
                          <span className="ml-2 flex-shrink-0">{job.progress}%</span>
                        </div>
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Error indicator for failed jobs */}
                    {job.status === 'failed' && job.error && (
                      <p className="text-xs text-danger-700 mt-1 truncate">
                        {job.error}
                      </p>
                    )}
                  </div>

                  {/* Arrow indicator */}
                  <svg
                    className="w-5 h-5 text-gray-300 group-hover:text-primary-500 transition-colors flex-shrink-0 ml-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </button>
            )
          })}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-3 bg-cream border-t border-border-warm">
          <p className="text-xs text-gray-400 text-center">
            Click to view research details
          </p>
        </div>
      </div>
    </div>
  )
}
