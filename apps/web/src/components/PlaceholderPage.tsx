import { LucideIcon } from 'lucide-react'

interface Props {
  title: string
  description: string
  Icon: LucideIcon
}

export default function PlaceholderPage({ title, description, Icon }: Props) {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">{title}</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-8">{description}</p>
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 py-20">
        <Icon size={40} className="text-slate-300 dark:text-slate-600 mb-4" strokeWidth={1.5} />
        <p className="text-sm font-medium text-slate-400 dark:text-slate-500">Coming in a later component</p>
      </div>
    </div>
  )
}
