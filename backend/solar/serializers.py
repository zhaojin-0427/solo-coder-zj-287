from rest_framework import serializers
from .models import (
    Inverter, SolarPanelGroup, DailyGeneration, HouseholdUsage,
    ElectricityPrice, RevenueRecord, HealthDiagnosis,
    StorageBattery, StorageSchedule, CleaningPlan
)


class InverterSerializer(serializers.ModelSerializer):
    panel_group_count = serializers.SerializerMethodField()

    class Meta:
        model = Inverter
        fields = '__all__'

    def get_panel_group_count(self, obj):
        return obj.panel_groups.count()


class SolarPanelGroupSerializer(serializers.ModelSerializer):
    inverter_name = serializers.CharField(source='inverter.__str__', read_only=True, default='')
    total_generation = serializers.SerializerMethodField()
    days_online = serializers.SerializerMethodField()

    class Meta:
        model = SolarPanelGroup
        fields = '__all__'

    def get_total_generation(self, obj):
        records = obj.daily_records.all()
        return sum(r.actual_kwh for r in records) if records else 0

    def get_days_online(self, obj):
        from datetime import date
        return (date.today() - obj.grid_date).days if obj.grid_date else 0


class DailyGenerationSerializer(serializers.ModelSerializer):
    panel_group_name = serializers.CharField(source='panel_group.name', read_only=True)

    class Meta:
        model = DailyGeneration
        fields = '__all__'


class HouseholdUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseholdUsage
        fields = '__all__'


class ElectricityPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricityPrice
        fields = '__all__'


class RevenueRecordSerializer(serializers.ModelSerializer):
    panel_group_name = serializers.CharField(source='panel_group.name', read_only=True)

    class Meta:
        model = RevenueRecord
        fields = '__all__'


class HealthDiagnosisSerializer(serializers.ModelSerializer):
    device_display_name = serializers.SerializerMethodField()
    anomaly_level_display = serializers.SerializerMethodField()
    anomaly_type_display = serializers.SerializerMethodField()

    class Meta:
        model = HealthDiagnosis
        fields = '__all__'

    def get_device_display_name(self, obj):
        return obj.device_name or f'{obj.get_device_type_display()} #{obj.device_id}'

    def get_anomaly_level_display(self, obj):
        return obj.get_anomaly_level_display()

    def get_anomaly_type_display(self, obj):
        return obj.get_anomaly_type_display()


class StorageBatterySerializer(serializers.ModelSerializer):
    panel_group_names = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_capacity_display = serializers.SerializerMethodField()
    days_enabled = serializers.SerializerMethodField()

    class Meta:
        model = StorageBattery
        fields = '__all__'

    def get_panel_group_names(self, obj):
        return [pg.name for pg in obj.panel_groups.all()]

    def get_total_capacity_display(self, obj):
        return f'{obj.capacity_kwh} kWh'

    def get_days_enabled(self, obj):
        from datetime import date
        return (date.today() - obj.enable_date).days if obj.enable_date else 0


class StorageScheduleSerializer(serializers.ModelSerializer):
    battery_name = serializers.CharField(source='battery.name', read_only=True)
    battery_capacity = serializers.FloatField(source='battery.capacity_kwh', read_only=True)

    class Meta:
        model = StorageSchedule
        fields = '__all__'


class CleaningPlanSerializer(serializers.ModelSerializer):
    panel_group_name = serializers.CharField(source='panel_group.name', read_only=True)
    panel_group_capacity = serializers.FloatField(source='panel_group.capacity_kw', read_only=True)
    cleaning_method_display = serializers.CharField(source='get_cleaning_method_display', read_only=True)
    effectiveness_level_display = serializers.CharField(source='get_effectiveness_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CleaningPlan
        fields = '__all__'
