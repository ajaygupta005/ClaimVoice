import DashboardGate from '@/components/DashboardGate'
import Sidebar from '@/components/Sidebar'
import TutorialModal from '@/components/TutorialModal'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0 bg-slate-50 dark:bg-slate-950">
        <div className="max-w-5xl mx-auto px-8 py-8">
          <DashboardGate>{children}</DashboardGate>
        </div>
      </main>
      <TutorialModal />
    </div>
  )
}
