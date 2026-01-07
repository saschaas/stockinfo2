import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchTriggeredAlerts, dismissAlert as dismissAlertApi } from '../services/api'
import type { TriggeredAlertResponse } from '../types'

interface AlertNotificationStore {
  // List of triggered alerts not yet dismissed
  triggeredAlerts: TriggeredAlertResponse[]
  // Whether there are any unread alerts (for badge)
  hasUnreadAlerts: boolean
  // Last time we checked for alerts
  lastCheckedAt: string | null
  // Loading state
  isLoading: boolean
  // Error state
  error: string | null

  // Actions
  fetchAlerts: () => Promise<void>
  dismissAlert: (alertId: number) => Promise<void>
  addAlert: (alert: TriggeredAlertResponse) => void
  markAllAsRead: () => void
  clearAlerts: () => void
}

export const useAlertNotificationStore = create<AlertNotificationStore>()(
  persist(
    (set, get) => ({
      triggeredAlerts: [],
      hasUnreadAlerts: false,
      lastCheckedAt: null,
      isLoading: false,
      error: null,

      fetchAlerts: async () => {
        const { isLoading } = get()

        // Don't fetch if already loading
        if (isLoading) return

        set({ isLoading: true, error: null })

        try {
          const response = await fetchTriggeredAlerts()

          set({
            triggeredAlerts: response.alerts,
            hasUnreadAlerts: response.alerts.some(a => !a.dismissed),
            lastCheckedAt: new Date().toISOString(),
            isLoading: false,
          })
        } catch (error: any) {
          console.error('Failed to fetch triggered alerts:', error)
          set({
            isLoading: false,
            error: error.message || 'Failed to fetch alerts',
          })
        }
      },

      dismissAlert: async (alertId: number) => {
        try {
          await dismissAlertApi(alertId)

          const { triggeredAlerts } = get()
          const updatedAlerts = triggeredAlerts.filter(a => a.id !== alertId)

          set({
            triggeredAlerts: updatedAlerts,
            hasUnreadAlerts: updatedAlerts.some(a => !a.dismissed),
          })
        } catch (error: any) {
          console.error('Failed to dismiss alert:', error)
          set({
            error: error.message || 'Failed to dismiss alert',
          })
        }
      },

      addAlert: (alert: TriggeredAlertResponse) => {
        const { triggeredAlerts } = get()

        // Check if alert already exists
        if (triggeredAlerts.some(a => a.id === alert.id)) {
          return
        }

        set({
          triggeredAlerts: [alert, ...triggeredAlerts],
          hasUnreadAlerts: true,
        })
      },

      markAllAsRead: () => {
        set({ hasUnreadAlerts: false })
      },

      clearAlerts: () => {
        set({
          triggeredAlerts: [],
          hasUnreadAlerts: false,
        })
      },
    }),
    {
      name: 'alert-notifications',
      // Only persist these fields
      partialize: (state) => ({
        lastCheckedAt: state.lastCheckedAt,
      } as unknown as AlertNotificationStore),
    }
  )
)
