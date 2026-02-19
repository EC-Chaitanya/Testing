"""
Data Providers Package - MStock Only
Abstraction layer for stock data fetching
Production-grade, no fallbacks, fail-fast on configuration errors
"""

from .base import DataProviderBase
from .factory import DataProviderRegistry, get_data_provider
from .mstock_provider import MStockProvider

__all__ = [
    'DataProviderBase',
    'DataProviderRegistry',
    'get_data_provider',
    'MStockProvider',
]