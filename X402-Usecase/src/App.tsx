import { SupportedWallet, WalletId, WalletManager, WalletProvider } from '@txnlab/use-wallet-react'
import { SnackbarProvider } from 'notistack'
import { useState } from 'react'
import Home from './Home'
import MemeHome from './MemeHome'
import AnalyticsPanel from './components/AnalyticsPanel'
import AIAnalysisPanel from './components/AIAnalysisPanel'
import CreatorContentPanel from './components/CreatorContentPanel'
import TacticalHero from './components/TacticalHero'
import CodeMentorPlayground from './components/CodeMentorPlayground'
import { getAlgodConfigFromViteEnvironment, getKmdConfigFromViteEnvironment } from './utils/network/getAlgoClientConfigs'

let supportedWallets: SupportedWallet[]
if (import.meta.env.VITE_ALGOD_NETWORK === 'localnet') {
  const kmdConfig = getKmdConfigFromViteEnvironment()
  supportedWallets = [
    {
      id: WalletId.KMD,
      options: {
        baseServer: kmdConfig.server,
        token: String(kmdConfig.token),
        port: String(kmdConfig.port),
      },
    },
  ]
} else {
  supportedWallets = [
    { id: WalletId.DEFLY },
    { id: WalletId.PERA },
    { id: WalletId.EXODUS },
    { id: WalletId.LUTE },
    // If you are interested in WalletConnect v2 provider
    // refer to https://github.com/TxnLab/use-wallet for detailed integration instructions
  ]
}

type TabType = 'weather' | 'meme' | 'analytics' | 'ai' | 'creator' | 'pro' | 'mentor'

export default function App() {
  const algodConfig = getAlgodConfigFromViteEnvironment()
  const [activeTab, setActiveTab] = useState<TabType>('mentor')

  const walletManager = new WalletManager({
    wallets: supportedWallets,
    defaultNetwork: algodConfig.network,
    networks: {
      [algodConfig.network]: {
        algod: {
          baseServer: algodConfig.server,
          port: algodConfig.port,
          token: String(algodConfig.token),
        },
      },
    },
    options: {
      resetNetwork: true,
    },
  })

  return activeTab === 'mentor' ? (
    <CodeMentorPlayground onExitApp={(tab) => setActiveTab(tab as TabType)} />
  ) : (
    <SnackbarProvider maxSnack={3}>
      <WalletProvider manager={walletManager}>
        <div className="min-h-screen">
          {/* Tab Navigation */}
          <div className="bg-white shadow-md sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4">
              <div className="flex space-x-1">
                <button
                  onClick={() => setActiveTab('weather')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'weather'
                      ? 'text-teal-600 border-b-4 border-teal-600 bg-teal-50'
                      : 'text-gray-600 hover:text-teal-600 hover:bg-gray-50'
                  }`}
                >
                  🌤️ Weather
                </button>
                <button
                  onClick={() => setActiveTab('meme')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'meme'
                      ? 'text-purple-600 border-b-4 border-purple-600 bg-purple-50'
                      : 'text-gray-600 hover:text-purple-600 hover:bg-gray-50'
                  }`}
                >
                  🎨 Meme
                </button>
                <button
                  onClick={() => setActiveTab('analytics')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'analytics'
                      ? 'text-blue-600 border-b-4 border-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  📊 Analytics
                </button>
                <button
                  onClick={() => setActiveTab('ai')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'ai'
                      ? 'text-indigo-600 border-b-4 border-indigo-600 bg-indigo-50'
                      : 'text-gray-600 hover:text-indigo-600 hover:bg-gray-50'
                  }`}
                >
                  🤖 AI
                </button>
                <button
                  onClick={() => setActiveTab('creator')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'creator'
                      ? 'text-amber-600 border-b-4 border-amber-600 bg-amber-50'
                      : 'text-gray-600 hover:text-amber-600 hover:bg-gray-50'
                  }`}
                >
                  👤 Creator
                </button>
                <button
                  onClick={() => setActiveTab('pro')}
                  className={`px-5 py-4 font-semibold transition-all ${
                    activeTab === 'pro'
                      ? 'text-orange-600 border-b-4 border-orange-600 bg-orange-50'
                      : 'text-gray-600 hover:text-orange-600 hover:bg-gray-50'
                  }`}
                >
                  ⚡ Pro Landing
                </button>
                <button
                  onClick={() => setActiveTab('mentor')}
                  className="px-5 py-4 font-semibold transition-all text-red-600 hover:text-red-700"
                >
                  🧠 Mentor
                </button>
              </div>
            </div>
          </div>

          {/* Tab Content */}
          <div className="transition-all duration-300">
            {activeTab === 'weather' && <Home />}
            {activeTab === 'meme' && <MemeHome />}
            {activeTab === 'analytics' && (
              <div className="min-h-screen bg-slate-50 p-4">
                <div className="max-w-7xl mx-auto">
                  <AnalyticsPanel />
                </div>
              </div>
            )}
            {activeTab === 'ai' && (
              <div className="min-h-screen bg-slate-50 p-4">
                <div className="max-w-7xl mx-auto">
                  <AIAnalysisPanel />
                </div>
              </div>
            )}
            {activeTab === 'creator' && (
              <div className="min-h-screen bg-slate-50 p-4">
                <div className="max-w-7xl mx-auto">
                  <CreatorContentPanel />
                </div>
              </div>
            )}
            {activeTab === 'pro' && <TacticalHero />}
          </div>
        </div>
      </WalletProvider>
    </SnackbarProvider>
  )
}