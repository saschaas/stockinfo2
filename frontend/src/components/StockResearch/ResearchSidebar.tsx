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
        bg: 'bg-green-100',
        text: 'text-green-800',
        label: 'Completed',
      }
    case 'running':
      return {
        bg: 'bg-blue-100',
        text: 'text-blue-800',
        label: 'Running',
      }
    case 'pending':
      return {
        bg: 'bg-yellow-100',
        text: 'text-yellow-800',
        label: 'Pending',
      }
    case 'failed':
      return {
        bg: 'bg-red-100',
        text: 'text-red-800',
        label: 'Failed',
      }
    default:
      return {
        bg: 'bg-gray-100',
        text: 'text-gray-800',
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
      <div className="bg-white rounded-lg shadow-lg overflow-hidden sticky top-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-4 py-3">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-white"
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
            <h3 className="text-white font-semibold">Research History</h3>
          </div>
          <p className="text-primary-100 text-xs mt-1">
            {sidebarJobs.length} previous {sidebarJobs.length === 1 ? 'search' : 'searches'}
          </p>
        </div>

        {/* Job List */}
        <div className="divide-y divide-gray-100 max-h-[calc(100vh-200px)] overflow-y-auto">
          {sidebarJobs.map((job) => {
            const statusBadge = getStatusBadge(job.status)
            const isInProgress = job.status === 'pending' || job.status === 'running'

            return (
              <button
                key={job.id}
                onClick={() => onSelectJob(job.id)}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors focus:outline-none focus:bg-gray-50 group"
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
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge.bg} ${statusBadge.text}`}
                      >
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
                          <span className="truncate max-w-[180px]">{job.currentStep}</span>
                          <span className="ml-2 flex-shrink-0">{job.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Error indicator for failed jobs */}
                    {job.status === 'failed' && job.error && (
                      <p className="text-xs text-red-600 mt-1 truncate">
                        {job.error}
                      </p>
                    )}
                  </div>

                  {/* Arrow indicator */}
                  <svg
                    className="w-5 h-5 text-gray-400 group-hover:text-primary-500 transition-colors flex-shrink-0 ml-2"
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
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500 text-center">
            Click to view details
          </p>
        </div>
      </div>
    </div>
  )
}
