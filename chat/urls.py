from django.urls import path
from .views import CeaBot_API

urlpatterns = [
    path('chatbot/',CeaBot_API.as_view(),name='chatbot'),
]