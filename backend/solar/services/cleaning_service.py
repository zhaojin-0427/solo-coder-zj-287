from datetime import date, timedelta
from django.utils import timezone

from ..models import (
    CleaningPlan, DailyGeneration, HealthDiagnosis, SolarPanelGroup
)
from .generation_service import (
    get_electricity_prices, AVERAGE_SUNSHINE_HOURS
)


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
