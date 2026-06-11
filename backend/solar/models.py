from django.db import models


class Inverter(models.Model):
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    rated_power = models.FloatField(help_text='kW')
    efficiency = models.FloatField(help_text='%')
    api_endpoint = models.CharField(max_length=500, blank=True, default='')
    api_key = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.brand} {self.model}'


class SolarPanelGroup(models.Model):
    name = models.CharField(max_length=200)
    capacity_kw = models.FloatField()
    install_angle = models.FloatField(help_text='degrees')
    azimuth = models.FloatField(default=180, help_text='degrees, 180=south')
    inverter = models.ForeignKey(Inverter, on_delete=models.SET_NULL, null=True, blank=True, related_name='panel_groups')
    grid_date = models.DateField()
    location = models.CharField(max_length=200, default='', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name


class DailyGeneration(models.Model):
    panel_group = models.ForeignKey(SolarPanelGroup, on_delete=models.CASCADE, related_name='daily_records')
    date = models.DateField()
    actual_kwh = models.FloatField(default=0)
    theoretical_kwh = models.FloatField(default=0)
    peak_kwh = models.FloatField(default=0, help_text='kWh generated during peak hours')
    valley_kwh = models.FloatField(default=0, help_text='kWh generated during valley hours')
    sunshine_hours = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['panel_group', 'date']

    def __str__(self):
        return f'{self.panel_group.name} - {self.date}'


class HouseholdUsage(models.Model):
    date = models.DateField()
    total_kwh = models.FloatField(default=0)
    peak_kwh = models.FloatField(default=0)
    valley_kwh = models.FloatField(default=0)
    shoulder_kwh = models.FloatField(default=0)
    self_use_kwh = models.FloatField(default=0, help_text='kWh from solar used by household')
    grid_buy_kwh = models.FloatField(default=0, help_text='kWh bought from grid')
    grid_sell_kwh = models.FloatField(default=0, help_text='kWh sold to grid')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['date']

    def __str__(self):
        return f'Usage - {self.date}'


class ElectricityPrice(models.Model):
    price_type = models.CharField(max_length=50, choices=[
        ('grid_buy_peak', 'grid_buy_peak'),
        ('grid_buy_valley', 'grid_buy_valley'),
        ('grid_buy_shoulder', 'grid_buy_shoulder'),
        ('grid_sell', 'grid_sell'),
    ])
    price = models.FloatField(help_text='yuan/kWh')
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_date']

    def __str__(self):
        return f'{self.price_type}: {self.price}'


class HealthDiagnosis(models.Model):
    LEVEL_CHOICES = [
        ('normal', '正常'),
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]
    ANOMALY_TYPE_CHOICES = [
        ('none', '无异常'),
        ('low_generation', '发电量偏低'),
        ('efficiency_drop', '逆变器效率下降'),
        ('consecutive_low', '连续低发电'),
        ('grid_issue', '并网异常'),
        ('peak_valley_abnormal', '峰谷分布异常'),
        ('deviation_high', '实际/理论偏差过大'),
    ]
    device_type = models.CharField(max_length=20, choices=[('panel_group', '光伏板组'), ('inverter', '逆变器')])
    device_id = models.IntegerField()
    device_name = models.CharField(max_length=200, default='')
    date = models.DateField()
    health_score = models.FloatField(default=100, help_text='0-100')
    anomaly_type = models.CharField(max_length=30, choices=ANOMALY_TYPE_CHOICES, default='none')
    anomaly_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='normal')
    possible_cause = models.TextField(default='', blank=True)
    handling_suggestion = models.TextField(default='', blank=True)
    deviation_rate = models.FloatField(default=0, help_text='actual/theoretical deviation %')
    inverter_efficiency = models.FloatField(default=0, help_text='%')
    consecutive_low_days = models.IntegerField(default=0)
    grid_days = models.IntegerField(default=0)
    peak_valley_ratio = models.FloatField(default=0, help_text='peak/valley ratio')
    is_handled = models.BooleanField(default=False)
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-anomaly_level']
        unique_together = ['device_type', 'device_id', 'date']

    def __str__(self):
        return f'{self.device_name} - {self.date} - {self.anomaly_level}'


class RevenueRecord(models.Model):
    date = models.DateField()
    panel_group = models.ForeignKey(SolarPanelGroup, on_delete=models.CASCADE, related_name='revenue_records')
    generation_kwh = models.FloatField(default=0)
    self_use_kwh = models.FloatField(default=0)
    grid_sell_kwh = models.FloatField(default=0)
    self_use_saving = models.FloatField(default=0, help_text='yuan saved by self-use')
    grid_sell_income = models.FloatField(default=0, help_text='yuan earned from selling to grid')
    total_income = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['date', 'panel_group']

    def __str__(self):
        return f'{self.panel_group.name} - {self.date}: {self.total_income}'


class StorageBattery(models.Model):
    STATUS_CHOICES = [
        ('normal', '正常'),
        ('warning', '告警'),
        ('maintenance', '维护中'),
    ]
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='')
    capacity_kwh = models.FloatField(help_text='额定容量 kWh')
    max_charge_power_kw = models.FloatField(help_text='最大充电功率 kW')
    max_discharge_power_kw = models.FloatField(help_text='最大放电功率 kW')
    charge_efficiency = models.FloatField(default=95, help_text='充电效率 %')
    discharge_efficiency = models.FloatField(default=95, help_text='放电效率 %')
    soc_upper_limit = models.FloatField(default=90, help_text='SOC上限 %')
    soc_lower_limit = models.FloatField(default=15, help_text='SOC下限 %')
    enable_date = models.DateField(help_text='启用日期')
    panel_groups = models.ManyToManyField(SolarPanelGroup, related_name='storage_batteries', blank=True)
    current_soc = models.FloatField(default=50, help_text='当前SOC %')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal')
    warning_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.name} ({self.capacity_kwh}kWh)'


class StorageSchedule(models.Model):
    battery = models.ForeignKey(StorageBattery, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    initial_soc = models.FloatField(default=50, help_text='初始SOC %')
    final_soc = models.FloatField(default=50, help_text='结束SOC %')
    charge_kwh = models.FloatField(default=0, help_text='实际充电量 kWh')
    discharge_kwh = models.FloatField(default=0, help_text='实际放电量 kWh')
    reduced_curtailment_kwh = models.FloatField(default=0, help_text='弃光减少量 kWh')
    peak_discharge_saving = models.FloatField(default=0, help_text='峰时放电节省电费 元')
    valley_charge_cost = models.FloatField(default=0, help_text='谷时充电成本 元')
    grid_income_change = models.FloatField(default=0, help_text='上网收益变化 元')
    total_profit_diff = models.FloatField(default=0, help_text='储能参与后总收益差额 元')
    hourly_soc = models.JSONField(default=list, help_text='24小时SOC数组')
    hourly_charge_discharge = models.JSONField(default=list, help_text='24小时充放电明细 (正=充电, 负=放电)')
    hourly_detail = models.JSONField(default=dict, help_text='详细小时级数据')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['battery', 'date']

    def __str__(self):
        return f'{self.battery.name} - {self.date}: 收益+{self.total_profit_diff}'


class CleaningPlan(models.Model):
    CLEANING_METHOD_CHOICES = [
        ('manual', '人工清洁'),
        ('water', '水洗清洁'),
        ('dry', '干洗清洁'),
        ('robot', '机器人清洁'),
        ('rain', '雨水自洁'),
    ]
    EFFECTIVENESS_LEVEL_CHOICES = [
        ('excellent', '优秀'),
        ('good', '良好'),
        ('fair', '一般'),
        ('poor', '较差'),
        ('none', '未评估'),
    ]
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    panel_group = models.ForeignKey(SolarPanelGroup, on_delete=models.CASCADE, related_name='cleaning_plans')
    plan_name = models.CharField(max_length=200, default='常规清洁')
    cleaning_method = models.CharField(max_length=30, choices=CLEANING_METHOD_CHOICES, default='manual')
    estimated_cost = models.FloatField(default=0, help_text='预计费用 元')
    actual_cost = models.FloatField(default=0, help_text='实际费用 元')
    operator = models.CharField(max_length=100, default='', blank=True, help_text='执行人员')
    plan_date = models.DateField(help_text='计划日期')
    actual_date = models.DateField(null=True, blank=True, help_text='实际完成日期')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(default='', blank=True, help_text='备注')

    pre_avg_efficiency = models.FloatField(default=0, help_text='清洁前7日平均发电效率 %')
    post_avg_efficiency = models.FloatField(default=0, help_text='清洁后7日平均发电效率 %')
    pre_avg_deviation = models.FloatField(default=0, help_text='清洁前7日平均偏差率 %')
    post_avg_deviation = models.FloatField(default=0, help_text='清洁后7日平均偏差率 %')
    consecutive_low_days = models.IntegerField(default=0, help_text='清洁前连续低发电天数')
    weather_sunshine_coeff = models.FloatField(default=1.0, help_text='天气日照系数')
    health_score_before = models.FloatField(default=0, help_text='清洁前健康评分')
    health_score_after = models.FloatField(default=0, help_text='清洁后健康评分')

    recovered_generation_kwh = models.FloatField(default=0, help_text='发电恢复量 kWh')
    extra_revenue = models.FloatField(default=0, help_text='额外收益 元')
    cost_recovery_days = models.IntegerField(default=0, help_text='费用回收天数')
    effectiveness_level = models.CharField(max_length=20, choices=EFFECTIVENESS_LEVEL_CHOICES, default='none')
    evaluation_detail = models.JSONField(default=dict, help_text='评估详细数据')
    evaluated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-plan_date', '-id']

    def __str__(self):
        return f'{self.panel_group.name} - {self.plan_date} - {self.get_status_display()}'
