"""
Middleware for subscription system security and rate limiting.
"""
import time
import json
import logging
from django.http import JsonResponse, HttpResponseTooManyRequests
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .utils import log_webhook_request

# Configure logging
webhook_logger = logging.getLogger('webhooks')


class WebhookRateLimitMiddleware:
    """
    Middleware to enforce rate limiting on webhook endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('webhooks')

    def __call__(self, request):
        # Check if this is a webhook endpoint
        if '/api/custom-bot/webhook/receive/' in request.path:
            webhook_secret = self._extract_webhook_secret(request.path)

            if webhook_secret:
                # Check rate limiting
                if not self._check_rate_limit(request, webhook_secret):
                    response = JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': 60
                    }, status=429)

                    # Add rate limit headers
                    response['Retry-After'] = '60'
                    response['X-RateLimit-Limit'] = str(getattr(settings, 'WEBHOOK_RATE_LIMIT', 10))
                    response['X-RateLimit-Remaining'] = '0'
                    response['X-RateLimit-Reset'] = str(int(time.time()) + 60)

                    # Log rate limit violation
                    self._log_rate_limit_violation(request, webhook_secret)

                    return response

                # Log the request
                log_webhook_request(request, webhook_secret, 200)

        response = self.get_response(request)

        return response

    def _extract_webhook_secret(self, path):
        """Extract webhook secret from URL path."""
        try:
            parts = path.strip('/').split('/')
            if len(parts) >= 5 and parts[0] == 'api' and parts[1] == 'custom-bot' and parts[2] == 'webhook' and parts[3] == 'receive':
                return parts[4]
        except (IndexError, AttributeError):
            pass
        return None

    def _check_rate_limit(self, request, webhook_secret):
        """Check if the webhook is within rate limits."""
        rate_limit = getattr(settings, 'WEBHOOK_RATE_LIMIT', 10)  # requests per minute
        window_seconds = 60  # 1 minute window

        cache_key = f"webhook_rate_limit:{webhook_secret}"
        current_time = time.time()

        # Get current requests from cache
        requests = cache.get(cache_key, [])

        # Remove old requests outside the time window
        requests = [req_time for req_time in requests if current_time - req_time < window_seconds]

        # Check if rate limit exceeded
        if len(requests) >= rate_limit:
            return False

        # Add current request
        requests.append(current_time)

        # Update cache with expiration
        cache.set(cache_key, requests, window_seconds)

        return True

    def _log_rate_limit_violation(self, request, webhook_secret):
        """Log rate limit violation."""
        try:
            client_ip = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            self.logger.warning(
                f"Rate limit exceeded for webhook {webhook_secret} from IP {client_ip} "
                f"with User-Agent: {user_agent}"
            )

        except Exception as e:
            self.logger.error(f"Error logging rate limit violation: {e}")

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SubscriptionCheckMiddleware:
    """
    Middleware to check subscription status for protected endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('subscriptions')

    def __call__(self, request):
        # Check if this is a protected endpoint
        if self._is_protected_endpoint(request.path):
            if hasattr(request, 'user') and request.user.is_authenticated:
                if not self._has_valid_subscription(request.user):
                    return JsonResponse({
                        'error': 'Subscription Required',
                        'message': 'This feature requires an active subscription',
                        'subscription_url': '/api/subscription-plans/'
                    }, status=402)

        return self.get_response(request)

    def _is_protected_endpoint(self, path):
        """Check if endpoint requires subscription."""
        protected_patterns = [
            '/api/custom-bot/webhook/generate/',
            '/api/managed-bot/subscribe/',
            '/api/bots/',
            '/api/trading/execute/',
        ]

        for pattern in protected_patterns:
            if path.startswith(pattern):
                return True
        return False

    def _has_valid_subscription(self, user):
        """Check if user has valid subscription."""
        try:
            from .models import UserSubscription

            subscription = UserSubscription.objects.filter(
                user=user,
                status='active',
                end_date__gte=timezone.now()
            ).first()

            return subscription is not None

        except Exception as e:
            self.logger.error(f"Error checking subscription for user {user.id}: {e}")
            return False


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to API responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # Add API-specific headers
        if request.path.startswith('/api/'):
            response['API-Version'] = '1.0.0'
            response['Content-Security-Policy'] = "default-src 'self'"

        return response


class RequestLoggingMiddleware:
    """
    Middleware to log API requests for monitoring and debugging.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('api_requests')

    def __call__(self, request):
        start_time = time.time()

        # Log request details
        request_data = {
            'method': request.method,
            'path': request.path,
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now().isoformat(),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
        }

        # Process request
        response = self.get_response(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Add response details
        request_data.update({
            'status_code': response.status_code,
            'processing_time_ms': round(processing_time * 1000, 2),
            'response_size': len(response.content) if hasattr(response, 'content') else 0
        })

        # Log the request
        self.logger.info(f"API Request: {json.dumps(request_data)}")

        return response

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CORSMiddleware:
    """
    Enhanced CORS middleware for API endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        self.allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
        self.allowed_headers = getattr(settings, 'CORS_ALLOWED_HEADERS', [
            'accept',
            'accept-encoding',
            'authorization',
            'content-type',
            'dnt',
            'origin',
            'user-agent',
            'x-csrftoken',
            'x-requested-with',
        ])

    def __call__(self, request):
        # Only apply CORS to API endpoints
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(request)

        response = self.get_response(request)

        # Add CORS headers to actual response
        self._add_cors_headers(request, response)

        return response

    def _handle_preflight(self, request):
        """Handle CORS preflight requests."""
        response = JsonResponse({'status': 'preflight'}, status=200)
        self._add_cors_headers(request, response)
        response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        return response

    def _add_cors_headers(self, request, response):
        """Add CORS headers to response."""
        origin = request.META.get('HTTP_ORIGIN')

        if self._is_origin_allowed(origin):
            response['Access-Control-Allow-Origin'] = origin

        response['Access-Control-Allow-Credentials'] = 'true'

    def _is_origin_allowed(self, origin):
        """Check if origin is allowed."""
        if not origin:
            return False

        # Check against allowed origins
        for allowed_origin in self.allowed_origins:
            if origin == allowed_origin or allowed_origin == '*':
                return True

        return False


class WebhookSecurityMiddleware:
    """
    Enhanced security middleware specifically for webhook endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('webhook_security')

    def __call__(self, request):
        # Only apply to webhook endpoints
        if '/api/custom-bot/webhook/receive/' in request.path:
            if not self._validate_webhook_security(request):
                return JsonResponse({
                    'error': 'Security validation failed',
                    'message': 'Request blocked by security middleware'
                }, status=403)

        return self.get_response(request)

    def _validate_webhook_security(self, request):
        """Validate webhook security requirements."""
        client_ip = self._get_client_ip(request)

        # Check against blocked IPs
        if self._is_ip_blocked(client_ip):
            self.logger.warning(f"Blocked IP attempted webhook access: {client_ip}")
            return False

        # Check User-Agent (optional but recommended)
        user_agent = request.META.get('HTTP_USER-Agent', '')
        if not self._is_valid_user_agent(user_agent):
            self.logger.warning(f"Invalid User-Agent blocked: {user_agent}")
            return False

        # Check for suspicious headers
        if self._has_suspicious_headers(request):
            self.logger.warning(f"Suspicious headers detected from {client_ip}")
            return False

        return True

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_ip_blocked(self, ip):
        """Check if IP is blocked."""
        # Implement IP blocking logic here
        # This could check against a database, cache, or settings
        blocked_ips = getattr(settings, 'BLOCKED_IPS', [])
        return ip in blocked_ips

    def _is_valid_user_agent(self, user_agent):
        """Validate User-Agent string."""
        if not user_agent:
            return False

        # Block common bot User-Agents that shouldn't be hitting webhooks
        blocked_agents = ['curl', 'wget', 'python-requests', 'scanner', 'bot']
        user_agent_lower = user_agent.lower()

        for blocked_agent in blocked_agents:
            if blocked_agent in user_agent_lower:
                # Allow TradingView User-Agent specifically
                if 'tradingview' in user_agent_lower:
                    return True
                return False

        return True

    def _has_suspicious_headers(self, request):
        """Check for suspicious request headers."""
        suspicious_patterns = [
            'x-forwarded-for',  # Might indicate proxy/VPN abuse
            'x-real-ip',         # Another proxy indicator
        ]

        # This is a simplified check - in production, you'd want more sophisticated detection
        for pattern in suspicious_patterns:
            if pattern in request.META:
                # Not automatically suspicious, but worth logging
                self.logger.info(f"Suspicious header '{pattern}' detected from {self._get_client_ip(request)}")

        return False