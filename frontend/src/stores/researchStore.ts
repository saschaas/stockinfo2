import { create } from 'zustand'

export interface ResearchJob {
  id: string
  ticker: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  currentStep: string
  result?: any
  error?: string
  suggestion?: string
  createdAt: Date  // Timestamp when job was created
}

interface ResearchStore {
  jobs: ResearchJob[]
  activeJob: string | null

  addJob: (job: ResearchJob) => void
  updateJob: (id: string, updates: Partial<ResearchJob>) => void
  removeJob: (id: string) => void
  setActiveJob: (id: string | null) => void
  getJob: (id: string) => ResearchJob | undefined
}

export const useResearchStore = create<ResearchStore>((set, get) => ({
  jobs: [],
  activeJob: null,

  addJob: (job) => set((state) => ({
    jobs: [...state.jobs, job],
    activeJob: job.id,
  })),

  updateJob: (id, updates) => set((state) => ({
    jobs: state.jobs.map((job) =>
      job.id === id ? { ...job, ...updates } : job
    ),
  })),

  removeJob: (id) => set((state) => ({
    jobs: state.jobs.filter((job) => job.id !== id),
    activeJob: state.activeJob === id ? null : state.activeJob,
  })),

  setActiveJob: (id) => set({ activeJob: id }),

  getJob: (id) => get().jobs.find((job) => job.id === id),
}))
