#!/usr/bin/env python3
"""
Advanced AI-powered features for TrustLens.AI
- Explainable Risk Factors (XAI)
- Simulated Transaction Risk Checker
- Behavioral Clustering
- Gemini AI Integration
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import google.generativeai as genai
from scoring import WalletMetrics

logger = logging.getLogger(__name__)

@dataclass
class ExplainableRiskFactor:
    """Enhanced risk factor with detailed explanation"""
    factor_type: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    title: str
    explanation: str
    evidence: Dict[str, Any]
    recommendation: str
    impact_score: int  # 0-100

@dataclass
class BehavioralCluster:
    """Behavioral clustering result"""
    cluster_type: str
    similarity_score: float
    description: str
    typical_behaviors: List[str]
    risk_indicators: List[str]

@dataclass
class TransactionRiskAssessment:
    """Simulated transaction risk assessment"""
    risk_score: int  # 0-100
    risk_level: str
    warnings: List[str]
    recommendations: List[str]
    estimated_loss_probability: float

class ExplainableAI:
    """Explainable AI for risk factor analysis"""
    
    def __init__(self):
        self.risk_patterns = {
            'high_volume_new_wallet': {
                'threshold': {'age_days': 30, 'volume_eth': 100},
                'severity': 'high',
                'explanation': 'New wallets handling large volumes often indicate money laundering or exchange testing'
            },
            'wash_trading_pattern': {
                'threshold': {'self_tx_ratio': 0.3, 'unique_counterparties': 5},
                'severity': 'critical',
                'explanation': 'High ratio of self-transactions suggests artificial volume inflation'
            },
            'mixer_interaction': {
                'threshold': {'mixer_tx_count': 1},
                'severity': 'high',
                'explanation': 'Interactions with known mixers indicate privacy-seeking or money laundering'
            },
            'flash_loan_abuse': {
                'threshold': {'flash_loan_count': 3, 'failed_tx_ratio': 0.2},
                'severity': 'medium',
                'explanation': 'Multiple flash loans with failures suggest MEV exploitation attempts'
            },
            'dormant_reactivation': {
                'threshold': {'dormant_days': 365, 'sudden_activity': 10},
                'severity': 'medium',
                'explanation': 'Long-dormant wallets suddenly becoming active often indicate compromised accounts'
            }
        }
    
    async def analyze_explainable_risks(self, metrics: WalletMetrics) -> List[ExplainableRiskFactor]:
        """Generate explainable risk factors with detailed analysis"""
        risk_factors = []
        
        # Analyze high volume new wallet pattern
        if metrics.wallet_age < 30 and (metrics.incoming_volume + metrics.outgoing_volume) > 100:
            risk_factors.append(ExplainableRiskFactor(
                factor_type="high_volume_new_wallet",
                severity="high",
                confidence=0.85,
                title="High Volume Activity in New Wallet",
                explanation=f"This wallet is only {metrics.wallet_age} days old but has processed {metrics.incoming_volume + metrics.outgoing_volume:.2f} ETH. New wallets handling large volumes often indicate: (1) Money laundering operations, (2) Exchange hot wallet testing, (3) Institutional setup, or (4) Compromised account activity.",
                evidence={
                    "wallet_age_days": metrics.wallet_age,
                    "total_volume_eth": metrics.incoming_volume + metrics.outgoing_volume,
                    "daily_volume_avg": (metrics.incoming_volume + metrics.outgoing_volume) / max(metrics.wallet_age, 1)
                },
                recommendation="Exercise extreme caution. Verify the wallet owner's identity and transaction purposes before engaging.",
                impact_score=85
            ))
        
        # Analyze wash trading patterns
        if metrics.unique_counterparties < 5 and metrics.total_transactions > 20:
            self_dealing_ratio = 1 - (metrics.unique_counterparties / max(metrics.total_transactions, 1))
            if self_dealing_ratio > 0.7:
                risk_factors.append(ExplainableRiskFactor(
                    factor_type="wash_trading_pattern",
                    severity="critical",
                    confidence=0.92,
                    title="Suspected Wash Trading Activity",
                    explanation=f"This wallet shows {self_dealing_ratio*100:.1f}% self-dealing ratio with only {metrics.unique_counterparties} unique counterparties across {metrics.total_transactions} transactions. This pattern strongly suggests: (1) Artificial volume inflation, (2) Market manipulation, (3) Tax evasion schemes, or (4) NFT wash trading.",
                    evidence={
                        "self_dealing_ratio": self_dealing_ratio,
                        "unique_counterparties": metrics.unique_counterparties,
                        "total_transactions": metrics.total_transactions,
                        "counterparty_diversity_score": metrics.unique_counterparties / max(metrics.total_transactions, 1)
                    },
                    recommendation="AVOID: This wallet exhibits clear wash trading patterns. Do not engage in transactions.",
                    impact_score=95
                ))
        
        # Analyze net outflow patterns
        if metrics.outgoing_volume > 0 and abs(metrics.net_flow / metrics.outgoing_volume) > 0.8:
            outflow_ratio = abs(metrics.net_flow / metrics.outgoing_volume)
            risk_factors.append(ExplainableRiskFactor(
                factor_type="significant_net_outflow",
                severity="medium",
                confidence=0.75,
                title="Significant Net Fund Outflow",
                explanation=f"This wallet shows {outflow_ratio*100:.1f}% net outflow ratio, indicating more funds leaving than entering. This could suggest: (1) Liquidation of positions, (2) Fund withdrawal to cold storage, (3) Potential exit scam preparation, or (4) Normal business operations.",
                evidence={
                    "net_flow_eth": metrics.net_flow,
                    "outgoing_volume_eth": metrics.outgoing_volume,
                    "incoming_volume_eth": metrics.incoming_volume,
                    "outflow_ratio": outflow_ratio
                },
                recommendation="Monitor closely. Large outflows may indicate preparation for exit or legitimate business operations.",
                impact_score=60
            ))
        
        # Analyze contract interaction patterns
        if metrics.total_transactions > 50:
            contract_ratio = metrics.contract_interactions / metrics.total_transactions
            if contract_ratio > 0.8:
                risk_factors.append(ExplainableRiskFactor(
                    factor_type="high_contract_interaction",
                    severity="low",
                    confidence=0.65,
                    title="High Smart Contract Interaction",
                    explanation=f"This wallet has {contract_ratio*100:.1f}% smart contract interactions, indicating: (1) DeFi power user behavior, (2) Automated trading bot, (3) MEV searcher activity, or (4) Protocol interaction specialist. Generally positive for legitimacy.",
                    evidence={
                        "contract_interaction_ratio": contract_ratio,
                        "contract_interactions": metrics.contract_interactions,
                        "total_transactions": metrics.total_transactions
                    },
                    recommendation="Positive indicator. High contract interaction suggests legitimate DeFi usage.",
                    impact_score=25
                ))
        
        # Analyze transaction failure patterns
        if metrics.total_transactions > 10 and metrics.failed_transactions > 0:
            failure_rate = metrics.failed_transactions / metrics.total_transactions
            if failure_rate > 0.15:
                risk_factors.append(ExplainableRiskFactor(
                    factor_type="high_failure_rate",
                    severity="medium",
                    confidence=0.70,
                    title="High Transaction Failure Rate",
                    explanation=f"This wallet has {failure_rate*100:.1f}% transaction failure rate ({metrics.failed_transactions}/{metrics.total_transactions}). High failure rates may indicate: (1) MEV bot activity, (2) Front-running attempts, (3) Poor transaction management, or (4) Interaction with buggy contracts.",
                    evidence={
                        "failure_rate": failure_rate,
                        "failed_transactions": metrics.failed_transactions,
                        "total_transactions": metrics.total_transactions
                    },
                    recommendation="Moderate risk. High failure rates suggest either sophisticated trading or poor execution.",
                    impact_score=45
                ))
        
        return sorted(risk_factors, key=lambda x: x.impact_score, reverse=True)

class BehavioralClustering:
    """Behavioral clustering analysis"""
    
    def __init__(self):
        self.cluster_profiles = {
            'whale': {
                'balance_min': 100,
                'tx_count_min': 50,
                'avg_tx_value_min': 10,
                'description': 'Large holder with significant transaction values',
                'behaviors': ['Large balance holdings', 'High-value transactions', 'Infrequent but significant moves'],
                'risk_indicators': ['Market manipulation potential', 'Price impact on trades']
            },
            'defi_power_user': {
                'contract_ratio_min': 0.6,
                'unique_counterparties_min': 20,
                'description': 'Active DeFi protocol user',
                'behaviors': ['High contract interaction', 'Multiple protocol usage', 'Yield farming activities'],
                'risk_indicators': ['Smart contract risks', 'Impermanent loss exposure']
            },
            'trader': {
                'tx_frequency_min': 1.0,
                'unique_counterparties_min': 10,
                'description': 'Active trader with frequent transactions',
                'behaviors': ['High transaction frequency', 'Multiple counterparties', 'Regular trading patterns'],
                'risk_indicators': ['Market timing risks', 'Slippage exposure']
            },
            'mixer_user': {
                'privacy_score_min': 0.7,
                'description': 'Privacy-focused user with potential mixer usage',
                'behaviors': ['Privacy-seeking transactions', 'Complex transaction paths', 'Obfuscated fund flows'],
                'risk_indicators': ['AML compliance issues', 'Regulatory scrutiny']
            },
            'new_user': {
                'age_max': 30,
                'tx_count_max': 20,
                'description': 'New wallet with limited activity',
                'behaviors': ['Recent wallet creation', 'Limited transaction history', 'Learning curve activities'],
                'risk_indicators': ['Inexperience risks', 'Potential for mistakes']
            },
            'dormant': {
                'last_activity_min': 90,
                'description': 'Inactive wallet with old transactions',
                'behaviors': ['Long periods of inactivity', 'Sporadic usage', 'Potential abandonment'],
                'risk_indicators': ['Account compromise risk', 'Lost key potential']
            }
        }
    
    async def classify_behavior(self, metrics: WalletMetrics) -> List[BehavioralCluster]:
        """Classify wallet behavior into known patterns"""
        clusters = []
        
        # Calculate derived metrics
        tx_frequency = metrics.activity_frequency if metrics.wallet_age > 0 else 0
        contract_ratio = metrics.contract_interactions / max(metrics.total_transactions, 1)
        avg_tx_value = metrics.average_transaction_value
        
        # Check whale pattern
        if (metrics.current_balance >= 100 and 
            metrics.total_transactions >= 50 and 
            avg_tx_value >= 10):
            clusters.append(BehavioralCluster(
                cluster_type="whale",
                similarity_score=0.85,
                description="Large holder with significant transaction values and market influence",
                typical_behaviors=self.cluster_profiles['whale']['behaviors'],
                risk_indicators=self.cluster_profiles['whale']['risk_indicators']
            ))
        
        # Check DeFi power user pattern
        if (contract_ratio >= 0.6 and 
            metrics.unique_counterparties >= 20):
            clusters.append(BehavioralCluster(
                cluster_type="defi_power_user",
                similarity_score=0.90,
                description="Active DeFi protocol user with sophisticated on-chain behavior",
                typical_behaviors=self.cluster_profiles['defi_power_user']['behaviors'],
                risk_indicators=self.cluster_profiles['defi_power_user']['risk_indicators']
            ))
        
        # Check trader pattern
        if (tx_frequency >= 1.0 and 
            metrics.unique_counterparties >= 10 and
            metrics.total_transactions >= 100):
            clusters.append(BehavioralCluster(
                cluster_type="trader",
                similarity_score=0.80,
                description="Active trader with frequent transactions and multiple counterparties",
                typical_behaviors=self.cluster_profiles['trader']['behaviors'],
                risk_indicators=self.cluster_profiles['trader']['risk_indicators']
            ))
        
        # Check new user pattern
        if (metrics.wallet_age <= 30 and 
            metrics.total_transactions <= 20):
            clusters.append(BehavioralCluster(
                cluster_type="new_user",
                similarity_score=0.95,
                description="New wallet with limited activity and transaction history",
                typical_behaviors=self.cluster_profiles['new_user']['behaviors'],
                risk_indicators=self.cluster_profiles['new_user']['risk_indicators']
            ))
        
        # Check dormant pattern
        if metrics.last_activity_days >= 90:
            clusters.append(BehavioralCluster(
                cluster_type="dormant",
                similarity_score=0.88,
                description="Inactive wallet with potential abandonment or compromise risk",
                typical_behaviors=self.cluster_profiles['dormant']['behaviors'],
                risk_indicators=self.cluster_profiles['dormant']['risk_indicators']
            ))
        
        return clusters

class TransactionSimulator:
    """Simulated transaction risk assessment"""
    
    async def assess_transaction_risk(
        self, 
        from_wallet: WalletMetrics, 
        to_address: str, 
        amount_eth: float,
        transaction_type: str = "transfer"
    ) -> TransactionRiskAssessment:
        """Assess risk of a simulated transaction"""
        
        warnings = []
        recommendations = []
        risk_score = 0
        
        # Analyze sender wallet risks
        if from_wallet.wallet_age < 7:
            risk_score += 30
            warnings.append("Sender wallet is very new (< 7 days)")
            recommendations.append("Verify sender identity before proceeding")
        
        # Analyze transaction amount relative to wallet balance
        if amount_eth > from_wallet.current_balance * 0.8:
            risk_score += 25
            warnings.append("Transaction amount is >80% of wallet balance")
            recommendations.append("Consider smaller transaction amounts")
        
        # Analyze transaction amount relative to historical patterns
        if amount_eth > from_wallet.average_transaction_value * 10:
            risk_score += 20
            warnings.append("Transaction amount is 10x larger than average")
            recommendations.append("Unusual transaction size - verify legitimacy")
        
        # Check for potential mixer/privacy coin interaction
        if self._is_potential_mixer(to_address):
            risk_score += 40
            warnings.append("Recipient address shows mixer-like characteristics")
            recommendations.append("HIGH RISK: Potential AML compliance issues")
        
        # Analyze gas efficiency
        if from_wallet.gas_efficiency_score < 30:
            risk_score += 15
            warnings.append("Sender has poor gas efficiency history")
            recommendations.append("Monitor gas prices and set appropriate limits")
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 60:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        elif risk_score >= 20:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        # Calculate estimated loss probability
        loss_probability = min(risk_score / 100.0, 0.95)
        
        return TransactionRiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            warnings=warnings,
            recommendations=recommendations,
            estimated_loss_probability=loss_probability
        )
    
    def _is_potential_mixer(self, address: str) -> bool:
        """Simple heuristic to detect potential mixer addresses"""
        # This is a simplified check - in production, you'd use a database of known mixers
        mixer_patterns = [
            "tornado", "mixer", "tumbler", "privacy", "anon"
        ]
        address_lower = address.lower()
        return any(pattern in address_lower for pattern in mixer_patterns)

class GeminiAIIntegration:
    """Gemini AI integration for enhanced chat capabilities"""
    
    def __init__(self, api_key: str):
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            logger.warning("No Gemini API key provided")
    
    async def enhance_analysis_explanation(self, wallet_analysis: Dict[str, Any]) -> str:
        """Use Gemini AI to provide enhanced explanations"""
        if not self.model:
            return "AI enhancement unavailable - no API key configured"
        
        try:
            prompt = f"""
            As a blockchain security expert, provide a comprehensive analysis of this Ethereum wallet:
            
            Trust Score: {wallet_analysis.get('trust_score', 'N/A')}/100
            Risk Level: {wallet_analysis.get('risk_level', 'N/A')}
            
            Wallet Metrics:
            - Balance: {wallet_analysis.get('raw_metrics', {}).get('current_balance', 'N/A')} ETH
            - Age: {wallet_analysis.get('raw_metrics', {}).get('wallet_age', 'N/A')} days
            - Transactions: {wallet_analysis.get('raw_metrics', {}).get('total_transactions', 'N/A')}
            - Unique Counterparties: {wallet_analysis.get('raw_metrics', {}).get('unique_counterparties', 'N/A')}
            
            Risk Factors: {wallet_analysis.get('risk_factors', [])}
            
            Please provide:
            1. A brief security assessment
            2. Key insights about the wallet's behavior
            3. Specific recommendations for interacting with this wallet
            4. Any red flags or positive indicators
            
            Keep the response concise but informative (max 200 words).
            """
            
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini AI error: {str(e)}")
            return f"AI analysis unavailable: {str(e)}"
    
    async def answer_followup_question(self, question: str, wallet_context: Dict[str, Any]) -> str:
        """Answer follow-up questions about wallet analysis"""
        if not self.model:
            return "AI chat unavailable - no API key configured"
        
        try:
            prompt = f"""
            You are a blockchain security expert. A user is asking about an Ethereum wallet analysis.
            
            Wallet Context:
            {json.dumps(wallet_context, indent=2)}
            
            User Question: {question}
            
            Provide a helpful, accurate response based on the wallet data. If the question is outside 
            the scope of wallet analysis, politely redirect to wallet-related topics.
            
            Keep responses concise and actionable (max 150 words).
            """
            
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini AI error: {str(e)}")
            return f"Sorry, I couldn't process your question: {str(e)}"

# Factory function to create AI features
async def create_ai_features(gemini_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Create and return all AI feature instances"""
    return {
        'explainable_ai': ExplainableAI(),
        'behavioral_clustering': BehavioralClustering(),
        'transaction_simulator': TransactionSimulator(),
        'gemini_ai': GeminiAIIntegration(gemini_api_key) if gemini_api_key else None
    }