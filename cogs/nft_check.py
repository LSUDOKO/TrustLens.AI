import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import hashlib
from .risk_analysis.risk_orchestrator import RiskOrchestrator
from ..database.redis_manager import RedisManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file (if present)
from dotenv import load_dotenv
load_dotenv()

# Log API key presence for early debugging
logger.info(f"bitsCrunch key loaded: {bool(os.getenv('BITSCRUNCH_API_KEY'))}")
logger.info(f"OpenRouter key loaded: {bool(os.getenv('OPENROUTER_API_KEY'))}")

class RiskLevel(Enum):
    LOW = "🟢 LOW"
    MEDIUM = "🟡 MEDIUM" 
    HIGH = "🟠 HIGH"
    CRITICAL = "🔴 CRITICAL"

@dataclass
class WalletAnalysis:
    wallet: str
    risk_score: int
    risk_level: RiskLevel
    risky_nfts: List[Dict]
    transaction_count: int
    total_value: float
    suspicious_activity: List[str]
    recommendations: List[str]
    last_activity: Optional[str]
    connected_wallets: List[str]

class NFTCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis_manager = RedisManager()
        self.session = None
        self.orchestrator = None
        self.risk_color_map = {
            "LOW": discord.Color.green(),
            "MEDIUM": discord.Color.gold(),
            "HIGH": discord.Color.orange(),
            "CRITICAL": discord.Color.red(),
            "NO_DATA": discord.Color.greyple(),
        }

    async def cog_load(self):
        """Initialize aiohttp session and RiskOrchestrator when cog loads."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        )
        
        api_keys = {
            "BITSCRUNCH_API_KEY": os.getenv("BITSCRUNCH_API_KEY"),
            "CONTRACTSCAN_API_KEY": os.getenv("CONTRACTSCAN_API_KEY", "dummy_key_for_fictional_service")
        }

        if not api_keys["BITSCRUNCH_API_KEY"]:
            logger.error("CRITICAL: BITSCRUNCH_API_KEY not found in environment!")
        else:
            logger.info("bitsCrunch API key loaded.")

        await self.redis_manager.initialize()
        self.orchestrator = RiskOrchestrator(api_keys, self.session, self.redis_manager)
        logger.info("RiskOrchestrator initialized with multi-source support and Redis integration.")

    async def cog_unload(self):
        """Clean up sessions when cog unloads."""
        if self.session:
            await self.session.close()
        if self.redis_manager:
            await self.redis_manager.close()

    def _create_risk_bar(self, score: int) -> str:
        """Create visual risk score bar."""
        bar_length = 10
        filled_blocks = round(score / 100 * bar_length)
        return "█" * filled_blocks + "░" * (bar_length - filled_blocks)

    def _create_risk_report_embed(self, wallet: str, result: Dict, contract: Optional[str], social: Optional[str]) -> discord.Embed:
        """Creates a comprehensive Discord embed from the orchestrated analysis result."""
        overall_score = result.get('overall_score', 0)
        
        def get_risk_level_from_score(score):
            if score >= 75: return "CRITICAL"
            if score >= 50: return "HIGH"
            if score >= 25: return "MEDIUM"
            return "LOW"

        risk_level = get_risk_level_from_score(overall_score)
        title = f"🛡️ Multi-Source Risk Report for {wallet[:10]}..."
        embed = discord.Embed(title=title, color=self.risk_color_map.get(risk_level, discord.Color.greyple()))
        embed.add_field(name="Overall Risk Score", value=f"**{overall_score}/100** (`{risk_level}`)\n{self._create_risk_bar(overall_score)}", inline=False)

        # --- Analysis Sections ---
        analysis_types = ["wallet_analysis", "contract_analysis", "social_analysis", "graph_analysis"]
        section_titles = {
            "wallet_analysis": "💳 Wallet Analysis",
            "contract_analysis": "📄 Contract Analysis",
            "social_analysis": "📱 Social Analysis",
            "graph_analysis": "🌐 Trust Flow Analysis"
        }

        for analysis_key in analysis_types:
            if analysis_key in result and result[analysis_key]:
                res = result[analysis_key]
                if res.risk_level not in ["NO_DATA", "ERROR"]:
                    details_str = ""
                    if analysis_key == "graph_analysis":
                        influential_wallets = "\n".join([f"- `{w}`" for w in res.details.get('most_influential_wallets', [])])
                        details_str = (
                            f">>> **Influence Concentration (Top 5):** `{res.details.get('influence_concentration_top_5', 'N/A')}`\n"
                            f"- Wallets in Graph: `{res.details.get('total_wallets_in_graph', 'N/A')}`\n"
                            f"- Most Influential:\n{influential_wallets}"
                        )
                    else:
                        details_str = ' | '.join([f"{k.replace('_', ' ').title()}: `{v}`" for k, v in res.details.items()])

                    embed.add_field(
                        name=f"{section_titles[analysis_key]} (Score: {res.score})",
                        value=details_str,
                        inline=False
                    )

        # Recommendations
        if result.get('overall_recommendations'):
            recs = "\n".join([f"- {rec}" for rec in result['overall_recommendations']])
            embed.add_field(name="💡 Recommendations", value=recs, inline=False)

        embed.set_footer(text="Powered by TrustLens Multi-Source Analysis")
        return embed

    @app_commands.command(name="nftcheck", description="Analyzes a wallet, contract, and social handle for risk factors.")
    @app_commands.describe(
        wallet="The wallet address to analyze.",
        contract="(Optional) The smart contract address to analyze.",
        social="(Optional) The social media handle to analyze."
    )
    async def nftcheck(self, interaction: discord.Interaction, wallet: str, contract: Optional[str] = None, social: Optional[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=False)

        cache_key = f"nft_check:{wallet}:{contract}:{social}"
        cached_result = await self.redis_manager.get_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for wallet {wallet}. Serving from Redis.")
            embed = self._create_risk_report_embed(wallet, cached_result, contract, social)
            await interaction.followup.send(embed=embed)
            return

        try:
            result = await self.orchestrator.analyze_all(
                wallet_address=wallet,
                contract_address=contract,
                social_handle=social
            )
            await self.redis_manager.set_cache(cache_key, result, ttl_seconds=1800)
            embed = self._create_risk_report_embed(wallet, result, contract, social)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error during multi-source analysis for {wallet}: {e}", exc_info=True)
            await interaction.followup.send("An unexpected error occurred during analysis. Please check the address and try again.")

        if nft_count > 0:
            suspicious_ratio = suspicious_count / nft_count
            risk_score += int(suspicious_ratio * 40)  # Up to 40 points for suspicious NFTs
        
        # Portfolio value analysis
        portfolio_value = portfolio_data.get("total_value_usd", 0)
        if portfolio_value > 10000000:  # $10M+ could indicate institutional or high-risk activity
            risk_score += 20
        elif portfolio_value > 1000000:  # $1M+
            risk_score += 10
        
        # Ensure score is within bounds
        return min(max(risk_score, 0), 100)
    
    def _calculate_risk_score_simple(self, nft_count: int, nfts: List[Dict], collections: List[Dict]) -> int:
        """Calculate simplified risk score based on available data"""
        risk_score = 0
        
        # NFT count analysis
        if nft_count == 0:
            risk_score += 30  # No NFTs might indicate new/inactive wallet
        elif nft_count > 1000:
            risk_score += 40  # Extremely high NFT count could indicate bot activity
        elif nft_count > 500:
            risk_score += 25  # High but might be legitimate collector
        elif nft_count > 100:
            risk_score += 10  # Active collector
        else:
            risk_score += 5   # Normal activity
        
        # Collection analysis (if available)
        if nfts:
            collection_names = set()
            suspicious_indicators = 0
            
            for nft in nfts:
                if isinstance(nft, dict):
                    collection_name = nft.get("collection_name", nft.get("name", "Unknown"))
                    collection_names.add(collection_name)
                    
                    # Check for suspicious indicators in metadata
                    nft_str = str(nft).lower()
                    if any(flag in nft_str for flag in ['suspicious', 'flagged', 'reported', 'fake']):
                        suspicious_indicators += 1
            
            # Collection diversity risk
            if nft_count > 0:
                diversity_ratio = len(collection_names) / nft_count
                if diversity_ratio < 0.1:  # Very low diversity
                    risk_score += 20
                elif diversity_ratio < 0.3:  # Low diversity
                    risk_score += 10
            
            # Suspicious indicators
            if suspicious_indicators > 0:
                suspicious_ratio = suspicious_indicators / nft_count
                risk_score += int(suspicious_ratio * 30)  # Up to 30 points
        
        # Market context (if collections data available)
        if collections and isinstance(collections, list):
            # If we have market data, we can make more informed decisions
            risk_score -= 5  # Slight reduction for having market context
        
        return min(max(risk_score, 0), 100)
    
    def _get_last_activity_simple(self, nfts: List[Dict]) -> Optional[str]:
        """Get simplified last activity information"""
        if not nfts:
            return "No NFT activity found"
    async def _generate_ai_summary(self, analysis: WalletAnalysis) -> str:
        """Generate AI-powered risk assessment summary"""
        try:
            prompt = f"""
            Analyze this NFT wallet risk assessment:
            
            Wallet: {analysis.wallet}
            Risk Score: {analysis.risk_score}/100
            Risk Level: {analysis.risk_level.value}
            Risky NFTs: {len(analysis.risky_nfts)}
            Transaction Count: {analysis.transaction_count}
            Total Portfolio Value: ${analysis.total_value:,.2f}
            Suspicious Activities: {len(analysis.suspicious_activity)}
            Last Activity: {analysis.last_activity}
            
            Provide a concise, professional risk assessment in 2-3 sentences. 
            Focus on actionable insights and clear recommendations.
            Use emojis appropriately but sparingly.
            """

            headers = {
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("BOT_REFERER_URL", "riskraider-bot"),
                "X-Title": "RiskRaider NFT Risk Analyzer"
            }

            payload = {
                "model": "anthropic/claude-3-haiku",  # More reliable than GPT-3.5
                "messages": [
                    {"role": "system", "content": "You are an expert NFT risk analyst. Provide clear, actionable risk assessments."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.3
            }

            async with self.session.post(f"{self.openrouter_base}/chat/completions", 
                                       headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()
                
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
        
        # Fallback summary
        risk_emoji = "🔴" if analysis.risk_score > 70 else "🟡" if analysis.risk_score > 40 else "🟢"
        return f"{risk_emoji} This wallet has a {analysis.risk_level.value.split()[1]} risk profile with {len(analysis.risky_nfts)} flagged NFTs. {'Proceed with extreme caution.' if analysis.risk_score > 70 else 'Standard security practices recommended.' if analysis.risk_score > 40 else 'Generally safe for interaction.'}"

    def _create_detailed_embed(self, analysis: WalletAnalysis, ai_summary: str) -> discord.Embed:
        """Create comprehensive Discord embed"""
        # Color based on risk level
        color_map = {
            RiskLevel.LOW: discord.Color.green(),
            RiskLevel.MEDIUM: discord.Color.yellow(), 
            RiskLevel.HIGH: discord.Color.orange(),
            RiskLevel.CRITICAL: discord.Color.red()
        }
        
        embed = discord.Embed(
            title=f"🔍 NFT Wallet Analysis",
            description=ai_summary,
            color=color_map[analysis.risk_level],
            timestamp=datetime.now(timezone.utc)
        )
        
        # Wallet info
        wallet_display = analysis.wallet[:10] + "..." + analysis.wallet[-8:] if len(analysis.wallet) > 20 else analysis.wallet
        embed.add_field(
            name="📋 Wallet Address", 
            value=f"`{wallet_display}`", 
            inline=False
        )
        
        # Risk metrics
        risk_bar = self._create_risk_bar(analysis.risk_score)
        embed.add_field(
            name="⚠️ Risk Assessment",
            value=f"{analysis.risk_level.value}\n`{risk_bar}` **{analysis.risk_score}/100**",
            inline=True
        )
        
        # Portfolio info
        embed.add_field(
            name="💼 Portfolio Overview",
            value=f"🏷️ **Risky NFTs:** {len(analysis.risky_nfts)}\n"
                  f"📊 **Transactions:** {analysis.transaction_count:,}\n"
                  f"💰 **Est. Value:** ${analysis.total_value:,.2f}",
            inline=True
        )
        
        # Activity info
        embed.add_field(
            name="📈 Activity Status", 
            value=f"🕒 **Last Activity:** {analysis.last_activity or 'Unknown'}\n"
        )
        
        # Social Analysis Section
        if social and "social_analysis" in result and result["social_analysis"]:
            social_res = result["social_analysis"]
            if not social_res.get("error"):
                social_details = social_res.get("details", {})
                embed.add_field(
                    name="📱 Social Analysis",
                    value=f"**Risk Score: {social_res.get('score', 'N/A')}/100**\n" +
                          f">>> Reputational Clues: `_`\n" +
                          f"- Followers: `{social_details.get('followers', 'N/A')}`\n" +
                          f"- Account Age: `{social_details.get('account_age_days', 'N/A')} days`\n" +
                          f"- Engagement Ratio: `{social_details.get('engagement_ratio', 'N/A')}`",
                    inline=False
                )

        # Graph Analysis Section
        if "graph_analysis" in result and result["graph_analysis"]:
            graph_res = result["graph_analysis"]
            if graph_res.risk_level != "NO_DATA" and graph_res.risk_level != "ERROR":
                graph_details = graph_res.details
                influential_wallets = "\n".join([f"- `{w}`" for w in graph_details.get('most_influential_wallets', [])])
                embed.add_field(
                    name="🌐 Trust Flow Analysis",
                    value=f"**Risk Score: {graph_res.score}/100** (`{graph_res.risk_level}`)\n" +
                          f">>> **Influence Concentration (Top 5):** `{graph_details.get('influence_concentration_top_5', 'N/A')}`\n" +
                          f"- Wallets in Graph: `{graph_details.get('total_wallets_in_graph', 'N/A')}`\n" +
                          f"- Most Influential:\n{influential_wallets}",
                    inline=False
                )      
        embed.set_footer(
            text="Powered by bitsCrunch • Data cached for 30 minutes",
            icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png"  # Optional: Add your bot's icon
        )
        
        return embed

    def _create_risk_bar(self, score: int) -> str:
        """Create visual risk score bar"""
        filled = int(score / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty

    @commands.command(name="nftcheck", help="🔍 Comprehensive NFT wallet risk analysis with AI insights")
    async def nftcheck(self, ctx: commands.Context, *, wallet: str):
        """Analyzes an NFT wallet for risk factors."""
        logger.info(f"🔍 nftcheck called by {ctx.author} with wallet: {wallet}")
        
        # Defer the response to prevent timeout
        async with ctx.typing():
            # Rate limiting
            if not await self._check_rate_limit(ctx.author.id):
                embed = discord.Embed(
                    title="⏱️ Rate Limited",
                    description="You can only check 5 wallets per 10 minutes. Please try again later.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            # Validate wallet
            is_valid, result = self._validate_wallet(wallet)
            if not is_valid:
                embed = discord.Embed(
                    title="❌ Invalid Wallet",
                    description=result,
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            wallet = result
            logger.info(f"✅ Wallet validated: {wallet}")
            
            # Check cache first
            cache_key = hashlib.md5(f"{wallet}".encode()).hexdigest()
            cached_analysis = await self.redis_manager.get_cache(cache_key)
            
            if cached_analysis:
                ai_summary = await self._generate_ai_summary(cached_analysis)
                embed = self._create_detailed_embed(cached_analysis, ai_summary)
                embed.set_footer(text="Powered by bitsCrunch • Cached data")
                await ctx.send(embed=embed)
                return
            
            # Fetch fresh data
            status_embed = discord.Embed(
                title="🔄 Analyzing Wallet...",
                description=f"Fetching risk data for `{wallet[:10]}...{wallet[-8:]}`\n"
                           f"⏳ This may take up to 30 seconds...",
                color=discord.Color.blue()
            )
            
            # Cache the result
            self.cache.set(cache_key, analysis)
            
            # Generate AI summary
            ai_summary = await self._generate_ai_summary(analysis)
            
            # Create and send final embed
            embed = self._create_detailed_embed(analysis, ai_summary)
            
            await status_message.edit(embed=embed)
            
            # Log successful analysis
            logger.info(f"NFT analysis completed for {wallet} (Risk: {analysis.risk_score})")
            
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for debugging"""
        if isinstance(error, commands.CommandInvokeError):
            original_error = error.original
            logger.error(f"💥 Command {ctx.command} failed: {original_error}")
            
            embed = discord.Embed(
                title="❌ Command Error",
                description=f"An error occurred: `{str(original_error)[:500]}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"💥 Unhandled error in {ctx.command}: {error}")
            await ctx.send(f"❌ Error: `{error}`")
            

    @commands.command(name="nftstats", help="📊 View your NFT checking statistics")
    async def nftstats(self, ctx: commands.Context):
        """Show user's usage statistics"""
        user_id = ctx.author.id
        recent_requests = len(self.rate_limits.get(user_id, []))
        
        embed = discord.Embed(
            title="📊 Your NFT Check Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⏱️ Recent Usage",
            value=f"**{recent_requests}/5** requests used in the last 10 minutes",
            inline=False
        )
        embed.add_field(
            name="💾 Cache Status", 
            value=f"**{len(self.cache.cache)}** analyses cached",
            inline=True
        )
        embed.add_field(
            name="🔄 Reset Time",
            value=f"<t:{int(time.time() + 600)}:R>",  # 10 minutes from now
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.command(
        name="clearcache", 
        description="(Admin) Clears the NFT analysis cache.",
        hidden=True
    )
    @commands.has_permissions(administrator=True)
    async def clear_cache(self, ctx):
        """Admin command to clear the analysis cache"""
        self.cache.cache.clear()
        await ctx.send("🧹 Analysis cache cleared successfully!")

async def setup(bot):
    await bot.add_cog(NFTCheck(bot))