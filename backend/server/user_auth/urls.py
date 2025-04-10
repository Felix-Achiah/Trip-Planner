from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginView

router = DefaultRouter()
router.register(r'users', UserViewSet)  # Signup

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login')
]
