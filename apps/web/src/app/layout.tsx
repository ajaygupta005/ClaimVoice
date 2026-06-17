import './globals.css'
import { ClerkProvider } from '@clerk/nextjs'

export const metadata = { title: 'ClaimVoice', description: 'AI insurance assistant' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  )
}
