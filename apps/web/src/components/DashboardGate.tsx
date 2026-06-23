'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { hasCardReviewSession } from '@/lib/demo-session'

export default function DashboardGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const isCardRoute = useMemo(
    () => pathname === '/dashboard/card' || pathname.startsWith('/dashboard/card/'),
    [pathname],
  )
  const [allowed, setAllowed] = useState(isCardRoute)

  useEffect(() => {
    if (isCardRoute) {
      setAllowed(true)
      return
    }

    if (hasCardReviewSession()) {
      setAllowed(true)
      return
    }

    setAllowed(false)
    router.replace('/dashboard/card')
  }, [isCardRoute, pathname, router])

  if (!allowed && !isCardRoute) return null
  return <>{children}</>
}
