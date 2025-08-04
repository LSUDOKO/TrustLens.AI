# TrustLens.AI 🔍

**Advanced On-Chain Trust & Risk Analysis Platform**

Built for HyperHack - A comprehensive web application that analyzes wallet addresses and provides AI-powered trust scores and risk assessments.

## 🚀 Features

- **Real-time Wallet Analysis**: Analyze any Ethereum wallet address or ENS name
- **Trust Score Calculation**: 0-100 scoring system with color-coded risk levels
- **Risk Factor Detection**: Identifies specific risk patterns and behaviors
- **AI-Powered Explanations**: Natural language explanations of risk assessments
- **Modern UI**: Clean, responsive interface built with React and Tailwind CSS
- **Fast API Backend**: High-performance FastAPI backend with async processing

## 🏗️ Architecture

```
TrustLens.AI/
├── frontend/          # React + Vite + Tailwind CSS
│   ├── src/
│   │   ├── App.jsx    # Main application component
│   │   └── index.css  # Tailwind CSS configuration
│   └── package.json
├── backend/           # FastAPI Python backend
│   ├── main.py        # API endpoints and server configuration
│   ├── scoring.py     # Trust score calculation engine
│   ├── requirements.txt
│   └── .env           # Environment variables (not in git)
└── README_TRUSTLENS.md
```

## 🛠️ Setup Instructions

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8+
- npm or yarn

### 1. Clone and Navigate
```bash
cd TrustLens.AI
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
# Edit .env file and add your API keys:
# OPENROUTER_API_KEY=your_key_here
# ONCHAIN_PROVIDER_API_KEY=your_key_here
# FRONTEND_ORIGIN=http://localhost:5173

# Start the backend server
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## 🎯 How to Use

1. **Open the Application**: Navigate to `http://localhost:5173` in your browser
2. **Enter Wallet Address**: Input any Ethereum wallet address or ENS name
3. **Analyze**: Click the "Analyze" button to get the trust score
4. **Review Results**: 
   - **Trust Score**: 0-100 rating with color coding
   - **Risk Factors**: Specific tags indicating potential risks
   - **AI Explanation**: Natural language analysis of the wallet

## 📊 Trust Score Breakdown

| Score Range | Risk Level | Color | Description |
|-------------|------------|-------|-------------|
| 70-100 | Low Risk | 🟢 Green | High trust, established wallet |
| 40-69 | Medium Risk | 🟡 Yellow | Some concerns, proceed with caution |
| 0-39 | High Risk | 🔴 Red | Multiple risk factors detected |

## 🔧 Risk Factors Analyzed

- **Wallet Age**: Newer wallets are considered riskier
- **Transaction Volume**: Low activity may indicate suspicious behavior
- **DeFi Engagement**: Contract interactions show legitimate usage
- **Identity Verification**: ENS domains and social links add credibility
- **Flagged Interactions**: Connections to known risky addresses
- **Trading Patterns**: Detection of potential wash trading

## 🚀 Deployment

### Backend Deployment (Railway/Render/Fly.io)
```bash
# Example for Railway
railway login
railway init
railway up
```

### Frontend Deployment (Vercel/Netlify)
```bash
# Example for Vercel
npm install -g vercel
vercel
```

## 🔮 Future Enhancements

- **Real API Integration**: Connect to Etherscan, Alchemy, or Moralis
- **OpenRouter AI**: Advanced AI explanations using OpenRouter
- **ENS Resolution**: Automatic ENS name resolution
- **Social Profile Linking**: GitHub, Farcaster, Lens integration
- **Batch Analysis**: Analyze multiple wallets simultaneously
- **Historical Tracking**: Track wallet trust scores over time
- **Custom Risk Models**: Configurable scoring algorithms

## 🛡️ Security Notes

- Never commit `.env` files to version control
- API keys should be stored securely
- Rate limiting should be implemented for production
- Input validation is crucial for wallet addresses

## 📝 API Documentation

### POST `/api/score`
Analyze a wallet address and return trust score.

**Request:**
```json
{
  "address": "0x742d35Cc6634C0532925a3b8D0B4E0c0c0c0c0c0"
}
```

**Response:**
```json
{
  "address": "0x742d35Cc6634C0532925a3b8D0B4E0c0c0c0c0c0",
  "trust_score": 75,
  "risk_tags": ["ENS Verified", "High Activity"],
  "explanation": "Wallet shows high trustworthiness...",
  "wallet_age_days": 450,
  "transaction_count": 1250,
  "contract_interactions": 45
}
```

## 🏆 Built for HyperHack

This project demonstrates:
- **Full-stack development** with modern technologies
- **AI integration** for intelligent analysis
- **On-chain data processing** for real-world utility
- **Clean architecture** with separation of concerns
- **Production-ready** deployment configuration

## 📞 Support

For questions or issues, please check the console logs and ensure both frontend and backend servers are running correctly.

---

**TrustLens.AI** - Making on-chain trust transparent and accessible 🚀
