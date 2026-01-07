import { useState } from 'react'
import type { WatchlistLineResponse, WatchlistLineUpdate, TriggeredAlertResponse } from '../../types'

interface CustomLinesListProps {
  lines: WatchlistLineResponse[]
  triggeredAlerts: TriggeredAlertResponse[]
  onUpdateLine: (lineId: number, updates: WatchlistLineUpdate) => Promise<void>
  onDeleteLine: (lineId: number) => Promise<void>
}

export default function CustomLinesList({
  lines,
  triggeredAlerts,
  onUpdateLine,
  onDeleteLine,
}: CustomLinesListProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editPrice, setEditPrice] = useState('')

  const handleStartEdit = (line: WatchlistLineResponse) => {
    setEditingId(line.id)
    setEditName(line.name)
    setEditPrice(line.price_level.toString())
  }

  const handleSaveEdit = async (lineId: number) => {
    const updates: WatchlistLineUpdate = {}
    const line = lines.find((l) => l.id === lineId)
    if (!line) return

    if (editName !== line.name) {
      updates.name = editName
    }
    const newPrice = parseFloat(editPrice)
    if (!isNaN(newPrice) && newPrice !== line.price_level) {
      updates.price_level = newPrice
    }

    if (Object.keys(updates).length > 0) {
      await onUpdateLine(lineId, updates)
    }
    setEditingId(null)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditName('')
    setEditPrice('')
  }

  const handleToggleActive = async (line: WatchlistLineResponse) => {
    await onUpdateLine(line.id, { is_active: !line.is_active })
  }

  const getLineTypeStyles = (lineType: string) => {
    if (lineType === 'alert') {
      return {
        bg: 'bg-orange-50',
        border: 'border-orange-200',
        text: 'text-orange-700',
        badge: 'bg-orange-100 text-orange-700',
        dot: 'bg-orange-500',
      }
    }
    return {
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      text: 'text-purple-700',
      badge: 'bg-purple-100 text-purple-700',
      dot: 'bg-purple-500',
    }
  }

  const trendLines = lines.filter((l) => l.line_type === 'trend')
  const alertLines = lines.filter((l) => l.line_type === 'alert')

  // Get triggered alerts for alert lines
  const getTriggeredForLine = (lineId: number) => {
    return triggeredAlerts.find((a) => a.line_id === lineId)
  }

  return (
    <div className="card card-body">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Custom Lines & Alerts</h2>

      {lines.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
              />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">No custom lines yet</p>
          <p className="text-gray-400 text-xs mt-1">
            Use the chart buttons to add trend lines or alerts
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Triggered Alerts Banner */}
          {triggeredAlerts.length > 0 && (
            <div className="p-3 bg-warning-50 border border-warning-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full bg-warning-500 animate-pulse" />
                <span className="text-sm font-medium text-warning-800">
                  {triggeredAlerts.length} Alert{triggeredAlerts.length > 1 ? 's' : ''} Triggered Today
                </span>
              </div>
              <div className="space-y-1">
                {triggeredAlerts.map((alert) => (
                  <div key={alert.id} className="text-xs text-warning-700">
                    <span className="font-medium">{alert.line_name}</span>:{' '}
                    {alert.direction === 'crossed_up' ? 'Crossed up' : 'Crossed down'} at $
                    {alert.triggered_price.toFixed(2)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Alert Lines */}
          {alertLines.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-orange-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                Alert Lines ({alertLines.length})
              </h3>
              {alertLines.map((line) => {
                const styles = getLineTypeStyles(line.line_type)
                const triggered = getTriggeredForLine(line.id)
                const isEditing = editingId === line.id

                return (
                  <div
                    key={line.id}
                    className={`p-3 rounded-lg border ${styles.border} ${styles.bg} ${
                      !line.is_active ? 'opacity-50' : ''
                    }`}
                  >
                    {isEditing ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="input w-full text-sm"
                          placeholder="Line name"
                        />
                        <div className="flex gap-2">
                          <input
                            type="number"
                            step="0.01"
                            value={editPrice}
                            onChange={(e) => setEditPrice(e.target.value)}
                            className="input flex-1 text-sm"
                            placeholder="Price level"
                          />
                          <button
                            onClick={() => handleSaveEdit(line.id)}
                            className="btn-primary text-sm px-3"
                          >
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="btn-secondary text-sm px-3"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: line.color }}
                          />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900">{line.name}</span>
                              {triggered && (
                                <span className="px-1.5 py-0.5 text-xs rounded bg-warning-200 text-warning-800">
                                  Triggered
                                </span>
                              )}
                            </div>
                            <span className="text-sm text-gray-600">
                              ${line.price_level.toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleToggleActive(line)}
                            className={`p-1.5 rounded-lg transition-colors ${
                              line.is_active
                                ? 'text-success-600 hover:bg-success-100'
                                : 'text-gray-400 hover:bg-gray-200'
                            }`}
                            title={line.is_active ? 'Disable' : 'Enable'}
                          >
                            <svg
                              className="w-4 h-4"
                              fill={line.is_active ? 'currentColor' : 'none'}
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                              />
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                              />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleStartEdit(line)}
                            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                              />
                            </svg>
                          </button>
                          <button
                            onClick={() => onDeleteLine(line.id)}
                            className="p-1.5 text-gray-500 hover:text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
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
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Trend Lines */}
          {trendLines.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-purple-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
                  />
                </svg>
                Trend Lines ({trendLines.length})
              </h3>
              {trendLines.map((line) => {
                const styles = getLineTypeStyles(line.line_type)
                const isEditing = editingId === line.id

                return (
                  <div
                    key={line.id}
                    className={`p-3 rounded-lg border ${styles.border} ${styles.bg} ${
                      !line.is_active ? 'opacity-50' : ''
                    }`}
                  >
                    {isEditing ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="input w-full text-sm"
                          placeholder="Line name"
                        />
                        <div className="flex gap-2">
                          <input
                            type="number"
                            step="0.01"
                            value={editPrice}
                            onChange={(e) => setEditPrice(e.target.value)}
                            className="input flex-1 text-sm"
                            placeholder="Price level"
                          />
                          <button
                            onClick={() => handleSaveEdit(line.id)}
                            className="btn-primary text-sm px-3"
                          >
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="btn-secondary text-sm px-3"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: line.color }}
                          />
                          <div>
                            <span className="font-medium text-gray-900">{line.name}</span>
                            <span className="text-sm text-gray-600 ml-2">
                              ${line.price_level.toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleToggleActive(line)}
                            className={`p-1.5 rounded-lg transition-colors ${
                              line.is_active
                                ? 'text-success-600 hover:bg-success-100'
                                : 'text-gray-400 hover:bg-gray-200'
                            }`}
                            title={line.is_active ? 'Disable' : 'Enable'}
                          >
                            <svg
                              className="w-4 h-4"
                              fill={line.is_active ? 'currentColor' : 'none'}
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                              />
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                              />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleStartEdit(line)}
                            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                              />
                            </svg>
                          </button>
                          <button
                            onClick={() => onDeleteLine(line.id)}
                            className="p-1.5 text-gray-500 hover:text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
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
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
