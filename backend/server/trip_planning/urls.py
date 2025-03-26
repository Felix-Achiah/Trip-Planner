from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'waypoints', views.WaypointViewSet, basename='waypoint')
router.register(r'log-entries', views.LogEntryViewSet, basename='logentry')
router.register(r'daily-logs', views.DailyLogViewSet, basename='dailylog')

urlpatterns = [
    path('', include(router.urls)),
]