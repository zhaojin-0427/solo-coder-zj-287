import math
from datetime import date, timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import Inverter, SolarPanelGroup, DailyGeneration, HouseholdUsage, ElectricityPrice, RevenueRecord
from .serializers import (
    InverterSerializer, SolarPanelGroupSerializer, DailyGenerationSerializer,
    HouseholdUsageSerializer, ElectricityPriceSerializer, RevenueRecordSerializer
)


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


@api_view(['POST'])
def import_generation_data(request):
    data = request.data
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
        return Response(DailyGenerationSerializer(obj).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def calculate_revenue(request):
    dt = request.data.get('date')
    if not dt:
        return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)

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

    return Response({
        'generation_trend': generation_trend,
        'self_use_rate_trend': self_use_rate_trend,
        'peak_valley_match': peak_valley_match,
        'payback_pct': payback_pct,
        'total_investment': total_investment,
        'total_revenue': round(total_revenue, 2),
        'irr': irr,
        'monthly_income': [{'month': k, 'income': round(monthly_income.get(k, 0), 2)} for k in all_keys],
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
    from datetime import date, timedelta
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

    return Response({'message': 'Demo data seeded successfully'})
