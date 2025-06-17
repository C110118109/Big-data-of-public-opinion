from django.urls import path
from . import views

app_name = 'app_ai_stock_hype'

urlpatterns = [
    path('', views.home, name='home'),
]