import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchConfigSettings,
  updateConfigSettings,
  testAPIKey,
  fetchAvailableModels,
  getMarketScrapingConfig,
  fetchDataUseCategories,
  fetchScrapedWebsites,
  createScrapedWebsite,
  updateScrapedWebsite,
  deleteScrapedWebsite,
  testScrapeWebsite,
  testExistingWebsite,
  fetchCategoryMappings,
  updateCategoryMappings,
  refreshCategoryData,
  ConfigSettings,
  OllamaModelsResponse,
  ScrapedWebsite,
  ScrapedWebsiteCreate,
  ScrapedWebsiteUpdate,
  ScrapedWebsiteTestResponse,
  DataUseCategoriesResponse,
  CategoryMappingsResponse,
} from '../../services/api'

export default function Configuration() {
  const queryClient = useQueryClient()

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

  // Legacy custom websites (kept for backward compatibility)
  const [customWebsites, setCustomWebsites] = useState<Record<string, { name: string; url: string }>>({})

  // New enhanced website form
  const [showAddWebsite, setShowAddWebsite] = useState(false)
  const [newWebsite, setNewWebsite] = useState<ScrapedWebsiteCreate>({
    key: '',
    name: '',
    url: '',
    description: '',
    data_use: ['dashboard_sentiment'],  // Now an array for multiple selection
  })

  // Test scraping state
  const [testingWebsite, setTestingWebsite] = useState<string | null>(null)
  const [testPreviewResult, setTestPreviewResult] = useState<ScrapedWebsiteTestResponse | null>(null)
  const [showTestPreview, setShowTestPreview] = useState(false)

  // Edit website state
  const [editingWebsite, setEditingWebsite] = useState<ScrapedWebsite | null>(null)
  const [editWebsiteData, setEditWebsiteData] = useState<ScrapedWebsiteUpdate>({})

  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [saveMessage, setSaveMessage] = useState('')
  const [testingKey, setTestingKey] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { valid: boolean; message: string }>>({})

  // Category mappings state
  const [categoryMappings, setCategoryMappings] = useState<Record<string, string[]>>({})
  const [mappingsSaveStatus, setMappingsSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [refreshingCategory, setRefreshingCategory] = useState<string | null>(null)

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

  // Fetch data use categories and templates
  const { data: categoriesData } = useQuery<DataUseCategoriesResponse>({
    queryKey: ['dataUseCategories'],
    queryFn: fetchDataUseCategories,
  })

  // Fetch user's custom scraped websites
  const { data: scrapedWebsites, refetch: refetchWebsites } = useQuery<ScrapedWebsite[]>({
    queryKey: ['scrapedWebsites'],
    queryFn: () => fetchScrapedWebsites(),
  })

  // Fetch category mappings
  const { data: categoryMappingsData, refetch: refetchCategoryMappings } = useQuery<CategoryMappingsResponse>({
    queryKey: ['categoryMappings'],
    queryFn: fetchCategoryMappings,
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

  // Update category mappings when data is loaded
  useEffect(() => {
    if (categoryMappingsData) {
      setCategoryMappings(categoryMappingsData.mappings || {})
    }
  }, [categoryMappingsData])

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

  // Test scrape before adding a website
  const handleTestScrape = async () => {
    if (!newWebsite.url || !newWebsite.data_use) {
      alert('Please provide a URL and select a data category')
      return
    }

    setTestingWebsite('new')
    setTestPreviewResult(null)

    try {
      const result = await testScrapeWebsite({
        url: newWebsite.url,
        description: newWebsite.description,
        data_use: newWebsite.data_use,
      })
      setTestPreviewResult(result)
      setShowTestPreview(true)
    } catch (error: any) {
      setTestPreviewResult({
        success: false,
        error: error.response?.data?.detail || 'Test scraping failed',
        response_time_ms: 0,
        extraction_prompt_used: '',
      })
      setShowTestPreview(true)
    } finally {
      setTestingWebsite(null)
    }
  }

  // Test an existing website
  const handleTestExistingWebsite = async (key: string) => {
    setTestingWebsite(key)
    setTestPreviewResult(null)

    try {
      const result = await testExistingWebsite(key)
      setTestPreviewResult(result)
      setShowTestPreview(true)
      // Refetch websites to get updated last_test_* fields
      refetchWebsites()
    } catch (error: any) {
      setTestPreviewResult({
        success: false,
        error: error.response?.data?.detail || 'Test scraping failed',
        response_time_ms: 0,
        extraction_prompt_used: '',
      })
      setShowTestPreview(true)
    } finally {
      setTestingWebsite(null)
    }
  }

  // Add a new website using the new API
  const handleAddWebsite = async () => {
    const dataUseArray = Array.isArray(newWebsite.data_use) ? newWebsite.data_use : [newWebsite.data_use]
    if (!newWebsite.key || !newWebsite.name || !newWebsite.url || dataUseArray.length === 0) {
      alert('Please fill in all required fields (Key, Name, URL, and at least one Data Category)')
      return
    }

    // Validate key format (no spaces, alphanumeric and underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(newWebsite.key)) {
      alert('Key must contain only letters, numbers, and underscores')
      return
    }

    try {
      await createScrapedWebsite(newWebsite)
      setNewWebsite({
        key: '',
        name: '',
        url: '',
        description: '',
        data_use: ['dashboard_sentiment'],
      })
      setShowAddWebsite(false)
      setTestPreviewResult(null)
      setShowTestPreview(false)
      refetchWebsites()
      // Refetch the scraping config to update the dropdown
      queryClient.invalidateQueries({ queryKey: ['marketScrapingConfig'] })
      setSaveStatus('success')
      setSaveMessage('Website added successfully!')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (error: any) {
      setSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to add website')
      setTimeout(() => setSaveStatus('idle'), 5000)
    }
  }

  // Delete a website using the new API
  const handleRemoveWebsite = async (key: string) => {
    if (!confirm(`Are you sure you want to remove this website?`)) {
      return
    }

    try {
      await deleteScrapedWebsite(key)
      refetchWebsites()
      // Refetch the scraping config to update the dropdown
      queryClient.invalidateQueries({ queryKey: ['marketScrapingConfig'] })
      // If the removed website was selected, clear the selection
      if (marketScraping.website_key === key) {
        setMarketScraping({ ...marketScraping, website_key: '' })
      }
      setSaveStatus('success')
      setSaveMessage('Website removed successfully!')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (error: any) {
      setSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to remove website')
      setTimeout(() => setSaveStatus('idle'), 5000)
    }
  }

  // Legacy handler for backward compatibility with old custom_websites
  const handleRemoveLegacyWebsite = (key: string) => {
    const updated = { ...customWebsites }
    delete updated[key]
    setCustomWebsites(updated)

    // If the removed website was selected, clear the selection
    if (marketScraping.website_key === key) {
      setMarketScraping({ ...marketScraping, website_key: '' })
    }
  }

  // Start editing a website
  const handleStartEdit = (website: ScrapedWebsite) => {
    setEditingWebsite(website)
    setEditWebsiteData({
      name: website.name,
      url: website.url,
      description: website.description || '',
      data_use: website.data_use_list,
      is_active: website.is_active,
    })
    // Close add form if open
    setShowAddWebsite(false)
  }

  // Cancel editing
  const handleCancelEdit = () => {
    setEditingWebsite(null)
    setEditWebsiteData({})
  }

  // Save edited website
  const handleSaveEdit = async () => {
    if (!editingWebsite) return

    try {
      await updateScrapedWebsite(editingWebsite.key, editWebsiteData)
      setEditingWebsite(null)
      setEditWebsiteData({})
      refetchWebsites()
      queryClient.invalidateQueries({ queryKey: ['marketScrapingConfig'] })
      setSaveStatus('success')
      setSaveMessage('Website updated successfully!')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (error: any) {
      setSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to update website')
      setTimeout(() => setSaveStatus('idle'), 5000)
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

  // Toggle a source in a category mapping
  const handleToggleCategorySource = (category: string, sourceKey: string) => {
    setCategoryMappings((prev) => {
      const currentSources = prev[category] || []
      if (currentSources.includes(sourceKey)) {
        return { ...prev, [category]: currentSources.filter((s) => s !== sourceKey) }
      } else {
        return { ...prev, [category]: [...currentSources, sourceKey] }
      }
    })
  }

  // Save category mappings
  const handleSaveCategoryMappings = async () => {
    setMappingsSaveStatus('saving')
    try {
      await updateCategoryMappings(categoryMappings)
      setMappingsSaveStatus('success')
      refetchCategoryMappings()
      setTimeout(() => setMappingsSaveStatus('idle'), 3000)
    } catch (error: any) {
      setMappingsSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to save category mappings')
      setTimeout(() => setMappingsSaveStatus('idle'), 5000)
    }
  }

  // Refresh data for a category
  const handleRefreshCategory = async (category: string) => {
    setRefreshingCategory(category)
    try {
      const result = await refreshCategoryData(category)
      if (result.status === 'queued') {
        setSaveStatus('success')
        setSaveMessage(`Triggered refresh for ${result.jobs.length} data source(s)`)
        setTimeout(() => setSaveStatus('idle'), 3000)
      } else {
        setSaveStatus('error')
        setSaveMessage(result.message)
        setTimeout(() => setSaveStatus('idle'), 5000)
      }
    } catch (error: any) {
      setSaveStatus('error')
      setSaveMessage(error.response?.data?.detail || 'Failed to refresh category data')
      setTimeout(() => setSaveStatus('idle'), 5000)
    } finally {
      setRefreshingCategory(null)
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Default Model
              {!aiModels.default_model && modelsData?.default_model && (
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (using system default: {modelsData.default_model})
                </span>
              )}
            </label>
            <select
              value={aiModels.default_model || modelsData?.default_model || ''}
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
              <option value="">
                Use default model {aiModels.default_model || modelsData?.default_model ? `(${aiModels.default_model || modelsData?.default_model})` : ''}
              </option>
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
              <option value="">
                Use default model {aiModels.default_model || modelsData?.default_model ? `(${aiModels.default_model || modelsData?.default_model})` : ''}
              </option>
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
              <option value="">
                Use default model {aiModels.default_model || modelsData?.default_model ? `(${aiModels.default_model || modelsData?.default_model})` : ''}
              </option>
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
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-4">
              <h3 className="text-sm font-semibold text-gray-900">Add New Website to Scrape</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Website Key (ID) *</label>
                  <input
                    type="text"
                    value={newWebsite.key}
                    onChange={(e) => setNewWebsite({ ...newWebsite, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="e.g., custom_market_watch"
                  />
                  <p className="mt-1 text-xs text-gray-500">Unique identifier (letters, numbers, underscores)</p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Data Source Name *</label>
                  <input
                    type="text"
                    value={newWebsite.name}
                    onChange={(e) => setNewWebsite({ ...newWebsite, name: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="e.g., MarketWatch Daily"
                  />
                  <p className="mt-1 text-xs text-gray-500">Display name for this data source</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Website URL *</label>
                <input
                  type="url"
                  value={newWebsite.url}
                  onChange={(e) => setNewWebsite({ ...newWebsite, url: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="https://example.com/market-data"
                />
                <p className="mt-1 text-xs text-gray-500">Full URL of the page to scrape</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Data Categories * (select multiple)</label>
                <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-lg p-2 space-y-1">
                  {categoriesData?.categories.map((cat) => {
                    const dataUseArray = Array.isArray(newWebsite.data_use) ? newWebsite.data_use : [newWebsite.data_use]
                    const isSelected = dataUseArray.includes(cat.value)
                    return (
                      <label
                        key={cat.value}
                        className={`flex items-start gap-2 p-2 rounded cursor-pointer hover:bg-gray-50 ${isSelected ? 'bg-primary-50 border border-primary-200' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            const currentArray = Array.isArray(newWebsite.data_use) ? newWebsite.data_use : [newWebsite.data_use]
                            if (e.target.checked) {
                              setNewWebsite({ ...newWebsite, data_use: [...currentArray, cat.value] })
                            } else {
                              setNewWebsite({ ...newWebsite, data_use: currentArray.filter(v => v !== cat.value) })
                            }
                          }}
                          className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900">{cat.label}</div>
                          <div className="text-xs text-gray-500">{cat.description}</div>
                        </div>
                      </label>
                    )
                  })}
                </div>
                <p className="mt-1 text-xs text-gray-500">Select which features/functions will use this data (can select multiple)</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Scraping Description</label>
                <textarea
                  value={newWebsite.description || ''}
                  onChange={(e) => setNewWebsite({ ...newWebsite, description: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Describe what specific data should be extracted from this page..."
                  rows={3}
                />
                <p className="mt-1 text-xs text-gray-500">Help the AI understand what data you want to extract</p>
              </div>

              {/* Test Preview Results */}
              {showTestPreview && testPreviewResult && (
                <div className={`p-4 rounded-lg border ${testPreviewResult.success ? 'bg-success-50 border-success-200' : 'bg-danger-50 border-danger-200'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testPreviewResult.success ? (
                      <svg className="w-5 h-5 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-danger-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                    <span className={`text-sm font-semibold ${testPreviewResult.success ? 'text-success-800' : 'text-danger-800'}`}>
                      {testPreviewResult.success ? 'Test Successful' : 'Test Failed'}
                    </span>
                    <span className="text-xs text-gray-500">({testPreviewResult.response_time_ms}ms)</span>
                  </div>

                  {testPreviewResult.success && testPreviewResult.scraped_data && (
                    <div className="mt-2">
                      <p className="text-xs font-medium text-gray-700 mb-1">Extracted Data Preview:</p>
                      <pre className="p-2 bg-white rounded border text-xs overflow-auto max-h-48">
                        {JSON.stringify(testPreviewResult.scraped_data, null, 2)}
                      </pre>
                    </div>
                  )}

                  {testPreviewResult.error && (
                    <p className="text-sm text-danger-700 mt-2">{testPreviewResult.error}</p>
                  )}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleTestScrape}
                  disabled={testingWebsite === 'new' || !newWebsite.url}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {testingWebsite === 'new' ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Testing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Test Scraping
                    </>
                  )}
                </button>
                <button
                  onClick={handleAddWebsite}
                  disabled={!newWebsite.key || !newWebsite.name || !newWebsite.url}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Add Website
                </button>
                <button
                  onClick={() => {
                    setShowAddWebsite(false)
                    setNewWebsite({ key: '', name: '', url: '', description: '', data_use: ['dashboard_sentiment'] })
                    setTestPreviewResult(null)
                    setShowTestPreview(false)
                  }}
                  className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Scraped Websites List (from database) */}
          {scrapedWebsites && scrapedWebsites.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">Your Configured Websites</h3>
              {scrapedWebsites.map((website) => (
                <div key={website.key}>
                  {/* Edit Form */}
                  {editingWebsite?.key === website.key ? (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-gray-900">Edit Website: {website.key}</h4>
                        <button
                          onClick={handleCancelEdit}
                          className="text-gray-500 hover:text-gray-700"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">Data Source Name</label>
                          <input
                            type="text"
                            value={editWebsiteData.name || ''}
                            onChange={(e) => setEditWebsiteData({ ...editWebsiteData, name: e.target.value })}
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
                          <select
                            value={editWebsiteData.is_active ? 'active' : 'inactive'}
                            onChange={(e) => setEditWebsiteData({ ...editWebsiteData, is_active: e.target.value === 'active' })}
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Website URL</label>
                        <input
                          type="url"
                          value={editWebsiteData.url || ''}
                          onChange={(e) => setEditWebsiteData({ ...editWebsiteData, url: e.target.value })}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Data Categories</label>
                        <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2 space-y-1">
                          {categoriesData?.categories.map((cat) => {
                            const currentDataUse = Array.isArray(editWebsiteData.data_use) ? editWebsiteData.data_use : []
                            const isSelected = currentDataUse.includes(cat.value)
                            return (
                              <label
                                key={cat.value}
                                className={`flex items-start gap-2 p-2 rounded cursor-pointer hover:bg-gray-50 ${isSelected ? 'bg-primary-50 border border-primary-200' : ''}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setEditWebsiteData({ ...editWebsiteData, data_use: [...currentDataUse, cat.value] })
                                    } else {
                                      setEditWebsiteData({ ...editWebsiteData, data_use: currentDataUse.filter(v => v !== cat.value) })
                                    }
                                  }}
                                  className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                />
                                <div className="flex-1">
                                  <div className="text-sm font-medium text-gray-900">{cat.label}</div>
                                  <div className="text-xs text-gray-500">{cat.description}</div>
                                </div>
                              </label>
                            )
                          })}
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Scraping Description</label>
                        <textarea
                          value={editWebsiteData.description || ''}
                          onChange={(e) => setEditWebsiteData({ ...editWebsiteData, description: e.target.value })}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                          placeholder="Describe what specific data should be extracted..."
                          rows={3}
                        />
                      </div>

                      <div className="flex gap-2 pt-2">
                        <button
                          onClick={handleSaveEdit}
                          className="flex-1 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
                        >
                          Save Changes
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Display Mode */
                    <div className={`p-3 rounded-lg border ${website.is_active ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">{website.name}</span>
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              website.is_active ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-600'
                            }`}>
                              {website.is_active ? 'Active' : 'Inactive'}
                            </span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">
                              {website.data_use_display}
                            </span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">{website.url}</div>
                          {website.description && (
                            <div className="text-xs text-gray-500 mt-1 italic">{website.description}</div>
                          )}
                          {website.last_test_at && (
                            <div className="flex items-center gap-2 mt-2 text-xs">
                              <span className="text-gray-500">Last tested: {new Date(website.last_test_at).toLocaleString()}</span>
                              {website.last_test_success !== null && (
                                <span className={`px-1.5 py-0.5 rounded ${website.last_test_success ? 'bg-success-100 text-success-700' : 'bg-danger-100 text-danger-700'}`}>
                                  {website.last_test_success ? 'Passed' : 'Failed'}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 ml-3">
                          <button
                            onClick={() => handleStartEdit(website)}
                            className="p-2 text-amber-600 hover:bg-amber-100 rounded-lg transition-colors"
                            title="Edit website"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleTestExistingWebsite(website.key)}
                            disabled={testingWebsite === website.key}
                            className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                            title="Test scraping"
                          >
                            {testingWebsite === website.key ? (
                              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                              </svg>
                            ) : (
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            )}
                          </button>
                          <button
                            onClick={() => handleRemoveWebsite(website.key)}
                            className="p-2 text-danger-600 hover:bg-danger-100 rounded-lg transition-colors"
                            title="Remove website"
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
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Legacy Custom Websites List (backward compatibility) */}
          {Object.keys(customWebsites).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">Legacy Custom Websites</h3>
              <p className="text-xs text-gray-500">These websites use the old format. Consider re-adding them with the new form for better functionality.</p>
              {Object.entries(customWebsites).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{value.name}</div>
                    <div className="text-xs text-gray-600">{value.url}</div>
                    <div className="text-xs text-gray-500 mt-1">Key: {key}</div>
                  </div>
                  <button
                    onClick={() => handleRemoveLegacyWebsite(key)}
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
              <option value="">
                Use default model {aiModels.web_scraping_model || aiModels.default_model || modelsData?.default_model ? `(${aiModels.web_scraping_model || aiModels.default_model || modelsData?.default_model})` : ''}
              </option>
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
              <option value="">
                Use default model {aiModels.market_sentiment_model || aiModels.default_model || modelsData?.default_model ? `(${aiModels.market_sentiment_model || aiModels.default_model || modelsData?.default_model})` : ''}
              </option>
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

      {/* Section 5: Category Data Source Mappings */}
      <div className="card card-body bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Category Data Source Mappings</h2>
            <p className="text-sm text-gray-500">Configure which data sources to use for each dashboard category</p>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Select one or more data sources for each category. When the Dashboard loads, data from all selected sources
            will be fetched and combined for display.
          </p>

          {/* Mappings Save Status */}
          {mappingsSaveStatus !== 'idle' && (
            <div
              className={`p-3 rounded-lg ${
                mappingsSaveStatus === 'success'
                  ? 'bg-success-50 border border-success-200 text-success-800'
                  : mappingsSaveStatus === 'error'
                  ? 'bg-danger-50 border border-danger-200 text-danger-800'
                  : 'bg-primary-50 border border-primary-200 text-primary-800'
              }`}
            >
              {mappingsSaveStatus === 'saving' ? 'Saving mappings...' :
               mappingsSaveStatus === 'success' ? 'Category mappings saved successfully!' :
               'Failed to save category mappings'}
            </div>
          )}

          {/* Category Mappings Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {categoryMappingsData?.categories.map((catInfo) => (
              <div
                key={catInfo.category}
                className="p-4 border border-gray-200 rounded-lg bg-gray-50"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{catInfo.display_name}</h3>
                    <p className="text-xs text-gray-500">
                      {(categoryMappings[catInfo.category] || []).length} source(s) selected
                    </p>
                  </div>
                  <button
                    onClick={() => handleRefreshCategory(catInfo.category)}
                    disabled={refreshingCategory === catInfo.category || (categoryMappings[catInfo.category] || []).length === 0}
                    className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Refresh data from all sources"
                  >
                    {refreshingCategory === catInfo.category ? (
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    )}
                  </button>
                </div>

                {catInfo.available_sources.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No data sources configured for this category</p>
                ) : (
                  <div className="space-y-1">
                    {catInfo.available_sources.map((source) => {
                      const isSelected = (categoryMappings[catInfo.category] || []).includes(source.key)
                      return (
                        <label
                          key={source.key}
                          className={`flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-white ${
                            isSelected ? 'bg-primary-50 border border-primary-200' : 'border border-transparent'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleCategorySource(catInfo.category, source.key)}
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-900 truncate">{source.name}</div>
                            <div className="text-xs text-gray-500 truncate">{source.url}</div>
                          </div>
                        </label>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Save Mappings Button */}
          <div className="flex justify-end pt-4 border-t border-gray-200">
            <button
              onClick={handleSaveCategoryMappings}
              disabled={mappingsSaveStatus === 'saving'}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {mappingsSaveStatus === 'saving' ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Saving...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Save Category Mappings
                </>
              )}
            </button>
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
