"""
Morning Stock Assistant Pro

Base Collector
"""

from abc import ABC
from abc import abstractmethod


class BaseCollector(ABC):
    """
    모든 Collector의 부모 클래스
    """

    @abstractmethod
    def collect(self, *args, **kwargs):
        """
        데이터 수집
        """
        raise NotImplementedError