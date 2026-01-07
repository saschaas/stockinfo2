import { useState, useEffect, useCallback, useRef } from 'react'
import Plot from 'react-plotly.js'
import type { ChartDataResponse, WatchlistLineResponse } from '../../types'

interface InteractiveChartProps {
  chartData: ChartDataResponse
  customLines: WatchlistLineResponse[]
  isAddingLine: boolean
  newLineType: 'trend' | 'alert'
  onAddLine: (priceLevel: number) => void
  onLinePriceChange: (lineId: number, newPrice: number) => void
}

export default function InteractiveChart({
  chartData,
  customLines,
  isAddingLine,
  newLineType,
  onAddLine,
  onLinePriceChange,
}: InteractiveChartProps) {
  const [eurRate, setEurRate] = useState<number | null>(null)
  const [hoverPrice, setHoverPrice] = useState<number | null>(null)
  const plotRef = useRef<any>(null)

  // Fetch USD to EUR exchange rate on mount
  useEffect(() => {
    const fetchExchangeRate = async () => {
      try {
        const response = await fetch('https://api.frankfurter.app/latest?from=USD&to=EUR')
        const data = await response.json()
        if (data.rates?.EUR) {
          setEurRate(data.rates.EUR)
        }
      } catch (error) {
        console.warn('Failed to fetch exchange rate:', error)
      }
    }
    fetchExchangeRate()
  }, [])

  if (!chartData || !chartData.dates || chartData.dates.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">Chart data not available</p>
      </div>
    )
  }

  // Build traces
  const traces: any[] = []

  // Main price line with EUR hover
  traces.push({
    type: 'scatter',
    mode: 'lines',
    x: chartData.dates,
    y: chartData.ohlcv.close,
    name: chartData.ticker || 'Price',
    line: { color: '#000000', width: 2.5 },
    yaxis: 'y',
    xaxis: 'x',
    hovertemplate: eurRate
      ? `<b>Price:</b> $%{y:.2f} (%{customdata:.2f})<extra></extra>`
      : `<b>Price:</b> $%{y:.2f}<extra></extra>`,
    customdata: eurRate
      ? chartData.ohlcv.close.map((price: number) => price * eurRate)
      : undefined,
  })

  // Moving Averages
  if (chartData.moving_averages.sma_20) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_20,
      name: 'SMA 20',
      line: { color: '#eab308', width: 1.5 },
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  if (chartData.moving_averages.sma_50) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_50,
      name: 'SMA 50',
      line: { color: '#f97316', width: 1.5 },
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  if (chartData.moving_averages.sma_200) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_200,
      name: 'SMA 200',
      line: { color: '#a855f7', width: 1.5 },
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  // Support levels (blue solid)
  chartData.support_levels.forEach((level, idx) => {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: [chartData.dates[0], chartData.dates[chartData.dates.length - 1]],
      y: [level, level],
      name: `Support ${idx + 1}`,
      line: { color: '#3b82f6', width: 1.5 },
      yaxis: 'y',
      showlegend: idx === 0,
      legendgroup: 'support',
      hoverinfo: 'skip',
    })
  })

  // Resistance levels (red solid)
  chartData.resistance_levels.forEach((level, idx) => {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: [chartData.dates[0], chartData.dates[chartData.dates.length - 1]],
      y: [level, level],
      name: `Resistance ${idx + 1}`,
      line: { color: '#ef4444', width: 1.5 },
      yaxis: 'y',
      showlegend: idx === 0,
      legendgroup: 'resistance',
      hoverinfo: 'skip',
    })
  })

  // Volume bars
  traces.push({
    type: 'bar',
    x: chartData.dates,
    y: chartData.ohlcv.volume,
    name: 'Volume',
    marker: {
      color: chartData.ohlcv.close.map((close: number, i: number) =>
        i === 0 || close >= chartData.ohlcv.close[i - 1]
          ? 'rgba(16, 185, 129, 0.3)'
          : 'rgba(239, 68, 68, 0.3)'
      ),
    },
    yaxis: 'y2',
    xaxis: 'x',
    hoverinfo: 'skip',
  })

  // Build shapes for custom lines and built-in levels
  const shapes: any[] = []
  const annotations: any[] = []

  // Entry level line (if available)
  if (chartData.entry_level) {
    shapes.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: chartData.entry_level,
      y1: chartData.entry_level,
      line: { color: '#6366f1', width: 1.5, dash: 'dash' },
    })
    annotations.push({
      x: 1.02,
      y: chartData.entry_level,
      xref: 'paper',
      yref: 'y',
      text: `Entry $${chartData.entry_level.toFixed(2)}`,
      showarrow: false,
      font: { size: 9, color: '#ffffff' },
      bgcolor: '#6366f1',
      bordercolor: '#4f46e5',
      borderwidth: 1,
      borderpad: 2,
    })
  }

  // Stop loss line (if available)
  if (chartData.stop_loss) {
    shapes.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: chartData.stop_loss,
      y1: chartData.stop_loss,
      line: { color: '#ef4444', width: 1.5, dash: 'dash' },
    })
    annotations.push({
      x: 1.02,
      y: chartData.stop_loss,
      xref: 'paper',
      yref: 'y',
      text: `Stop $${chartData.stop_loss.toFixed(2)}`,
      showarrow: false,
      font: { size: 9, color: '#ffffff' },
      bgcolor: '#ef4444',
      bordercolor: '#dc2626',
      borderwidth: 1,
      borderpad: 2,
    })
  }

  // Target price line (if available)
  if (chartData.target_price) {
    shapes.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: chartData.target_price,
      y1: chartData.target_price,
      line: { color: '#22c55e', width: 1.5, dash: 'dash' },
    })
    annotations.push({
      x: 1.02,
      y: chartData.target_price,
      xref: 'paper',
      yref: 'y',
      text: `Target $${chartData.target_price.toFixed(2)}`,
      showarrow: false,
      font: { size: 9, color: '#ffffff' },
      bgcolor: '#22c55e',
      bordercolor: '#16a34a',
      borderwidth: 1,
      borderpad: 2,
    })
  }

  // Custom lines from database
  customLines.forEach((line) => {
    if (!line.is_active) return

    const isTrend = line.line_type === 'trend'
    const defaultColor = isTrend ? '#8b5cf6' : '#f97316'
    const color = line.color || defaultColor

    shapes.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: line.price_level,
      y1: line.price_level,
      line: {
        color,
        width: isTrend ? 1.5 : 2,
        dash: isTrend ? 'dash' : 'dot',
      },
      editable: true,
      name: `line-${line.id}`,
    })

    annotations.push({
      x: 1.02,
      y: line.price_level,
      xref: 'paper',
      yref: 'y',
      text: `${line.name} $${line.price_level.toFixed(2)}`,
      showarrow: false,
      font: { size: 9, color: '#ffffff' },
      bgcolor: color,
      bordercolor: color,
      borderwidth: 1,
      borderpad: 2,
    })
  })

  // Add hover price indicator when adding line
  if (isAddingLine && hoverPrice !== null) {
    const indicatorColor = newLineType === 'alert' ? '#f97316' : '#8b5cf6'
    shapes.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      yref: 'y',
      y0: hoverPrice,
      y1: hoverPrice,
      line: {
        color: indicatorColor,
        width: 2,
        dash: newLineType === 'alert' ? 'dot' : 'dash',
      },
      opacity: 0.7,
    })
    annotations.push({
      x: 0.5,
      y: hoverPrice,
      xref: 'paper',
      yref: 'y',
      text: `Click to place at $${hoverPrice.toFixed(2)}`,
      showarrow: false,
      font: { size: 11, color: '#ffffff' },
      bgcolor: indicatorColor,
      borderpad: 4,
    })
  }

  const layout: any = {
    title: {
      text: `${chartData.ticker || 'Stock'} - ${chartData.company_name || ''}`,
      font: { size: 16, weight: 600 },
      x: 0.5,
      xanchor: 'center',
      y: 0.98,
      yanchor: 'top',
    },
    xaxis: {
      title: 'Date',
      rangeslider: { visible: false },
      type: 'date',
    },
    yaxis: {
      title: 'Price ($)',
      domain: [0.25, 1],
      side: 'right',
    },
    yaxis2: {
      title: 'Volume',
      domain: [0, 0.2],
      side: 'right',
    },
    hovermode: 'x unified',
    showlegend: true,
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.08,
      xanchor: 'center',
      x: 0.5,
    },
    margin: { l: 50, r: 100, t: 80, b: 50 },
    height: 550,
    plot_bgcolor: '#f9fafb',
    paper_bgcolor: 'white',
    shapes,
    annotations,
    dragmode: isAddingLine ? 'select' : 'zoom',
  }

  const config: any = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    editable: false, // We handle edits ourselves
  }

  // Handle hover to show price indicator when adding line
  const handleHover = useCallback(
    (event: any) => {
      if (!isAddingLine) return

      if (event.points && event.points.length > 0) {
        // Get y value from the first point (price line)
        const point = event.points.find((p: any) => p.data.name === (chartData.ticker || 'Price'))
        if (point) {
          setHoverPrice(point.y)
        }
      }
    },
    [isAddingLine, chartData.ticker]
  )

  // Handle click to place new line
  const handleClick = useCallback(
    (event: any) => {
      if (!isAddingLine) return

      if (event.points && event.points.length > 0) {
        const point = event.points.find((p: any) => p.data.name === (chartData.ticker || 'Price'))
        if (point) {
          onAddLine(point.y)
          setHoverPrice(null)
        }
      }
    },
    [isAddingLine, chartData.ticker, onAddLine]
  )

  // Handle relayout for shape dragging (line movement)
  const handleRelayout = useCallback(
    (event: any) => {
      // Check if a shape was moved
      Object.keys(event).forEach((key) => {
        const match = key.match(/shapes\[(\d+)\]\.y(\d+)/)
        if (match) {
          const shapeIndex = parseInt(match[1])
          const shape = shapes[shapeIndex]

          if (shape && shape.name && shape.name.startsWith('line-')) {
            const lineId = parseInt(shape.name.replace('line-', ''))
            const newY = event[key]
            onLinePriceChange(lineId, newY)
          }
        }
      })
    },
    [shapes, onLinePriceChange]
  )

  return (
    <div className="w-full relative">
      {isAddingLine && (
        <div className="absolute top-2 left-2 z-10 px-3 py-1.5 rounded-lg bg-gray-900 text-white text-sm shadow-lg">
          {newLineType === 'alert' ? 'Alert' : 'Trend'} line mode - hover to see price, click to
          place
        </div>
      )}
      <Plot
        ref={plotRef}
        data={traces}
        layout={layout}
        config={config}
        style={{ width: '100%', height: '550px' }}
        useResizeHandler={true}
        onHover={handleHover}
        onClick={handleClick}
        onRelayout={handleRelayout}
      />
    </div>
  )
}
