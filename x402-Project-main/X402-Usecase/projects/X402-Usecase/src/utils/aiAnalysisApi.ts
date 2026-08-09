import { createX402Fetch, X402WalletSigner } from './x402Client'

export async function analyzeContent(
  url: string,
  walletSigner: X402WalletSigner,
  payload: { content: string; analysis_type?: string },
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`AI analysis failed: HTTP ${response.status}`)
  }

  return response.json()
}

export async function analyzeContentBatch(
  url: string,
  walletSigner: X402WalletSigner,
  payload: { items: string[]; analysis_type?: string },
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`AI batch analysis failed: HTTP ${response.status}`)
  }

  return response.json()
}
