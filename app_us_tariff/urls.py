from django.urls import path
from app_us_tariff import views

app_name="app_us_tariff"

urlpatterns = [

    path('', views.home, name='home'),
    

]
