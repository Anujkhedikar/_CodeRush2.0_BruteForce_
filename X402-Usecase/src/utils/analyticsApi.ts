import { createX402Fetch, X402WalletSigner } from './x402Client'

export async function fetchAnalytics(
  url: string,
  walletSigner: X402WalletSigner,
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url)

  if (!response.ok) {
    throw new Error(`Analytics fetch failed: HTTP ${response.status}`)
  }

  return response.json()
}

export async function createAnalyticsReport(
  url: string,
  walletSigner: X402WalletSigner,
  reportRequest: {
    start_date?: string
    end_date?: string
    report_type?: string
  },
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(reportRequest),
  })

  if (!response.ok) {
    throw new Error(`Analytics report failed: HTTP ${response.status}`)
  }

  return response.json()
}
