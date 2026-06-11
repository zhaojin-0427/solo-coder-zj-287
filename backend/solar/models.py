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
