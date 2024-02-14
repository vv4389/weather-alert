from django.urls import path
from myapp import views

urlpatterns = [
    path('', views.index, name='index'),  # Mapping for the root URL to the index view
    path('remove_subscription/', views.remove_subscription, name='remove_subscription'),

]
