import { createX402Fetch, X402WalletSigner } from './x402Client'

export async function fetchExclusiveContent(
  url: string,
  walletSigner: X402WalletSigner,
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url)

  if (!response.ok) {
    throw new Error(`Exclusive content failed: HTTP ${response.status}`)
  }

  return response.json()
}

export async function fetchCreatorContentList(
  url: string,
  walletSigner: X402WalletSigner,
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url)

  if (!response.ok) {
    throw new Error(`Creator content list failed: HTTP ${response.status}`)
  }

  return response.json()
}

export async function publishCreatorContent(
  url: string,
  walletSigner: X402WalletSigner,
  body: {
    title: string
    type: string
    price: string
    content: string
    creator_wallet: string
  },
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Publish content failed: HTTP ${response.status}`)
  }

  return response.json()
}

export async function fetchCreatorEarnings(
  url: string,
  walletSigner: X402WalletSigner,
): Promise<any> {
  const fetchFn = await createX402Fetch(walletSigner)
  const response = await fetchFn(url)

  if (!response.ok) {
    throw new Error(`Creator earnings failed: HTTP ${response.status}`)
  }

  return response.json()
}
