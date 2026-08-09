import React, { useState } from 'react'
import { useWallet } from '@txnlab/use-wallet-react'
import {
  fetchExclusiveContent,
  fetchCreatorContentList,
  publishCreatorContent,
  fetchCreatorEarnings,
} from '../utils/creatorContentApi'
import { X402WalletSigner } from '../utils/x402Client'

const CreatorContentPanel: React.FC = () => {
  const { activeAddress, signTransactions } = useWallet()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<any>(null)
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [contentId, setContentId] = useState('456')
  const [creatorWallet, setCreatorWallet] = useState('')

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4021'
  const signer: X402WalletSigner = {
    address: activeAddress ?? '',
    signTransactions: signTransactions,
  }

  const handleFetchExclusiveContent = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await fetchExclusiveContent(`${apiBaseUrl}/exclusive-content/${contentId}`, signer)
      setData(response)
      setMessage('Exclusive content retrieved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFetchCreatorContentList = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    if (!creatorWallet) {
      setError('Enter a creator wallet address')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await fetchCreatorContentList(`${apiBaseUrl}/creators/${creatorWallet}/content`, signer)
      setData(response)
      setMessage('Creator content list retrieved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed')
    } finally {
      setLoading(false)
    }
  }

  const handlePublishContent = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await publishCreatorContent(`${apiBaseUrl}/creators/publish`, signer, {
        title: 'New Algorand Creator Content',
        type: 'tutorial',
        price: '0.05',
        content: 'This is paid creator content delivered via x402.',
        creator_wallet: activeAddress,
      })
      setData(response)
      setMessage('Content published successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Publish failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFetchEarnings = async () => {
    if (!activeAddress || !signTransactions) {
      setError('Connect wallet first')
      return
    }

    if (!creatorWallet) {
      setError('Enter a creator wallet address')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await fetchCreatorEarnings(`${apiBaseUrl}/creators/${creatorWallet}/earnings`, signer)
      setData(response)
      setMessage('Creator earnings retrieved')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card bg-white shadow-xl">
      <div className="card-body">
        <h2 className="card-title">Creator Content</h2>
        <p className="text-sm text-base-content/70">Access exclusive content and creator dashboards with x402 payment.</p>

        <div className="grid gap-3 md:grid-cols-2 mt-4">
          <button className={`btn btn-primary ${loading ? 'loading' : ''}`} onClick={handleFetchExclusiveContent} disabled={loading}>
            Fetch Exclusive Content
          </button>
          <button className={`btn btn-secondary ${loading ? 'loading' : ''}`} onClick={handlePublishContent} disabled={loading}>
            Publish Content
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2 mt-4">
          <button className={`btn btn-accent ${loading ? 'loading' : ''}`} onClick={handleFetchCreatorContentList} disabled={loading}>
            Creator Content List
          </button>
          <button className={`btn btn-info ${loading ? 'loading' : ''}`} onClick={handleFetchEarnings} disabled={loading}>
            Creator Earnings
          </button>
        </div>

        <div className="form-control mt-4">
          <label className="label">
            <span className="label-text">Creator Wallet Address</span>
          </label>
          <input
            type="text"
            className="input input-bordered"
            placeholder="Algorand wallet address"
            value={creatorWallet}
            onChange={(e) => setCreatorWallet(e.target.value)}
            disabled={loading}
          />
        </div>

        {message && (
          <div className="alert alert-success mt-4">{message}</div>
        )}

        {error && (
          <div className="alert alert-error mt-4">{error}</div>
        )}

        {data && (
          <div className="mt-4">
            <h3 className="font-semibold">Response Data</h3>
            <pre className="whitespace-pre-wrap bg-slate-950 text-slate-100 rounded-lg p-3 text-sm">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default CreatorContentPanel
