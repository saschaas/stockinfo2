import { useResearchStore } from '../../stores/researchStore'
import { useJobProgress } from '../../hooks/useWebSocket'

interface ProgressTrackerProps {
  jobId: string
  progress: number
  currentStep: string
}

export default function ProgressTracker({
  jobId,
  progress,
  currentStep,
}: ProgressTrackerProps) {
  const updateJob = useResearchStore((state) => state.updateJob)

  useJobProgress(jobId, (data) => {
    if (data.type === 'progress') {
      updateJob(jobId, {
        progress: data.progress,
        currentStep: data.current_step,
        status: data.status,
      })
    } else if (data.type === 'complete') {
      updateJob(jobId, {
        status: 'completed',
        progress: 100,
        result: data.result,
      })
    } else if (data.type === 'error') {
      updateJob(jobId, {
        status: 'failed',
        error: data.error,
        suggestion: data.suggestion,
      })
    }
  })

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{currentStep}</span>
        <span className="font-medium">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
    </div>
  )
}
