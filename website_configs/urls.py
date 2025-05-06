from django.contrib import admin
from django.urls import path
from django.urls import include

urlpatterns = [
    # top keywords
    path('topword/', include('app_top_keyword.urls')),
    path('', include('app_top_keyword.urls')),
    
    # app top persons
    path('topperson/', include('app_top_person.urls')),
    # user keyword analysis
    path('userkeyword/', include('app_user_keyword.urls')),
    
    path('trump/', include('app_voice_trump.urls')),

    # full text search and associated keyword display
    path('userkeyword_assoc/', include('app_user_keyword_association.urls')),
    
    path('app_us_tariff/', include('app_us_tariff.urls')),

    # user keyword sentiment 
    path('userkeyword_senti/', include('app_user_keyword_sentiment.urls')),

    path('personmayor/', include('app_person_mayor.urls')),

    # full text search and associated keyword display using db
    path('userkeyword_db/', include('app_user_keyword_db.urls')),

    # admin 後台資料庫管理
    path('admin/', admin.site.urls),

    # full text search and associated keyword display using db
    path('topperson_db/', include('app_top_person_db.urls')),

]
