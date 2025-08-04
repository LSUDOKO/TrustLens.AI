import { useState } from 'react'

function App() {
  const [walletAddress, setWalletAddress] = useState('')
  const [trustScore, setTrustScore] = useState(null)
  const [loading, setLoading] = useState(false)
  const [riskTags, setRiskTags] = useState([])
  const [explanation, setExplanation] = useState('')

  const analyzeWallet = async () => {
    if (!walletAddress.trim()) return
    
    setLoading(true)
    setTrustScore(null) // Reset previous results
    setRiskTags([])
    setExplanation('')
    
    try {
      const response = await fetch('http://localhost:8000/api/score', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ address: walletAddress.trim() }),
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setTrustScore(data.trust_score)
      setRiskTags(data.risk_tags)
      setExplanation(data.explanation)
      
    } catch (error) {
      console.error('Error analyzing wallet:', error)
      setExplanation(`Error analyzing wallet: ${error.message}. Make sure the backend server is running on http://localhost:8000`)
      setTrustScore(0)
      setRiskTags(['Analysis Failed'])
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-green-500'
    if (score >= 40) return 'text-yellow-500'
    return 'text-red-500'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Trust<span className="text-indigo-600">Lens</span>.AI
          </h1>
          <p className="text-xl text-gray-600">
            Advanced On-Chain Trust & Risk Analysis
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          {/* Input Section */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Wallet Address or ENS Name
            </label>
            <div className="flex gap-4">
              <input
                type="text"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
                placeholder="0x... or vitalik.eth"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <button
                onClick={analyzeWallet}
                disabled={loading || !walletAddress.trim()}
                className="px-8 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </div>

          {/* Results Section */}
          {trustScore !== null && (
            <div className="space-y-6">
              {/* Trust Score */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-32 h-32 rounded-full bg-gray-100 mb-4">
                  <span className={`text-4xl font-bold ${getScoreColor(trustScore)}`}>
                    {trustScore}
                  </span>
                </div>
                <h3 className="text-2xl font-semibold text-gray-900 mb-2">
                  Trust Score
                </h3>
                <div className="flex justify-center space-x-4 text-sm">
                  <span className="text-green-500">70-100: High Trust</span>
                  <span className="text-yellow-500">40-69: Medium Risk</span>
                  <span className="text-red-500">0-39: High Risk</span>
                </div>
              </div>

              {/* Risk Tags */}
              {riskTags.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">
                    Risk Factors
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {riskTags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Explanation */}
              {explanation && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">
                    AI Analysis
                  </h4>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-700">{explanation}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center text-gray-500 text-sm">
          <p>Built for HyperHack • Powered by AI & On-Chain Data</p>
        </div>
      </div>
    </div>
  )
}

export default App
