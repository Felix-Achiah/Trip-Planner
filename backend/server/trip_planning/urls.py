# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'trips', views.TripViewSet)
router.register(r'routes', views.RouteViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'waypoints', views.WaypointViewSet)
router.register(r'log-entries', views.LogEntryViewSet)
router.register(r'daily-logs', views.DailyLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]