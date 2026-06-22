import { redirect } from 'next/navigation'

export default function Home() {
  // Landing page is a placeholder; send users straight to the dashboard.
  redirect('/dashboard/voice')
}
