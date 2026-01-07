import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchDatabaseStats,
  exportDatabase,
  downloadExport,
  importDatabase,
  type ExportResponse,
  type ImportResponse,
} from '../../services/api'

// User data tables that are exported (funds/ETFs are loaded daily, not exported)
const USER_DATA_TABLES = [
  'watchlist_items',
  'user_configs',
]

// Friendly names for tables
const TABLE_DISPLAY_NAMES: Record<string, string> = {
  watchlist_items: 'Watchlist',
  stock_analyses: 'Research History',
  funds: 'Funds',
  fund_holdings: 'Fund Holdings',
  etfs: 'ETFs',
  etf_holdings: 'ETF Holdings',
  user_configs: 'User Settings',
  scraped_websites: 'Scraped Websites',
  stock_prices: 'Stock Prices',
  market_sentiment: 'Market Sentiment',
  web_scraped_market_data: 'Web Scraped Data',
  scraped_category_data: 'Category Data',
  research_jobs: 'Research Jobs',
  data_sources: 'Data Sources',
}

export default function Database() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [lastExport, setLastExport] = useState<ExportResponse | null>(null)
  const [importResult, setImportResult] = useState<ImportResponse | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [showConfirmImport, setShowConfirmImport] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch database stats
  const {
    data: stats,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['databaseStats'],
    queryFn: fetchDatabaseStats,
  })

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: exportDatabase,
    onSuccess: async (data) => {
      setLastExport(data)
      // Download the file
      try {
        const blob = await downloadExport(data.filename)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = data.filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } catch (err) {
        setError('Failed to download export file')
      }
      setExporting(false)
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to export database')
      setExporting(false)
    },
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: importDatabase,
    onSuccess: (data) => {
      setImportResult(data)
      setImporting(false)
      setSelectedFile(null)
      setShowConfirmImport(false)
      // Refresh stats after import
      queryClient.invalidateQueries({ queryKey: ['databaseStats'] })
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to import database')
      setImporting(false)
    },
  })

  // Handle export
  const handleExport = () => {
    setExporting(true)
    setError(null)
    exportMutation.mutate()
  }

  // Handle file selection
  const handleFileSelect = (file: File) => {
    if (!file.name.endsWith('.json')) {
      setError('Please select a JSON file')
      return
    }
    setSelectedFile(file)
    setShowConfirmImport(true)
    setError(null)
  }

  // Handle file input change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  // Handle drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [])

  // Handle import confirmation
  const handleConfirmImport = () => {
    if (!selectedFile) return
    setImporting(true)
    setError(null)
    importMutation.mutate(selectedFile)
  }

  // Get user data tables from stats
  const getUserDataStats = () => {
    if (!stats) return []
    return stats.tables.filter((t) => t.category === 'user_data')
  }

  // Calculate total user data rows
  const getTotalUserDataRows = () => {
    return getUserDataStats().reduce((sum, t) => sum + t.row_count, 0)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Database Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            View database statistics, export for backup, or import from backup
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn-secondary flex items-center gap-2"
          disabled={isLoading}
        >
          <svg
            className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-danger-50 border border-danger-200 rounded-xl text-danger-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-danger-500 hover:text-danger-700"
          >
            &times;
          </button>
        </div>
      )}

      {/* Database Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center">
              <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Size</p>
              <p className="text-2xl font-bold text-gray-900">
                {isLoading ? '...' : stats?.total_size_formatted || '0 B'}
              </p>
            </div>
          </div>
        </div>

        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-success-50 flex items-center justify-center">
              <svg className="w-6 h-6 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Tables</p>
              <p className="text-2xl font-bold text-gray-900">
                {isLoading ? '...' : stats?.table_count || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card card-body">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Rows</p>
              <p className="text-2xl font-bold text-gray-900">
                {isLoading ? '...' : stats?.total_rows?.toLocaleString() || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tables List */}
      <div className="card card-body">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Tables</h2>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-cream-dark rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="table-header text-left">
                  <th className="px-4 py-3 rounded-l-lg">Table</th>
                  <th className="px-4 py-3 text-right">Rows</th>
                  <th className="px-4 py-3 text-right">Size</th>
                  <th className="px-4 py-3 text-center rounded-r-lg">Category</th>
                </tr>
              </thead>
              <tbody>
                {stats?.tables.map((table) => (
                  <tr key={table.name} className="table-row">
                    <td className="px-4 py-3">
                      <span className="font-medium">{TABLE_DISPLAY_NAMES[table.name] || table.name}</span>
                      <span className="text-gray-400 text-sm ml-2">({table.name})</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {table.row_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {table.size_formatted}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`badge ${
                          table.category === 'user_data'
                            ? 'badge-success'
                            : table.category === 'cache'
                            ? 'badge-neutral'
                            : 'badge-warning'
                        }`}
                      >
                        {table.category === 'user_data'
                          ? 'User Data'
                          : table.category === 'cache'
                          ? 'Cache'
                          : 'System'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Export & Import Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Export Section */}
        <div className="card card-body">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Export Data</h2>
          <p className="text-gray-600 mb-4">
            Export your research data for backup or migration to another PC.
          </p>

          <div className="bg-cream rounded-xl p-4 mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Tables included:</h3>
            <ul className="space-y-1">
              {USER_DATA_TABLES.map((table) => {
                const tableStats = stats?.tables.find((t) => t.name === table)
                return (
                  <li key={table} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {TABLE_DISPLAY_NAMES[table] || table}
                    </span>
                    <span className="text-gray-500">
                      {tableStats ? `${tableStats.row_count.toLocaleString()} rows` : '...'}
                    </span>
                  </li>
                )
              })}
            </ul>
            <div className="mt-3 pt-3 border-t border-border-warm">
              <div className="flex items-center justify-between text-sm font-medium">
                <span>Total</span>
                <span>{getTotalUserDataRows().toLocaleString()} rows</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleExport}
            disabled={exporting || isLoading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {exporting ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Exporting...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export Database
              </>
            )}
          </button>

          {/* Last export info */}
          {lastExport && (
            <div className="mt-4 p-3 bg-success-50 border border-success-200 rounded-xl">
              <div className="flex items-center gap-2 text-success-700">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Export successful!</span>
              </div>
              <p className="mt-1 text-sm text-success-600">
                {lastExport.filename} ({lastExport.size_formatted})
              </p>
            </div>
          )}
        </div>

        {/* Import Section */}
        <div className="card card-body">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Import Data</h2>
          <p className="text-gray-600 mb-4">
            Restore data from a backup file. This will replace existing data.
          </p>

          {/* File drop zone */}
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary-500 bg-primary-50'
                : 'border-border-warm hover:border-primary-300 hover:bg-cream'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
            />
            <svg
              className="w-12 h-12 mx-auto text-gray-400 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-gray-600">
              Drop your backup file here or{' '}
              <span className="text-primary-600 font-medium cursor-pointer">browse</span>
            </p>
            <p className="text-sm text-gray-400 mt-1">JSON files only</p>
          </div>

          {/* Selected file */}
          {selectedFile && !showConfirmImport && (
            <div className="mt-4 p-3 bg-cream rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm font-medium">{selectedFile.name}</span>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>
          )}

          {/* Import result */}
          {importResult && (
            <div
              className={`mt-4 p-3 rounded-xl ${
                importResult.success
                  ? 'bg-success-50 border border-success-200'
                  : 'bg-danger-50 border border-danger-200'
              }`}
            >
              <div className={`flex items-center gap-2 ${importResult.success ? 'text-success-700' : 'text-danger-700'}`}>
                {importResult.success ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
                <span className="font-medium">
                  {importResult.success ? 'Import successful!' : 'Import failed'}
                </span>
              </div>
              {importResult.success && (
                <div className="mt-2 text-sm text-success-600">
                  <p>Imported {importResult.tables_imported.length} tables:</p>
                  <ul className="mt-1 space-y-0.5">
                    {importResult.tables_imported.map((table) => (
                      <li key={table}>
                        {TABLE_DISPLAY_NAMES[table] || table}: {importResult.row_counts[table]} rows
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {importResult.errors.length > 0 && (
                <div className="mt-2 text-sm text-danger-600">
                  <p>Errors:</p>
                  <ul className="mt-1 list-disc list-inside">
                    {importResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
              {importResult.warnings.length > 0 && (
                <div className="mt-2 text-sm text-yellow-600">
                  <p>Warnings:</p>
                  <ul className="mt-1 list-disc list-inside">
                    {importResult.warnings.map((warn, i) => (
                      <li key={i}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Import Confirmation Modal */}
      {showConfirmImport && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowConfirmImport(false)}
        >
          <div
            className="card card-body max-w-md w-full m-4 animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-danger-50 flex items-center justify-center">
                <svg className="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Confirm Import</h3>
                <p className="text-sm text-gray-500">This action will replace existing data</p>
              </div>
            </div>

            <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 mb-4">
              <p className="text-sm text-danger-700">
                <strong>Warning:</strong> Importing will delete all existing user data (watchlist, research history, fund/ETF configurations) and replace it with the data from the backup file.
              </p>
            </div>

            {selectedFile && (
              <div className="bg-cream rounded-xl p-3 mb-4">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm font-medium">{selectedFile.name}</span>
                  <span className="text-sm text-gray-500">
                    ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowConfirmImport(false)
                  setSelectedFile(null)
                }}
                className="btn-secondary flex-1"
                disabled={importing}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmImport}
                className="btn-primary flex-1 bg-danger-600 hover:bg-danger-700 flex items-center justify-center gap-2"
                disabled={importing}
              >
                {importing ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Importing...
                  </>
                ) : (
                  'Import & Replace'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
