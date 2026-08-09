import { x402Client, wrapFetchWithPayment } from '@x402-avm/fetch'
import { ALGORAND_TESTNET_CAIP2 } from '@x402-avm/avm'
import type { ClientAvmSigner } from '@x402-avm/avm'
import { ExactAvmScheme } from '@x402-avm/avm/exact/client'

export interface X402WalletSigner {
  address: string
  signTransactions: (txns: Uint8Array[]) => Promise<Array<Uint8Array | null> | Uint8Array[] | string[]>
}

export async function createX402Fetch(walletSigner: X402WalletSigner) {
  if (!walletSigner?.address || typeof walletSigner.signTransactions !== 'function') {
    throw new Error('Invalid wallet signer provided for x402')
  }

  console.log('createX402Fetch: initializing for address', walletSigner.address)
  const client = new x402Client()

  const x402Signer: ClientAvmSigner = {
    address: walletSigner.address,
    signTransactions: async (txns: Uint8Array[]) => {
      console.log('x402Signer.signTransactions: received', txns.length, 'transaction(s)')
      const result = await walletSigner.signTransactions(txns)

      if (Array.isArray(result)) {
        return result.map((item, index) => {
          if (item === null || item === undefined) {
            console.warn(`Transaction ${index} was not signed; returning original unsigned transaction`)
            return txns[index]
          }
          if (item instanceof Uint8Array) {
            return item
          }
          if (typeof item === 'string') {
            const binaryString = atob(item)
            const bytes = new Uint8Array(binaryString.length)
            for (let j = 0; j < binaryString.length; j += 1) {
              bytes[j] = binaryString.charCodeAt(j)
            }
            return bytes
          }
          return txns[index]
        }) as Array<Uint8Array | null>
      }

      return txns.map((txn) => txn as Uint8Array | null)
    },
  }

  client.register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme(x402Signer))
  console.log('x402 client registered for TestNet')
  return wrapFetchWithPayment(fetch, client)
}
