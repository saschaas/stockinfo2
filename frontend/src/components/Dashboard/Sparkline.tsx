interface SparklineProps {
  data: Array<{ date: string; close: number | null }>
  width?: number
  height?: number
  className?: string
}

export default function Sparkline({
  data,
  width = 200,
  height = 50,
  className = ''
}: SparklineProps) {
  if (!data || data.length === 0) {
    return null
  }

  // Filter out null values
  const validData = data.filter(d => d.close !== null) as Array<{ date: string; close: number }>

  if (validData.length < 2) {
    return null
  }

  // Find min and max values for scaling
  const values = validData.map(d => d.close)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  // Calculate points for the polyline
  const padding = 5
  const usableWidth = width - (padding * 2)
  const usableHeight = height - (padding * 2)

  const points = validData.map((d, i) => {
    const x = padding + (i / (validData.length - 1)) * usableWidth
    const y = padding + usableHeight - ((d.close - min) / range) * usableHeight
    return `${x},${y}`
  }).join(' ')

  // Determine color based on first vs last value
  const isPositive = validData[validData.length - 1].close >= validData[0].close
  const strokeColor = isPositive ? '#10b981' : '#ef4444' // green-500 or red-500

  return (
    <svg
      width={width}
      height={height}
      className={className}
      style={{ opacity: 0.3 }}
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
