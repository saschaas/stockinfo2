import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  fetchConfigSettings,
  updateConfigSettings,
  testAPIKey,
  fetchAvailableModels,
  getMarketScrapingConfig,
  ConfigSettings,
  OllamaModelsResponse,
} from '../../services/api'

export default function Configuration() {
  // State for form values
  const [apiKeys, setApiKeys] = useState({
    alphaVantage: '',
    fmp: '',
    secUserAgent: '',
  })

  const [aiModels, setAiModels] = useState({
    default_model: '',
    stock_research_model: '',
    market_sentiment_model: '',
    web_scraping_model: '',
    temperature: 0.3,
    max_tokens: 2048,
  })

  const [displayPreferences, setDisplayPreferences] = useState({
    research_history_items: 10,
    fund_recent_changes_items: 10,
    holdings_per_fund: 50,
    peers_in_comparison: 5,
  })

  const [marketScraping, setMarketScraping] = useState({
    website_key: '',
    scraping_model: '',
    analysis_model: '',
  })

  const [customWebsites, setCustomWebsites] = useState<Record<string, { name: string; url: string }>>({})
  const [showAddWebsite, setShowAddWebsite] = useState(false)
  const [newWebsite, setNewWebsite] = useState({
    key: '',
    name: '',
    url: '',
  })

  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [saveMessage, setSaveMessage] = useState('')
  const [testingKey, setTestingKey] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { valid: boolean; message: string }>>({})

  // Fetch current configuration
  const { data: configData, isLoading: configLoading } = useQuery({
    queryKey: ['configSettings'],
    queryFn: fetchConfigSettings,
  })

  // Fetch available Ollama models
  const { data: modelsData } = useQuery<OllamaModelsResponse>({
    queryKey: ['availableModels'],
    queryFn: fetchAvailableModels,
  })

  // Fetch market scraping websites
  const { data: scrapingConfig } = useQuery({
    queryKey: ['marketScrapingConfig'],
    queryFn: getMarketScrapingConfig,
  })

  // Update form when config data is loaded
  useEffect(() => {
    if (configData) {
      setAiModels({
        default_model: configData.settings.ai_models.default_model || '',
        stock_research_model: configData.settings.ai_models.stock_research_model || '',
        market_sentiment_model: configData.settings.ai_models.market_sentiment_model || '',
        web_scraping_model: configData.settings.ai_models.web_scraping_model || '',
        temperature: configData.settings.ai_models.temperature ?? 0.3,
        max_tokens: configData.settings.ai_models.max_tokens ?? 2048,
      })

      setDisplayPreferences({
        research_history_items: configData.settings.display_preferences.research_history_items ?? 10,
        fund_recent_changes_items: configData.settings.display_preferences.fund_recent_changes_items ?? 10,
        holdings_per_fund: configData.settings.display_preferences.holdings_per_fund ?? 50,
        peers_in_comparison: configData.settings.display_preferences.peers_in_comparison ?? 5,
      })

      setMarketScraping({
        website_key: configData.settings.market_scraping.website_key || '',
        scraping_model: configData.settings.market_scraping.scraping_model || '',
        analysis_model: configData.settings.market_scraping.analysis_model || '',
      })

      setCustomWebsites(configData.settings.market_scraping.custom_websites || {})
    }
  }, [configData])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (settings: ConfigSettings) => updateConfigSettings(settings),
    onSuccess: () => {
      setSaveStatus('success')
      setSaveMessage('Configuration saved successfully!')
      setTimeout(() => setSaveStatus('idle'), 3000)
    },
    onError: (error: any) => {
      setSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to save configuration')
      setTimeout(() => setSaveStatus('idle'), 5000)
    },
  })

  const handleSave = () => {
    setSaveStatus('saving')

    const settings: ConfigSettings = {
      ai_models: aiModels,
      display_preferences: displayPreferences,
      market_scraping: {
        ...marketScraping,
        custom_websites: customWebsites,
      },
    }

    saveMutation.mutate(settings)
  }

  const handleAddWebsite = () => {
    if (!newWebsite.key || !newWebsite.name || !newWebsite.url) {
      alert('Please fill in all fields')
      return
    }

    if (customWebsites[newWebsite.key]) {
      alert('A website with this key already exists')
      return
    }

    setCustomWebsites({
      ...customWebsites,
      [newWebsite.key]: {
        name: newWebsite.name,
        url: newWebsite.url,
      },
    })

    setNewWebsite({ key: '', name: '', url: '' })
    setShowAddWebsite(false)
  }

  const handleRemoveWebsite = (key: string) => {
    const updated = { ...customWebsites }
    delete updated[key]
    setCustomWebsites(updated)

    // If the removed website was selected, clear the selection
    if (marketScraping.website_key === key) {
      setMarketScraping({ ...marketScraping, website_key: '' })
    }
  }

  const handleTestAPIKey = async (provider: 'alpha_vantage' | 'fmp') => {
    const key = provider === 'alpha_vantage' ? apiKeys.alphaVantage : apiKeys.fmp

    if (!key) {
      setTestResults({
        ...testResults,
        [provider]: { valid: false, message: 'Please enter an API key first' },
      })
      return
    }

    setTestingKey(provider)

    try {
      const result = await testAPIKey({ provider, api_key: key })
      setTestResults({
        ...testResults,
        [provider]: { valid: result.valid, message: result.message },
      })
    } catch (error: any) {
      setTestResults({
        ...testResults,
        [provider]: { valid: false, message: error.response?.data?.detail || 'Test failed' },
      })
    } finally {
      setTestingKey(null)
    }
  }

  if (configLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center animate-pulse">
          <svg className="w-6 h-6 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
      </div>
    )
  }

  const availableModels = modelsData?.models || []
  const websites = scrapingConfig?.available_websites || {}

  // Merge default websites with custom websites
  const allWebsites = { ...websites, ...customWebsites }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configuration</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your application settings and preferences</p>
      </div>

      {/* Save Status Banner */}
      {saveStatus !== 'idle' && (
        <div
          className={`card card-body ${
            saveStatus === 'success'
              ? 'bg-success-50 border-success-200'
              : saveStatus === 'error'
              ? 'bg-danger-50 border-danger-200'
              : 'bg-primary-50 border-primary-200'
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                saveStatus === 'success'
                  ? 'bg-success-100'
                  : saveStatus === 'error'
                  ? 'bg-danger-100'
                  : 'bg-primary-100'
              }`}
            >
              {saveStatus === 'saving' ? (
                <svg className="w-5 h-5 text-primary-600 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : saveStatus === 'success' ? (
                <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              )}
            </div>
            <p
              className={`font-medium ${
                saveStatus === 'success'
                  ? 'text-success-800'
                  : saveStatus === 'error'
                  ? 'text-danger-800'
                  : 'text-primary-800'
              }`}
            >
              {saveMessage || 'Saving configuration...'}
            </p>
          </div>
        </div>
      )}

      {/* Section 0: VPN / Network Settings */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">VPN / Network Settings</h2>
            <p className="text-sm text-gray-500">NordVPN connection for external API requests</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* VPN Status */}
          <div className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 bg-gray-50">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                configData?.vpn_status?.connected
                  ? 'bg-success-100'
                  : configData?.vpn_status?.enabled
                  ? 'bg-warning-100'
                  : 'bg-gray-100'
              }`}
            >
              {configData?.vpn_status?.connected ? (
                <svg className="w-6 h-6 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  />
                </svg>
              ) : configData?.vpn_status?.enabled ? (
                <svg className="w-6 h-6 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              ) : (
                <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                  />
                </svg>
              )}
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-gray-900">
                  {configData?.vpn_status?.connected
                    ? 'VPN Connected'
                    : configData?.vpn_status?.enabled
                    ? 'VPN Disconnected'
                    : 'VPN Disabled'}
                </h3>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    configData?.vpn_status?.connected
                      ? 'bg-success-100 text-success-800'
                      : configData?.vpn_status?.enabled
                      ? 'bg-warning-100 text-warning-800'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {configData?.vpn_status?.connected ? 'Protected' : configData?.vpn_status?.enabled ? 'Not Protected' : 'Direct'}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-2">{configData?.vpn_status?.message}</p>

              {configData?.vpn_status?.location && (
                <p className="text-xs text-gray-500">
                  <span className="font-medium">Location:</span> {configData.vpn_status.location}
                </p>
              )}
            </div>
          </div>

          {/* VPN Instructions */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">How to Toggle VPN Mode</h4>
            <p className="text-sm text-blue-800 mb-3">
              VPN routing is configured at the Docker level and requires container restart to change.
            </p>

            <div className="space-y-2 text-sm">
              <div className="p-3 bg-white rounded border border-blue-200">
                <p className="font-medium text-gray-900 mb-1">To disable VPN (direct connection):</p>
                <code className="block text-xs bg-gray-100 p-2 rounded text-gray-800 font-mono">
                  docker-compose -f docker-compose.yml -f docker-compose.no-vpn.yml up -d
                </code>
              </div>

              <div className="p-3 bg-white rounded border border-blue-200">
                <p className="font-medium text-gray-900 mb-1">To enable VPN (default):</p>
                <code className="block text-xs bg-gray-100 p-2 rounded text-gray-800 font-mono">
                  docker-compose up -d
                </code>
              </div>
            </div>

            <p className="text-xs text-blue-700 mt-3">
              Note: Without VPN, some APIs (especially Yahoo Finance) may rate-limit your IP address.
            </p>
          </div>
        </div>
      </div>

      {/* Section 1: API & Data Sources */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">API Keys & Data Sources</h2>
            <p className="text-sm text-gray-500">Configure API keys for external data providers</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Alpha Vantage API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Alpha Vantage API Key
              {configData?.has_alpha_vantage_key && (
                <span className="ml-2 text-xs text-success-600 font-normal">Configured</span>
              )}
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKeys.alphaVantage}
                onChange={(e) => setApiKeys({ ...apiKeys, alphaVantage: e.target.value })}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Enter your Alpha Vantage API key"
              />
              <button
                onClick={() => handleTestAPIKey('alpha_vantage')}
                disabled={testingKey === 'alpha_vantage' || !apiKeys.alphaVantage}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {testingKey === 'alpha_vantage' ? 'Testing...' : 'Test'}
              </button>
            </div>
            {testResults.alpha_vantage && (
              <p
                className={`mt-2 text-sm ${
                  testResults.alpha_vantage.valid ? 'text-success-600' : 'text-danger-600'
                }`}
              >
                {testResults.alpha_vantage.message}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Note: API keys are stored in environment variables. Enter and test here to update the server configuration.
            </p>
          </div>

          {/* FMP API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Financial Modeling Prep API Key
              {configData?.has_fmp_key && (
                <span className="ml-2 text-xs text-success-600 font-normal">Configured</span>
              )}
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKeys.fmp}
                onChange={(e) => setApiKeys({ ...apiKeys, fmp: e.target.value })}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Enter your FMP API key"
              />
              <button
                onClick={() => handleTestAPIKey('fmp')}
                disabled={testingKey === 'fmp' || !apiKeys.fmp}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {testingKey === 'fmp' ? 'Testing...' : 'Test'}
              </button>
            </div>
            {testResults.fmp && (
              <p className={`mt-2 text-sm ${testResults.fmp.valid ? 'text-success-600' : 'text-danger-600'}`}>
                {testResults.fmp.message}
              </p>
            )}
          </div>

          {/* SEC User Agent */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              SEC EDGAR User Agent
              {configData?.has_sec_user_agent && (
                <span className="ml-2 text-xs text-success-600 font-normal">Configured</span>
              )}
            </label>
            <input
              type="text"
              value={apiKeys.secUserAgent}
              onChange={(e) => setApiKeys({ ...apiKeys, secUserAgent: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Your Name your@email.com"
            />
            <p className="mt-1 text-xs text-gray-500">
              Required format: Your Name your@email.com (SEC requires identification for API access)
            </p>
          </div>
        </div>
      </div>

      {/* Section 2: AI Model Selection */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">AI Model Selection</h2>
            <p className="text-sm text-gray-500">Choose AI models for different analysis tasks</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Default Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Default Model</label>
            <select
              value={aiModels.default_model}
              onChange={(e) => setAiModels({ ...aiModels, default_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a model...</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Default model for all AI tasks</p>
          </div>

          {/* Stock Research Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Stock Research Model</label>
            <select
              value={aiModels.stock_research_model}
              onChange={(e) => setAiModels({ ...aiModels, stock_research_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Use default model</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Model for stock analysis and research</p>
          </div>

          {/* Market Sentiment Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Market Sentiment Model</label>
            <select
              value={aiModels.market_sentiment_model}
              onChange={(e) => setAiModels({ ...aiModels, market_sentiment_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Use default model</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Model for sentiment analysis</p>
          </div>

          {/* Web Scraping Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Web Scraping Model</label>
            <select
              value={aiModels.web_scraping_model}
              onChange={(e) => setAiModels({ ...aiModels, web_scraping_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Use default model</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Model for web scraping and extraction</p>
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temperature: {aiModels.temperature.toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={aiModels.temperature}
              onChange={(e) => setAiModels({ ...aiModels, temperature: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>More Focused</span>
              <span>More Creative</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Max Tokens</label>
            <input
              type="number"
              min="512"
              max="4096"
              step="256"
              value={aiModels.max_tokens}
              onChange={(e) => setAiModels({ ...aiModels, max_tokens: parseInt(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500">Maximum response length (512-4096)</p>
          </div>
        </div>
      </div>

      {/* Section 3: Display Preferences */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Display Preferences</h2>
            <p className="text-sm text-gray-500">Customize how information is displayed</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Research History Items */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Research History Items: {displayPreferences.research_history_items}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={displayPreferences.research_history_items}
              onChange={(e) =>
                setDisplayPreferences({
                  ...displayPreferences,
                  research_history_items: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          {/* Fund Recent Changes Items */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fund Recent Changes: {displayPreferences.fund_recent_changes_items}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={displayPreferences.fund_recent_changes_items}
              onChange={(e) =>
                setDisplayPreferences({
                  ...displayPreferences,
                  fund_recent_changes_items: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          {/* Holdings per Fund */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Holdings per Fund: {displayPreferences.holdings_per_fund}
            </label>
            <input
              type="range"
              min="10"
              max="100"
              step="10"
              value={displayPreferences.holdings_per_fund}
              onChange={(e) =>
                setDisplayPreferences({
                  ...displayPreferences,
                  holdings_per_fund: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>10</span>
              <span>100</span>
            </div>
          </div>

          {/* Peers in Comparison */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Peers in Comparison: {displayPreferences.peers_in_comparison}
            </label>
            <input
              type="range"
              min="3"
              max="10"
              step="1"
              value={displayPreferences.peers_in_comparison}
              onChange={(e) =>
                setDisplayPreferences({
                  ...displayPreferences,
                  peers_in_comparison: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>3</span>
              <span>10</span>
            </div>
          </div>
        </div>
      </div>

      {/* Section 4: Market Data Scraping */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Market Data Scraping</h2>
            <p className="text-sm text-gray-500">Configure web-scraped market data sources</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Website Selection */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-gray-700">Data Source Website</label>
              <button
                onClick={() => setShowAddWebsite(!showAddWebsite)}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Add Custom Website
              </button>
            </div>
            <select
              value={marketScraping.website_key}
              onChange={(e) => setMarketScraping({ ...marketScraping, website_key: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a website...</option>
              {Object.entries(allWebsites).map(([key, value]: [string, any]) => (
                <option key={key} value={key}>
                  {value.name} - {value.url}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Website to scrape for market insights</p>
          </div>

          {/* Add Website Form */}
          {showAddWebsite && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
              <h3 className="text-sm font-semibold text-gray-900">Add Custom Website</h3>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Website Key (ID)</label>
                <input
                  type="text"
                  value={newWebsite.key}
                  onChange={(e) => setNewWebsite({ ...newWebsite, key: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., custom_market_watch"
                />
                <p className="mt-1 text-xs text-gray-500">Unique identifier (no spaces, use underscores)</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Website Name</label>
                <input
                  type="text"
                  value={newWebsite.name}
                  onChange={(e) => setNewWebsite({ ...newWebsite, name: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Custom Market Watch"
                />
                <p className="mt-1 text-xs text-gray-500">Display name for the website</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Website URL</label>
                <input
                  type="url"
                  value={newWebsite.url}
                  onChange={(e) => setNewWebsite({ ...newWebsite, url: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="https://example.com/market-data"
                />
                <p className="mt-1 text-xs text-gray-500">Full URL of the website to scrape</p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleAddWebsite}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
                >
                  Add Website
                </button>
                <button
                  onClick={() => {
                    setShowAddWebsite(false)
                    setNewWebsite({ key: '', name: '', url: '' })
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Custom Websites List */}
          {Object.keys(customWebsites).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">Your Custom Websites</h3>
              {Object.entries(customWebsites).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{value.name}</div>
                    <div className="text-xs text-gray-600">{value.url}</div>
                    <div className="text-xs text-gray-500 mt-1">Key: {key}</div>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Remove custom website "${value.name}"?`)) {
                        handleRemoveWebsite(key)
                      }
                    }}
                    className="ml-3 p-2 text-danger-600 hover:bg-danger-100 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Scraping Model Override */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Scraping Model (Optional Override)
            </label>
            <select
              value={marketScraping.scraping_model}
              onChange={(e) => setMarketScraping({ ...marketScraping, scraping_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Use default scraping model</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Override model for web content extraction</p>
          </div>

          {/* Analysis Model Override */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Analysis Model (Optional Override)
            </label>
            <select
              value={marketScraping.analysis_model}
              onChange={(e) => setMarketScraping({ ...marketScraping, analysis_model: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Use default analysis model</option>
              {availableModels.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">Override model for sentiment analysis of scraped data</p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 py-4 -mx-6 px-6">
        <div className="max-w-6xl mx-auto flex justify-end gap-3">
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {saveStatus === 'saving' ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Saving...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
                  />
                </svg>
                Save Configuration
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
