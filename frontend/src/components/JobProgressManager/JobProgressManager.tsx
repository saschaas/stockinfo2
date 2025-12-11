import { useEffect, useRef, useCallback } from 'react'
import { useResearchStore } from '../../stores/researchStore'

// Construct WebSocket URL based on current page URL (works with both normal and host networking)
const getWsBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  // Use current page's host and protocol (http -> ws, https -> wss)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

const WS_BASE_URL = getWsBaseUrl()

/**
 * JobProgressManager maintains WebSocket connections for ALL pending/running jobs,
 * not just the active one. This ensures progress updates are received even when
 * jobs are displayed in the sidebar.
 */
export default function JobProgressManager() {
  const { jobs, updateJob } = useResearchStore()
  const connectionsRef = useRef<Map<string, WebSocket>>(new Map())
  const pingIntervalsRef = useRef<Map<string, number>>(new Map())
  const updateJobRef = useRef(updateJob)

  // Keep updateJob ref current without triggering re-renders
  useEffect(() => {
    updateJobRef.current = updateJob
  }, [updateJob])

  // Memoized function to create a connection for a job
  const createConnection = useCallback((jobId: string) => {
    // Skip if connection already exists
    if (connectionsRef.current.has(jobId)) {
      return
    }

    console.log(`Creating WebSocket connection for job ${jobId}`)
    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/ws/progress/${jobId}`)

    ws.onopen = () => {
      console.log(`Connected to job ${jobId}`)
      // Send ping every 30 seconds to keep connection alive
      const pingInterval = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
      pingIntervalsRef.current.set(jobId, pingInterval)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return

        if (data.type === 'progress') {
          updateJobRef.current(jobId, {
            progress: data.progress,
            currentStep: data.current_step,
            status: data.status,
          })
        } else if (data.type === 'complete') {
          updateJobRef.current(jobId, {
            status: 'completed',
            progress: 100,
            result: data.result,
          })
        } else if (data.type === 'error') {
          updateJobRef.current(jobId, {
            status: 'failed',
            error: data.error,
            suggestion: data.suggestion,
          })
        }
      } catch {
        // Ignore non-JSON messages
      }
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error for job ${jobId}:`, error)
    }

    ws.onclose = () => {
      console.log(`Disconnected from job ${jobId}`)
      // Clear ping interval on close
      const pingInterval = pingIntervalsRef.current.get(jobId)
      if (pingInterval) {
        clearInterval(pingInterval)
        pingIntervalsRef.current.delete(jobId)
      }
      connectionsRef.current.delete(jobId)
    }

    connectionsRef.current.set(jobId, ws)
  }, [])

  useEffect(() => {
    // Get all jobs that need WebSocket connections (pending or running)
    const activeJobs = jobs.filter(
      (job) => job.status === 'pending' || job.status === 'running'
    )
    const activeJobIds = new Set(activeJobs.map((job) => job.id))

    // Close connections for jobs that are no longer active
    connectionsRef.current.forEach((ws, jobId) => {
      if (!activeJobIds.has(jobId)) {
        console.log(`Closing connection for completed/failed job ${jobId}`)
        // Clear ping interval
        const pingInterval = pingIntervalsRef.current.get(jobId)
        if (pingInterval) {
          clearInterval(pingInterval)
          pingIntervalsRef.current.delete(jobId)
        }
        ws.close()
        connectionsRef.current.delete(jobId)
      }
    })

    // Create connections for new active jobs
    activeJobs.forEach((job) => {
      createConnection(job.id)
    })

    // Cleanup on unmount
    return () => {
      connectionsRef.current.forEach((ws, jobId) => {
        const pingInterval = pingIntervalsRef.current.get(jobId)
        if (pingInterval) {
          clearInterval(pingInterval)
        }
        ws.close()
      })
      connectionsRef.current.clear()
      pingIntervalsRef.current.clear()
    }
  }, [jobs, createConnection])

  // This component doesn't render anything
  return null
}
