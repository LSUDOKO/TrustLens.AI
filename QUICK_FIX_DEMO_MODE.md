# 🚀 Quick Fix: Enable Demo Mode

If you want your deployed frontend to work immediately without deploying the backend, you can enable demo mode with mock data.

## 🎯 Quick Demo Mode Fix

Update the configuration in `frontend/app.html` to use demo mode:

### Step 1: Find this section in app.html:
```javascript
window.TrustLensConfig = {
    API_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:8000' 
        : 'https://your-backend-url.com',
```

### Step 2: Replace with demo mode:
```javascript
window.TrustLensConfig = {
    API_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:8000' 
        : 'DEMO_MODE', // This enables demo mode
```

### Step 3: Add demo data handling

Add this demo function after the TrustLensConfig:

```javascript
// Demo mode function
window.getDemoAnalysis = function(address) {
    return {
        address: address,
        trust_score: Math.floor(Math.random() * 40) + 60, // Random score 60-100
        risk_category: "moderate",
        explanation: `Demo analysis for ${address}. This wallet shows moderate trustworthiness with a balanced transaction history. In demo mode, this data is simulated for demonstration purposes.`,
        metadata: {
            age_days: Math.floor(Math.random() * 365) + 30,
            transaction_count: Math.floor(Math.random() * 1000) + 100,
            balance_usd: (Math.random() * 10000).toFixed(2),
            contract_interactions: Math.floor(Math.random() * 50) + 10
        },
        risk_factors: [
            { type: "demo", severity: "low", confidence: 0.8, description: "This is demo data" }
        ],
        processing_time_ms: 1250,
        cached: false,
        confidence_score: 0.85
    };
};
```

### Step 4: Update the fetch calls

Replace the API calls with demo mode checks:

```javascript
// In the analyzeWallet function, replace:
const response = await fetch(`${window.TrustLensConfig.API_URL}/api/v2/analyze`, {

// With:
let analysisData;
if (window.TrustLensConfig.API_URL === 'DEMO_MODE') {
    // Demo mode
    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
    analysisData = window.getDemoAnalysis(address);
} else {
    // Real API call
    const response = await fetch(`${window.TrustLensConfig.API_URL}/api/v2/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: address, blockchain: 'ethereum' })
    });
    analysisData = await response.json();
}
```

## 🎉 Result

Your deployed frontend will now:
- ✅ Work immediately without backend
- ✅ Show realistic demo data
- ✅ Demonstrate all features
- ✅ No more "Failed to fetch" errors

## 🔄 Switch to Real Backend Later

When you deploy your backend:
1. Replace `'DEMO_MODE'` with your actual backend URL
2. Remove the demo functions
3. Restore the original fetch calls
4. Commit and redeploy

This gives you a working demo while you set up the backend! 🚀