from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.react_app_view, name='home'),
    path('react/', views.react_app_view, name='react_app'),
    path('classic/', views.home_view, name='classic_home'),
    path('about/', views.about_view, name='about'),
]
