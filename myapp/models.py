from django.db import models


class ClimateData(models.Model):
    date = models.DateField()
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    wind_speed = models.DecimalField(max_digits=5, decimal_places=2)

    # Add more fields as needed

    def __str__(self):
        return f"Climate data for {self.date}"


class UserSubscription(models.Model):
    email = models.EmailField()
    subscription_arn = models.CharField(max_length=255, blank=True, null=True)

    # Add more fields as needed

    def __str__(self):
        return self.email
