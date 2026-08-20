from django.db import models

class WeatherCondition(models.TextChoices):
    SUNNY = "sunny", "Sunny"
    PARTLY_CLOUDY = "partly_cloudy", "Partly Cloudy"
    CLOUDY = "cloudy", "Cloudy"
    WINDY = "windy", "Windy"
    LIGHT_RAIN = "light_rain", "Light Rain"
    HEAVY_RAIN = "heavy_rain", "Heavy Rain"
    STORM = "storm", "Storm"
    VERY_HOT = "very_hot", "Very Hot"
    COLD = "cold", "Cold"
    EXTREME = "extreme", "Extreme Weather"