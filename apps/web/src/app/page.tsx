import { redirect } from 'next/navigation'

export default function Home() {
  // Start the product flow at insurance-card extraction; plan/provider/voice
  // pages use the demo member only after the operator moves through the demo.
  redirect('/dashboard/card')
}
