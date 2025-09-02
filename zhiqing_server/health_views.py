"""
健康检查视图
用于Docker容器健康检查和监控
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis
import os
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    健康检查端点
    检查数据库连接、Redis连接等关键服务状态
    """
    health_status = {
        'status': 'healthy',
        'services': {},
        'timestamp': None
    }
    
    from datetime import datetime
    health_status['timestamp'] = datetime.now().isoformat()
    
    # 检查数据库连接
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status['services']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
    except Exception as e:
        health_status['services']['database'] = {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }
        health_status['status'] = 'unhealthy'
        logger.error(f"Database health check failed: {e}")
    
    # 检查Redis连接
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        r.ping()
        health_status['services']['redis'] = {
            'status': 'healthy',
            'message': 'Redis connection successful'
        }
    except Exception as e:
        health_status['services']['redis'] = {
            'status': 'unhealthy',
            'message': f'Redis connection failed: {str(e)}'
        }
        health_status['status'] = 'unhealthy'
        logger.error(f"Redis health check failed: {e}")
    
    # 检查缓存
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['services']['cache'] = {
                'status': 'healthy',
                'message': 'Cache system working'
            }
        else:
            health_status['services']['cache'] = {
                'status': 'unhealthy',
                'message': 'Cache system not working properly'
            }
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['services']['cache'] = {
            'status': 'unhealthy',
            'message': f'Cache system failed: {str(e)}'
        }
        health_status['status'] = 'unhealthy'
        logger.error(f"Cache health check failed: {e}")
    
    # 检查媒体目录
    try:
        from django.conf import settings
        import os
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root) and os.access(media_root, os.W_OK):
            health_status['services']['media'] = {
                'status': 'healthy',
                'message': 'Media directory accessible'
            }
        else:
            health_status['services']['media'] = {
                'status': 'unhealthy',
                'message': 'Media directory not accessible'
            }
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['services']['media'] = {
            'status': 'unhealthy',
            'message': f'Media directory check failed: {str(e)}'
        }
        health_status['status'] = 'unhealthy'
        logger.error(f"Media directory health check failed: {e}")
    
    # 根据整体状态返回相应的HTTP状态码
    if health_status['status'] == 'healthy':
        return JsonResponse(health_status, status=200)
    else:
        return JsonResponse(health_status, status=503)


def simple_health_check(request):
    """
    简单的健康检查端点
    仅返回基本状态信息，用于快速检查
    """
    from datetime import datetime
    return JsonResponse({
        'status': 'ok',
        'message': 'Service is running',
        'timestamp': datetime.now().isoformat()
    })
