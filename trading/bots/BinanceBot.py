"""
Binance trading bot implementation.
"""
import logging
import requests
import hmac
import hashlib
import time
from decimal import Decimal
from urllib.parse import urlencode
from .BaseBot import BaseBot


class BinanceBots(BaseBot):
    """
    Binance trading bot implementation.
    """

    def __init__(self, user, pair_config=None, credentials=None):
        super().__init__(user, pair_config, credentials)
        self.base_url = self.get_base_url()
        self.api_key = self.credentials.get('api_key')
        self.api_secret = self.credentials.get('api_secret')

    def get_base_url(self):
        """Get API base URL based on demo mode."""
        exchange_config = self.get_exchange_config()
        if self.is_demo_mode():
            return exchange_config.get('testnet_url', 'https://testnet.binance.vision')
        return exchange_config.get('api_url', 'https://api.binance.com')

    def _generate_signature(self, params):
        """Generate HMAC signature for API requests."""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method, endpoint, params=None, signed=False):
        """Make HTTP request to Binance API."""
        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key}

        if signed:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)

        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise

    def startBot(self):
        """Start the bot trading logic."""
        self.is_running = True
        self.logger.info(f"Starting Binance bot for {self.pair_config.pair_symbol}")

        try:
            # Main bot logic would go here
            # This is a simplified placeholder implementation
            while self.is_running:
                try:
                    # Check account status
                    account_info = self.get_account_balance()
                    self.logger.debug(f"Account info: {account_info}")

                    # Get current price
                    ticker_info = self.get_ticker_price()
                    if ticker_info:
                        self.current_price = Decimal(ticker_info['price'])
                        self.logger.debug(f"Current price: {self.current_price}")

                    # Bot strategy implementation would go here
                    # For now, just sleep to prevent busy loop
                    time.sleep(10)

                except Exception as e:
                    self.logger.error(f"Error in bot loop: {e}")
                    time.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        finally:
            self.is_running = False

    def stop_bot(self):
        """Stop the bot."""
        self.is_running = False
        self.logger.info("Binance bot stopped")

    def execute_market_order(self, action: str, quantity: Decimal) -> Dict[str, Any]:
        """Execute a market order."""
        self.validate_order_params(action, quantity)

        symbol = self.pair_config.pair_symbol
        side = action.upper()

        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': str(quantity),
            'newOrderRespType': 'FULL'
        }

        try:
            result = self._make_request('POST', '/api/v3/order', params, signed=True)

            # Extract execution details
            fills = result.get('fills', [])
            executed_price = Decimal('0')
            executed_quantity = Decimal('0')

            if fills:
                # Calculate weighted average price
                total_value = sum(Decimal(fill['price']) * Decimal(fill['qty']) for fill in fills)
                executed_quantity = sum(Decimal(fill['qty']) for fill in fills)
                executed_price = total_value / executed_quantity if executed_quantity > 0 else Decimal('0')

            order_result = {
                'success': True,
                'order_id': result.get('orderId'),
                'client_order_id': result.get('clientOrderId'),
                'price': executed_price,
                'quantity': executed_quantity,
                'status': result.get('status'),
                'fills': fills
            }

            self.log_order(action, quantity, executed_price, order_result)
            return order_result

        except Exception as e:
            self.logger.error(f"Failed to execute market order: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def execute_limit_order(self, action: str, quantity: Decimal, price: Decimal) -> Dict[str, Any]:
        """Execute a limit order."""
        self.validate_order_params(action, quantity, price)

        symbol = self.pair_config.pair_symbol
        side = action.upper()

        params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'timeInForce': 'GTC',  # Good Till Cancelled
            'quantity': str(quantity),
            'price': str(price)
        }

        try:
            result = self._make_request('POST', '/api/v3/order', params, signed=True)

            order_result = {
                'success': True,
                'order_id': result.get('orderId'),
                'client_order_id': result.get('clientOrderId'),
                'price': Decimal(result.get('price', '0')),
                'quantity': Decimal(result.get('origQty', '0')),
                'status': result.get('status')
            }

            self.log_order(action, quantity, price, order_result)
            return order_result

        except Exception as e:
            self.logger.error(f"Failed to execute limit order: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balance."""
        try:
            result = self._make_request('GET', '/api/v3/account', signed=True)

            balances = {}
            for asset_info in result.get('balances', []):
                asset = asset_info['asset']
                free_balance = Decimal(asset_info['free'])
                locked_balance = Decimal(asset_info['locked'])
                total_balance = free_balance + locked_balance

                if total_balance > 0:  # Only include assets with non-zero balance
                    balances[asset] = {
                        'free': free_balance,
                        'locked': locked_balance,
                        'total': total_balance
                    }

            return balances

        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return {}

    def get_open_positions(self) -> list:
        """Get open positions."""
        # For spot trading, there are no positions like futures
        # Return open orders instead
        try:
            symbol = self.pair_config.pair_symbol
            params = {'symbol': symbol}
            result = self._make_request('GET', '/api/v3/openOrders', params, signed=True)
            return result
        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            return []

    def get_ticker_price(self):
        """Get current ticker price."""
        try:
            symbol = self.pair_config.pair_symbol
            result = self._make_request('GET', f'/api/v3/ticker/price', {'symbol': symbol})
            return result
        except Exception as e:
            self.logger.error(f"Failed to get ticker price: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancel an existing order."""
        try:
            symbol = self.pair_config.pair_symbol
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            result = self._make_request('DELETE', '/api/v3/order', params, signed=True)
            return result
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return None