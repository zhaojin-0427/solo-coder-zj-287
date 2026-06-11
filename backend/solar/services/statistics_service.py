import math
from datetime import date, timedelta, datetime

from ..models import (
    SolarPanelGroup, Inverter, DailyGeneration, RevenueRecord,
    HealthDiagnosis, StorageBattery, StorageSchedule, CleaningPlan,
    HouseholdUsage
)
from .generation_service import calc_theoretical_kwh


def get_dashboard_data():
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

    return {
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
    }


def get_statistics_data(months=12):
    today = date.today()
    start_date = today - timedelta(days=months * 30)

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

    return {
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
    }


def get_payback_prediction():
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

    return {
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
    }


def get_alert_summary():
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

    return {
        'unhandled_count': unhandled_count,
        'highest_level': highest_level,
        'level_counts': level_counts,
        'recent_7_health': recent_7_health,
    }


def get_storage_summary():
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

    return {
        'battery_count': batteries.count(),
        'active_battery_count': active_count,
        'total_capacity_kwh': total_capacity,
        'today_current_soc': avg_soc,
        'today_charge_kwh': round(today_charge, 2),
        'today_discharge_kwh': round(today_discharge, 2),
        'today_storage_profit': round(today_profit, 2),
        'month_storage_profit': round(month_profit, 2),
        'month_reduced_curtailment_kwh': round(month_reduced_curtailment, 2),
    }


def get_cleaning_summary():
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

    return {
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
    }
