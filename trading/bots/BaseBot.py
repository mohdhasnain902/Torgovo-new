"""
Base class for all trading bots.
"""
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from django.utils import timezone
from typing import Dict, Any, Optional


class BaseBot(ABC):
    """
    Abstract base class for all trading bots.
    """

    def __init__(self, user, pair_config=None, credentials=None):
        self.user = user
        self.pair_config = pair_config
        self.credentials = credentials or {}
        self.logger = logging.getLogger(f'trading.bots.{self.__class__.__name__}')
        self.is_running = False
        self.position_size = Decimal('0')
        self.current_price = None

    @abstractmethod
    def startBot(self):
        """Start the bot trading logic."""
        pass

    @abstractmethod
    def stop_bot(self):
        """Stop the bot."""
        pass

    @abstractmethod
    def execute_market_order(self, action: str, quantity: Decimal) -> Dict[str, Any]:
        """Execute a market order."""
        pass

    @abstractmethod
    def execute_limit_order(self, action: str, quantity: Decimal, price: Decimal) -> Dict[str, Any]:
        """Execute a limit order."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balance."""
        pass

    @abstractmethod
    def get_open_positions(self) -> list:
        """Get open positions."""
        pass

    def validate_order_params(self, action: str, quantity: Decimal, price: Decimal = None):
        """Validate order parameters."""
        if action not in ['buy', 'sell']:
            raise ValueError("Action must be 'buy' or 'sell'")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")

        if price is not None and price <= 0:
            raise ValueError("Price must be greater than 0")

        # Check against pair limits
        if self.pair_config:
            if quantity < self.pair_config.min_order_size:
                raise ValueError(f"Quantity below minimum: {self.pair_config.min_order_size}")
            if quantity > self.pair_config.max_order_size:
                raise ValueError(f"Quantity above maximum: {self.pair_config.max_order_size}")

    def log_order(self, action: str, quantity: Decimal, price: Decimal, result: Dict[str, Any]):
        """Log order execution."""
        self.logger.info(f"Order executed: {action.upper()} {quantity} @ {price} - Result: {result}")

    def get_exchange_config(self):
        """Get exchange configuration."""
        return self.credentials.get('exchange_config', {})

    def is_demo_mode(self):
        """Check if bot is in demo mode."""
        return self.credentials.get('demo_mode', True)