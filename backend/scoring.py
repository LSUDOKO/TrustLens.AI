#!/usr/bin/env python3
"""
Enhanced scoring system with real blockchain API integration
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from blockchain_api import EtherscanAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WalletMetrics:
    """Data class to hold wallet metrics"""
    address: str
    current_balance: float
    total_transactions: int
    wallet_age: int  # in days
    average_transaction_value: float
    max_transaction_value: float
    unique_counterparties: int
    gas_efficiency_score: float
    activity_frequency: float  # transactions per day
    last_activity_days: int
    incoming_volume: float
    outgoing_volume: float
    net_flow: float
    contract_interactions: int
    failed_transactions: int
    data_source: str  # 'real' or 'simulated'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'address': self.address,
            'current_balance': self.current_balance,
            'total_transactions': self.total_transactions,
            'wallet_age': self.wallet_age,
            'average_transaction_value': self.average_transaction_value,
            'max_transaction_value': self.max_transaction_value,
            'unique_counterparties': self.unique_counterparties,
            'gas_efficiency_score': self.gas_efficiency_score,
            'activity_frequency': self.activity_frequency,
            'last_activity_days': self.last_activity_days,
            'incoming_volume': self.incoming_volume,
            'outgoing_volume': self.outgoing_volume,
            'net_flow': self.net_flow,
            'contract_interactions': self.contract_interactions,
            'failed_transactions': self.failed_transactions,
            'data_source': self.data_source
        }

class WalletDataAggregator:
    """Aggregates wallet data from various blockchain sources"""
    
    def __init__(self, etherscan_api: EtherscanAPI):
        self.etherscan = etherscan_api
        
    async def aggregate_wallet_data(self, address: str) -> WalletMetrics:
        """
        Aggregate comprehensive wallet data from blockchain APIs
        """
        try:
            logger.info(f"Aggregating data for wallet: {address}")
            
            # Fetch basic account info
            balance = await self.etherscan.get_account_balance(address)
            transactions = await self.etherscan.get_transaction_list(address, limit=1000)
            
            logger.info(f"Fetched {len(transactions)} transactions for {address}")
            
            if not transactions:
                # Return minimal metrics for empty wallet
                logger.info(f"No transactions found for {address}, returning minimal metrics")
                return WalletMetrics(
                    address=address,
                    current_balance=balance,
                    total_transactions=0,
                    wallet_age=0,
                    average_transaction_value=0.0,
                    max_transaction_value=0.0,
                    unique_counterparties=0,
                    gas_efficiency_score=0.0,
                    activity_frequency=0.0,
                    last_activity_days=999999,
                    incoming_volume=0.0,
                    outgoing_volume=0.0,
                    net_flow=0.0,
                    contract_interactions=0,
                    failed_transactions=0,
                    data_source='real'
                )
            
            # Calculate metrics
            now = datetime.now(timezone.utc)
            
            # Transaction values and volumes
            transaction_values = []
            incoming_volume = 0.0
            outgoing_volume = 0.0
            counterparties = set()
            contract_interactions = 0
            failed_transactions = 0
            
            # Gas metrics
            total_gas_used = 0
            total_gas_price = 0
            gas_transactions = 0
            
            # Timestamps for age and activity calculation
            timestamps = []
            
            for tx in transactions:
                # Add timestamp first
                timestamps.append(tx.timestamp)
                
                # Transaction value (only count non-zero values)
                if tx.value > 0:
                    transaction_values.append(tx.value)
                
                # Volume calculation (incoming vs outgoing)
                if tx.to_address.lower() == address.lower():
                    # Incoming transaction
                    incoming_volume += tx.value
                    # Add sender as counterparty
                    if tx.from_address.lower() != address.lower():
                        counterparties.add(tx.from_address.lower())
                else:
                    # Outgoing transaction
                    outgoing_volume += tx.value
                    # Add recipient as counterparty
                    if tx.to_address.lower() != address.lower():
                        counterparties.add(tx.to_address.lower())
                
                # Contract interactions (transactions with contract addresses)
                if tx.input_data and tx.input_data != '0x' and len(tx.input_data) > 2:
                    contract_interactions += 1
                
                # Failed transactions
                if hasattr(tx, 'is_error') and tx.is_error:
                    failed_transactions += 1
                
                # Gas efficiency
                if tx.gas_used > 0 and tx.gas_price > 0:
                    total_gas_used += tx.gas_used
                    total_gas_price += tx.gas_price
                    gas_transactions += 1
            
            # Calculate derived metrics
            total_transactions = len(transactions)
            
            # Wallet age (days since first transaction)
            if timestamps:
                oldest_timestamp = min(timestamps)
                newest_timestamp = max(timestamps)
                wallet_age = (now - oldest_timestamp).days
                last_activity_days = (now - newest_timestamp).days
            else:
                wallet_age = 0
                last_activity_days = 999999
            
            # Average and max transaction values
            if transaction_values:
                average_transaction_value = sum(transaction_values) / len(transaction_values)
                max_transaction_value = max(transaction_values)
            else:
                average_transaction_value = 0.0
                max_transaction_value = 0.0
            
            # Activity frequency (transactions per day)
            if wallet_age > 0:
                activity_frequency = total_transactions / wallet_age
            else:
                activity_frequency = 0.0
            
            # Gas efficiency score (lower is better, normalized to 0-100)
            if gas_transactions > 0:
                avg_gas_price = total_gas_price / gas_transactions
                # Normalize based on typical gas prices (this is simplified)
                gas_efficiency_score = max(0, min(100, 100 - (avg_gas_price / 1e9 - 20) * 2))
            else:
                gas_efficiency_score = 50.0  # neutral score
            
            # Net flow
            net_flow = incoming_volume - outgoing_volume
            
            return WalletMetrics(
                address=address,
                current_balance=balance,
                total_transactions=total_transactions,
                wallet_age=wallet_age,
                average_transaction_value=average_transaction_value,
                max_transaction_value=max_transaction_value,
                unique_counterparties=len(counterparties),
                gas_efficiency_score=gas_efficiency_score,
                activity_frequency=activity_frequency,
                last_activity_days=last_activity_days,
                incoming_volume=incoming_volume,
                outgoing_volume=outgoing_volume,
                net_flow=net_flow,
                contract_interactions=contract_interactions,
                failed_transactions=failed_transactions,
                data_source='real'
            )
            
        except Exception as e:
            logger.error(f"Error aggregating wallet data: {str(e)}")
            # Return simulated data as fallback
            logger.warning(f"Falling back to simulated data for {address} due to error: {str(e)}")
            return await self._generate_simulated_metrics(address)
    
    async def _generate_simulated_metrics(self, address: str) -> WalletMetrics:
        """Generate simulated metrics for testing when API fails"""
        import random
        
        logger.warning(f"Generating simulated data for {address}")
        
        return WalletMetrics(
            address=address,
            current_balance=random.uniform(0.1, 50.0),
            total_transactions=random.randint(10, 1000),
            wallet_age=random.randint(30, 1000),
            average_transaction_value=random.uniform(0.01, 5.0),
            max_transaction_value=random.uniform(1.0, 100.0),
            unique_counterparties=random.randint(5, 100),
            gas_efficiency_score=random.uniform(30, 95),
            activity_frequency=random.uniform(0.1, 5.0),
            last_activity_days=random.randint(1, 30),
            incoming_volume=random.uniform(10.0, 500.0),
            outgoing_volume=random.uniform(5.0, 450.0),
            net_flow=random.uniform(-50.0, 100.0),
            contract_interactions=random.randint(0, 50),
            failed_transactions=random.randint(0, 10),
            data_source='simulated'
        )

class TrustScoreCalculator:
    """Calculate trust scores based on wallet metrics"""
    
    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'balance': 0.15,
            'activity': 0.20,
            'age': 0.15,
            'transaction_patterns': 0.20,
            'network_behavior': 0.15,
            'risk_factors': 0.15
        }
    
    def calculate_trust_score(self, metrics: WalletMetrics) -> Dict[str, Any]:
        """Calculate comprehensive trust score"""
        
        # Component scores (0-100)
        balance_score = self._score_balance(metrics)
        activity_score = self._score_activity(metrics)
        age_score = self._score_age(metrics)
        transaction_score = self._score_transactions(metrics)
        network_score = self._score_network_behavior(metrics)
        risk_score = self._score_risk_factors(metrics)
        
        # Weighted total score
        total_score = (
            balance_score * self.weights['balance'] +
            activity_score * self.weights['activity'] +
            age_score * self.weights['age'] +
            transaction_score * self.weights['transaction_patterns'] +
            network_score * self.weights['network_behavior'] +
            risk_score * self.weights['risk_factors']
        )
        
        # Determine risk level
        if total_score >= 80:
            risk_level = 'very_low'
        elif total_score >= 60:
            risk_level = 'low'
        elif total_score >= 40:
            risk_level = 'medium'
        elif total_score >= 20:
            risk_level = 'high'
        else:
            risk_level = 'very_high'
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(metrics)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(metrics)
        
        return {
            'trust_score': round(total_score),
            'risk_level': risk_level,
            'confidence': confidence,
            'component_scores': {
                'balance': round(balance_score),
                'activity': round(activity_score),
                'age': round(age_score),
                'transactions': round(transaction_score),
                'network': round(network_score),
                'risk': round(risk_score)
            },
            'risk_factors': risk_factors,
            'raw_metrics': metrics.to_dict()
        }
    
    def _score_balance(self, metrics: WalletMetrics) -> float:
        """Score based on current balance (0-100)"""
        balance = metrics.current_balance
        
        if balance >= 100.0:
            return 100.0
        elif balance >= 10.0:
            return 80.0 + (min(balance, 100) - 10.0) * 0.22  # Linear scale from 80-100
        elif balance >= 1.0:
            return 60.0 + (balance - 1.0) * 2.22  # Linear scale from 60-80
        elif balance >= 0.1:
            return 30.0 + (balance - 0.1) * 33.33  # Linear scale from 30-60
        elif balance >= 0.01:
            return 10.0 + (balance - 0.01) * 222.22  # Linear scale from 10-30
        elif balance > 0:
            return balance * 1000  # Linear scale from 0-10
        else:
            return 0.0
    
    def _score_activity(self, metrics: WalletMetrics) -> float:
        """Score based on activity patterns (0-100)"""
        if metrics.total_transactions == 0:
            return 0.0
        
        # Transaction count component (more transactions = higher score)
        if metrics.total_transactions >= 1000:
            tx_score = 100.0
        elif metrics.total_transactions >= 100:
            tx_score = 70.0 + (metrics.total_transactions - 100) * 0.033  # 70-100
        elif metrics.total_transactions >= 10:
            tx_score = 40.0 + (metrics.total_transactions - 10) * 0.33  # 40-70
        else:
            tx_score = metrics.total_transactions * 4.0  # 0-40
        
        # Recent activity component
        if metrics.last_activity_days <= 1:
            recency_score = 100.0
        elif metrics.last_activity_days <= 7:
            recency_score = 90.0
        elif metrics.last_activity_days <= 30:
            recency_score = 70.0
        elif metrics.last_activity_days <= 90:
            recency_score = 50.0
        elif metrics.last_activity_days <= 365:
            recency_score = 30.0
        else:
            recency_score = 10.0
        
        return (tx_score + recency_score) / 2
    
    def _score_age(self, metrics: WalletMetrics) -> float:
        """Score based on wallet age (0-100)"""
        age = metrics.wallet_age
        
        if age >= 1095:  # 3+ years
            return 100.0
        elif age >= 730:  # 2+ years
            return 90.0 + (age - 730) * 10 / 365
        elif age >= 365:  # 1+ years
            return 75.0 + (age - 365) * 15 / 365
        elif age >= 180:  # 6+ months
            return 55.0 + (age - 180) * 20 / 185
        elif age >= 90:   # 3+ months
            return 35.0 + (age - 90) * 20 / 90
        elif age >= 30:   # 1+ months
            return 15.0 + (age - 30) * 20 / 60
        elif age > 0:
            return age * 0.5  # Linear scale from 0-15
        else:
            return 0.0
    
    def _score_transactions(self, metrics: WalletMetrics) -> float:
        """Score based on transaction patterns (0-100)"""
        if metrics.total_transactions == 0:
            return 0.0
        
        # Transaction volume score (more reasonable scaling)
        if metrics.total_transactions >= 1000:
            volume_score = 100.0
        elif metrics.total_transactions >= 100:
            volume_score = 80.0 + (metrics.total_transactions - 100) * 0.022  # 80-100
        elif metrics.total_transactions >= 50:
            volume_score = 60.0 + (metrics.total_transactions - 50) * 0.4  # 60-80
        elif metrics.total_transactions >= 10:
            volume_score = 30.0 + (metrics.total_transactions - 10) * 0.75  # 30-60
        else:
            volume_score = metrics.total_transactions * 3.0  # 0-30
        
        # Value diversity score (reasonable transaction values)
        if metrics.average_transaction_value > 0 and metrics.max_transaction_value > 0:
            value_ratio = metrics.max_transaction_value / metrics.average_transaction_value
            if value_ratio <= 10:  # Normal diversity
                diversity_score = 100.0
            elif value_ratio <= 100:  # Moderate diversity
                diversity_score = 80.0
            elif value_ratio <= 1000:  # High diversity
                diversity_score = 60.0
            else:  # Very high diversity (potentially suspicious)
                diversity_score = 40.0
        else:
            diversity_score = 70.0  # Default for no value transactions
        
        # Failed transaction penalty (more lenient)
        if metrics.total_transactions > 0:
            failure_rate = metrics.failed_transactions / metrics.total_transactions
            if failure_rate <= 0.05:  # Less than 5% failure rate
                failure_penalty = 0
            elif failure_rate <= 0.1:  # 5-10% failure rate
                failure_penalty = 10
            elif failure_rate <= 0.2:  # 10-20% failure rate
                failure_penalty = 25
            else:  # More than 20% failure rate
                failure_penalty = 40
        else:
            failure_penalty = 0
        
        return max(0, (volume_score + diversity_score) / 2 - failure_penalty)
    
    def _score_network_behavior(self, metrics: WalletMetrics) -> float:
        """Score based on network interaction patterns (0-100)"""
        if metrics.total_transactions == 0:
            return 0.0
        
        # Counterparty diversity (more realistic scaling)
        if metrics.unique_counterparties >= 100:
            counterparty_score = 100.0
        elif metrics.unique_counterparties >= 50:
            counterparty_score = 85.0 + (metrics.unique_counterparties - 50) * 0.3
        elif metrics.unique_counterparties >= 20:
            counterparty_score = 65.0 + (metrics.unique_counterparties - 20) * 0.67
        elif metrics.unique_counterparties >= 5:
            counterparty_score = 35.0 + (metrics.unique_counterparties - 5) * 2.0
        else:
            counterparty_score = metrics.unique_counterparties * 7.0  # 0-35
        
        # Contract interaction score (indicates DeFi/dApp usage)
        if metrics.total_transactions > 0:
            contract_ratio = metrics.contract_interactions / metrics.total_transactions
            if contract_ratio >= 0.5:  # 50%+ contract interactions
                contract_score = 100.0
            elif contract_ratio >= 0.3:  # 30-50%
                contract_score = 80.0 + (contract_ratio - 0.3) * 100
            elif contract_ratio >= 0.1:  # 10-30%
                contract_score = 50.0 + (contract_ratio - 0.1) * 150
            else:  # Less than 10%
                contract_score = contract_ratio * 500  # 0-50
        else:
            contract_score = 0.0
        
        # Gas efficiency score (use existing score)
        gas_score = metrics.gas_efficiency_score
        
        return (counterparty_score + contract_score + gas_score) / 3
        
    def _score_risk_factors(self, metrics: WalletMetrics) -> float:
        """Score based on identified risk factors (0-100, where 100 is low risk)"""
        risk_penalty = 0
        
        # High net outflow
        if metrics.outgoing_volume > 0 and (metrics.net_flow / metrics.outgoing_volume) < -0.8:
            risk_penalty += 20
        
        # Very new wallet
        if metrics.wallet_age < 7:
            risk_penalty += 25
        
        # Low transaction count
        if metrics.total_transactions < 5:
            risk_penalty += 15
        
        # High failure rate
        if metrics.total_transactions > 0 and (metrics.failed_transactions / metrics.total_transactions) > 0.2:
            risk_penalty += 20
        
        # Low unique counterparties (potential self-dealing)
        if metrics.unique_counterparties < 3 and metrics.total_transactions > 5:
            risk_penalty += 15
            
        return max(0, 100 - risk_penalty)

    def _calculate_confidence(self, metrics: WalletMetrics) -> float:
        """Calculate confidence score based on data source and completeness"""
        if metrics.data_source == 'simulated':
            return 0.6  # Lower confidence for simulated data
        
        confidence = 0.8  # Base confidence for real data
        if metrics.total_transactions > 100:
            confidence += 0.1
        if metrics.wallet_age > 90:
            confidence += 0.1
        
        return min(1.0, round(confidence, 2))

    def _identify_risk_factors(self, metrics: WalletMetrics) -> List[str]:
        """Identify and list potential risk factors"""
        factors = []
        
        if metrics.wallet_age < 30:
            factors.append("New wallet (<30 days)")
        if metrics.last_activity_days > 90:
            factors.append("Inactive for >90 days")
        if metrics.total_transactions < 10:
            factors.append("Low transaction history (<10)")
        if metrics.unique_counterparties < 5 and metrics.total_transactions > 10:
            factors.append("Limited network interaction")
        if metrics.total_transactions > 0 and (metrics.failed_transactions / metrics.total_transactions) > 0.1:
            factors.append("High rate of failed transactions")
        if metrics.outgoing_volume > 0 and (metrics.net_flow / metrics.outgoing_volume) < -0.5:
            factors.append("Significant net outflow of funds")
        if metrics.current_balance < 0.01:
            factors.append("Very low current balance")
            
        return factors

async def analyze_wallet(address: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for wallet analysis.
    Initializes dependencies and returns the full analysis result.
    """
    if not api_key:
        logger.warning("No Etherscan API key provided. Using simulated data.")
        # In a real app, you might have a different way to handle this,
        # but for this script, we'll just generate simulated data directly.
        metrics = await WalletDataAggregator(None)._generate_simulated_metrics(address)
    else:
        async with EtherscanAPI(api_key) as etherscan:
            aggregator = WalletDataAggregator(etherscan)
            metrics = await aggregator.aggregate_wallet_data(address)

    calculator = TrustScoreCalculator()
    score_result = calculator.calculate_trust_score(metrics)
    
    return score_result

# Example usage (for direct script execution)
async def main():
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("ETHERSCAN_API_KEY")
    wallet_address = "0x73BCEb1Cd57C711feC4224D864b04132486B1Be0"  # Example: Vitalik Buterin's address
    
    if not api_key:
        print("ETHERSCAN_API_KEY not found in .env file. Running with simulated data.")
    
    result = await analyze_wallet(wallet_address, api_key)
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())