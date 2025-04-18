from django.contrib import admin
from django.urls import path
from django.urls import include

urlpatterns = [
    # top keywords
    path('topword/', include('app_top_keyword.urls')),
    # app top persons
    path('topperson/', include('app_top_person.urls')),
    # user keyword analysis
    path('userkeyword/', include('app_user_keyword.urls')),
    
    path('trump/', include('app_voice_trump.urls')),

    # full text search and associated keyword display
    path('userkeyword_assoc/', include('app_user_keyword_association.urls')),
    
    path('app_us_tariff/', include('app_us_tariff.urls')),

]
