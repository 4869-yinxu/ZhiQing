"""
URL configuration for open_ragbook_server project.

The `urlpatterns` list routes URLs to api. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function api
    1. Add an import:  from my_app import api
    2. Add a URL to urlpatterns:  path('', api.home, name='home')
Class-based api
    1. Add an import:  from other_app.api import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import health_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/account/', include('account_mgt.urls')),
    path('api/v1/knowledge/', include('knowledge_mgt.urls')),
    path('api/v1/system/', include('system_mgt.urls')),
    path('api/v1/chat/', include('chat_mgt.urls')),
    # 健康检查端点
    path('health/', health_views.health_check, name='health_check'),
    path('health/simple/', health_views.simple_health_check, name='simple_health_check'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
