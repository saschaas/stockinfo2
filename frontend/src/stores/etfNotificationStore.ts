import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { checkETFUpdates, ETFUpdateInfo } from '../services/api'

interface ETFNotificationStore {
  // Set of ETF IDs that have new updates
  updatedETFIds: Set<number>
  // Whether there are any updates (for nav badge)
  hasUpdates: boolean
  // Last time the user viewed the ETF Tracker page
  lastViewedAt: string | null
  // Last time we checked for updates
  lastCheckedAt: string | null
  // Loading state
  isChecking: boolean
  // Error state
  error: string | null
  // ETF update details for showing in UI
  etfUpdates: ETFUpdateInfo[]

  // Actions
  checkForUpdates: () => Promise<void>
  markAsViewed: () => void
  clearUpdates: () => void
  clearETFUpdate: (etfId: number) => void
}

export const useETFNotificationStore = create<ETFNotificationStore>()(
  persist(
    (set, get) => ({
      updatedETFIds: new Set(),
      hasUpdates: false,
      lastViewedAt: null,
      lastCheckedAt: null,
      isChecking: false,
      error: null,
      etfUpdates: [],

      checkForUpdates: async () => {
        const { lastViewedAt, isChecking } = get()

        // Don't check if already checking
        if (isChecking) return

        set({ isChecking: true, error: null })

        try {
          const response = await checkETFUpdates(lastViewedAt || undefined)

          // Get ETF IDs that have new data
          const updatedIds = new Set(
            response.etfs
              .filter(e => e.has_new_data)
              .map(e => e.etf_id)
          )

          set({
            updatedETFIds: updatedIds,
            hasUpdates: response.has_any_updates,
            lastCheckedAt: response.checked_at,
            etfUpdates: response.etfs,
            isChecking: false,
          })
        } catch (error: any) {
          console.error('Failed to check ETF updates:', error)
          set({
            isChecking: false,
            error: error.message || 'Failed to check for updates',
          })
        }
      },

      markAsViewed: () => {
        const now = new Date().toISOString()
        set({
          lastViewedAt: now,
          updatedETFIds: new Set(),
          hasUpdates: false,
        })
      },

      clearUpdates: () => {
        set({
          updatedETFIds: new Set(),
          hasUpdates: false,
        })
      },

      clearETFUpdate: (etfId: number) => {
        const { updatedETFIds } = get()
        const newSet = new Set(updatedETFIds)
        newSet.delete(etfId)
        set({
          updatedETFIds: newSet,
          hasUpdates: newSet.size > 0,
        })
      },
    }),
    {
      name: 'etf-notifications',
      // Custom serialization for Set
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null
          const parsed = JSON.parse(str)
          // Convert array back to Set
          if (parsed.state?.updatedETFIds) {
            parsed.state.updatedETFIds = new Set(parsed.state.updatedETFIds)
          }
          return parsed
        },
        setItem: (name, value) => {
          // Convert Set to array for storage
          const toStore = {
            ...value,
            state: {
              ...value.state,
              updatedETFIds: Array.from(value.state.updatedETFIds || []),
            },
          }
          localStorage.setItem(name, JSON.stringify(toStore))
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
      // Only persist these fields
      partialize: (state) => ({
        lastViewedAt: state.lastViewedAt,
        updatedETFIds: state.updatedETFIds,
        hasUpdates: state.hasUpdates,
      } as unknown as ETFNotificationStore),
    }
  )
)
