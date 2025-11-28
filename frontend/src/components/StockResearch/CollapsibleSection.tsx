import { ReactNode, useState, useRef, useEffect } from 'react'

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
  const contentRef = useRef<HTMLDivElement>(null)
  const [contentHeight, setContentHeight] = useState<number | undefined>(undefined)

  // Update height when content changes or isOpen changes
  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(isOpen ? contentRef.current.scrollHeight : 0)
    }
  }, [isOpen, children])

  return (
    <div className="card overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5 bg-cream hover:bg-cream-dark transition-colors duration-200"
      >
        <div className="flex items-center gap-3">
          {icon && (
            <span className="text-primary-500 bg-primary-50 p-2 rounded-xl">
              {icon}
            </span>
          )}
          <h4 className="font-semibold text-gray-900">{title}</h4>
          {badge && <span>{badge}</span>}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 hidden sm:block">
            {isOpen ? 'Collapse' : 'Expand'}
          </span>
          <div className={`p-1.5 rounded-lg bg-white shadow-soft transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}>
            <svg
              className="w-4 h-4 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </button>

      {/* Content - Animated Collapse */}
      <div
        className="collapsible-content"
        style={{
          height: contentHeight !== undefined ? contentHeight : (isOpen ? 'auto' : 0),
          opacity: isOpen ? 1 : 0,
        }}
      >
        <div ref={contentRef} className="p-5 border-t border-border-warm bg-white">
          {children}
        </div>
      </div>
    </div>
  )
}
