import Plot from 'react-plotly.js'

interface ScoringBreakdownProps {
  fundamentalScore: number
  sentimentScore: number
  technicalScore: number
  competitiveScore: number
  riskAdjustedScore: number
  compositeScore: number
}

export default function ScoringBreakdown({
  fundamentalScore,
  sentimentScore,
  technicalScore,
  competitiveScore,
  riskAdjustedScore,
  compositeScore
}: ScoringBreakdownProps) {
  const categories = [
    'Fundamental',
    'Sentiment',
    'Technical',
    'Competitive',
    'Risk-Adjusted'
  ]

  const scores = [
    fundamentalScore,
    sentimentScore,
    technicalScore,
    competitiveScore,
    riskAdjustedScore
  ]

  const weights = {
    'Fundamental': 35,
    'Sentiment': 20,
    'Technical': 15,
    'Competitive': 20,
    'Risk-Adjusted': 10
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-blue-600'
    if (score >= 4) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-900">Multi-Factor Scoring</h4>
          <div className="text-right">
            <div className={`text-2xl font-bold ${getScoreColor(compositeScore)}`}>
              {compositeScore.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500">Composite Score</div>
          </div>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="mb-4">
        <Plot
          data={[
            {
              type: 'scatterpolar',
              r: scores,
              theta: categories,
              fill: 'toself',
              fillcolor: 'rgba(59, 130, 246, 0.2)',
              line: {
                color: 'rgb(59, 130, 246)',
                width: 2
              },
              marker: {
                color: 'rgb(59, 130, 246)',
                size: 8
              }
            }
          ]}
          layout={{
            polar: {
              radialaxis: {
                visible: true,
                range: [0, 10],
                tickmode: 'linear',
                tick0: 0,
                dtick: 2,
                gridcolor: 'rgba(0,0,0,0.1)'
              },
              angularaxis: {
                gridcolor: 'rgba(0,0,0,0.1)'
              }
            },
            showlegend: false,
            margin: { l: 60, r: 60, t: 20, b: 20 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {
              size: 11,
              color: '#374151'
            }
          }}
          config={{
            displayModeBar: false,
            responsive: true
          }}
          style={{ width: '100%', height: '300px' }}
        />
      </div>

      {/* Score Details */}
      <div className="space-y-2">
        {categories.map((category, idx) => (
          <div key={category} className="flex items-center justify-between">
            <div className="flex items-center flex-1">
              <span className="text-xs font-medium text-gray-700 w-24">{category}</span>
              <div className="flex-1 mx-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      scores[idx] >= 8 ? 'bg-green-500' :
                      scores[idx] >= 6 ? 'bg-blue-500' :
                      scores[idx] >= 4 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${(scores[idx] / 10) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-sm font-bold ${getScoreColor(scores[idx])}`}>
                {scores[idx].toFixed(1)}
              </span>
              <span className="text-xs text-gray-500 w-12 text-right">
                ({weights[category as keyof typeof weights]}%)
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t text-xs text-gray-500">
        <p>Scores range from 0-10. Weights indicate contribution to composite score.</p>
      </div>
    </div>
  )
}
