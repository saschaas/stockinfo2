import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

interface ErrorSuggestionProps {
  error: string
  suggestion?: string
  onRetry?: () => void
}

export default function ErrorSuggestion({
  error,
  suggestion,
  onRetry,
}: ErrorSuggestionProps) {
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null)

  const generateSuggestion = useMutation({
    mutationFn: async () => {
      // In production, this would call an API endpoint
      // that uses Ollama to generate a suggestion
      const response = await fetch('/api/v1/ai/error-suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate suggestion')
      }

      const data = await response.json()
      return data.suggestion
    },
    onSuccess: (suggestion) => {
      setAiSuggestion(suggestion)
    },
  })

  const displaySuggestion = aiSuggestion || suggestion

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-800">Error</h3>
          <p className="mt-1 text-sm text-red-700">{error}</p>

          {/* Action buttons */}
          <div className="mt-3 flex gap-2">
            {onRetry && (
              <button
                onClick={onRetry}
                className="text-sm font-medium text-red-600 hover:text-red-500"
              >
                Retry
              </button>
            )}

            {!displaySuggestion && (
              <button
                onClick={() => generateSuggestion.mutate()}
                disabled={generateSuggestion.isPending}
                className="text-sm font-medium text-primary-600 hover:text-primary-500 flex items-center gap-1"
              >
                {generateSuggestion.isPending ? (
                  <>
                    <svg
                      className="animate-spin h-4 w-4"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Generating...
                  </>
                ) : (
                  <>
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Get AI Suggestion
                  </>
                )}
              </button>
            )}
          </div>

          {/* Suggestion display */}
          {displaySuggestion && (
            <div className="mt-3 p-3 bg-white rounded border border-red-100">
              <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                <svg
                  className="h-3 w-3"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                Suggestion
              </div>
              <p className="text-sm text-gray-700">{displaySuggestion}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
