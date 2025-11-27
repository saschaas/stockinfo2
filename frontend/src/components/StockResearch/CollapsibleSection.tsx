import { ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  isOpen: boolean
  onToggle: () => void
  children: ReactNode
  badge?: ReactNode
  icon?: ReactNode
}

export default function CollapsibleSection({
  title,
  isOpen,
  onToggle,
  children,
  badge,
  icon,
}: CollapsibleSectionProps) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Header - Always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-gray-500">{icon}</span>}
          <h4 className="font-semibold text-gray-800">{title}</h4>
          {badge && <span>{badge}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {isOpen ? 'Click to collapse' : 'Click to expand'}
          </span>
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Content - Collapsible */}
      {isOpen && (
        <div className="p-4 border-t border-gray-200">
          {children}
        </div>
      )}
    </div>
  )
}
