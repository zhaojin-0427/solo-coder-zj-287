from datetime import date, timedelta

from ..models import (
    SolarPanelGroup, Inverter, DailyGeneration, HealthDiagnosis
)
from ..serializers import HealthDiagnosisSerializer


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
