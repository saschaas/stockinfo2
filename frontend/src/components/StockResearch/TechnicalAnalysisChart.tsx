import { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'
import type { TechnicalAnalysisData } from '../../types/technical-analysis'
import type { RiskAssessmentData } from '../../types/risk-assessment'

interface TechnicalAnalysisChartProps {
  data: TechnicalAnalysisData
  riskAssessment?: RiskAssessmentData
}

export default function TechnicalAnalysisChart({ data, riskAssessment }: TechnicalAnalysisChartProps) {
  const [eurRate, setEurRate] = useState<number | null>(null)

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
  const safeToFixed = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === undefined || value === null || isNaN(value)) return 'N/A'
    return value.toFixed(decimals)
  }

  // All indicators are always visible
  const showIndicators = {
    sma20: true,
    sma50: true,
    sma200: true,
    bollinger: true,
    supportResistance: true,
    volume: true,
  }

  const chartData = data.chart_data

  if (!chartData || !chartData.dates || chartData.dates.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">Chart data not available</p>
      </div>
    )
  }

  // Main price line (black, bold) with custom hover showing USD and EUR
  const priceLine: any = {
    type: 'scatter',
    mode: 'lines',
    x: chartData.dates,
    y: chartData.ohlcv.close,
    name: data.ticker || 'Price',
    line: { color: '#000000', width: 2.5 },
    yaxis: 'y',
    xaxis: 'x',
    hovertemplate: eurRate
      ? `<b>Price:</b> $%{y:.2f} (€%{customdata:.2f})<extra></extra>`
      : `<b>Price:</b> $%{y:.2f}<extra></extra>`,
    customdata: eurRate ? chartData.ohlcv.close.map((price: number) => price * eurRate) : undefined,
  }

  const traces: any[] = [priceLine]

  // Moving Averages (hover disabled)
  if (showIndicators.sma20 && chartData.moving_averages.sma_20) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_20,
      name: 'SMA 20',
      line: { color: '#eab308', width: 1.5 },  // Yellow
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  if (showIndicators.sma50 && chartData.moving_averages.sma_50) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_50,
      name: 'SMA 50',
      line: { color: '#f97316', width: 1.5 },  // Orange
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  if (showIndicators.sma200 && chartData.moving_averages.sma_200) {
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.moving_averages.sma_200,
      name: 'SMA 200',
      line: { color: '#a855f7', width: 1.5 },  // Purple
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  // Bollinger Bands (hover disabled)
  if (showIndicators.bollinger && chartData.bollinger_bands) {
    // Upper band
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.bollinger_bands.upper,
      name: 'BB Upper',
      line: { color: '#94a3b8', width: 1, dash: 'dot' },
      yaxis: 'y',
      hoverinfo: 'skip',
    })

    // Middle band
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.bollinger_bands.middle,
      name: 'BB Middle',
      line: { color: '#64748b', width: 1 },
      yaxis: 'y',
      hoverinfo: 'skip',
    })

    // Lower band
    traces.push({
      type: 'scatter',
      mode: 'lines',
      x: chartData.dates,
      y: chartData.bollinger_bands.lower,
      name: 'BB Lower',
      line: { color: '#94a3b8', width: 1, dash: 'dot' },
      yaxis: 'y',
      hoverinfo: 'skip',
    })
  }

  // Support and Resistance Lines (hover disabled)
  if (showIndicators.supportResistance) {
    // Resistance levels (red solid horizontal lines)
    data.resistance_levels.forEach((level, idx) => {
      traces.push({
        type: 'scatter',
        mode: 'lines',
        x: [chartData.dates[0], chartData.dates[chartData.dates.length - 1]],
        y: [level, level],
        name: `Resistance ${idx + 1}`,
        line: { color: '#ef4444', width: 1.5 },  // Red solid
        yaxis: 'y',
        showlegend: idx === 0,
        legendgroup: 'resistance',
        hoverinfo: 'skip',
      })
    })

    // Support levels (blue solid horizontal lines)
    data.support_levels.forEach((level, idx) => {
      traces.push({
        type: 'scatter',
        mode: 'lines',
        x: [chartData.dates[0], chartData.dates[chartData.dates.length - 1]],
        y: [level, level],
        name: `Support ${idx + 1}`,
        line: { color: '#3b82f6', width: 1.5 },  // Blue solid
        yaxis: 'y',
        showlegend: idx === 0,
        legendgroup: 'support',
        hoverinfo: 'skip',
      })
    })
  }

  // Volume bars (hover disabled)
  if (showIndicators.volume) {
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
  }

  // Get ticker name with fallback
  const tickerName = data.ticker || 'Stock'

  // Safely get current price as a number
  const currentPrice = typeof data.current_price === 'number' && !isNaN(data.current_price)
    ? data.current_price
    : null

  const layout: any = {
    title: {
      text: `${tickerName} - Technical Analysis`,
      font: { size: 18, weight: 600 },
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
      domain: showIndicators.volume ? [0.25, 1] : [0, 1],
      side: 'right',
    },
    ...(showIndicators.volume && {
      yaxis2: {
        title: 'Volume',
        domain: [0, 0.2],
        side: 'right',
      },
    }),
    hovermode: 'x unified',
    showlegend: true,
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.08,
      xanchor: 'center',
      x: 0.5,
    },
    margin: { l: 50, r: 80, t: 120, b: 50 },
    height: 600,
    plot_bgcolor: '#f9fafb',
    paper_bgcolor: 'white',
    // Add horizontal line annotations for current price and trading levels
    shapes: [
      // Current price line
      ...(currentPrice ? [{
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: currentPrice,
        y1: currentPrice,
        line: {
          color: '#000000',
          width: 1,
          dash: 'dot',
        },
      }] : []),
      // Entry level line
      ...(riskAssessment?.risk_reward?.suggested_entry ? [{
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: riskAssessment.risk_reward.suggested_entry,
        y1: riskAssessment.risk_reward.suggested_entry,
        line: {
          color: '#6366f1',
          width: 1.5,
          dash: 'dash',
        },
      }] : []),
      // Stop loss line
      ...(riskAssessment?.risk_reward?.suggested_stop ? [{
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: riskAssessment.risk_reward.suggested_stop,
        y1: riskAssessment.risk_reward.suggested_stop,
        line: {
          color: '#ef4444',
          width: 1.5,
          dash: 'dash',
        },
      }] : []),
      // Target price line
      ...(riskAssessment?.risk_reward?.suggested_target ? [{
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: 'y',
        y0: riskAssessment.risk_reward.suggested_target,
        y1: riskAssessment.risk_reward.suggested_target,
        line: {
          color: '#22c55e',
          width: 1.5,
          dash: 'dash',
        },
      }] : []),
    ],
    annotations: [
      // Current price annotation
      ...(currentPrice ? [{
        x: 1.02,
        y: currentPrice,
        xref: 'paper',
        yref: 'y',
        text: `$${currentPrice.toFixed(2)}`,
        showarrow: false,
        font: {
          size: 10,
          color: '#000000',
        },
        bgcolor: '#fef3c7',
        bordercolor: '#f59e0b',
        borderwidth: 1,
        borderpad: 2,
      }] : []),
      // Entry level annotation with arrow
      ...(riskAssessment?.risk_reward?.suggested_entry ? [{
        x: 0,
        y: riskAssessment.risk_reward.suggested_entry,
        xref: 'paper',
        yref: 'y',
        text: `Entry $${riskAssessment.risk_reward.suggested_entry.toFixed(2)}`,
        showarrow: true,
        arrowhead: 2,
        arrowsize: 1,
        arrowwidth: 2,
        arrowcolor: '#6366f1',
        ax: -40,
        ay: 0,
        font: {
          size: 9,
          color: '#ffffff',
        },
        bgcolor: '#6366f1',
        bordercolor: '#4f46e5',
        borderwidth: 1,
        borderpad: 2,
      }] : []),
      // Stop loss annotation with arrow
      ...(riskAssessment?.risk_reward?.suggested_stop ? [{
        x: 0,
        y: riskAssessment.risk_reward.suggested_stop,
        xref: 'paper',
        yref: 'y',
        text: `Stop $${riskAssessment.risk_reward.suggested_stop.toFixed(2)}`,
        showarrow: true,
        arrowhead: 2,
        arrowsize: 1,
        arrowwidth: 2,
        arrowcolor: '#ef4444',
        ax: -40,
        ay: 0,
        font: {
          size: 9,
          color: '#ffffff',
        },
        bgcolor: '#ef4444',
        bordercolor: '#dc2626',
        borderwidth: 1,
        borderpad: 2,
      }] : []),
      // Target price annotation with arrow
      ...(riskAssessment?.risk_reward?.suggested_target ? [{
        x: 0,
        y: riskAssessment.risk_reward.suggested_target,
        xref: 'paper',
        yref: 'y',
        text: `Target $${riskAssessment.risk_reward.suggested_target.toFixed(2)}`,
        showarrow: true,
        arrowhead: 2,
        arrowsize: 1,
        arrowwidth: 2,
        arrowcolor: '#22c55e',
        ax: -50,
        ay: 0,
        font: {
          size: 9,
          color: '#ffffff',
        },
        bgcolor: '#22c55e',
        bordercolor: '#16a34a',
        borderwidth: 1,
        borderpad: 2,
      }] : []),
    ],
  }

  const config: any = {
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  }

  // Get signal color
  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'strong_buy':
        return 'bg-green-600 text-white'
      case 'buy':
        return 'bg-green-500 text-white'
      case 'neutral':
        return 'bg-gray-500 text-white'
      case 'sell':
        return 'bg-red-500 text-white'
      case 'strong_sell':
        return 'bg-red-600 text-white'
      default:
        return 'bg-gray-400 text-white'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-4">
      {/* Header with Signal */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold text-gray-900">Technical Analysis</h3>
          <p className="text-sm text-gray-600 mt-1">
            {data.trend_direction.charAt(0).toUpperCase() + data.trend_direction.slice(1)} trend •
            {' '}{data.adx_signal.replace('_', ' ')} strength (ADX: {safeToFixed(data.adx, 1)})
          </p>
        </div>
        <div className="text-right">
          <div className={`inline-block px-4 py-2 rounded-lg font-bold ${getSignalColor(data.overall_signal)}`}>
            {data.overall_signal.replace('_', ' ').toUpperCase()}
          </div>
          <p className="text-sm text-gray-600 mt-1">
            Confidence: {safeToFixed(data.signal_confidence, 1)}%
          </p>
        </div>
      </div>

      {/* Current Price and Key Levels */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
        <div>
          <p className="text-xs text-gray-600">Current Price</p>
          <p className="text-lg font-bold text-gray-900">${safeToFixed(data.current_price, 2)}</p>
        </div>
        {data.nearest_resistance && (
          <div>
            <p className="text-xs text-red-600">Next Resistance</p>
            <p className="text-lg font-bold text-red-600">
              ${safeToFixed(data.nearest_resistance, 2)}
              <span className="text-xs ml-1">
                (+{safeToFixed(data.resistance_distance_pct, 1)}%)
              </span>
            </p>
          </div>
        )}
        {data.nearest_support && (
          <div>
            <p className="text-xs text-green-600">Next Support</p>
            <p className="text-lg font-bold text-green-600">
              ${safeToFixed(data.nearest_support, 2)}
              <span className="text-xs ml-1">
                (-{safeToFixed(data.support_distance_pct, 1)}%)
              </span>
            </p>
          </div>
        )}
        <div>
          <p className="text-xs text-gray-600">Technical Score</p>
          <p className="text-lg font-bold text-gray-900">
            {safeToFixed(data.composite_technical_score, 1)}/10
          </p>
        </div>
      </div>

      {/* Trading Levels from Risk Assessment */}
      {riskAssessment?.risk_reward && (
        <div className="grid grid-cols-3 gap-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
          <div>
            <p className="text-xs text-indigo-600 font-medium">Entry Level</p>
            <p className="text-lg font-bold text-indigo-700">
              ${safeToFixed(riskAssessment.risk_reward.suggested_entry, 2)}
              {currentPrice && riskAssessment.risk_reward.suggested_entry && (
                <span className="text-xs ml-1 text-indigo-500">
                  ({((riskAssessment.risk_reward.suggested_entry - currentPrice) / currentPrice * 100) >= 0 ? '+' : ''}
                  {safeToFixed((riskAssessment.risk_reward.suggested_entry - currentPrice) / currentPrice * 100, 1)}%)
                </span>
              )}
            </p>
          </div>
          <div>
            <p className="text-xs text-red-600 font-medium">Stop Loss</p>
            <p className="text-lg font-bold text-red-600">
              ${safeToFixed(riskAssessment.risk_reward.suggested_stop, 2)}
              {currentPrice && riskAssessment.risk_reward.suggested_stop && (
                <span className="text-xs ml-1">
                  ({safeToFixed((riskAssessment.risk_reward.suggested_stop - currentPrice) / currentPrice * 100, 1)}%)
                </span>
              )}
            </p>
          </div>
          <div>
            <p className="text-xs text-green-600 font-medium">Target</p>
            <p className="text-lg font-bold text-green-600">
              ${safeToFixed(riskAssessment.risk_reward.suggested_target, 2)}
              {currentPrice && riskAssessment.risk_reward.suggested_target && (
                <span className="text-xs ml-1">
                  (+{safeToFixed((riskAssessment.risk_reward.suggested_target - currentPrice) / currentPrice * 100, 1)}%)
                </span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="w-full">
        <Plot
          data={traces}
          layout={layout}
          config={config}
          style={{ width: '100%', height: '600px' }}
          useResizeHandler={true}
        />
      </div>

      {/* Chart Patterns */}
      {data.patterns && data.patterns.length > 0 && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-semibold text-blue-900 mb-2">Detected Patterns</h4>
          <ul className="space-y-1">
            {data.patterns.map((pattern, idx) => (
              <li key={idx} className="text-sm text-blue-800 flex items-center">
                <span className="mr-2">•</span>
                {pattern}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
