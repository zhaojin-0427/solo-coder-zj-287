from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from solar.views import (
    InverterViewSet, SolarPanelGroupViewSet, DailyGenerationViewSet,
    HouseholdUsageViewSet, ElectricityPriceViewSet, RevenueRecordViewSet,
    import_generation_data, calculate_revenue, dashboard, statistics,
    payback_prediction, seed_demo_data
)

router = DefaultRouter()
router.register(r'inverters', InverterViewSet)
router.register(r'panel-groups', SolarPanelGroupViewSet)
router.register(r'daily-generation', DailyGenerationViewSet)
router.register(r'household-usage', HouseholdUsageViewSet)
router.register(r'electricity-prices', ElectricityPriceViewSet)
router.register(r'revenue-records', RevenueRecordViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/import-generation/', import_generation_data),
    path('api/calculate-revenue/', calculate_revenue),
    path('api/dashboard/', dashboard),
    path('api/statistics/', statistics),
    path('api/payback-prediction/', payback_prediction),
    path('api/seed-demo/', seed_demo_data),
]
