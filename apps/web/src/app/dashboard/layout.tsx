import Link from 'next/link'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <nav className="w-48 border-r p-4">
        <Link href="/dashboard/card">Card</Link><br/>
        <Link href="/dashboard/plan">Plan</Link><br/>
        <Link href="/dashboard/providers">Providers</Link><br/>
        <Link href="/dashboard/voice">Voice</Link><br/>
        <Link href="/dashboard/calls">Calls</Link>
      </nav>
      <section className="flex-1">{children}</section>
    </div>
  )
}
