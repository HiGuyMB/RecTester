"""RecTester URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from recapp import views

router = routers.DefaultRouter()
router.register('submissions', views.SubmissionViewSet, basename='submission')
router.register('pending_submissions/(?P<os>[a-z_0-9-]+)', views.PendingSubmissionViewSet, basename='pending_submissions')
router.register('submissions/(?P<submission_id>[0-9]+)/runs', views.RunViewSet)
router.register('users', views.UserViewSet)
router.register('groups', views.GroupViewSet)

urlpatterns = [
    path('', include('recapp.urls'), name='app'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls), name='api'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-auth-token/', obtain_auth_token),
]
