from django.urls import path
from app import views

urlpatterns = [
    path('',views.index,name="index"),
    path('wealth_building/',views.wealth_building,name="wealth_building"),
    path('fetch_data/',views.fetch_data,name="fetch_data"),
    path('download_file/',views.download_file,name="download_file"),
]