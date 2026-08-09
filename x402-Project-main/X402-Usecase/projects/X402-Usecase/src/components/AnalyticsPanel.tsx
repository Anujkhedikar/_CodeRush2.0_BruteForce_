import React, { useState } from 'react'
import { useWallet } from '@txnlab/use-wallet-react'
import { fetchAnalytics, createAnalyticsReport } from '../utils/analyticsApi'
import { X402WalletSigner } from '../utils/x402Client'

const AnalyticsPanel: React.FC = () => {
  const { activeAddress, signTransactions } = useWallet()
  const [loading, setLoading] = useState(false)
  const [analytics, setAnalytics] = useState<any>(null)
  const [report, setReport] = useState<any>(null)
  const [error, setError] = useState<string>('')

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4021'

  const signer: X402WalletSigner = {
    address: activeAddress ?? '',
    signTransactions: signTransactions,
  }

  const handleFetchAnalytics = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await fetchAnalytics(`${apiBaseUrl}/analytics?user_id=demo_user&range=7d`, signer)
      setAnalytics(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analytics request failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await createAnalyticsReport(
        `${apiBaseUrl}/analytics/report`,
        signer,
        {
          start_date: '2026-05-01',
          end_date: '2026-05-07',
          report_type: 'summary',
        },
      )
      setReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card bg-white shadow-xl">
      <div className="card-body">
        <h2 className="card-title">Premium Analytics</h2>
        <p className="text-sm text-base-content/70">Pay 0.01 USDC to access analytics and 0.02 USDC to generate a report.</p>

        <div className="grid gap-3 md:grid-cols-2">
          <button className={`btn btn-primary ${loading ? 'loading' : ''}`} onClick={handleFetchAnalytics} disabled={loading}>
            Fetch Analytics
          </button>
          <button className={`btn btn-secondary ${loading ? 'loading' : ''}`} onClick={handleGenerateReport} disabled={loading}>
            Generate Report
          </button>
        </div>

        {error && (
          <div className="alert alert-error mt-4">
            <div>{error}</div>
          </div>
        )}

        {analytics && (
          <div className="mt-4">
            <h3 className="font-semibold">Analytics Result</h3>
            <pre className="whitespace-pre-wrap bg-slate-950 text-slate-100 rounded-lg p-3 text-sm">
              {JSON.stringify(analytics, null, 2)}
            </pre>
          </div>
        )}

        {report && (
          <div className="mt-4">
            <h3 className="font-semibold">Generated Report</h3>
            <pre className="whitespace-pre-wrap bg-slate-950 text-slate-100 rounded-lg p-3 text-sm">
              {JSON.stringify(report, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnalyticsPanel
