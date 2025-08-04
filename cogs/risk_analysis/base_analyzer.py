from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class AnalysisResult:
    score: int
    risk_level: str
    details: Dict[str, Any]
    recommendations: List[str]

class BaseAnalyzer(ABC):
    """Abstract base class for all risk analyzers."""

    def __init__(self, session):
        self.session = session

    @abstractmethod
    async def analyze(self, target: str) -> AnalysisResult:
        """Perform analysis on a given target and return a score and details."""
        pass
