from datetime import date, timedelta, datetime
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import (
    Inverter, SolarPanelGroup, DailyGeneration, HouseholdUsage,
    ElectricityPrice, RevenueRecord, HealthDiagnosis,
    StorageBattery, StorageSchedule, CleaningPlan
)
from .serializers import (
    InverterSerializer, SolarPanelGroupSerializer, DailyGenerationSerializer,
    HouseholdUsageSerializer, ElectricityPriceSerializer, RevenueRecordSerializer,
    HealthDiagnosisSerializer,
    StorageBatterySerializer, StorageScheduleSerializer,
    CleaningPlanSerializer, DailyGenerationSerializer as DailyGenSerializer
)
from .utils.pagination import StandardResultsSetPagination, apply_date_filters, apply_panel_group_filter

from .services.generation_service import (
    calc_theoretical_kwh, calc_revenue_for_date,
    import_generation_item, get_electricity_prices
)
from .services.health_service import (
    generate_diagnosis_for_date, generate_diagnosis_for_date_range,
    generate_diagnosis_for_panel_group, generate_diagnosis_for_inverter
)
from .services.storage_service import (
    calculate_storage_schedule, calculate_storage_schedule_for_date,
    calculate_storage_schedule_for_range
)
from .services.cleaning_service import evaluate_cleaning_effect
from .services.statistics_service import (
    get_dashboard_data, get_statistics_data, get_payback_prediction,
    get_alert_summary, get_storage_summary, get_cleaning_summary
)


class InverterViewSet(viewsets.ModelViewSet):
    queryset = Inverter.objects.all()
    serializer_class = InverterSerializer

    @action(detail=True, methods=['post'], url_path='fetch-data')
    def fetch_data(self, request, pk=None):
        inverter = self.get_object()
        if not inverter.api_endpoint:
            return Response({'error': 'No API endpoint configured'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Inverter API integration placeholder', 'inverter': inverter.model})


class SolarPanelGroupViewSet(viewsets.ModelViewSet):
    queryset = SolarPanelGroup.objects.all()
    serializer_class = SolarPanelGroupSerializer


class DailyGenerationViewSet(viewsets.ModelViewSet):
    queryset = DailyGeneration.objects.all()
    serializer_class = DailyGenerationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_panel_group_filter(qs, self.request.query_params)
        qs = apply_date_filters(qs, self.request.query_params, 'date')
        return qs


class HouseholdUsageViewSet(viewsets.ModelViewSet):
    queryset = HouseholdUsage.objects.all()
    serializer_class = HouseholdUsageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_date_filters(qs, self.request.query_params, 'date')
        return qs


class ElectricityPriceViewSet(viewsets.ModelViewSet):
    queryset = ElectricityPrice.objects.all()
    serializer_class = ElectricityPriceSerializer


class RevenueRecordViewSet(viewsets.ModelViewSet):
    queryset = RevenueRecord.objects.all()
    serializer_class = RevenueRecordSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_panel_group_filter(qs, self.request.query_params)
        qs = apply_date_filters(qs, self.request.query_params, 'date')
        return qs


class HealthDiagnosisViewSet(viewsets.ModelViewSet):
    queryset = HealthDiagnosis.objects.all()
    serializer_class = HealthDiagnosisSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        anomaly_level = params.get('anomaly_level')
        device_type = params.get('device_type')
        device_id = params.get('device_id')
        is_handled = params.get('is_handled')
        include_normal = params.get('include_normal')

        if self.action == 'list':
            if anomaly_level:
                qs = qs.filter(anomaly_level=anomaly_level)
            else:
                if include_normal is None or include_normal.lower() not in ('true', '1', 'yes'):
                    qs = qs.exclude(anomaly_level='normal')

            if is_handled is not None and is_handled != '':
                handled_bool = is_handled.lower() in ('true', '1', 'yes')
                if handled_bool:
                    qs = qs.filter(is_handled=True)
                else:
                    qs = qs.filter(is_handled=False).exclude(anomaly_level='normal')

        if device_type:
            qs = qs.filter(device_type=device_type)
        if device_id:
            qs = qs.filter(device_id=device_id)
        qs = apply_date_filters(qs, params, 'date')
        return qs

    @action(detail=True, methods=['post'], url_path='mark-handled')
    def mark_handled(self, request, pk=None):
        obj = self.get_object()
        if obj.anomaly_level == 'normal':
            return Response(
                {'error': '正常记录无需标记处理'},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj.is_handled = True
        obj.handled_at = timezone.now()
        obj.save()
        return Response(HealthDiagnosisSerializer(obj).data)


@api_view(['POST'])
def import_generation_data(request):
    data = request.data
    dates_to_calc = set()
    dates_to_diagnose = set()

    if isinstance(data, list):
        results = []
        for item in data:
            obj = import_generation_item(item)
            if obj:
                results.append(DailyGenSerializer(obj).data)
                dt = item.get('date')
                if dt:
                    dates_to_calc.add(dt)
                    dates_to_diagnose.add(dt)
        for dt in dates_to_calc:
            calc_revenue_for_date(dt)
        for dt in dates_to_diagnose:
            generate_diagnosis_for_date(dt)
        for dt in dates_to_calc:
            calculate_storage_schedule_for_date(dt)
        return Response(results, status=status.HTTP_201_CREATED)
    else:
        obj = import_generation_item(data)
        if not obj:
            return Response({'error': 'Panel group not found'}, status=status.HTTP_404_NOT_FOUND)
        dt = data.get('date')
        if dt:
            calc_revenue_for_date(dt)
            generate_diagnosis_for_date(dt)
            calculate_storage_schedule_for_date(dt)
        return Response(DailyGenSerializer(obj).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def calculate_revenue(request):
    dt = request.data.get('date')
    if not dt:
        return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)

    results = calc_revenue_for_date(dt)
    return Response(results)


@api_view(['GET'])
def dashboard(request):
    return Response(get_dashboard_data())


@api_view(['GET'])
def statistics(request):
    months_param = int(request.query_params.get('months', 12))
    return Response(get_statistics_data(months_param))


@api_view(['GET'])
def payback_prediction(request):
    return Response(get_payback_prediction())


@api_view(['POST'])
def seed_demo_data(request):
    import random

    inv, _ = Inverter.objects.get_or_create(
        brand='华为', model='SUN2000-6KTL',
        defaults={'rated_power': 6.0, 'efficiency': 98.6, 'api_endpoint': '', 'api_key': ''}
    )
    inv2, _ = Inverter.objects.get_or_create(
        brand='阳光电源', model='SG5KTL-D',
        defaults={'rated_power': 5.0, 'efficiency': 98.0, 'api_endpoint': '', 'api_key': ''}
    )

    pg1, _ = SolarPanelGroup.objects.get_or_create(
        name='屋顶南侧A组', defaults={
            'capacity_kw': 5.5, 'install_angle': 30, 'azimuth': 180,
            'inverter': inv, 'grid_date': date(2025, 3, 15), 'location': '上海'
        }
    )
    pg2, _ = SolarPanelGroup.objects.get_or_create(
        name='屋顶东侧B组', defaults={
            'capacity_kw': 3.0, 'install_angle': 25, 'azimuth': 135,
            'inverter': inv2, 'grid_date': date(2025, 6, 1), 'location': '上海'
        }
    )

    ElectricityPrice.objects.get_or_create(
        price_type='grid_buy_peak', effective_date=date(2025, 1, 1),
        defaults={'price': 0.85}
    )
    ElectricityPrice.objects.get_or_create(
        price_type='grid_buy_valley', effective_date=date(2025, 1, 1),
        defaults={'price': 0.38}
    )
    ElectricityPrice.objects.get_or_create(
        price_type='grid_buy_shoulder', effective_date=date(2025, 1, 1),
        defaults={'price': 0.55}
    )
    ElectricityPrice.objects.get_or_create(
        price_type='grid_sell', effective_date=date(2025, 1, 1),
        defaults={'price': 0.45}
    )

    today = date.today()
    for i in range(90, 0, -1):
        d = today - timedelta(days=i)
        month = d.month
        for pg in [pg1, pg2]:
            theo = calc_theoretical_kwh(pg.capacity_kw, pg.install_angle, month, pg.inverter.efficiency if pg.inverter else 98.0)
            weather_factor = random.uniform(0.65, 1.05)
            actual = round(theo * weather_factor, 2)
            sunshine = 0
            from .services.generation_service import AVERAGE_SUNSHINE_HOURS
            sunshine = AVERAGE_SUNSHINE_HOURS.get(month, 6.0) * random.uniform(0.8, 1.1)
            DailyGeneration.objects.update_or_create(
                panel_group=pg, date=d,
                defaults={
                    'actual_kwh': actual,
                    'theoretical_kwh': theo,
                    'sunshine_hours': round(sunshine, 1),
                    'peak_kwh': round(actual * 0.6, 2),
                    'valley_kwh': round(actual * 0.4, 2),
                }
            )

        total_gen = sum(DailyGeneration.objects.filter(date=d).values_list('actual_kwh', flat=True))
        household_total = round(random.uniform(8, 18), 2)
        self_use = round(min(total_gen * random.uniform(0.3, 0.5), household_total), 2)
        grid_buy = round(max(household_total - self_use, 0), 2)
        grid_sell = round(max(total_gen - self_use, 0), 2)
        HouseholdUsage.objects.update_or_create(
            date=d,
            defaults={
                'total_kwh': household_total,
                'peak_kwh': round(household_total * 0.6, 2),
                'valley_kwh': round(household_total * 0.25, 2),
                'shoulder_kwh': round(household_total * 0.15, 2),
                'self_use_kwh': self_use,
                'grid_buy_kwh': grid_buy,
                'grid_sell_kwh': grid_sell,
            }
        )

    for i in range(90, 0, -1):
        d = today - timedelta(days=i)
        for pg in [pg1, pg2]:
            try:
                gen = DailyGeneration.objects.get(panel_group=pg, date=d)
                usage = HouseholdUsage.objects.get(date=d)
                self_use_ratio = random.uniform(0.35, 0.5)
                self_use_kwh = round(gen.actual_kwh * self_use_ratio, 2)
                grid_sell_kwh = round(gen.actual_kwh - self_use_kwh, 2)
                self_use_saving = round(self_use_kwh * 0.6 * 0.85 + self_use_kwh * 0.4 * 0.38, 2)
                grid_sell_income = round(grid_sell_kwh * 0.45, 2)
                total_income = round(self_use_saving + grid_sell_income, 2)
                RevenueRecord.objects.update_or_create(
                    date=d, panel_group=pg,
                    defaults={
                        'generation_kwh': gen.actual_kwh,
                        'self_use_kwh': self_use_kwh,
                        'grid_sell_kwh': grid_sell_kwh,
                        'self_use_saving': self_use_saving,
                        'grid_sell_income': grid_sell_income,
                        'total_income': total_income,
                    }
                )
            except (DailyGeneration.DoesNotExist, HouseholdUsage.DoesNotExist):
                pass

    for i in range(90, 0, -1):
        d = today - timedelta(days=i)
        generate_diagnosis_for_date(d)

    bat1, _ = StorageBattery.objects.get_or_create(
        name='家庭储能主电池', defaults={
            'brand': '宁德时代', 'model': 'EVE-10kWh',
            'capacity_kwh': 10.0,
            'max_charge_power_kw': 3.0,
            'max_discharge_power_kw': 3.0,
            'charge_efficiency': 95,
            'discharge_efficiency': 95,
            'soc_upper_limit': 90,
            'soc_lower_limit': 15,
            'enable_date': date(2025, 6, 1),
            'current_soc': 55,
            'status': 'normal',
            'warning_message': '',
        }
    )
    bat1.panel_groups.set([pg1, pg2])

    bat2, _ = StorageBattery.objects.get_or_create(
        name='备用储能电池', defaults={
            'brand': '比亚迪', 'model': 'Blade-5kWh',
            'capacity_kwh': 5.0,
            'max_charge_power_kw': 2.0,
            'max_discharge_power_kw': 2.0,
            'charge_efficiency': 94,
            'discharge_efficiency': 94,
            'soc_upper_limit': 88,
            'soc_lower_limit': 20,
            'enable_date': date(2025, 7, 15),
            'current_soc': 40,
            'status': 'normal',
            'warning_message': '',
        }
    )
    bat2.panel_groups.set([pg1])

    earliest_enable = min(bat1.enable_date, bat2.enable_date)
    start_date = max(earliest_enable, today - timedelta(days=90))
    calculate_storage_schedule_for_range(start_date, today)

    cleaning_methods = ['manual', 'water', 'dry', 'robot']
    operators = ['张三', '李四', '王五', '清洁服务公司']
    plan_names = ['季度常规清洁', '灰尘严重清洁', '雨季前清洁', '例行维护清洁']

    for i, pg in enumerate([pg1, pg2]):
        for j in range(3):
            offset_days = 20 + j * 25 + i * 5
            plan_dt = today - timedelta(days=offset_days)
            actual_dt = plan_dt
            method = cleaning_methods[j % len(cleaning_methods)]
            cost = 50 + j * 30 + i * 20

            plan = CleaningPlan.objects.create(
                panel_group=pg,
                plan_name=plan_names[j % len(plan_names)],
                cleaning_method=method,
                estimated_cost=cost,
                actual_cost=cost + random.randint(-10, 15),
                operator=operators[(i + j) % len(operators)],
                plan_date=plan_dt,
                actual_date=actual_dt,
                status='completed',
                notes='定期清洁，组件表面灰尘较多'
            )
            eval_result = evaluate_cleaning_effect(plan)
            if eval_result:
                for key, value in eval_result.items():
                    setattr(plan, key, value)
                plan.save()

        future_offset = 5 + i * 8
        CleaningPlan.objects.create(
            panel_group=pg,
            plan_name='下月常规清洁',
            cleaning_method='water',
            estimated_cost=80,
            operator='清洁服务公司',
            plan_date=today + timedelta(days=future_offset),
            status='pending',
            notes='预约下月初进行清洁'
        )

    return Response({'message': 'Demo data seeded successfully'})


@api_view(['POST'])
def generate_diagnosis(request):
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    if not date_from or not date_to:
        return Response({'error': 'date_from and date_to are required'}, status=status.HTTP_400_BAD_REQUEST)
    start = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
    end = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
    generate_diagnosis_for_date_range(start, end)
    return Response({'message': 'Diagnosis generated successfully'})


@api_view(['GET'])
def alert_summary(request):
    return Response(get_alert_summary())


class StorageBatteryViewSet(viewsets.ModelViewSet):
    queryset = StorageBattery.objects.all()
    serializer_class = StorageBatterySerializer

    @action(detail=True, methods=['post'], url_path='recalculate')
    def recalculate(self, request, pk=None):
        battery = self.get_object()
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        if not date_from or not date_to:
            return Response(
                {'error': 'date_from and date_to are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        start = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
        end = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
        results = []
        current = start
        while current <= end:
            if battery.enable_date <= current and battery.status != 'maintenance':
                obj = calculate_storage_schedule(battery, current)
                results.append(StorageScheduleSerializer(obj).data)
            current += timedelta(days=1)
        return Response({'recalculated': len(results), 'results': results})


class StorageScheduleViewSet(viewsets.ModelViewSet):
    queryset = StorageSchedule.objects.all()
    serializer_class = StorageScheduleSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        battery_id = params.get('battery')
        if battery_id:
            qs = qs.filter(battery_id=battery_id)
        qs = apply_date_filters(qs, params, 'date')
        return qs


@api_view(['POST'])
def calculate_storage(request):
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    battery_id = request.data.get('battery_id')
    if not date_from or not date_to:
        return Response(
            {'error': 'date_from and date_to are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    start = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
    end = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to

    results = []
    if battery_id:
        try:
            battery = StorageBattery.objects.get(pk=battery_id)
            current = start
            while current <= end:
                if battery.enable_date <= current and battery.status != 'maintenance':
                    obj = calculate_storage_schedule(battery, current)
                    results.append(StorageScheduleSerializer(obj).data)
                current += timedelta(days=1)
        except StorageBattery.DoesNotExist:
            return Response({'error': 'Battery not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        results = calculate_storage_schedule_for_range(start, end)
    return Response({'calculated': len(results), 'results': results})


@api_view(['GET'])
def storage_summary(request):
    return Response(get_storage_summary())


class CleaningPlanViewSet(viewsets.ModelViewSet):
    queryset = CleaningPlan.objects.all()
    serializer_class = CleaningPlanSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        qs = apply_panel_group_filter(qs, params)
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        status_param = params.get('status')
        effectiveness = params.get('effectiveness')

        if date_from:
            qs = qs.filter(plan_date__gte=date_from)
        if date_to:
            qs = qs.filter(plan_date__lte=date_to)
        if status_param:
            qs = qs.filter(status=status_param)
        if effectiveness:
            qs = qs.filter(effectiveness_level=effectiveness)
        return qs

    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        obj = self.get_object()
        actual_date = request.data.get('actual_date')
        actual_cost = request.data.get('actual_cost')
        operator = request.data.get('operator')
        notes = request.data.get('notes')

        obj.status = 'completed'
        obj.actual_date = actual_date or date.today().isoformat()
        if actual_cost is not None:
            obj.actual_cost = actual_cost
        if operator:
            obj.operator = operator
        if notes:
            obj.notes = notes
        obj.save()

        eval_result = evaluate_cleaning_effect(obj)
        if eval_result:
            for key, value in eval_result.items():
                setattr(obj, key, value)
            obj.save()

        return Response(CleaningPlanSerializer(obj).data)

    @action(detail=True, methods=['post'], url_path='re-evaluate')
    def re_evaluate(self, request, pk=None):
        obj = self.get_object()
        if obj.status != 'completed' or not obj.actual_date:
            return Response(
                {'error': '只有已完成且有实际完成日期的计划才能进行评估'},
                status=status.HTTP_400_BAD_REQUEST
            )
        eval_result = evaluate_cleaning_effect(obj)
        if eval_result:
            for key, value in eval_result.items():
                setattr(obj, key, value)
            obj.save()
        return Response(CleaningPlanSerializer(obj).data)

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        return Response(get_cleaning_summary())
