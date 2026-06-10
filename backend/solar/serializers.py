from rest_framework import serializers
from .models import Inverter, SolarPanelGroup, DailyGeneration, HouseholdUsage, ElectricityPrice, RevenueRecord


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
