from django.urls import path
from app import views

urlpatterns = [
    # path('',views.index,name="index"),
    path('',views.wealth_building,name="wealth_building"),
    path('crypto_analysis_api/',views.index,name="crypto"),
    path('fetch_data/',views.fetch_data,name="fetch_data"),
    path('download_file/',views.download_file,name="download_file"),
]