from django.urls import path
from . import views

app_name='app_person_mayor'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_person_mayor_data/', views.api_get_person_mayor_data),
]
