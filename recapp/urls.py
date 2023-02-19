from django.urls import path

from . import views

app_name = 'recapp'
urlpatterns = [
    path('', views.index, name='index'),
    path('newest', views.newest, name='newest'),
    path('compare/<str:os1>/<str:os2>', views.compare, name='compare'),
    path('discrepancies', views.discrepancies, name='discrepancies'),
    path('best', views.best, name='best'),
    path('worst', views.worst, name='worst'),
    path('submissions', views.index),
    path('submissions/<int:pk>', views.detail, name='detail'),
    path('submissions/<int:pk>/download', views.download, name='download'),
    path('upload/', views.upload, name='upload')
]
