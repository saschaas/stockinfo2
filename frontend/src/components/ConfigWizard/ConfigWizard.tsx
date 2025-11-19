import { useState } from 'react'

interface ConfigStep {
  id: number
  title: string
  description: string
}

const steps: ConfigStep[] = [
  {
    id: 1,
    title: 'API Keys',
    description: 'Configure your data source API keys',
  },
  {
    id: 2,
    title: 'Fund Selection',
    description: 'Choose which funds to track',
  },
  {
    id: 3,
    title: 'Analysis Settings',
    description: 'Configure analysis parameters',
  },
]

export default function ConfigWizard() {
  const [currentStep, setCurrentStep] = useState(1)
  const [config, setConfig] = useState({
    alphaVantageKey: '',
    fmpKey: '',
    secUserAgent: '',
    selectedFunds: [] as string[],
    analysisSettings: {
      includeTechnical: true,
      includePeers: true,
      includeAiAnalysis: true,
    },
  })

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSave = () => {
    // Save configuration
    console.log('Saving config:', config)
    alert('Configuration saved!')
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Configuration</h2>

      {/* Progress Steps */}
      <div className="bg-white rounded-lg shadow p-6">
        <nav aria-label="Progress">
          <ol className="flex items-center">
            {steps.map((step, index) => (
              <li
                key={step.id}
                className={`relative ${index !== steps.length - 1 ? 'flex-1' : ''}`}
              >
                <div className="flex items-center">
                  <span
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      step.id < currentStep
                        ? 'bg-primary-600 text-white'
                        : step.id === currentStep
                        ? 'border-2 border-primary-600 text-primary-600'
                        : 'border-2 border-gray-300 text-gray-500'
                    }`}
                  >
                    {step.id < currentStep ? '✓' : step.id}
                  </span>
                  {index !== steps.length - 1 && (
                    <div
                      className={`h-0.5 w-full mx-4 ${
                        step.id < currentStep ? 'bg-primary-600' : 'bg-gray-300'
                      }`}
                    />
                  )}
                </div>
                <span className="absolute mt-2 text-xs text-gray-500 whitespace-nowrap">
                  {step.title}
                </span>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {/* Step Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {currentStep === 1 && (
          <div className="space-y-4">
            <h3 className="text-lg font-medium">API Keys</h3>
            <p className="text-sm text-gray-500 mb-4">
              Enter your API keys for data sources. These are stored securely and never shared.
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Alpha Vantage API Key
              </label>
              <input
                type="password"
                value={config.alphaVantageKey}
                onChange={(e) =>
                  setConfig({ ...config, alphaVantageKey: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="Enter your Alpha Vantage API key"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Financial Modeling Prep API Key
              </label>
              <input
                type="password"
                value={config.fmpKey}
                onChange={(e) => setConfig({ ...config, fmpKey: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="Enter your FMP API key"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SEC User Agent
              </label>
              <input
                type="text"
                value={config.secUserAgent}
                onChange={(e) =>
                  setConfig({ ...config, secUserAgent: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="YourCompany/1.0 admin@company.com"
              />
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Fund Selection</h3>
            <p className="text-sm text-gray-500 mb-4">
              Select which funds you want to track for portfolio changes.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-sm mb-2">Tech-Focused Funds</h4>
                {['ARKK', 'XLK', 'VGT', 'IXN', 'BOTZ'].map((fund) => (
                  <label key={fund} className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={config.selectedFunds.includes(fund)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setConfig({
                            ...config,
                            selectedFunds: [...config.selectedFunds, fund],
                          })
                        } else {
                          setConfig({
                            ...config,
                            selectedFunds: config.selectedFunds.filter(
                              (f) => f !== fund
                            ),
                          })
                        }
                      }}
                      className="mr-2"
                    />
                    <span className="text-sm">{fund}</span>
                  </label>
                ))}
              </div>
              <div>
                <h4 className="font-medium text-sm mb-2">General Funds</h4>
                {['BRK-A', 'XLV', 'XLE', 'XLF', 'XLI'].map((fund) => (
                  <label key={fund} className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={config.selectedFunds.includes(fund)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setConfig({
                            ...config,
                            selectedFunds: [...config.selectedFunds, fund],
                          })
                        } else {
                          setConfig({
                            ...config,
                            selectedFunds: config.selectedFunds.filter(
                              (f) => f !== fund
                            ),
                          })
                        }
                      }}
                      className="mr-2"
                    />
                    <span className="text-sm">{fund}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Analysis Settings</h3>
            <p className="text-sm text-gray-500 mb-4">
              Configure what to include in stock analysis.
            </p>

            <label className="flex items-center mb-3">
              <input
                type="checkbox"
                checked={config.analysisSettings.includeTechnical}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    analysisSettings: {
                      ...config.analysisSettings,
                      includeTechnical: e.target.checked,
                    },
                  })
                }
                className="mr-2"
              />
              <span>Include Technical Analysis (RSI, MACD, etc.)</span>
            </label>

            <label className="flex items-center mb-3">
              <input
                type="checkbox"
                checked={config.analysisSettings.includePeers}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    analysisSettings: {
                      ...config.analysisSettings,
                      includePeers: e.target.checked,
                    },
                  })
                }
                className="mr-2"
              />
              <span>Include Peer Comparison</span>
            </label>

            <label className="flex items-center mb-3">
              <input
                type="checkbox"
                checked={config.analysisSettings.includeAiAnalysis}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    analysisSettings: {
                      ...config.analysisSettings,
                      includeAiAnalysis: e.target.checked,
                    },
                  })
                }
                className="mr-2"
              />
              <span>Include AI-Powered Analysis and Recommendations</span>
            </label>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-6 pt-6 border-t">
          <button
            onClick={handleBack}
            disabled={currentStep === 1}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50"
          >
            Back
          </button>
          {currentStep < steps.length ? (
            <button
              onClick={handleNext}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Save Configuration
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
