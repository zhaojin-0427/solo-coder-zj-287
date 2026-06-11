import math
from datetime import date, timedelta, datetime
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
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
    CleaningPlanSerializer
)

PEAK_HOURS = list(range(8, 12)) + list(range(17, 22))
VALLEY_HOURS = list(range(0, 6)) + list(range(22, 24))
SHOULDER_HOURS = [h for h in range(24) if h not in PEAK_HOURS and h not in VALLEY_HOURS]

SOLAR_GENERATION_PROFILE = [
    0, 0, 0, 0, 0, 0.01, 0.05, 0.12,
    0.22, 0.35, 0.55, 0.72, 0.85, 0.92, 0.95, 0.90,
    0.78, 0.60, 0.40, 0.22, 0.10, 0.04, 0.01, 0
]

HOUSEHOLD_USAGE_PROFILE = [
    0.02, 0.015, 0.01, 0.01, 0.01, 0.015, 0.03, 0.05,
    0.06, 0.04, 0.035, 0.04, 0.05, 0.04, 0.035, 0.04,
    0.05, 0.07, 0.08, 0.09, 0.08, 0.06, 0.04, 0.025
]


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


SEASONAL_COEFFICIENTS = {
    1: 0.55, 2: 0.60, 3: 0.75, 4: 0.85, 5: 0.95, 6: 1.05,
    7: 1.10, 8: 1.05, 9: 0.90, 10: 0.78, 11: 0.60, 12: 0.50
}

AVERAGE_SUNSHINE_HOURS = {
    1: 4.5, 2: 5.0, 3: 5.8, 4: 6.5, 5: 7.2, 6: 7.5,
    7: 7.8, 8: 7.3, 9: 6.5, 10: 5.8, 11: 4.8, 12: 4.2
}

ANGLE_EFFICIENCY_TABLE = [
    (0, 0.85), (10, 0.90), (15, 0.93), (20, 0.96), (25, 0.98),
    (30, 1.00), (35, 0.99), (40, 0.97), (45, 0.94), (50, 0.90),
    (60, 0.82), (70, 0.72), (80, 0.60), (90, 0.45)
]


def get_angle_efficiency(angle):
    for i in range(len(ANGLE_EFFICIENCY_TABLE) - 1):
        a1, e1 = ANGLE_EFFICIENCY_TABLE[i]
        a2, e2 = ANGLE_EFFICIENCY_TABLE[i + 1]
        if a1 <= angle <= a2:
            t = (angle - a1) / (a2 - a1) if a2 != a1 else 0
            return e1 + t * (e2 - e1)
    if angle > 90:
        return 0.45 * (1 - (angle - 90) / 90)
    return 0.85


def calc_theoretical_kwh(capacity_kw, angle, month, inverter_efficiency=0.98):
    season_coeff = SEASONAL_COEFFICIENTS.get(month, 1.0)
    sunshine = AVERAGE_SUNSHINE_HOURS.get(month, 6.0)
    angle_eff = get_angle_efficiency(angle)
    inverter_eff = inverter_efficiency / 100.0
    theoretical = capacity_kw * sunshine * season_coeff * angle_eff * inverter_eff
    return round(theoretical, 2)


def generate_diagnosis_for_panel_group(pg, target_date):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    try:
        gen = DailyGeneration.objects.get(panel_group=pg, date=target_date)
    except DailyGeneration.DoesNotExist:
        return None

    deviation_rate = 0
    if gen.theoretical_kwh > 0:
        deviation_rate = round((gen.theoretical_kwh - gen.actual_kwh) / gen.theoretical_kwh * 100, 1)
    else:
        deviation_rate = 0

    inverter_eff = pg.inverter.efficiency if pg.inverter else 98.0

    consecutive_low_days = 0
    check_date = target_date
    while True:
        try:
            prev_gen = DailyGeneration.objects.get(panel_group=pg, date=check_date)
            if prev_gen.theoretical_kwh > 0 and prev_gen.actual_kwh / prev_gen.theoretical_kwh < 0.7:
                consecutive_low_days += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        except DailyGeneration.DoesNotExist:
            break

    grid_days = (target_date - pg.grid_date).days if pg.grid_date else 0

    peak_valley_ratio = 0
    if gen.valley_kwh > 0:
        peak_valley_ratio = round(gen.peak_kwh / gen.valley_kwh, 2)
    elif gen.peak_kwh > 0:
        peak_valley_ratio = 99.0

    health_score = 100
    anomaly_type = 'none'
    anomaly_level = 'normal'
    possible_cause = ''
    handling_suggestion = ''

    if deviation_rate > 50:
        health_score -= 40
        anomaly_type = 'deviation_high'
        anomaly_level = 'critical'
        possible_cause = '实际发电量与理论发电量偏差超过50%，可能存在组件严重遮挡、故障或线路问题。'
        handling_suggestion = '立即现场检查光伏组件表面是否有遮挡物、检查接线盒和线缆连接是否正常，必要时联系运维人员。'
    elif deviation_rate > 35:
        health_score -= 25
        anomaly_type = 'low_generation'
        anomaly_level = 'high'
        possible_cause = '发电量偏低，偏差35%-50%，可能存在部分组件遮挡、积灰或轻微故障。'
        handling_suggestion = '检查组件表面清洁度，排查是否存在局部遮挡，检查逆变器运行状态。'
    elif deviation_rate > 20:
        health_score -= 15
        anomaly_type = 'low_generation'
        anomaly_level = 'medium'
        possible_cause = '发电量略低于预期，偏差20%-35%，可能与天气、积灰或组件老化有关。'
        handling_suggestion = '建议清洁组件表面，关注后续几日发电情况，如持续偏低则进一步排查。'

    if inverter_eff < 90:
        health_score -= 20
        if anomaly_type == 'none':
            anomaly_type = 'efficiency_drop'
            anomaly_level = 'high'
            possible_cause = f'逆变器效率仅{inverter_eff}%，远低于正常水平(>95%)，可能存在硬件故障。'
            handling_suggestion = '建议立即检查逆变器运行日志，排查硬件故障，联系厂家维修。'
        else:
            possible_cause += f' 逆变器效率偏低({inverter_eff}%)。'
            handling_suggestion += ' 同时检查逆变器效率。'
    elif inverter_eff < 95:
        health_score -= 8
        if anomaly_type == 'none':
            anomaly_type = 'efficiency_drop'
            anomaly_level = 'low'
            possible_cause = f'逆变器效率{inverter_eff}%，略低于标准值，可能存在轻微老化。'
            handling_suggestion = '关注逆变器效率变化趋势，如持续下降建议安排检修。'
        else:
            possible_cause += f' 逆变器效率略低({inverter_eff}%)。'

    if consecutive_low_days >= 5:
        health_score -= 20
        prev_type = anomaly_type
        anomaly_type = 'consecutive_low'
        anomaly_level = 'critical'
        possible_cause += f' 连续{consecutive_low_days}天发电量偏低，可能存在持续性故障。'
        handling_suggestion += ' 连续多日低发电，建议立即安排现场巡检。'
    elif consecutive_low_days >= 3:
        health_score -= 10
        anomaly_type = 'consecutive_low'
        if anomaly_level in ('normal', 'low'):
            anomaly_level = 'medium'
        possible_cause += f' 连续{consecutive_low_days}天发电偏低。'
        handling_suggestion += ' 关注发电趋势，若持续偏低需排查原因。'

    if grid_days < 30 and grid_days > 0:
        health_score -= 5
        if anomaly_type == 'none':
            anomaly_type = 'grid_issue'
            anomaly_level = 'low'
            possible_cause = f'并网运行仅{grid_days}天，系统可能仍在调试期。'
            handling_suggestion = '并网初期需密切关注系统运行状态，确保各参数正常。'
    elif grid_days <= 0:
        health_score -= 15
        anomaly_type = 'grid_issue'
        anomaly_level = 'high'
        possible_cause = '板组尚未并网或并网日期异常。'
        handling_suggestion = '请确认并网状态，检查并网日期设置是否正确。'

    if peak_valley_ratio > 3.0 or (peak_valley_ratio < 0.8 and gen.actual_kwh > 0):
        health_score -= 10
        if anomaly_type == 'none':
            anomaly_type = 'peak_valley_abnormal'
            anomaly_level = 'medium'
            if peak_valley_ratio > 3.0:
                possible_cause = f'峰谷发电比{peak_valley_ratio}异常偏高，可能存在组串失配或MPPT跟踪异常。'
                handling_suggestion = '检查组串配置和MPPT跟踪是否正常，排查是否存在部分组串离线。'
            else:
                possible_cause = f'峰谷发电比{peak_valley_ratio}异常偏低，谷段发电占比过高。'
                handling_suggestion = '检查组件朝向和倾角是否正确，排查逆变器MPPT算法是否正常。'
        else:
            possible_cause += f' 峰谷比{peak_valley_ratio}异常。'
            handling_suggestion += ' 检查峰谷发电分布。'

    health_score = max(0, min(100, health_score))

    if health_score >= 90:
        if anomaly_level == 'normal':
            anomaly_level = 'normal'
    elif health_score >= 75:
        if anomaly_level == 'normal':
            anomaly_level = 'low'
    elif health_score >= 50:
        if anomaly_level in ('normal', 'low'):
            anomaly_level = 'medium'
    elif health_score >= 25:
        if anomaly_level in ('normal', 'low', 'medium'):
            anomaly_level = 'high'
    else:
        anomaly_level = 'critical'

    if anomaly_type == 'none' and health_score >= 90:
        possible_cause = '设备运行正常，各项指标在合理范围内。'
        handling_suggestion = '继续保持日常巡检和定期维护。'

    obj, _ = HealthDiagnosis.objects.update_or_create(
        device_type='panel_group', device_id=pg.id,
        date=target_date,
        defaults={
            'device_name': pg.name,
            'health_score': health_score,
            'anomaly_type': anomaly_type,
            'anomaly_level': anomaly_level,
            'possible_cause': possible_cause.strip(),
            'handling_suggestion': handling_suggestion.strip(),
            'deviation_rate': deviation_rate,
            'inverter_efficiency': inverter_eff,
            'consecutive_low_days': consecutive_low_days,
            'grid_days': grid_days,
            'peak_valley_ratio': peak_valley_ratio,
        }
    )
    return obj


def generate_diagnosis_for_inverter(inv, target_date):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    pgs = inv.panel_groups.all()
    if not pgs.exists():
        return None

    total_actual = 0
    total_theoretical = 0
    total_peak = 0
    total_valley = 0
    panel_count = 0
    for pg in pgs:
        try:
            gen = DailyGeneration.objects.get(panel_group=pg, date=target_date)
            total_actual += gen.actual_kwh
            total_theoretical += gen.theoretical_kwh
            total_peak += gen.peak_kwh
            total_valley += gen.valley_kwh
            panel_count += 1
        except DailyGeneration.DoesNotExist:
            pass

    if panel_count == 0:
        return None

    deviation_rate = 0
    if total_theoretical > 0:
        deviation_rate = round((total_theoretical - total_actual) / total_theoretical * 100, 1)

    inverter_eff = inv.efficiency
    peak_valley_ratio = round(total_peak / total_valley, 2) if total_valley > 0 else (99.0 if total_peak > 0 else 0)

    consecutive_low_days = 0
    check_date = target_date
    while True:
        day_low = False
        for pg in pgs:
            try:
                prev_gen = DailyGeneration.objects.get(panel_group=pg, date=check_date)
                if prev_gen.theoretical_kwh > 0 and prev_gen.actual_kwh / prev_gen.theoretical_kwh < 0.7:
                    day_low = True
                    break
            except DailyGeneration.DoesNotExist:
                pass
        if day_low:
            consecutive_low_days += 1
            check_date = check_date - timedelta(days=1)
        else:
            break

    health_score = 100
    anomaly_type = 'none'
    anomaly_level = 'normal'
    possible_cause = ''
    handling_suggestion = ''

    if inverter_eff < 90:
        health_score -= 30
        anomaly_type = 'efficiency_drop'
        anomaly_level = 'critical'
        possible_cause = f'逆变器效率仅{inverter_eff}%，远低于正常水平，可能存在硬件故障。'
        handling_suggestion = '建议立即检查逆变器运行日志，排查硬件故障，联系厂家维修。'
    elif inverter_eff < 95:
        health_score -= 12
        anomaly_type = 'efficiency_drop'
        anomaly_level = 'medium'
        possible_cause = f'逆变器效率{inverter_eff}%，略低于标准值(>95%)。'
        handling_suggestion = '关注逆变器效率变化趋势，如持续下降建议安排检修。'

    if deviation_rate > 40:
        health_score -= 25
        if anomaly_type == 'none':
            anomaly_type = 'low_generation'
            anomaly_level = 'high'
        else:
            if anomaly_level != 'critical':
                anomaly_level = 'high'
        possible_cause += f' 下辖板组总发电偏差{deviation_rate}%。'
        handling_suggestion += ' 排查下辖板组运行状况。'

    if consecutive_low_days >= 5:
        health_score -= 20
        anomaly_type = 'consecutive_low'
        anomaly_level = 'critical'
        possible_cause += f' 连续{consecutive_low_days}天低发电。'
        handling_suggestion += ' 立即安排现场巡检。'
    elif consecutive_low_days >= 3:
        health_score -= 10
        if anomaly_type == 'none':
            anomaly_type = 'consecutive_low'
            anomaly_level = 'medium'
        possible_cause += f' 连续{consecutive_low_days}天发电偏低。'

    if peak_valley_ratio > 3.0 or (peak_valley_ratio < 0.8 and total_actual > 0):
        health_score -= 8
        if anomaly_type == 'none':
            anomaly_type = 'peak_valley_abnormal'
            anomaly_level = 'low'
        possible_cause += f' 峰谷比{peak_valley_ratio}异常。'
        handling_suggestion += ' 检查MPPT跟踪。'

    health_score = max(0, min(100, health_score))

    if health_score >= 90 and anomaly_level == 'normal':
        anomaly_level = 'normal'
    elif health_score >= 75 and anomaly_level == 'normal':
        anomaly_level = 'low'
    elif health_score >= 50 and anomaly_level in ('normal', 'low'):
        anomaly_level = 'medium'
    elif health_score >= 25 and anomaly_level in ('normal', 'low', 'medium'):
        anomaly_level = 'high'
    elif health_score < 25:
        anomaly_level = 'critical'

    if anomaly_type == 'none' and health_score >= 90:
        possible_cause = '逆变器运行正常，各项指标在合理范围内。'
        handling_suggestion = '继续保持日常巡检和定期维护。'

    earliest_grid = min((pg.grid_date for pg in pgs if pg.grid_date), default=None)
    grid_days = (target_date - earliest_grid).days if earliest_grid else 0

    obj, _ = HealthDiagnosis.objects.update_or_create(
        device_type='inverter', device_id=inv.id,
        date=target_date,
        defaults={
            'device_name': f'{inv.brand} {inv.model}',
            'health_score': health_score,
            'anomaly_type': anomaly_type,
            'anomaly_level': anomaly_level,
            'possible_cause': possible_cause.strip(),
            'handling_suggestion': handling_suggestion.strip(),
            'deviation_rate': deviation_rate,
            'inverter_efficiency': inverter_eff,
            'consecutive_low_days': consecutive_low_days,
            'grid_days': grid_days,
            'peak_valley_ratio': peak_valley_ratio,
        }
    )
    return obj


def generate_diagnosis_for_date(target_date):
    results = []
    for pg in SolarPanelGroup.objects.all():
        obj = generate_diagnosis_for_panel_group(pg, target_date)
        if obj:
            results.append(obj)
    for inv in Inverter.objects.all():
        obj = generate_diagnosis_for_inverter(inv, target_date)
        if obj:
            results.append(obj)
    return results


def generate_diagnosis_for_date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        generate_diagnosis_for_date(current)
        current += timedelta(days=1)


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
        panel_group = self.request.query_params.get('panel_group')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if panel_group:
            qs = qs.filter(panel_group_id=panel_group)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class HouseholdUsageViewSet(viewsets.ModelViewSet):
    queryset = HouseholdUsage.objects.all()
    serializer_class = HouseholdUsageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
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
        panel_group = self.request.query_params.get('panel_group')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if panel_group:
            qs = qs.filter(panel_group_id=panel_group)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class HealthDiagnosisViewSet(viewsets.ModelViewSet):
    queryset = HealthDiagnosis.objects.all()
    serializer_class = HealthDiagnosisSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        anomaly_level = self.request.query_params.get('anomaly_level')
        device_type = self.request.query_params.get('device_type')
        device_id = self.request.query_params.get('device_id')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        is_handled = self.request.query_params.get('is_handled')
        include_normal = self.request.query_params.get('include_normal')

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
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
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


def calc_revenue_for_date(dt):
    if isinstance(dt, str):
        dt = date.fromisoformat(dt)
    prices = {}
    for p in ElectricityPrice.objects.order_by('price_type', '-effective_date'):
        if p.price_type not in prices:
            prices[p.price_type] = p.price

    peak_price = prices.get('grid_buy_peak', 0.85)
    valley_price = prices.get('grid_buy_valley', 0.38)
    sell_price = prices.get('grid_sell', 0.45)

    try:
        usage = HouseholdUsage.objects.get(date=dt)
    except HouseholdUsage.DoesNotExist:
        usage = None

    results = []
    for pg in SolarPanelGroup.objects.all():
        try:
            gen = DailyGeneration.objects.get(panel_group=pg, date=dt)
        except DailyGeneration.DoesNotExist:
            continue

        if usage:
            self_use = min(usage.total_kwh, gen.actual_kwh) if usage.total_kwh > 0 else 0
            self_use = usage.self_use_kwh if usage.self_use_kwh > 0 else min(gen.actual_kwh * 0.4, usage.total_kwh)
            grid_sell = gen.actual_kwh - self_use
        else:
            self_use = gen.actual_kwh * 0.4
            grid_sell = gen.actual_kwh * 0.6

        self_use_peak = self_use * 0.6
        self_use_valley = self_use * 0.4
        self_use_saving = self_use_peak * peak_price + self_use_valley * valley_price
        grid_sell_income = grid_sell * sell_price
        total_income = self_use_saving + grid_sell_income

        obj, _ = RevenueRecord.objects.update_or_create(
            date=dt, panel_group=pg,
            defaults={
                'generation_kwh': gen.actual_kwh,
                'self_use_kwh': round(self_use, 2),
                'grid_sell_kwh': round(grid_sell, 2),
                'self_use_saving': round(self_use_saving, 2),
                'grid_sell_income': round(grid_sell_income, 2),
                'total_income': round(total_income, 2),
            }
        )
        results.append(RevenueRecordSerializer(obj).data)
    return results


@api_view(['POST'])
def import_generation_data(request):
    data = request.data
    dates_to_calc = set()
    dates_to_diagnose = set()

    if isinstance(data, list):
        results = []
        for item in data:
            panel_group_id = item.get('panel_group')
            dt = item.get('date')
            actual_kwh = item.get('actual_kwh', 0)
            try:
                pg = SolarPanelGroup.objects.get(pk=panel_group_id)
            except SolarPanelGroup.DoesNotExist:
                continue
            month = int(dt.split('-')[1]) if dt else date.today().month
            inv_eff = pg.inverter.efficiency if pg.inverter else 98.0
            theoretical_kwh = calc_theoretical_kwh(pg.capacity_kw, pg.install_angle, month, inv_eff)
            sunshine = AVERAGE_SUNSHINE_HOURS.get(month, 6.0)
            obj, created = DailyGeneration.objects.update_or_create(
                panel_group=pg, date=dt,
                defaults={
                    'actual_kwh': actual_kwh,
                    'theoretical_kwh': theoretical_kwh,
                    'sunshine_hours': sunshine,
                    'peak_kwh': item.get('peak_kwh', actual_kwh * 0.6),
                    'valley_kwh': item.get('valley_kwh', actual_kwh * 0.4),
                }
            )
            results.append(DailyGenerationSerializer(obj).data)
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
        panel_group_id = data.get('panel_group')
        dt = data.get('date')
        actual_kwh = data.get('actual_kwh', 0)
        try:
            pg = SolarPanelGroup.objects.get(pk=panel_group_id)
        except SolarPanelGroup.DoesNotExist:
            return Response({'error': 'Panel group not found'}, status=status.HTTP_404_NOT_FOUND)
        month = int(dt.split('-')[1]) if dt else date.today().month
        inv_eff = pg.inverter.efficiency if pg.inverter else 98.0
        theoretical_kwh = calc_theoretical_kwh(pg.capacity_kw, pg.install_angle, month, inv_eff)
        sunshine = AVERAGE_SUNSHINE_HOURS.get(month, 6.0)
        obj, created = DailyGeneration.objects.update_or_create(
            panel_group=pg, date=dt,
            defaults={
                'actual_kwh': actual_kwh,
                'theoretical_kwh': theoretical_kwh,
                'sunshine_hours': sunshine,
                'peak_kwh': data.get('peak_kwh', actual_kwh * 0.6),
                'valley_kwh': data.get('valley_kwh', actual_kwh * 0.4),
            }
        )
        if dt:
            calc_revenue_for_date(dt)
            generate_diagnosis_for_date(dt)
            calculate_storage_schedule_for_date(dt)
        return Response(DailyGenerationSerializer(obj).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def calculate_revenue(request):
    dt = request.data.get('date')
    if not dt:
        return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)

    results = calc_revenue_for_date(dt)
    return Response(results)


@api_view(['GET'])
def dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)

    total_capacity = sum(pg.capacity_kw for pg in SolarPanelGroup.objects.all())
    panel_groups = SolarPanelGroup.objects.all()

    today_gen = DailyGeneration.objects.filter(date=today)
    today_total = sum(g.actual_kwh for g in today_gen)
    today_theoretical = sum(g.theoretical_kwh for g in today_gen)

    month_gen = DailyGeneration.objects.filter(date__gte=month_start)
    month_total = sum(g.actual_kwh for g in month_gen)

    month_revenue = RevenueRecord.objects.filter(date__gte=month_start)
    month_income = sum(r.total_income for r in month_revenue)

    total_revenue = sum(r.total_income for r in RevenueRecord.objects.all())
    total_investment = sum(pg.capacity_kw * 4000 for pg in panel_groups)

    recent_7_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_gen = DailyGeneration.objects.filter(date=d)
        day_total = sum(g.actual_kwh for g in day_gen)
        day_theo = sum(g.theoretical_kwh for g in day_gen)
        day_rev = RevenueRecord.objects.filter(date=d)
        day_income = sum(r.total_income for r in day_rev)
        recent_7_days.append({
            'date': d.isoformat(),
            'actual_kwh': round(day_total, 2),
            'theoretical_kwh': round(day_theo, 2),
            'income': round(day_income, 2),
        })

    self_use_rate = 0
    total_gen_kwh = sum(g.actual_kwh for g in DailyGeneration.objects.all())
    total_self_use = sum(r.self_use_kwh for r in RevenueRecord.objects.all())
    if total_gen_kwh > 0:
        self_use_rate = round(total_self_use / total_gen_kwh * 100, 1)

    payback_pct = round(total_revenue / total_investment * 100, 1) if total_investment > 0 else 0

    unhandled_alert_count = HealthDiagnosis.objects.filter(is_handled=False).exclude(anomaly_level='normal').count()
    highest_alert_level = 'normal'
    level_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'normal': 0}
    unhandled_alerts = HealthDiagnosis.objects.filter(is_handled=False).exclude(anomaly_level='normal')
    for alert in unhandled_alerts:
        if level_order.get(alert.anomaly_level, 0) > level_order.get(highest_alert_level, 0):
            highest_alert_level = alert.anomaly_level

    health_score_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        diagnoses = HealthDiagnosis.objects.filter(date=d)
        if diagnoses.exists():
            avg_score = round(sum(d.health_score for d in diagnoses) / diagnoses.count(), 1)
        else:
            avg_score = None
        health_score_trend.append({
            'date': d.isoformat(),
            'avg_health_score': avg_score,
        })

    batteries = StorageBattery.objects.all()
    storage_battery_count = batteries.count()
    storage_total_capacity = sum(b.capacity_kwh for b in batteries)

    storage_today_soc = 0
    storage_today_charge = 0
    storage_today_discharge = 0
    storage_today_profit = 0
    storage_today_schedules = StorageSchedule.objects.filter(date=today)
    current_hour = datetime.now().hour
    if storage_today_schedules.exists():
        soc_list = []
        for s in storage_today_schedules:
            if s.hourly_soc:
                current_h = min(current_hour, 23)
                if current_h < len(s.hourly_soc):
                    soc_list.append(s.hourly_soc[current_h])
                else:
                    soc_list.append(s.final_soc)
            else:
                soc_list.append(s.final_soc)
            storage_today_charge += s.charge_kwh
            storage_today_discharge += s.discharge_kwh
            storage_today_profit += s.total_profit_diff
        storage_today_soc = round(sum(soc_list) / len(soc_list), 1) if soc_list else 0

    storage_month_profit = sum(
        s.total_profit_diff for s in StorageSchedule.objects.filter(date__gte=month_start)
    )

    upcoming_cleaning_count = CleaningPlan.objects.filter(
        status='pending',
        plan_date__gte=today,
        plan_date__lte=today + timedelta(days=7)
    ).count()

    latest_completed = CleaningPlan.objects.filter(
        status='completed'
    ).order_by('-actual_date').first()
    latest_cleaning_revenue = latest_completed.extra_revenue if latest_completed else 0

    return Response({
        'total_capacity_kw': total_capacity,
        'panel_group_count': panel_groups.count(),
        'inverter_count': Inverter.objects.count(),
        'today_generation_kwh': round(today_total, 2),
        'today_theoretical_kwh': round(today_theoretical, 2),
        'today_efficiency_rate': round(today_total / today_theoretical * 100, 1) if today_theoretical > 0 else 0,
        'month_generation_kwh': round(month_total, 2),
        'month_income': round(month_income, 2),
        'total_income': round(total_revenue, 2),
        'total_investment': total_investment,
        'self_use_rate': self_use_rate,
        'payback_pct': payback_pct,
        'recent_7_days': recent_7_days,
        'unhandled_alert_count': unhandled_alert_count,
        'highest_alert_level': highest_alert_level,
        'health_score_trend': health_score_trend,
        'storage_battery_count': storage_battery_count,
        'storage_total_capacity_kwh': storage_total_capacity,
        'storage_today_soc': storage_today_soc,
        'storage_today_charge_kwh': round(storage_today_charge, 2),
        'storage_today_discharge_kwh': round(storage_today_discharge, 2),
        'storage_today_profit': round(storage_today_profit, 2),
        'storage_month_profit': round(storage_month_profit, 2),
        'upcoming_cleaning_count': upcoming_cleaning_count,
        'latest_cleaning_revenue': round(latest_cleaning_revenue, 2),
    })


@api_view(['GET'])
def statistics(request):
    months_param = int(request.query_params.get('months', 12))
    today = date.today()
    start_date = today - timedelta(days=months_param * 30)

    monthly_gen = {}
    monthly_self_use = {}
    monthly_grid_sell = {}
    monthly_income = {}

    gen_records = DailyGeneration.objects.filter(date__gte=start_date)
    for g in gen_records:
        key = g.date.strftime('%Y-%m')
        monthly_gen[key] = monthly_gen.get(key, 0) + g.actual_kwh

    rev_records = RevenueRecord.objects.filter(date__gte=start_date)
    for r in rev_records:
        key = r.date.strftime('%Y-%m')
        monthly_self_use[key] = monthly_self_use.get(key, 0) + r.self_use_kwh
        monthly_grid_sell[key] = monthly_grid_sell.get(key, 0) + r.grid_sell_kwh
        monthly_income[key] = monthly_income.get(key, 0) + r.total_income

    all_keys = sorted(set(list(monthly_gen.keys()) + list(monthly_income.keys())))

    generation_trend = [{'month': k, 'kwh': round(monthly_gen.get(k, 0), 2)} for k in all_keys]
    self_use_rate_trend = []
    for k in all_keys:
        gen_kwh = monthly_gen.get(k, 0)
        self_kwh = monthly_self_use.get(k, 0)
        rate = round(self_kwh / gen_kwh * 100, 1) if gen_kwh > 0 else 0
        self_use_rate_trend.append({'month': k, 'rate': rate})

    peak_valley_match = []
    usage_records = HouseholdUsage.objects.filter(date__gte=start_date)
    monthly_peak = {}
    monthly_valley = {}
    for u in usage_records:
        key = u.date.strftime('%Y-%m')
        monthly_peak[key] = monthly_peak.get(key, 0) + u.peak_kwh
        monthly_valley[key] = monthly_valley.get(key, 0) + u.valley_kwh
    for k in all_keys:
        peak = monthly_peak.get(k, 0)
        valley = monthly_valley.get(k, 0)
        total = peak + valley
        match_rate = round(min(peak, valley) / max(peak, valley) * 100, 1) if max(peak, valley) > 0 else 0
        peak_valley_match.append({
            'month': k,
            'peak_kwh': round(peak, 2),
            'valley_kwh': round(valley, 2),
            'match_rate': match_rate,
        })

    total_revenue = sum(r.total_income for r in RevenueRecord.objects.all())
    total_investment = sum(pg.capacity_kw * 4000 for pg in SolarPanelGroup.objects.all())
    payback_pct = round(total_revenue / total_investment * 100, 1) if total_investment > 0 else 0

    irr = 0
    if total_investment > 0 and total_revenue > 0:
        panel_list = list(SolarPanelGroup.objects.all())
        if panel_list:
            days_online = max((today - pg.grid_date).days for pg in panel_list)
        else:
            days_online = 1
        years = max(days_online / 365.0, 0.1)
        annual_income = total_revenue / years
        irr = round((annual_income / total_investment) * 100, 1)

    monthly_anomaly_count = {}
    diagnosis_records = HealthDiagnosis.objects.filter(date__gte=start_date).exclude(anomaly_level='normal')
    for d in diagnosis_records:
        key = d.date.strftime('%Y-%m')
        monthly_anomaly_count[key] = monthly_anomaly_count.get(key, 0) + 1

    anomaly_trend = [{'month': k, 'count': monthly_anomaly_count.get(k, 0)} for k in all_keys]

    panel_group_health = []
    for pg in SolarPanelGroup.objects.all():
        diagnoses = HealthDiagnosis.objects.filter(device_type='panel_group', device_id=pg.id, date__gte=start_date)
        if diagnoses.exists():
            avg_score = round(sum(d.health_score for d in diagnoses) / diagnoses.count(), 1)
        else:
            avg_score = None
        panel_group_health.append({
            'id': pg.id,
            'name': pg.name,
            'avg_health_score': avg_score,
        })

    monthly_storage_profit = {}
    monthly_peak_saving = {}
    monthly_valley_cost = {}
    monthly_reduced_curtailment = {}
    storage_schedules = StorageSchedule.objects.filter(date__gte=start_date)
    for s in storage_schedules:
        key = s.date.strftime('%Y-%m')
        monthly_storage_profit[key] = monthly_storage_profit.get(key, 0) + s.total_profit_diff
        monthly_peak_saving[key] = monthly_peak_saving.get(key, 0) + s.peak_discharge_saving
        monthly_valley_cost[key] = monthly_valley_cost.get(key, 0) + s.valley_charge_cost
        monthly_reduced_curtailment[key] = monthly_reduced_curtailment.get(key, 0) + s.reduced_curtailment_kwh

    storage_profit_trend = [
        {'month': k, 'profit': round(monthly_storage_profit.get(k, 0), 2)}
        for k in all_keys
    ]
    peak_valley_arbitrage = [
        {
            'month': k,
            'peak_saving': round(monthly_peak_saving.get(k, 0), 2),
            'valley_cost': round(monthly_valley_cost.get(k, 0), 2),
            'reduced_curtailment_kwh': round(monthly_reduced_curtailment.get(k, 0), 2),
            'net_profit': round(
                monthly_peak_saving.get(k, 0) - monthly_valley_cost.get(k, 0)
                + (monthly_storage_profit.get(k, 0) - (monthly_peak_saving.get(k, 0) - monthly_valley_cost.get(k, 0))),
                2
            ),
        }
        for k in all_keys
    ]
    total_storage_profit = round(sum(monthly_storage_profit.values()), 2)
    total_reduced_curtailment = round(sum(monthly_reduced_curtailment.values()), 2)

    monthly_cleaning_count = {}
    cleaning_efficiency_before = {}
    cleaning_efficiency_after = {}
    cleaning_revenue_monthly = {}
    panel_cleaning_contrib = {}

    cleaning_records = CleaningPlan.objects.filter(status='completed', actual_date__gte=start_date)
    for cp in cleaning_records:
        key = cp.actual_date.strftime('%Y-%m')
        monthly_cleaning_count[key] = monthly_cleaning_count.get(key, 0) + 1
        cleaning_revenue_monthly[key] = cleaning_revenue_monthly.get(key, 0) + cp.extra_revenue
        if key not in cleaning_efficiency_before:
            cleaning_efficiency_before[key] = []
        if key not in cleaning_efficiency_after:
            cleaning_efficiency_after[key] = []
        if cp.pre_avg_efficiency > 0:
            cleaning_efficiency_before[key].append(cp.pre_avg_efficiency)
        if cp.post_avg_efficiency > 0:
            cleaning_efficiency_after[key].append(cp.post_avg_efficiency)
        pg_name = cp.panel_group.name
        if pg_name not in panel_cleaning_contrib:
            panel_cleaning_contrib[pg_name] = {'name': pg_name, 'revenue': 0, 'count': 0, 'recovered_kwh': 0}
        panel_cleaning_contrib[pg_name]['revenue'] += cp.extra_revenue
        panel_cleaning_contrib[pg_name]['count'] += 1
        panel_cleaning_contrib[pg_name]['recovered_kwh'] += cp.recovered_generation_kwh

    monthly_cleaning_trend = [{'month': k, 'count': monthly_cleaning_count.get(k, 0)} for k in all_keys]

    cleaning_efficiency_compare = []
    for k in all_keys:
        before_list = cleaning_efficiency_before.get(k, [])
        after_list = cleaning_efficiency_after.get(k, [])
        before_avg = round(sum(before_list) / len(before_list), 2) if before_list else 0
        after_avg = round(sum(after_list) / len(after_list), 2) if after_list else 0
        cleaning_efficiency_compare.append({
            'month': k,
            'before_cleaning': before_avg,
            'after_cleaning': after_avg,
            'improvement': round(after_avg - before_avg, 2) if before_avg > 0 else 0,
        })

    panel_cleaning_ranking = sorted(
        panel_cleaning_contrib.values(),
        key=lambda x: x['revenue'],
        reverse=True
    )
    for item in panel_cleaning_ranking:
        item['revenue'] = round(item['revenue'], 2)
        item['recovered_kwh'] = round(item['recovered_kwh'], 2)

    total_cleaning_count = CleaningPlan.objects.filter(status='completed').count()
    total_cleaning_revenue = round(sum(cp.extra_revenue for cp in CleaningPlan.objects.filter(status='completed')), 2)
    total_cleaning_recovered = round(sum(cp.recovered_generation_kwh for cp in CleaningPlan.objects.filter(status='completed')), 2)

    return Response({
        'generation_trend': generation_trend,
        'self_use_rate_trend': self_use_rate_trend,
        'peak_valley_match': peak_valley_match,
        'payback_pct': payback_pct,
        'total_investment': total_investment,
        'total_revenue': round(total_revenue, 2),
        'irr': irr,
        'monthly_income': [{'month': k, 'income': round(monthly_income.get(k, 0), 2)} for k in all_keys],
        'anomaly_trend': anomaly_trend,
        'panel_group_health': panel_group_health,
        'storage_profit_trend': storage_profit_trend,
        'peak_valley_arbitrage': peak_valley_arbitrage,
        'total_storage_profit': total_storage_profit,
        'total_reduced_curtailment_kwh': total_reduced_curtailment,
        'monthly_cleaning_trend': monthly_cleaning_trend,
        'cleaning_efficiency_compare': cleaning_efficiency_compare,
        'panel_cleaning_ranking': panel_cleaning_ranking,
        'total_cleaning_count': total_cleaning_count,
        'total_cleaning_revenue': total_cleaning_revenue,
        'total_cleaning_recovered_kwh': total_cleaning_recovered,
    })


@api_view(['GET'])
def payback_prediction(request):
    panel_groups = SolarPanelGroup.objects.all()
    total_investment = sum(pg.capacity_kw * 4000 for pg in panel_groups)

    rev_records = RevenueRecord.objects.all()
    total_revenue = sum(r.total_income for r in rev_records)

    today = date.today()
    if panel_groups.exists():
        earliest = min(pg.grid_date for pg in panel_groups)
        days_online = (today - earliest).days
    else:
        days_online = 1

    avg_daily_income = total_revenue / max(days_online, 1)
    remaining = total_investment - total_revenue
    days_to_payback = int(remaining / avg_daily_income) if avg_daily_income > 0 else 0
    payback_date = (today + timedelta(days=days_to_payback)).isoformat() if avg_daily_income > 0 else None

    payback_pct = round(total_revenue / total_investment * 100, 1) if total_investment > 0 else 0

    monthly_projection = []
    if avg_daily_income > 0:
        for i in range(1, 13):
            future_date = today + timedelta(days=30 * i)
            projected_revenue = total_revenue + avg_daily_income * 30 * i
            projected_pct = round(min(projected_revenue / total_investment * 100, 100), 1) if total_investment > 0 else 0
            monthly_projection.append({
                'month': future_date.strftime('%Y-%m'),
                'projected_pct': projected_pct,
                'projected_revenue': round(projected_revenue, 2),
            })

    annual_income = avg_daily_income * 365
    irr = round((annual_income / total_investment) * 100, 1) if total_investment > 0 else 0

    npv = 0
    if annual_income > 0 and total_investment > 0:
        discount_rate = 0.05
        for year in range(1, 26):
            npv += annual_income / math.pow(1 + discount_rate, year)
        npv = round(npv - total_investment, 2)

    return Response({
        'total_investment': total_investment,
        'total_revenue': round(total_revenue, 2),
        'avg_daily_income': round(avg_daily_income, 2),
        'payback_pct': payback_pct,
        'remaining_amount': round(max(remaining, 0), 2),
        'days_to_payback': days_to_payback,
        'payback_date': payback_date,
        'irr': irr,
        'npv': npv,
        'annual_income': round(annual_income, 2),
        'monthly_projection': monthly_projection,
    })


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
    today = date.today()
    unhandled = HealthDiagnosis.objects.filter(is_handled=False).exclude(anomaly_level='normal')
    unhandled_count = unhandled.count()

    highest_level = 'normal'
    level_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'normal': 0}
    for a in unhandled:
        if level_order.get(a.anomaly_level, 0) > level_order.get(highest_level, 0):
            highest_level = a.anomaly_level

    recent_7_health = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        diagnoses = HealthDiagnosis.objects.filter(date=d)
        if diagnoses.exists():
            avg_score = round(sum(d.health_score for d in diagnoses) / diagnoses.count(), 1)
        else:
            avg_score = None
        recent_7_health.append({
            'date': d.isoformat(),
            'avg_health_score': avg_score,
        })

    level_counts = {}
    for level_key, _ in HealthDiagnosis.LEVEL_CHOICES:
        if level_key == 'normal':
            continue
        level_counts[level_key] = unhandled.filter(anomaly_level=level_key).count()

    return Response({
        'unhandled_count': unhandled_count,
        'highest_level': highest_level,
        'level_counts': level_counts,
        'recent_7_health': recent_7_health,
    })


def get_electricity_prices():
    prices = {}
    for p in ElectricityPrice.objects.order_by('price_type', '-effective_date'):
        if p.price_type not in prices:
            prices[p.price_type] = p.price
    return {
        'peak': prices.get('grid_buy_peak', 0.85),
        'valley': prices.get('grid_buy_valley', 0.38),
        'shoulder': prices.get('grid_buy_shoulder', 0.55),
        'sell': prices.get('grid_sell', 0.45),
    }


def get_hour_price(hour, prices):
    if hour in PEAK_HOURS:
        return prices['peak']
    elif hour in VALLEY_HOURS:
        return prices['valley']
    return prices['shoulder']


def generate_hourly_profile(total_kwh, profile):
    profile_sum = sum(profile)
    if profile_sum == 0:
        return [0] * 24
    return [round(total_kwh * p / profile_sum, 4) for p in profile]


def has_battery_alerts(battery, target_date):
    if battery.status in ('warning', 'maintenance'):
        return True
    pg_ids = list(battery.panel_groups.values_list('id', flat=True))
    inv_ids = list(Inverter.objects.filter(panel_groups__in=pg_ids).values_list('id', flat=True))
    alerts = HealthDiagnosis.objects.filter(
        date=target_date,
        is_handled=False,
    ).exclude(anomaly_level='normal')
    pg_alerts = alerts.filter(device_type='panel_group', device_id__in=pg_ids)
    inv_alerts = alerts.filter(device_type='inverter', device_id__in=inv_ids)
    return pg_alerts.exists() or inv_alerts.exists()


def calculate_storage_schedule(battery, target_date):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    prices = get_electricity_prices()
    capacity = battery.capacity_kwh
    max_charge = battery.max_charge_power_kw
    max_discharge = battery.max_discharge_power_kw
    charge_eff = battery.charge_efficiency / 100.0
    discharge_eff = battery.discharge_efficiency / 100.0
    soc_max = battery.soc_upper_limit
    soc_min = battery.soc_lower_limit

    has_alert = has_battery_alerts(battery, target_date)
    alert_discount = 0.5 if has_alert else 1.0

    try:
        prev_schedule = StorageSchedule.objects.filter(
            battery=battery, date__lt=target_date
        ).order_by('-date').first()
        initial_soc = prev_schedule.final_soc if prev_schedule else battery.current_soc
    except Exception:
        initial_soc = battery.current_soc

    initial_soc = max(soc_min, min(soc_max, initial_soc))

    pg_ids = list(battery.panel_groups.values_list('id', flat=True))
    gen_records = DailyGeneration.objects.filter(panel_group_id__in=pg_ids, date=target_date)
    total_gen = sum(g.actual_kwh for g in gen_records)
    hourly_gen = generate_hourly_profile(total_gen, SOLAR_GENERATION_PROFILE)

    try:
        usage = HouseholdUsage.objects.get(date=target_date)
        total_usage = usage.total_kwh
    except HouseholdUsage.DoesNotExist:
        total_usage = 12.0
    hourly_usage = generate_hourly_profile(total_usage, HOUSEHOLD_USAGE_PROFILE)

    hourly_charge_discharge = [0.0] * 24
    hourly_soc = [0.0] * 24
    hourly_detail = {}
    current_soc = initial_soc
    total_charge = 0.0
    total_discharge = 0.0

    solar_self_use_without = [0.0] * 24
    grid_sell_without = [0.0] * 24
    grid_buy_without = [0.0] * 24

    for h in range(24):
        gen = hourly_gen[h]
        use = hourly_usage[h]
        surplus = max(0, gen - use)
        deficit = max(0, use - gen)
        solar_self_use_without[h] = min(gen, use)
        grid_sell_without[h] = surplus
        grid_buy_without[h] = deficit

    solar_self_use_with = [0.0] * 24
    grid_sell_with = [0.0] * 24
    grid_buy_with = [0.0] * 24

    for h in range(24):
        gen = hourly_gen[h]
        use = hourly_usage[h]
        surplus = max(0, gen - use)
        deficit = max(0, use - gen)
        price = get_hour_price(h, prices)
        soc_frac = current_soc / 100.0
        available_charge_space = max(0, (soc_max / 100.0 - soc_frac) * capacity)
        available_discharge = max(0, (soc_frac - soc_min / 100.0) * capacity * discharge_eff)

        action = 'idle'
        charge_amount = 0.0
        discharge_amount = 0.0

        if surplus > 0 and available_charge_space > 0 and price < prices['sell'] * 1.1:
            charge_amount = min(surplus, max_charge * alert_discount, available_charge_space / charge_eff)
            actual_charge_into = charge_amount * charge_eff
            current_soc = (soc_frac * capacity + actual_charge_into) / capacity * 100
            current_soc = min(soc_max, current_soc)
            total_charge += charge_amount
            action = 'charge_solar'
            remaining_surplus = surplus - charge_amount
            solar_self_use_with[h] = min(gen, use)
            grid_sell_with[h] = remaining_surplus
            grid_buy_with[h] = 0

        elif deficit > 0 and available_discharge > 0 and price > prices['valley'] * 1.3:
            discharge_amount = min(deficit, max_discharge * alert_discount, available_discharge)
            actual_drawn = discharge_amount / discharge_eff
            current_soc = (soc_frac * capacity - actual_drawn) / capacity * 100
            current_soc = max(soc_min, current_soc)
            total_discharge += discharge_amount
            action = 'discharge'
            remaining_deficit = deficit - discharge_amount
            solar_self_use_with[h] = min(gen, use)
            grid_sell_with[h] = 0
            grid_buy_with[h] = remaining_deficit

        elif h in VALLEY_HOURS and price < prices['peak'] * 0.6 and available_charge_space > capacity * 0.2:
            max_grid_charge = min(max_charge * alert_discount, available_charge_space / charge_eff)
            target_soc_energy = (soc_max / 100.0) * capacity
            need_energy = target_soc_energy - soc_frac * capacity
            grid_charge_amount = min(max_grid_charge, max(0, need_energy / charge_eff))
            if grid_charge_amount > 0.1:
                charge_amount = grid_charge_amount
                actual_charge_into = charge_amount * charge_eff
                current_soc = (soc_frac * capacity + actual_charge_into) / capacity * 100
                current_soc = min(soc_max, current_soc)
                total_charge += charge_amount
                action = 'charge_grid_valley'
                solar_self_use_with[h] = min(gen, use)
                grid_sell_with[h] = max(0, gen - use)
                grid_buy_with[h] = deficit + charge_amount
            else:
                solar_self_use_with[h] = min(gen, use)
                grid_sell_with[h] = surplus
                grid_buy_with[h] = deficit
        else:
            solar_self_use_with[h] = min(gen, use)
            grid_sell_with[h] = surplus
            grid_buy_with[h] = deficit

        hourly_charge_discharge[h] = round(charge_amount - discharge_amount, 4)
        hourly_soc[h] = round(current_soc, 2)
        hourly_detail[str(h)] = {
            'hour': h,
            'generation_kwh': round(gen, 4),
            'usage_kwh': round(use, 4),
            'price': price,
            'price_type': 'peak' if h in PEAK_HOURS else ('valley' if h in VALLEY_HOURS else 'shoulder'),
            'action': action,
            'charge_kwh': round(charge_amount, 4),
            'discharge_kwh': round(discharge_amount, 4),
            'solar_self_use_without': round(solar_self_use_without[h], 4),
            'grid_sell_without': round(grid_sell_without[h], 4),
            'grid_buy_without': round(grid_buy_without[h], 4),
            'solar_self_use_with': round(solar_self_use_with[h], 4),
            'grid_sell_with': round(grid_sell_with[h], 4),
            'grid_buy_with': round(grid_buy_with[h], 4),
            'soc_pct': round(current_soc, 2),
        }

    total_grid_sell_without = sum(grid_sell_without)
    total_grid_buy_without = sum(grid_buy_without)
    total_solar_self_without = sum(solar_self_use_without)
    total_grid_sell_with = sum(grid_sell_with)
    total_grid_buy_with = sum(grid_buy_with)
    total_solar_self_with = sum(solar_self_use_with)

    reduced_curtailment = max(0, total_solar_self_with - total_solar_self_without
                              + (total_grid_sell_with - total_grid_sell_without))

    peak_saving = 0.0
    valley_cost = 0.0
    for h in range(24):
        d = hourly_detail[str(h)]
        price = d['price']
        if d['action'] == 'discharge' and d['price_type'] == 'peak':
            peak_saving += d['discharge_kwh'] * price
        if d['action'] == 'charge_grid_valley':
            valley_cost += d['charge_kwh'] * price

    grid_income_without = total_grid_sell_without * prices['sell']
    grid_income_with = total_grid_sell_with * prices['sell']
    grid_income_change = grid_income_with - grid_income_without

    buy_cost_without = 0.0
    buy_cost_with = 0.0
    for h in range(24):
        p = get_hour_price(h, prices)
        buy_cost_without += grid_buy_without[h] * p
        buy_cost_with += grid_buy_with[h] * p
    buy_saving = buy_cost_without - buy_cost_with

    total_profit_diff = buy_saving + grid_income_change - valley_cost

    obj, _ = StorageSchedule.objects.update_or_create(
        battery=battery, date=target_date,
        defaults={
            'initial_soc': round(initial_soc, 2),
            'final_soc': round(current_soc, 2),
            'charge_kwh': round(total_charge, 4),
            'discharge_kwh': round(total_discharge, 4),
            'reduced_curtailment_kwh': round(reduced_curtailment, 4),
            'peak_discharge_saving': round(peak_saving, 4),
            'valley_charge_cost': round(valley_cost, 4),
            'grid_income_change': round(grid_income_change, 4),
            'total_profit_diff': round(total_profit_diff, 4),
            'hourly_soc': [round(s, 2) for s in hourly_soc],
            'hourly_charge_discharge': [round(v, 4) for v in hourly_charge_discharge],
            'hourly_detail': hourly_detail,
        }
    )
    return obj


def calculate_storage_schedule_for_date(target_date):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    results = []
    for battery in StorageBattery.objects.filter(enable_date__lte=target_date):
        if battery.status == 'maintenance':
            continue
        obj = calculate_storage_schedule(battery, target_date)
        results.append(StorageScheduleSerializer(obj).data)
    return results


def calculate_storage_schedule_for_range(start_date, end_date):
    current = start_date
    all_results = []
    while current <= end_date:
        results = calculate_storage_schedule_for_date(current)
        all_results.extend(results)
        current += timedelta(days=1)
    return all_results


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
        battery_id = self.request.query_params.get('battery')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if battery_id:
            qs = qs.filter(battery_id=battery_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
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
    today = date.today()
    month_start = today.replace(day=1)
    current_hour = datetime.now().hour

    batteries = StorageBattery.objects.all()
    total_capacity = sum(b.capacity_kwh for b in batteries)
    active_count = batteries.exclude(status='maintenance').count()

    today_schedules = StorageSchedule.objects.filter(date=today)
    today_charge = sum(s.charge_kwh for s in today_schedules)
    today_discharge = sum(s.discharge_kwh for s in today_schedules)
    today_profit = sum(s.total_profit_diff for s in today_schedules)

    avg_soc = 0
    if today_schedules.exists():
        soc_list = []
        for s in today_schedules:
            if s.hourly_soc:
                current_h = min(current_hour, 23)
                if current_h < len(s.hourly_soc):
                    soc_list.append(s.hourly_soc[current_h])
                else:
                    soc_list.append(s.final_soc)
            else:
                soc_list.append(s.final_soc)
        avg_soc = round(sum(soc_list) / len(soc_list), 1) if soc_list else 0

    month_schedules = StorageSchedule.objects.filter(date__gte=month_start)
    month_profit = sum(s.total_profit_diff for s in month_schedules)
    month_reduced_curtailment = sum(s.reduced_curtailment_kwh for s in month_schedules)

    return Response({
        'battery_count': batteries.count(),
        'active_battery_count': active_count,
        'total_capacity_kwh': total_capacity,
        'today_current_soc': avg_soc,
        'today_charge_kwh': round(today_charge, 2),
        'today_discharge_kwh': round(today_discharge, 2),
        'today_storage_profit': round(today_profit, 2),
        'month_storage_profit': round(month_profit, 2),
        'month_reduced_curtailment_kwh': round(month_reduced_curtailment, 2),
    })


def calc_weather_sunshine_coeff(panel_group, target_date, days=7):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    start_date = target_date - timedelta(days=days - 1)
    records = DailyGeneration.objects.filter(
        panel_group=panel_group,
        date__gte=start_date,
        date__lte=target_date
    ).order_by('-date')
    if not records.exists():
        return 1.0
    coeffs = []
    for r in records:
        month = r.date.month
        avg_sun = AVERAGE_SUNSHINE_HOURS.get(month, 6.0)
        if avg_sun > 0 and r.sunshine_hours > 0:
            coeffs.append(r.sunshine_hours / avg_sun)
    if coeffs:
        return round(sum(coeffs) / len(coeffs), 2)
    return 1.0


def evaluate_cleaning_effect(cleaning_plan):
    panel_group = cleaning_plan.panel_group
    actual_date = cleaning_plan.actual_date
    if not actual_date:
        return None

    if isinstance(actual_date, str):
        actual_date = date.fromisoformat(actual_date)

    pre_start = actual_date - timedelta(days=7)
    pre_end = actual_date - timedelta(days=1)
    post_start = actual_date + timedelta(days=1)
    post_end = actual_date + timedelta(days=7)
    today = date.today()
    post_end = min(post_end, today)

    pre_records = DailyGeneration.objects.filter(
        panel_group=panel_group,
        date__gte=pre_start,
        date__lte=pre_end
    )
    post_records = DailyGeneration.objects.filter(
        panel_group=panel_group,
        date__gte=post_start,
        date__lte=post_end
    )

    pre_efficiencies = []
    pre_deviations = []
    pre_actuals = []
    pre_theoreticals = []
    for r in pre_records:
        if r.theoretical_kwh > 0:
            eff = round(r.actual_kwh / r.theoretical_kwh * 100, 2)
            pre_efficiencies.append(eff)
            dev = round((r.theoretical_kwh - r.actual_kwh) / r.theoretical_kwh * 100, 1)
            pre_deviations.append(dev)
            pre_actuals.append(r.actual_kwh)
            pre_theoreticals.append(r.theoretical_kwh)

    post_efficiencies = []
    post_deviations = []
    post_actuals = []
    post_theoreticals = []
    for r in post_records:
        if r.theoretical_kwh > 0:
            eff = round(r.actual_kwh / r.theoretical_kwh * 100, 2)
            post_efficiencies.append(eff)
            dev = round((r.theoretical_kwh - r.actual_kwh) / r.theoretical_kwh * 100, 1)
            post_deviations.append(dev)
            post_actuals.append(r.actual_kwh)
            post_theoreticals.append(r.theoretical_kwh)

    pre_avg_efficiency = round(sum(pre_efficiencies) / len(pre_efficiencies), 2) if pre_efficiencies else 0
    post_avg_efficiency = round(sum(post_efficiencies) / len(post_efficiencies), 2) if post_efficiencies else 0
    pre_avg_deviation = round(sum(pre_deviations) / len(pre_deviations), 1) if pre_deviations else 0
    post_avg_deviation = round(sum(post_deviations) / len(post_deviations), 1) if post_deviations else 0

    pre_avg_actual = round(sum(pre_actuals) / len(pre_actuals), 2) if pre_actuals else 0
    post_avg_actual = round(sum(post_actuals) / len(post_actuals), 2) if post_actuals else 0
    pre_avg_theoretical = round(sum(pre_theoreticals) / len(pre_theoreticals), 2) if pre_theoreticals else 0
    post_avg_theoretical = round(sum(post_theoreticals) / len(post_theoreticals), 2) if post_theoreticals else 0

    weather_coeff = calc_weather_sunshine_coeff(panel_group, actual_date, 7)

    consecutive_low = 0
    check_date = actual_date - timedelta(days=1)
    while check_date >= pre_start:
        try:
            prev_gen = DailyGeneration.objects.get(panel_group=panel_group, date=check_date)
            if prev_gen.theoretical_kwh > 0 and prev_gen.actual_kwh / prev_gen.theoretical_kwh < 0.7:
                consecutive_low += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        except DailyGeneration.DoesNotExist:
            break

    try:
        pre_diag = HealthDiagnosis.objects.get(
            device_type='panel_group', device_id=panel_group.id, date=pre_end
        )
        health_before = pre_diag.health_score
    except HealthDiagnosis.DoesNotExist:
        pre_diags = HealthDiagnosis.objects.filter(
            device_type='panel_group', device_id=panel_group.id,
            date__gte=pre_start, date__lte=pre_end
        ).order_by('-date')
        health_before = pre_diags.first().health_score if pre_diags.exists() else 80

    try:
        post_diag = HealthDiagnosis.objects.get(
            device_type='panel_group', device_id=panel_group.id, date=post_end
        )
        health_after = post_diag.health_score
    except HealthDiagnosis.DoesNotExist:
        post_diags = HealthDiagnosis.objects.filter(
            device_type='panel_group', device_id=panel_group.id,
            date__gte=post_start, date__lte=post_end
        ).order_by('-date')
        health_after = post_diags.first().health_score if post_diags.exists() else health_before

    method_coeff_map = {'manual': 0.92, 'water': 0.98, 'dry': 0.85, 'robot': 0.95, 'rain': 0.65}
    method_coeff = method_coeff_map.get(cleaning_plan.cleaning_method, 0.9)

    weather_adjusted_eff_diff = 0
    if pre_avg_efficiency > 0 and post_avg_efficiency > 0:
        raw_diff = post_avg_efficiency - pre_avg_efficiency
        weather_adjusted_eff_diff = round(raw_diff / max(weather_coeff, 0.3), 2)

    if post_avg_theoretical > 0:
        base_kwh_per_day = post_avg_theoretical * max(weather_adjusted_eff_diff, 0) / 100
    else:
        base_kwh_per_day = max(post_avg_actual - pre_avg_actual, 0)
    recovered_per_day = round(base_kwh_per_day * method_coeff, 2)
    recovered_30_days = round(recovered_per_day * 30, 2)

    prices = get_electricity_prices()
    avg_sell_price = (prices['peak'] * 0.6 + prices['valley'] * 0.2 + prices['shoulder'] * 0.2)
    blended_price = round(avg_sell_price * 0.5 + prices['sell'] * 0.5, 4)
    extra_revenue_30d = round(recovered_30_days * blended_price, 2)

    actual_cost = cleaning_plan.actual_cost if cleaning_plan.actual_cost > 0 else cleaning_plan.estimated_cost
    if recovered_per_day > 0 and blended_price > 0:
        cost_recovery_days = int(actual_cost / (recovered_per_day * blended_price)) if recovered_per_day * blended_price > 0 else 9999
    else:
        cost_recovery_days = 9999

    eff_improvement = post_avg_efficiency - pre_avg_efficiency if pre_avg_efficiency > 0 else 0
    health_improvement = health_after - health_before
    deviation_reduction = pre_avg_deviation - post_avg_deviation

    score = 0
    if eff_improvement >= 20:
        score += 40
    elif eff_improvement >= 15:
        score += 30
    elif eff_improvement >= 10:
        score += 20
    elif eff_improvement >= 5:
        score += 10

    if deviation_reduction >= 20:
        score += 25
    elif deviation_reduction >= 15:
        score += 18
    elif deviation_reduction >= 10:
        score += 12
    elif deviation_reduction >= 5:
        score += 6

    if health_improvement >= 20:
        score += 20
    elif health_improvement >= 10:
        score += 12
    elif health_improvement >= 5:
        score += 6

    if 0 <= cost_recovery_days <= 30:
        score += 15
    elif cost_recovery_days <= 60:
        score += 10
    elif cost_recovery_days <= 90:
        score += 5

    if score >= 75:
        effectiveness = 'excellent'
    elif score >= 55:
        effectiveness = 'good'
    elif score >= 35:
        effectiveness = 'fair'
    elif score >= 15:
        effectiveness = 'poor'
    else:
        effectiveness = 'poor'

    if post_avg_efficiency == 0 or pre_avg_efficiency >= post_avg_efficiency:
        effectiveness = 'poor'

    evaluation_detail = {
        'pre_daily_records': [
            {'date': r.date.isoformat(), 'actual_kwh': r.actual_kwh, 'theoretical_kwh': r.theoretical_kwh,
             'efficiency': round(r.actual_kwh / r.theoretical_kwh * 100, 2) if r.theoretical_kwh > 0 else 0}
            for r in pre_records.order_by('date')
        ],
        'post_daily_records': [
            {'date': r.date.isoformat(), 'actual_kwh': r.actual_kwh, 'theoretical_kwh': r.theoretical_kwh,
             'efficiency': round(r.actual_kwh / r.theoretical_kwh * 100, 2) if r.theoretical_kwh > 0 else 0}
            for r in post_records.order_by('date')
        ],
        'pre_avg_efficiency': pre_avg_efficiency,
        'post_avg_efficiency': post_avg_efficiency,
        'efficiency_improvement': round(eff_improvement, 2),
        'pre_avg_deviation': pre_avg_deviation,
        'post_avg_deviation': post_avg_deviation,
        'deviation_reduction': round(deviation_reduction, 1),
        'health_before': health_before,
        'health_after': health_after,
        'health_improvement': round(health_improvement, 1),
        'weather_sunshine_coeff': weather_coeff,
        'cleaning_method_coeff': method_coeff,
        'consecutive_low_days': consecutive_low,
        'recovered_kwh_per_day': recovered_per_day,
        'recovered_kwh_30d': recovered_30_days,
        'blended_electricity_price': blended_price,
        'extra_revenue_30d': extra_revenue_30d,
        'actual_cost': actual_cost,
        'cost_recovery_days': cost_recovery_days,
        'evaluation_score': score,
    }

    return {
        'pre_avg_efficiency': pre_avg_efficiency,
        'post_avg_efficiency': post_avg_efficiency,
        'pre_avg_deviation': pre_avg_deviation,
        'post_avg_deviation': post_avg_deviation,
        'consecutive_low_days': consecutive_low,
        'weather_sunshine_coeff': weather_coeff,
        'health_score_before': health_before,
        'health_score_after': health_after,
        'recovered_generation_kwh': recovered_30_days,
        'extra_revenue': extra_revenue_30d,
        'cost_recovery_days': cost_recovery_days,
        'effectiveness_level': effectiveness,
        'evaluation_detail': evaluation_detail,
        'evaluated_at': timezone.now(),
    }


class CleaningPlanViewSet(viewsets.ModelViewSet):
    queryset = CleaningPlan.objects.all()
    serializer_class = CleaningPlanSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        panel_group = self.request.query_params.get('panel_group')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        status = self.request.query_params.get('status')
        effectiveness = self.request.query_params.get('effectiveness')

        if panel_group:
            qs = qs.filter(panel_group_id=panel_group)
        if date_from:
            qs = qs.filter(plan_date__gte=date_from)
        if date_to:
            qs = qs.filter(plan_date__lte=date_to)
        if status:
            qs = qs.filter(status=status)
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
        today = date.today()
        month_start = today.replace(day=1)

        pending_count = CleaningPlan.objects.filter(status='pending').count()
        upcoming_7d = CleaningPlan.objects.filter(
            status='pending',
            plan_date__gte=today,
            plan_date__lte=today + timedelta(days=7)
        ).count()
        overdue = CleaningPlan.objects.filter(
            status='pending',
            plan_date__lt=today
        ).count()
        completed_count = CleaningPlan.objects.filter(status='completed').count()
        month_completed = CleaningPlan.objects.filter(
            status='completed',
            actual_date__gte=month_start
        ).count()

        completed_plans = CleaningPlan.objects.filter(status='completed')
        total_recovered_kwh = sum(p.recovered_generation_kwh for p in completed_plans)
        total_extra_revenue = sum(p.extra_revenue for p in completed_plans)
        avg_recovery_days = 0
        if completed_plans.filter(cost_recovery_days__lt=9999).exists():
            valid = completed_plans.filter(cost_recovery_days__lt=9999)
            avg_recovery_days = int(sum(p.cost_recovery_days for p in valid) / valid.count())

        latest_cleaning = CleaningPlan.objects.filter(status='completed').order_by('-actual_date').first()
        latest_revenue = latest_cleaning.extra_revenue if latest_cleaning else 0
        latest_panel_group_name = latest_cleaning.panel_group.name if latest_cleaning else ''

        panel_group_contrib = []
        for pg in SolarPanelGroup.objects.all():
            pg_plans = CleaningPlan.objects.filter(panel_group=pg, status='completed')
            contrib = sum(p.extra_revenue for p in pg_plans)
            count = pg_plans.count()
            recovered = sum(p.recovered_generation_kwh for p in pg_plans)
            if count > 0:
                panel_group_contrib.append({
                    'id': pg.id,
                    'name': pg.name,
                    'cleaning_count': count,
                    'total_recovered_kwh': round(recovered, 2),
                    'total_extra_revenue': round(contrib, 2),
                })
        panel_group_contrib.sort(key=lambda x: x['total_extra_revenue'], reverse=True)

        return Response({
            'pending_count': pending_count,
            'upcoming_7d_count': upcoming_7d,
            'overdue_count': overdue,
            'completed_count': completed_count,
            'month_completed_count': month_completed,
            'total_recovered_kwh': round(total_recovered_kwh, 2),
            'total_extra_revenue': round(total_extra_revenue, 2),
            'avg_cost_recovery_days': avg_recovery_days,
            'latest_extra_revenue': round(latest_revenue, 2),
            'latest_panel_group_name': latest_panel_group_name,
            'panel_group_contribution': panel_group_contrib,
        })
