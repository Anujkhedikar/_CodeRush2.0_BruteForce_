import React, { useState } from 'react'
import { useWallet } from '@txnlab/use-wallet-react'
import { analyzeContent, analyzeContentBatch } from '../utils/aiAnalysisApi'
import { X402WalletSigner } from '../utils/x402Client'

const AIAnalysisPanel: React.FC = () => {
  const { activeAddress, signTransactions } = useWallet()
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<string>('')
  const [content, setContent] = useState('I need an AI review for my Algorand contract.')

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4021'
  const signer: X402WalletSigner = {
    address: activeAddress ?? '',
    signTransactions: signTransactions,
  }

  const handleSingleAnalysis = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await analyzeContent(`${apiBaseUrl}/ai-analysis`, signer, {
        content,
        analysis_type: 'code-quality',
      })
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const handleBatchAnalysis = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await analyzeContentBatch(`${apiBaseUrl}/ai-analysis/batch`, signer, {
        items: [content, 'Please summarize this text for stakeholders.', 'Give feedback on this design plan.'],
        analysis_type: 'summary',
      })
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI batch analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card bg-white shadow-xl">
      <div className="card-body">
        <h2 className="card-title">AI Analysis</h2>
        <p className="text-sm text-base-content/70">Pay 0.02 USDC for single analysis or 0.04 USDC for batch analysis.</p>

        <textarea
          className="textarea textarea-bordered w-full resize-none"
          rows={4}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={loading}
        />

        <div className="grid gap-3 md:grid-cols-2 mt-4">
          <button className={`btn btn-primary ${loading ? 'loading' : ''}`} onClick={handleSingleAnalysis} disabled={loading}>
            Analyze Content
          </button>
          <button className={`btn btn-secondary ${loading ? 'loading' : ''}`} onClick={handleBatchAnalysis} disabled={loading}>
            Analyze Batch
          </button>
        </div>

        {error && (
          <div className="alert alert-error mt-4">{error}</div>
        )}

        {response && (
          <div className="mt-4">
            <h3 className="font-semibold">Response</h3>
            <pre className="whitespace-pre-wrap bg-slate-950 text-slate-100 rounded-lg p-3 text-sm">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default AIAnalysisPanel
