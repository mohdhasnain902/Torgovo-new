"""
URL configuration for Torgovo_new - Crypto Trading Bot Platform.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'Torgovo_new',
        'version': '1.0.0'
    })

@require_http_methods(["GET"])
def api_info(request):
    """API information endpoint."""
    return JsonResponse({
        'name': 'Torgovo_new API',
        'version': '1.0.0',
        'endpoints': {
            'subscription-plans': '/api/subscription-plans/',
            'subscriptions': '/api/subscriptions/',
            'custom-bot-webhook': '/api/custom-bot/webhook/',
            'managed-bot': '/api/managed-bot/',
            'trading': '/api/trading/',
        },
        'authentication': 'Token-based',
        'documentation': '/api/docs/'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/', api_info, name='api_info'),
    path('api/auth/', include('rest_framework.urls')),
    path('api/subscription-plans/', include('subscriptions.urls.subscription_plans')),
    path('api/subscriptions/', include('subscriptions.urls.user_subscriptions')),
    path('api/custom-bot/webhook/', include('subscriptions.urls.custom_bot_webhook')),
    path('api/managed-bot/', include('subscriptions.urls.managed_bot')),
    path('api/users/', include('users.urls')),
    path('api/trading/', include('trading.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Include debug toolbar URLs if available
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns