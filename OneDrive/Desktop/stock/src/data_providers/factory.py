"""
Data Provider Factory
Manages provider initialization and switching
Allows easy addition of new providers (Kite, Shoonya, m.Stock, etc.)
"""

from src.logger import logger
from .base import DataProviderBase
from .yfinance_provider import YFinanceProvider


class DataProviderRegistry:
    """
    Registry for available data providers
    Centralized location for managing multiple providers
    """
    
    _providers = {
        'yfinance': YFinanceProvider,
        # Future providers:
        # 'kite': KiteProvider,
        # 'shoonya': ShooinyaProvider,
        # 'mstock': MStockProvider,
    }
    
    @classmethod
    def register(cls, name: str, provider_class):
        """
        Register a new data provider
        
        Args:
            name: Provider identifier (e.g., 'kite', 'shoonya')
            provider_class: Class implementing DataProviderBase
        """
        if not issubclass(provider_class, DataProviderBase):
            raise TypeError(f"{provider_class} must inherit from DataProviderBase")
        
        cls._providers[name] = provider_class
        logger.info(f"Registered data provider: {name}")
    
    @classmethod
    def get_provider(cls, name: str = 'yfinance') -> DataProviderBase:
        """
        Get an instance of a registered provider
        
        Args:
            name: Provider identifier
        
        Returns:
            Instance of the provider
        
        Raises:
            ValueError: If provider not found
        """
        if name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(f"Provider '{name}' not found. Available: {available}")
        
        provider_class = cls._providers[name]
        logger.info(f"Using data provider: {name}")
        return provider_class()
    
    @classmethod
    def list_providers(cls) -> list:
        """List all available providers"""
        return list(cls._providers.keys())


# Factory function for convenience
def get_data_provider(name: str = 'yfinance') -> DataProviderBase:
    """
    Convenience function to get a data provider
    
    Usage:
        provider = get_data_provider('yfinance')
        df = provider.fetch_5min_data('RELIANCE')
    """
    return DataProviderRegistry.get_provider(name)
