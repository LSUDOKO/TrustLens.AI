from typing import Dict, Any, List, Optional, Set, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import re

from .base_analyzer import BaseAnalyzer, AnalysisResult
from ....api.api_aggregator import APIAggregator


@dataclass
class SocialMetrics:
    """Container for calculated social media metrics."""
    engagement_rate: float = 0.0
    authenticity_score: float = 0.0
    influence_score: float = 0.0
    activity_consistency: float = 0.0
    network_quality: float = 0.0


class SocialAnalyzer(BaseAnalyzer):
    """
    Advanced social media analyzer that efficiently fetches and analyzes 
    off-chain social profile data using multiple API sources.
    """

    def __init__(self, api_aggregator: APIAggregator, cache_ttl: int = 3600):
        self.api_aggregator = api_aggregator
        self.cache_ttl = cache_ttl  # Cache TTL in seconds
        self.logger = logging.getLogger(__name__)
        
        # Risk assessment weights
        self.risk_weights = {
            'authenticity': 0.25,
            'engagement': 0.20,
            'influence': 0.20,
            'activity': 0.15,
            'network': 0.10,
            'content': 0.10
        }
        
        # Suspicious patterns
        self.suspicious_patterns = {
            'bot_usernames': re.compile(r'.*\d{4,}$|.*bot.*|.*fake.*', re.I),
            'spam_content': re.compile(r'(buy now|click here|free money|guaranteed|urgent)', re.I),
            'fake_domains': {'bit.ly', 'tinyurl.com', 'goo.gl'}  # Shortened URLs often used by bots
        }

    async def analyze(self, social_handle: str, platforms: Optional[List[str]] = None) -> AnalysisResult:
        """
        Performs comprehensive social media analysis with efficient data fetching.
        
        Args:
            social_handle: The social media handle to analyze
            platforms: Optional list of specific platforms to analyze
            
        Returns:
            AnalysisResult with comprehensive risk assessment
        """
        try:
            # Normalize handle
            normalized_handle = self._normalize_handle(social_handle)
            
            # Fetch data from multiple sources concurrently
            aggregated_data = await self._fetch_social_data_efficiently(
                normalized_handle, platforms
            )

            if not aggregated_data:
                return self._create_no_data_result(normalized_handle)

            # Perform comprehensive analysis
            metrics = await self._calculate_comprehensive_metrics(aggregated_data)
            risk_indicators = self._identify_risk_indicators(aggregated_data, metrics)
            
            # Calculate final risk score
            risk_score = self._calculate_weighted_risk_score(metrics, risk_indicators)
            risk_level = self._get_risk_level(risk_score)
            
            # Generate detailed analysis
            details = self._generate_analysis_details(aggregated_data, metrics, risk_indicators)
            recommendations = self._generate_recommendations(risk_indicators, metrics)

            return AnalysisResult(
                score=risk_score,
                risk_level=risk_level,
                details=details,
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"Social analysis failed for {social_handle}: {str(e)}")
            return self._create_error_result(social_handle, str(e))

    async def _fetch_social_data_efficiently(
        self, 
        handle: str, 
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Efficiently fetch data from multiple sources with concurrency and error handling."""
        
        # Create concurrent tasks for different data sources
        tasks = []
        
        # Main profile data
        tasks.append(
            self._safe_fetch(
                self.api_aggregator.fetch_all_social_data, 
                handle, 
                "profile_data"
            )
        )
        
        # Recent posts/activity
        if hasattr(self.api_aggregator, 'fetch_recent_posts'):
            tasks.append(
                self._safe_fetch(
                    self.api_aggregator.fetch_recent_posts, 
                    handle, 
                    "recent_posts"
                )
            )
        
        # Network analysis
        if hasattr(self.api_aggregator, 'fetch_network_data'):
            tasks.append(
                self._safe_fetch(
                    self.api_aggregator.fetch_network_data, 
                    handle, 
                    "network_data"
                )
            )
        
        # Execute all tasks concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=30.0  # 30 second timeout
            )
            
            # Filter out exceptions and combine results
            combined_data = []
            for result in results:
                if isinstance(result, list) and result:
                    combined_data.extend(result)
                elif isinstance(result, dict) and result:
                    combined_data.append(result)
            
            return combined_data
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Data fetch timeout for handle: {handle}")
            return []

    async def _safe_fetch(self, fetch_func, *args, source_name: str = "unknown") -> List[Dict[str, Any]]:
        """Safely execute fetch function with error handling."""
        try:
            result = await fetch_func(*args)
            if result:
                # Add source metadata
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict):
                            item['_source'] = source_name
                elif isinstance(result, dict):
                    result['_source'] = source_name
                return result if isinstance(result, list) else [result]
            return []
        except Exception as e:
            self.logger.error(f"Failed to fetch {source_name}: {str(e)}")
            return []

    async def _calculate_comprehensive_metrics(self, data: List[Dict[str, Any]]) -> SocialMetrics:
        """Calculate comprehensive social media metrics."""
        metrics = SocialMetrics()
        
        try:
            # Aggregate data by type
            profile_data = [d for d in data if d.get('_source') == 'profile_data']
            post_data = [d for d in data if d.get('_source') == 'recent_posts']
            network_data = [d for d in data if d.get('_source') == 'network_data']
            
            # Calculate engagement rate
            metrics.engagement_rate = self._calculate_engagement_rate(profile_data, post_data)
            
            # Calculate authenticity score
            metrics.authenticity_score = self._calculate_authenticity_score(profile_data, post_data)
            
            # Calculate influence score
            metrics.influence_score = self._calculate_influence_score(profile_data, network_data)
            
            # Calculate activity consistency
            metrics.activity_consistency = self._calculate_activity_consistency(post_data)
            
            # Calculate network quality
            metrics.network_quality = self._calculate_network_quality(network_data)
            
        except Exception as e:
            self.logger.error(f"Metrics calculation failed: {str(e)}")
        
        return metrics

    def _calculate_engagement_rate(self, profile_data: List[Dict], post_data: List[Dict]) -> float:
        """Calculate engagement rate based on likes, comments, shares vs followers."""
        try:
            total_engagement = 0
            total_posts = 0
            follower_count = 0
            
            for profile in profile_data:
                follower_count = max(follower_count, profile.get('followers', 0))
            
            for post in post_data:
                likes = post.get('likes', 0)
                comments = post.get('comments', 0)
                shares = post.get('shares', 0)
                total_engagement += likes + comments + shares
                total_posts += 1
            
            if total_posts > 0 and follower_count > 0:
                avg_engagement = total_engagement / total_posts
                return min((avg_engagement / follower_count) * 100, 100.0)
            
            return 0.0
        except Exception:
            return 0.0

    def _calculate_authenticity_score(self, profile_data: List[Dict], post_data: List[Dict]) -> float:
        """Calculate authenticity score based on various indicators."""
        score = 100.0
        
        try:
            for profile in profile_data:
                # Check follower/following ratio
                followers = profile.get('followers', 0)
                following = profile.get('following', 0)
                
                if following > 0:
                    ratio = followers / following
                    if ratio < 0.1:  # Following way more than followers
                        score -= 20
                    elif ratio > 100:  # Suspiciously high follower count
                        score -= 15
                
                # Check profile completeness
                if not profile.get('bio'):
                    score -= 10
                if not profile.get('profile_image'):
                    score -= 5
                
                # Check for suspicious username patterns
                username = profile.get('username', '')
                if self.suspicious_patterns['bot_usernames'].match(username):
                    score -= 25
            
            # Analyze post patterns
            for post in post_data:
                content = post.get('content', '')
                if self.suspicious_patterns['spam_content'].search(content):
                    score -= 10
            
            return max(score, 0.0)
        except Exception:
            return 50.0  # Neutral score on error

    def _calculate_influence_score(self, profile_data: List[Dict], network_data: List[Dict]) -> float:
        """Calculate influence score based on reach and network quality."""
        try:
            max_followers = 0
            verified_count = 0
            total_profiles = len(profile_data)
            
            for profile in profile_data:
                followers = profile.get('followers', 0)
                max_followers = max(max_followers, followers)
                
                if profile.get('verified', False):
                    verified_count += 1
            
            # Base score on follower count (logarithmic scale)
            if max_followers > 0:
                import math
                follower_score = min(math.log10(max_followers) * 10, 70)
            else:
                follower_score = 0
            
            # Bonus for verification
            verification_bonus = (verified_count / max(total_profiles, 1)) * 20
            
            # Network quality bonus
            network_bonus = 10 if network_data else 0
            
            return min(follower_score + verification_bonus + network_bonus, 100.0)
        except Exception:
            return 0.0

    def _calculate_activity_consistency(self, post_data: List[Dict]) -> float:
        """Calculate consistency of posting activity."""
        try:
            if len(post_data) < 2:
                return 0.0
            
            # Analyze posting intervals
            timestamps = []
            for post in post_data:
                if 'timestamp' in post:
                    timestamps.append(post['timestamp'])
            
            if len(timestamps) < 2:
                return 50.0  # Neutral score
            
            timestamps.sort()
            intervals = []
            
            for i in range(1, len(timestamps)):
                try:
                    prev_time = datetime.fromisoformat(timestamps[i-1].replace('Z', '+00:00'))
                    curr_time = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
                    interval = (curr_time - prev_time).total_seconds() / 3600  # Hours
                    intervals.append(interval)
                except Exception:
                    continue
            
            if not intervals:
                return 50.0
            
            # Calculate coefficient of variation (lower = more consistent)
            mean_interval = sum(intervals) / len(intervals)
            if mean_interval == 0:
                return 0.0
            
            variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5
            cv = std_dev / mean_interval
            
            # Convert to consistency score (inverse of variation)
            consistency = max(0, 100 - (cv * 50))
            return min(consistency, 100.0)
            
        except Exception:
            return 50.0

    def _calculate_network_quality(self, network_data: List[Dict]) -> float:
        """Calculate quality of social network connections."""
        try:
            if not network_data:
                return 50.0
            
            total_connections = 0
            quality_connections = 0
            
            for network in network_data:
                connections = network.get('connections', [])
                total_connections += len(connections)
                
                for connection in connections:
                    # Quality indicators
                    if connection.get('verified', False):
                        quality_connections += 2
                    elif connection.get('followers', 0) > 1000:
                        quality_connections += 1
            
            if total_connections == 0:
                return 50.0
            
            quality_ratio = quality_connections / total_connections
            return min(quality_ratio * 100, 100.0)
            
        except Exception:
            return 50.0

    def _identify_risk_indicators(self, data: List[Dict], metrics: SocialMetrics) -> Dict[str, Any]:
        """Identify specific risk indicators from the data and metrics."""
        indicators = {
            'bot_likelihood': 0,
            'spam_indicators': [],
            'authenticity_flags': [],
            'engagement_anomalies': [],
            'network_risks': []
        }
        
        try:
            # Bot likelihood assessment
            if metrics.authenticity_score < 30:
                indicators['bot_likelihood'] += 40
            if metrics.engagement_rate > 20 or metrics.engagement_rate < 0.5:
                indicators['bot_likelihood'] += 20
            if metrics.activity_consistency > 95:  # Too consistent = bot
                indicators['bot_likelihood'] += 20
            
            # Spam indicators
            for item in data:
                content = str(item.get('content', ''))
                if self.suspicious_patterns['spam_content'].search(content):
                    indicators['spam_indicators'].append('Promotional content detected')
                
                # Check for suspicious links
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
                for url in urls:
                    domain = re.search(r'//([^/]+)', url)
                    if domain and any(sus_domain in domain.group(1) for sus_domain in self.suspicious_patterns['fake_domains']):
                        indicators['spam_indicators'].append('Suspicious shortened URL detected')
            
            # Authenticity flags
            if metrics.authenticity_score < 50:
                indicators['authenticity_flags'].append('Low authenticity score')
            
            # Engagement anomalies
            if metrics.engagement_rate > 15:
                indicators['engagement_anomalies'].append('Unusually high engagement rate')
            elif metrics.engagement_rate < 0.5:
                indicators['engagement_anomalies'].append('Very low engagement rate')
                
        except Exception as e:
            self.logger.error(f"Risk indicator identification failed: {str(e)}")
        
        return indicators

    def _calculate_weighted_risk_score(self, metrics: SocialMetrics, indicators: Dict[str, Any]) -> int:
        """Calculate final weighted risk score."""
        try:
            # Base risk from metrics (inverse scoring - lower metrics = higher risk)
            authenticity_risk = max(0, 100 - metrics.authenticity_score)
            engagement_risk = 50 if metrics.engagement_rate > 15 or metrics.engagement_rate < 0.5 else 0
            influence_risk = max(0, 50 - metrics.influence_score)
            activity_risk = 30 if metrics.activity_consistency > 95 else 0
            network_risk = max(0, 50 - metrics.network_quality)
            
            # Additional risk from indicators
            bot_risk = indicators.get('bot_likelihood', 0)
            spam_risk = min(len(indicators.get('spam_indicators', [])) * 20, 50)
            
            # Weighted combination
            weighted_score = (
                authenticity_risk * self.risk_weights['authenticity'] +
                engagement_risk * self.risk_weights['engagement'] +
                influence_risk * self.risk_weights['influence'] +
                activity_risk * self.risk_weights['activity'] +
                network_risk * self.risk_weights['network'] +
                (bot_risk + spam_risk) * self.risk_weights['content']
            )
            
            return min(int(weighted_score), 100)
            
        except Exception:
            return 50  # Neutral risk on calculation error

    def _generate_analysis_details(
        self, 
        data: List[Dict], 
        metrics: SocialMetrics, 
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed analysis information."""
        return {
            'data_sources': list(set(item.get('_source', 'unknown') for item in data)),
            'profiles_analyzed': len([d for d in data if d.get('_source') == 'profile_data']),
            'posts_analyzed': len([d for d in data if d.get('_source') == 'recent_posts']),
            'metrics': {
                'engagement_rate': round(metrics.engagement_rate, 2),
                'authenticity_score': round(metrics.authenticity_score, 2),
                'influence_score': round(metrics.influence_score, 2),
                'activity_consistency': round(metrics.activity_consistency, 2),
                'network_quality': round(metrics.network_quality, 2)
            },
            'risk_indicators': indicators,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def _generate_recommendations(self, indicators: Dict[str, Any], metrics: SocialMetrics) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        try:
            # High bot likelihood
            if indicators.get('bot_likelihood', 0) > 60:
                recommendations.append(
                    "HIGH RISK: Strong indicators suggest this may be an automated account. "
                    "Verify authenticity before engagement."
                )
            
            # Spam indicators
            spam_count = len(indicators.get('spam_indicators', []))
            if spam_count > 0:
                recommendations.append(
                    f"CAUTION: {spam_count} spam indicator(s) detected. "
                    "Review content carefully for promotional/malicious material."
                )
            
            # Low authenticity
            if metrics.authenticity_score < 40:
                recommendations.append(
                    "VERIFY: Low authenticity score detected. Cross-reference with other platforms "
                    "and look for verification badges or legitimate contact information."
                )
            
            # Engagement anomalies
            if metrics.engagement_rate > 15:
                recommendations.append(
                    "SUSPICIOUS: Unusually high engagement rate may indicate artificial inflation. "
                    "Investigate engagement quality and source."
                )
            elif metrics.engagement_rate < 0.5:
                recommendations.append(
                    "LOW ACTIVITY: Very low engagement suggests inactive or abandoned account."
                )
            
            # Network quality issues
            if metrics.network_quality < 30:
                recommendations.append(
                    "NETWORK RISK: Poor network quality detected. "
                    "Account may be associated with low-quality connections."
                )
            
            # No major issues found
            if not recommendations and indicators.get('bot_likelihood', 0) < 30:
                recommendations.append(
                    "NORMAL: Analysis shows typical social media activity patterns. "
                    "Standard verification procedures recommended."
                )
                
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {str(e)}")
            recommendations.append("Analysis completed with limited data. Manual review recommended.")
        
        return recommendations

    def _normalize_handle(self, handle: str) -> str:
        """Normalize social media handle format."""
        # Remove @ symbol and whitespace
        normalized = handle.strip().lstrip('@')
        # Convert to lowercase for consistent processing
        return normalized.lower()

    def _create_no_data_result(self, handle: str) -> AnalysisResult:
        """Create result for when no data is available."""
        return AnalysisResult(
            score=0,
            risk_level="NO_DATA",
            details={
                "info": f"No social media data found for handle: {handle}",
                "searched_platforms": ["twitter", "instagram", "linkedin", "facebook"],
                "suggestion": "Verify handle spelling and platform availability"
            },
            recommendations=[
                "No data available for analysis.",
                "Verify the social media handle is correct and publicly accessible.",
                "Consider alternative verification methods."
            ]
        )

    def _create_error_result(self, handle: str, error: str) -> AnalysisResult:
        """Create result for when analysis fails."""
        return AnalysisResult(
            score=50,  # Neutral risk due to uncertainty
            risk_level="UNKNOWN",
            details={
                "error": f"Analysis failed for {handle}: {error}",
                "timestamp": datetime.utcnow().isoformat()
            },
            recommendations=[
                "Analysis could not be completed due to technical issues.",
                "Consider manual verification or retry the analysis later.",
                "Treat with standard caution until proper analysis can be performed."
            ]
        )

    def _get_risk_level(self, score: int) -> str:
        """Convert numeric risk score to categorical risk level."""
        if score >= 80:
            return "CRITICAL"
        elif score >= 65:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        elif score >= 20:
            return "LOW"
        else:
            return "MINIMAL"