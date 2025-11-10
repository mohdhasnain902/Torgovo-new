"""
TradingManager class for managing crypto trading bots.
"""
import threading
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import Order, BotSession, PairConfig
from users.models import UserProfile

# Import bot implementations (these will be created separately)
from .bots.BinanceBot import BinanceBots
from .bots.BybitBot import BybitBots
from .bots.KrakenSpotBot import KrakenBots
from .bots.MexcBot import MexcBots
from .bots.BybitArbitrageBot import BybitArbitrageBot


class TradingManager:
    """
    Centralized manager for handling multiple trading bots across different users and pairs.

    Key Responsibilities:
    - Initialize and manage trading bots for different users and pairs
    - Provide thread-safe bot creation and management
    - Handle bot lifecycle (start, stop, pause)
    - Execute trades through exchange APIs
    - Manage bot sessions and track performance
    """

    def __init__(self):
        # Thread-safe dictionaries to store bots
        self._bots: Dict[str, Any] = {}
        self._arbitrage_bots: Dict[str, Any] = {}
        self._bot_sessions: Dict[str, BotSession] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger('trading')

    def _get_bot_key(self, user, pair_config: PairConfig, exchange: str) -> str:
        """Generate unique bot key."""
        return f"{user.id}_{pair_config.pair_symbol}_{exchange}"

    def _get_arbitrage_key(self, user, exchange: str) -> str:
        """Generate unique arbitrage bot key."""
        return f"{user.id}_{exchange}_arbitrage"

    def _get_user_exchange_credentials(self, user) -> Dict[str, Any]:
        """Get user's exchange API credentials from UserProfile."""
        try:
            profile = user.trading_profile  # Use the correct related_name from UserProfile
            credentials = {
                'binance': {
                    'api_key': profile.binance_api_key or profile.api_key,  # Fallback to generic API key
                    'api_secret': profile.binance_api_secret or profile.api_secret,
                },
                'bybit': {
                    'api_key': profile.bybit_api_key or profile.api_key,
                    'api_secret': profile.bybit_api_secret or profile.api_secret,
                },
                'mexc': {
                    'api_key': profile.mexc_api_key or profile.api_key,
                    'api_secret': profile.mexc_api_secret or profile.api_secret,
                }
            }
            return credentials
        except Exception as e:
            self.logger.error(f"Error getting user credentials: {e}")
            raise ValueError("User exchange credentials not configured")

    def create_bot(self, user, pair_config: PairConfig, exchange: str = None) -> Any:
        """
        Create a trading bot for a specific user and pair configuration.

        Args:
            user: Django User object
            pair_config: PairConfig object with trading settings
            exchange: Exchange override (optional)

        Returns:
            Bot instance for the given configuration
        """
        if not exchange:
            exchange = pair_config.exchange

        bot_key = self._get_bot_key(user, pair_config, exchange)

        with self._lock:
            # Check if bot already exists
            if bot_key in self._bots:
                self.logger.warning(f"Bot {bot_key} already exists. Returning existing instance.")
                return self._bots[bot_key]

            # Get user credentials
            credentials = self._get_user_exchange_credentials(user)

            # Create bot instance based on exchange using the user's provided code structure
            try:
                if exchange == "binance":
                    if exchange not in credentials or not credentials[exchange]['api_key']:
                        raise ValueError(f"Binance API keys not configured for user {user.username}")

                    # Initialize Binance connection using the provided TradingManager approach
                    bot = BinanceBots(
                        user=user,
                        pair_config=pair_config,
                        api_key=credentials[exchange]['api_key'],
                        api_secret=credentials[exchange]['api_secret'],
                        testnet=False  # Default to mainnet, can be made configurable
                    )

                elif exchange == "bybit":
                    if exchange not in credentials or not credentials[exchange]['api_key']:
                        raise ValueError(f"Bybit API keys not configured for user {user.username}")

                    bot = BybitBots(
                        user=user,
                        pair_config=pair_config,
                        api_key=credentials[exchange]['api_key'],
                        api_secret=credentials[exchange]['api_secret']
                    )

                elif exchange == "mexc":
                    if exchange not in credentials or not credentials[exchange]['api_key']:
                        raise ValueError(f"MEXC API keys not configured for user {user.username}")

                    bot = MexcBots(
                        user=user,
                        pair_config=pair_config,
                        api_key=credentials[exchange]['api_key'],
                        api_secret=credentials[exchange]['api_secret']
                    )

                elif exchange == "kraken_spot":
                    if exchange not in credentials or not credentials[exchange]['api_key']:
                        raise ValueError(f"Kraken API keys not configured for user {user.username}")

                    bot = KrakenBots(
                        user=user,
                        pair_config=pair_config,
                        api_key=credentials[exchange]['api_key'],
                        api_secret=credentials[exchange]['api_secret']
                    )
                else:
                    raise ValueError(f"Unsupported exchange: {exchange}")

                self._bots[bot_key] = bot
                self.logger.info(f"Created {exchange} bot for {bot_key}")
                return bot

            except Exception as e:
                self.logger.error(f"Failed to create {exchange} bot: {e}")
                raise

    def create_arbitrage_bot(self, user, exchange: str) -> Any:
        """
        Create an arbitrage bot for a specific user and exchange.

        Args:
            user: Django User object
            exchange: Exchange name

        Returns:
            ArbitrageBot instance
        """
        arbitrage_key = self._get_arbitrage_key(user, exchange)

        with self._lock:
            if arbitrage_key in self._arbitrage_bots:
                self.logger.warning(f"Arbitrage Bot {arbitrage_key} already exists. Returning existing instance.")
                return self._arbitrage_bots[arbitrage_key]

            # Get user credentials
            credentials = self._get_user_exchange_credentials(user)

            try:
                if exchange == 'bybit':
                    bot = BybitArbitrageBot(user=user, credentials=credentials)
                    self._arbitrage_bots[arbitrage_key] = bot
                    self.logger.info(f"Created {exchange} Arbitrage Bot for {arbitrage_key}")
                    return bot
                else:
                    raise ValueError(f"Arbitrage not supported for exchange: {exchange}")

            except Exception as e:
                self.logger.error(f"Failed to create {exchange} Arbitrage bot: {e}")
                raise

    def start_bot(self, user, pair_config: PairConfig, exchange: str = None, session_config: Dict = None) -> str:
        """
        Start a specific bot for a user and pair.

        Args:
            user: Django User object
            pair_config: PairConfig object
            exchange: Exchange name (optional)
            session_config: Additional session configuration

        Returns:
            Bot session ID
        """
        if not exchange:
            exchange = pair_config.exchange

        bot_key = self._get_bot_key(user, pair_config, exchange)
        session_id = str(uuid.uuid4())

        with self._lock:
            bot = self._bots.get(bot_key)
            if not bot:
                # Create bot if it doesn't exist
                bot = self.create_bot(user, pair_config, exchange)

            try:
                # Create bot session record
                bot_session = BotSession.objects.create(
                    user=user,
                    pair_config=pair_config,
                    session_id=session_id,
                    bot_type=pair_config.bot_type,
                    status='starting',
                    session_config=session_config or {}
                )

                # Store session reference
                self._bot_sessions[session_id] = bot_session

                # Start bot in background thread
                bot_thread = threading.Thread(
                    target=self._run_bot,
                    args=(bot, bot_session),
                    daemon=True
                )
                bot_thread.start()

                # Update session status
                bot_session.start_session()

                self.logger.info(f"Started bot {bot_key} with session {session_id}")
                return session_id

            except Exception as e:
                self.logger.error(f"Failed to start bot {bot_key}: {e}")
                raise

    def start_arbitrage_bot(self, user, exchange: str, session_config: Dict = None) -> str:
        """
        Start a specific arbitrage bot for a user and exchange.

        Args:
            user: Django User object
            exchange: Exchange name
            session_config: Additional session configuration

        Returns:
            Bot session ID
        """
        arbitrage_key = self._get_arbitrage_key(user, exchange)
        session_id = str(uuid.uuid4())

        with self._lock:
            bot = self._arbitrage_bots.get(arbitrage_key)
            if not bot:
                self.logger.warning(f"Arbitrage Bot {arbitrage_key} not found")
                return None

            try:
                # Create bot session record for arbitrage
                # Note: We'd need to create a dummy PairConfig or modify the model
                # For now, this is a simplified version

                # Start bot in background thread
                bot_thread = threading.Thread(
                    target=self._run_arbitrage_bot,
                    args=(bot, session_id),
                    daemon=True
                )
                bot_thread.start()

                self.logger.info(f"Started arbitrage bot {arbitrage_key}")
                return session_id

            except Exception as e:
                self.logger.error(f"Failed to start arbitrage bot {arbitrage_key}: {e}")
                raise

    def stop_bot(self, user, pair_symbol: str, exchange: str, session_id: str = None):
        """
        Stop a specific bot for a user and pair.

        Args:
            user: Django User object
            pair_symbol: Trading pair symbol
            exchange: Exchange name
            session_id: Specific session to stop (optional)
        """
        bot_key = f"{user.id}_{pair_symbol}_{exchange}"

        with self._lock:
            bot = self._bots.get(bot_key)
            if bot:
                try:
                    bot.stop_bot()

                    # Update bot sessions
                    if session_id and session_id in self._bot_sessions:
                        bot_session = self._bot_sessions[session_id]
                        bot_session.stop_session()
                        del self._bot_sessions[session_id]
                    else:
                        # Stop all sessions for this bot
                        BotSession.objects.filter(
                            user=user,
                            pair_config__pair_symbol=pair_symbol,
                            status='running'
                        ).update(status='stopped', stopped_at=timezone.now())

                    self.logger.info(f"Stopped bot {bot_key}")

                except Exception as e:
                    self.logger.error(f"Error stopping bot {bot_key}: {e}")
            else:
                self.logger.warning(f"Bot {bot_key} not found")

    def stop_arbitrage_bot(self, user, exchange: str):
        """
        Stop a specific arbitrage bot for a user and exchange.

        Args:
            user: Django User object
            exchange: Exchange name
        """
        arbitrage_key = f"{user.id}_{exchange}_arbitrage"

        with self._lock:
            bot = self._arbitrage_bots.get(arbitrage_key)
            if bot:
                try:
                    bot.stop_bot()
                    del self._arbitrage_bots[arbitrage_key]
                    self.logger.info(f"Stopped arbitrage bot {arbitrage_key}")
                    return True
                except Exception as e:
                    self.logger.error(f"Error stopping arbitrage bot {arbitrage_key}: {e}")
            return False

    def get_bot(self, user_id: int, pair_symbol: str, exchange: str) -> Optional[Any]:
        """
        Retrieve a specific bot instance.

        Args:
            user_id: User ID
            pair_symbol: Trading pair symbol
            exchange: Exchange name

        Returns:
            Bot instance or None
        """
        bot_key = f"{user_id}_{pair_symbol}_{exchange}"
        return self._bots.get(bot_key)

    def get_arbitrage_bot(self, user_id: int, exchange: str) -> Optional[Any]:
        """
        Retrieve a specific arbitrage bot instance.

        Args:
            user_id: User ID
            exchange: Exchange name

        Returns:
            ArbitrageBot instance or None
        """
        arbitrage_key = f"{user_id}_{exchange}_arbitrage"
        return self._arbitrage_bots.get(arbitrage_key)

    def execute_webhook_order(self, user, pair_config: PairConfig, action: str,
                            quantity: Decimal, price: Decimal = None,
                            webhook_secret: str = None) -> Order:
        """
        Execute order triggered by webhook.

        Args:
            user: Django User object
            pair_config: PairConfig object
            action: 'buy' or 'sell'
            quantity: Order quantity
            price: Order price (None for market orders)
            webhook_secret: Webhook secret for tracking

        Returns:
            Order object
        """
        try:
            with transaction.atomic():
                # Create order record
                order = Order.objects.create(
                    user=user,
                    pair_config=pair_config,
                    action=action,
                    order_type='market' if price is None else 'limit',
                    quantity=quantity,
                    price=price or Decimal('0'),  # Market orders will have price set by exchange
                    source='webhook',
                    webhook_secret=webhook_secret,
                    status='pending'
                )

                # Get or create bot instance
                bot = self.get_bot(user.id, pair_config.pair_symbol, pair_config.exchange)
                if not bot:
                    bot = self.create_bot(user, pair_config, pair_config.exchange)

                # Execute order through exchange API
                if price is None:
                    # Market order
                    result = bot.execute_market_order(action, quantity)
                else:
                    # Limit order
                    result = bot.execute_limit_order(action, quantity, price)

                # Update order with execution details
                order.execute_order(
                    executed_price=result.get('price'),
                    executed_quantity=result.get('quantity'),
                    exchange_order_id=result.get('order_id')
                )

                self.logger.info(f"Webhook order executed: {order.id}")
                return order

        except Exception as e:
            self.logger.error(f"Failed to execute webhook order: {e}")
            # Update order status to failed
            if 'order' in locals():
                order.status = 'failed'
                order.save()
            raise

    def _run_bot(self, bot, bot_session: BotSession):
        """
        Run bot in background thread.

        Args:
            bot: Bot instance
            bot_session: BotSession object
        """
        try:
            self.logger.info(f"Starting bot session {bot_session.session_id}")

            # Start the bot (this would be the main bot logic)
            bot.startBot()

        except Exception as e:
            self.logger.error(f"Bot session {bot_session.session_id} error: {e}")
            bot_session.status = 'error'
            bot_session.save()

    def _run_arbitrage_bot(self, bot, session_id: str):
        """
        Run arbitrage bot in background thread.

        Args:
            bot: ArbitrageBot instance
            session_id: Session ID
        """
        try:
            self.logger.info(f"Starting arbitrage bot session {session_id}")
            bot.startBot()

        except Exception as e:
            self.logger.error(f"Arbitrage bot session {session_id} error: {e}")

    def get_active_sessions(self, user=None) -> List[BotSession]:
        """
        Get active bot sessions.

        Args:
            user: Filter by specific user (optional)

        Returns:
            List of active BotSession objects
        """
        queryset = BotSession.objects.filter(status='running')
        if user:
            queryset = queryset.filter(user=user)
        return queryset.select_related('user', 'pair_config')

    def get_bot_statistics(self, user=None) -> Dict[str, Any]:
        """
        Get bot statistics.

        Args:
            user: Filter by specific user (optional)

        Returns:
            Statistics dictionary
        """
        queryset = BotSession.objects.all()
        if user:
            queryset = queryset.filter(user=user)

        return {
            'total_sessions': queryset.count(),
            'active_sessions': queryset.filter(status='running').count(),
            'total_orders': Order.objects.all().count() if not user else Order.objects.filter(user=user).count(),
            'successful_orders': queryset.aggregate(total=models.Sum('successful_orders'))['total'] or 0,
            'total_profit_loss': queryset.aggregate(total=models.Sum('total_profit_loss'))['total'] or 0,
        }


# Global singleton instance
trading_manager = TradingManager()