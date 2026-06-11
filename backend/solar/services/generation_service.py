from datetime import date, timedelta

from ..models import (
    DailyGeneration, SolarPanelGroup, HouseholdUsage,
    ElectricityPrice, RevenueRecord
)
from ..serializers import RevenueRecordSerializer


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


def calc_revenue_for_date(dt):
    if isinstance(dt, str):
        dt = date.fromisoformat(dt)
    prices = get_electricity_prices()

    peak_price = prices['peak']
    valley_price = prices['valley']
    sell_price = prices['sell']

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


def import_generation_item(item):
    panel_group_id = item.get('panel_group')
    dt = item.get('date')
    actual_kwh = item.get('actual_kwh', 0)
    try:
        pg = SolarPanelGroup.objects.get(pk=panel_group_id)
    except SolarPanelGroup.DoesNotExist:
        return None
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
    return obj
