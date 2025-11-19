import { useEffect, useRef, useCallback } from 'react'

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

interface UseWebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: any) => void
}

export function useWebSocket(
  endpoint: string,
  options: UseWebSocketOptions = {}
) {
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/ws/${endpoint}`)

    ws.onopen = () => {
      options.onConnect?.()
      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)

      ws.onclose = () => {
        clearInterval(pingInterval)
        options.onDisconnect?.()
        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 5000)
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type !== 'pong') {
          options.onMessage?.(data)
        }
      } catch {
        options.onMessage?.(event.data)
      }
    }

    ws.onerror = (error) => {
      options.onError?.(error)
    }

    socketRef.current = ws
  }, [endpoint, options])

  const send = useCallback((data: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        typeof data === 'string' ? data : JSON.stringify(data)
      )
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    socketRef.current?.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return { send, disconnect }
}

export function useJobProgress(
  jobId: string,
  onProgress: (data: any) => void
) {
  return useWebSocket(`progress/${jobId}`, {
    onMessage: onProgress,
    onConnect: () => console.log(`Connected to job ${jobId}`),
    onDisconnect: () => console.log(`Disconnected from job ${jobId}`),
  })
}
