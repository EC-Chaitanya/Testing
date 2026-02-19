"""
Data Provider Factory - MSTOCK ONLY
Production-grade data provider management
Enforces MStock as the sole data provider (no fallbacks, fail-fast)
"""

from src.logger import logger
from .base import DataProviderBase
from .mstock_provider import MStockProvider


class DataProviderRegistry:
    """
    Registry for data providers (MStock only)
    
    ⚠️ PRODUCTION CONSTRAINT:
    - Only MStock is supported
    - No YFinance, no fallbacks
    - Initialization fails fast on missing API keys
    - Prevents silent degradation to free/unreliable APIs
    """
    
    _providers = {
        'mstock': MStockProvider,
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
    def get_provider(cls, name: str = 'mstock', api_key: str = None, session=None) -> DataProviderBase:
        """
        Get an instance of a registered provider
        
        ⚠️ CRITICAL: This WILL FAIL if mstock is not requested or if api_key/session is missing
        This is intentional - no silent fallbacks to broken/free APIs
        
        Args:
            name: Provider identifier (MUST be 'mstock')
            api_key: API key for mstock (optional if session provided)
            session: Authenticated MConnect session object (optional if api_key provided)
        
        Returns:
            Instance of MStockProvider
        
        Raises:
            ValueError: If provider not 'mstock' or neither api_key nor session provided
            ImportError: If MStockProvider cannot be instantiated
        """
        if name != 'mstock':
            raise ValueError(
                f"Provider '{name}' is not supported. Only 'mstock' is allowed.\n"
                f"Available: mstock\n"
                f"Reason: YFinance limited to 60 days, free APIs unreliable."
            )
        
        if not api_key and not session:
            raise ValueError(
                "MStock requires either API key or authenticated session.\n"
                "Set API_KEY in config.py or pass session from get_session().\n"
                "Get your API key from M.Stock account."
            )
        
        provider_class = cls._providers[name]
        logger.info(f"Using data provider: {name}")
        
        return provider_class(api_key=api_key, session=session)
    
    @classmethod
    def list_providers(cls) -> list:
        """List all available providers"""
        return list(cls._providers.keys())


# Factory function for convenience
def get_data_provider(name: str = 'mstock', api_key: str = None, session=None) -> DataProviderBase:
    """
    Convenience function to get a data provider
    
    ⚠️ PRODUCTION RULE: This WILL FAIL if neither api_key nor session is provided
    No silent degradation. No fallbacks to YFinance.
    
    Args:
        name: Provider identifier (must be 'mstock')
        api_key: M.Stock API key (optional if session provided)
        session: Authenticated MConnect session (optional if api_key provided)
    
    Returns:
        MStockProvider instance
    
    Raises:
        ValueError: If name != 'mstock' or neither api_key nor session provided
    
    Usage:
        # Option 1: With authenticated session (recommended)
        from src.auth import get_session
        session = get_session(API_KEY, USER_ID, PASSWORD, DOB)
        provider = get_data_provider('mstock', session=session)
        
        # Option 2: With API key only
        from config import API_KEY
        provider = get_data_provider('mstock', api_key=API_KEY)
        
        df = provider.fetch_5min_data('RELIANCE')
    """
    return DataProviderRegistry.get_provider(name, api_key=api_key, session=session)

