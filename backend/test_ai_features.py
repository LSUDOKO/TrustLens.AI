#!/usr/bin/env python3
"""
Test script for AI-powered features
"""
import asyncio
import os
from dotenv import load_dotenv
from scoring import analyze_wallet

async def test_ai_features():
    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    
    print("🧠 Testing AI-Powered Features")
    print("=" * 50)
    
    try:
        # Test enhanced wallet analysis with AI features
        result = await analyze_wallet(test_address, api_key, include_ai_features=True)
        
        print(f"📊 Trust Score: {result.get('trust_score', 'N/A')}/100")
        print(f"🎯 Risk Level: {result.get('risk_level', 'N/A')}")
        print()
        
        # Test explainable risk factors
        explainable_risks = result.get('explainable_risks', [])
        if explainable_risks:
            print("🔍 EXPLAINABLE RISK FACTORS:")
            for i, risk in enumerate(explainable_risks[:3], 1):
                print(f"   {i}. {risk['title']} ({risk['severity'].upper()})")
                print(f"      Confidence: {risk['confidence']*100:.0f}%")
                print(f"      Impact: {risk['impact_score']}/100")
                print(f"      Explanation: {risk['explanation'][:100]}...")
                print(f"      Recommendation: {risk['recommendation'][:80]}...")
                print()
        
        # Test behavioral clustering
        behavioral_clusters = result.get('behavioral_clusters', [])
        if behavioral_clusters:
            print("🧠 BEHAVIORAL CLUSTERING:")
            for cluster in behavioral_clusters:
                print(f"   🎯 {cluster['cluster_type'].replace('_', ' ').title()}")
                print(f"      Similarity: {cluster['similarity_score']*100:.0f}%")
                print(f"      Description: {cluster['description']}")
                print(f"      Behaviors: {', '.join(cluster['typical_behaviors'][:3])}")
                print()
        
        # Test transaction simulation
        print("🔮 TRANSACTION SIMULATION TEST:")
        from ai_features import TransactionSimulator
        from scoring import WalletMetrics
        
        # Create metrics object from result
        raw_metrics = result.get('raw_metrics', {})
        metrics = WalletMetrics(
            address=test_address,
            current_balance=raw_metrics.get('current_balance', 0),
            total_transactions=raw_metrics.get('total_transactions', 0),
            wallet_age=raw_metrics.get('wallet_age', 0),
            average_transaction_value=raw_metrics.get('average_transaction_value', 0),
            max_transaction_value=raw_metrics.get('max_transaction_value', 0),
            unique_counterparties=raw_metrics.get('unique_counterparties', 0),
            gas_efficiency_score=raw_metrics.get('gas_efficiency_score', 50),
            activity_frequency=raw_metrics.get('activity_frequency', 0),
            last_activity_days=raw_metrics.get('last_activity_days', 999),
            incoming_volume=raw_metrics.get('incoming_volume', 0),
            outgoing_volume=raw_metrics.get('outgoing_volume', 0),
            net_flow=raw_metrics.get('net_flow', 0),
            contract_interactions=raw_metrics.get('contract_interactions', 0),
            failed_transactions=raw_metrics.get('failed_transactions', 0),
            data_source=raw_metrics.get('data_source', 'unknown')
        )
        
        simulator = TransactionSimulator()
        
        # Test different transaction scenarios
        scenarios = [
            ("Normal transaction", "0x1234567890123456789012345678901234567890", 1.0),
            ("Large transaction", "0x1234567890123456789012345678901234567890", 10.0),
            ("Potential mixer", "0xTornadoCash1234567890123456789012345678", 0.5)
        ]
        
        for scenario_name, to_address, amount in scenarios:
            risk_assessment = await simulator.assess_transaction_risk(
                metrics, to_address, amount
            )
            
            print(f"   📋 {scenario_name}:")
            print(f"      Risk Score: {risk_assessment.risk_score}/100 ({risk_assessment.risk_level})")
            print(f"      Loss Probability: {risk_assessment.estimated_loss_probability*100:.1f}%")
            if risk_assessment.warnings:
                print(f"      Warnings: {', '.join(risk_assessment.warnings[:2])}")
            print()
        
        print("✅ All AI features tested successfully!")
        
    except Exception as e:
        print(f"❌ Error testing AI features: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_features())