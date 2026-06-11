from datetime import date, timedelta
from django.utils import timezone

from ..models import (
    StorageBattery, StorageSchedule, DailyGeneration,
    HouseholdUsage, HealthDiagnosis, Inverter
)
from ..serializers import StorageScheduleSerializer
from .generation_service import (
    get_electricity_prices, get_hour_price,
    generate_hourly_profile,
    SOLAR_GENERATION_PROFILE, HOUSEHOLD_USAGE_PROFILE
)


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

        elif h in list(range(0, 6)) + list(range(22, 24)) and price < prices['peak'] * 0.6 and available_charge_space > capacity * 0.2:
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
            'price_type': 'peak' if h in [h for h in range(8, 12)] + list(range(17, 22)) else ('valley' if h in [h for h in range(0, 6)] + list(range(22, 24)) else 'shoulder'),
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
