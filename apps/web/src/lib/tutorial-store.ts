import { create } from 'zustand'

interface TutorialStore {
  open: boolean
  openTutorial: () => void
  closeTutorial: () => void
}

export const useTutorialStore = create<TutorialStore>(set => ({
  open: false,
  openTutorial:  () => set({ open: true }),
  closeTutorial: () => set({ open: false }),
}))
