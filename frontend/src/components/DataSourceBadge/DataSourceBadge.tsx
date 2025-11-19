interface DataSourceBadgeProps {
  source: 'api' | 'ai' | 'web' | string
  label: string
}

export default function DataSourceBadge({ source, label }: DataSourceBadgeProps) {
  const getSourceStyles = () => {
    switch (source) {
      case 'api':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          dot: 'bg-green-500',
          title: 'Direct API',
        }
      case 'ai':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          dot: 'bg-blue-500',
          title: 'AI Analysis',
        }
      case 'web':
        return {
          bg: 'bg-orange-100',
          text: 'text-orange-800',
          dot: 'bg-orange-500',
          title: 'Web Extraction',
        }
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          dot: 'bg-gray-500',
          title: 'Unknown',
        }
    }
  }

  const styles = getSourceStyles()

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles.bg} ${styles.text}`}
      title={styles.title}
    >
      <span className={`w-2 h-2 rounded-full ${styles.dot} mr-1.5`}></span>
      {label}
    </span>
  )
}
