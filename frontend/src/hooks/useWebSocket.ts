import { useEffect, useRef, useCallback } from 'react'

// Construct WebSocket URL based on current page URL (works with both normal and host networking)
// This allows WebSocket to work when accessing via IP address or domain
const getWsBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  // Use current page's host and protocol (http -> ws, https -> wss)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

const WS_BASE_URL = getWsBaseUrl()

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

  // Store callbacks in refs to avoid recreating connection on every render
  const onMessageRef = useRef(options.onMessage)
  const onConnectRef = useRef(options.onConnect)
  const onDisconnectRef = useRef(options.onDisconnect)
  const onErrorRef = useRef(options.onError)

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = options.onMessage
    onConnectRef.current = options.onConnect
    onDisconnectRef.current = options.onDisconnect
    onErrorRef.current = options.onError
  }, [options.onMessage, options.onConnect, options.onDisconnect, options.onError])

  const connect = useCallback(() => {
    // Close existing connection if any
    if (socketRef.current) {
      socketRef.current.close()
    }

    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/ws/${endpoint}`)

    ws.onopen = () => {
      onConnectRef.current?.()
      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)

      ws.onclose = () => {
        clearInterval(pingInterval)
        onDisconnectRef.current?.()
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
          onMessageRef.current?.(data)
        }
      } catch {
        onMessageRef.current?.(event.data)
      }
    }

    ws.onerror = (error) => {
      onErrorRef.current?.(error)
    }

    socketRef.current = ws
  }, [endpoint])

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
