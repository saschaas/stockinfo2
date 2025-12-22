import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { checkFundUpdates, FundUpdateInfo } from '../services/api'

interface FundNotificationStore {
  // Set of fund IDs that have new updates
  updatedFundIds: Set<number>
  // Whether there are any updates (for nav badge)
  hasUpdates: boolean
  // Last time the user viewed the Fund Tracker page
  lastViewedAt: string | null
  // Last time we checked for updates
  lastCheckedAt: string | null
  // Loading state
  isChecking: boolean
  // Error state
  error: string | null
  // Fund update details for showing in UI
  fundUpdates: FundUpdateInfo[]

  // Actions
  checkForUpdates: () => Promise<void>
  markAsViewed: () => void
  clearUpdates: () => void
  clearFundUpdate: (fundId: number) => void
}

export const useFundNotificationStore = create<FundNotificationStore>()(
  persist(
    (set, get) => ({
      updatedFundIds: new Set(),
      hasUpdates: false,
      lastViewedAt: null,
      lastCheckedAt: null,
      isChecking: false,
      error: null,
      fundUpdates: [],

      checkForUpdates: async () => {
        const { lastViewedAt, isChecking } = get()

        // Don't check if already checking
        if (isChecking) return

        set({ isChecking: true, error: null })

        try {
          const response = await checkFundUpdates(lastViewedAt || undefined)

          // Get fund IDs that have new data
          const updatedIds = new Set(
            response.funds
              .filter(f => f.has_new_data)
              .map(f => f.fund_id)
          )

          set({
            updatedFundIds: updatedIds,
            hasUpdates: response.has_any_updates,
            lastCheckedAt: response.checked_at,
            fundUpdates: response.funds,
            isChecking: false,
          })
        } catch (error: any) {
          console.error('Failed to check fund updates:', error)
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
          updatedFundIds: new Set(),
          hasUpdates: false,
        })
      },

      clearUpdates: () => {
        set({
          updatedFundIds: new Set(),
          hasUpdates: false,
        })
      },

      clearFundUpdate: (fundId: number) => {
        const { updatedFundIds } = get()
        const newSet = new Set(updatedFundIds)
        newSet.delete(fundId)
        set({
          updatedFundIds: newSet,
          hasUpdates: newSet.size > 0,
        })
      },
    }),
    {
      name: 'fund-notifications',
      // Custom serialization for Set
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null
          const parsed = JSON.parse(str)
          // Convert array back to Set
          if (parsed.state?.updatedFundIds) {
            parsed.state.updatedFundIds = new Set(parsed.state.updatedFundIds)
          }
          return parsed
        },
        setItem: (name, value) => {
          // Convert Set to array for storage
          const toStore = {
            ...value,
            state: {
              ...value.state,
              updatedFundIds: Array.from(value.state.updatedFundIds || []),
            },
          }
          localStorage.setItem(name, JSON.stringify(toStore))
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
      // Only persist these fields
      partialize: (state) => ({
        lastViewedAt: state.lastViewedAt,
        updatedFundIds: state.updatedFundIds,
        hasUpdates: state.hasUpdates,
      } as unknown as FundNotificationStore),
    }
  )
)
