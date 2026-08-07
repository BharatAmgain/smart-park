"""
Feature engineering for parking prediction
"""
import numpy as np
from datetime import datetime


class FeatureEngineering:
    """Engineer features for ML model"""

    @staticmethod
    def create_time_features(hour, day_of_week):
        """Create cyclical time features"""
        return {
            'hour_sin': np.sin(2 * np.pi * hour / 24),
            'hour_cos': np.cos(2 * np.pi * hour / 24),
            'day_sin': np.sin(2 * np.pi * day_of_week / 7),
            'day_cos': np.cos(2 * np.pi * day_of_week / 7),
            'is_weekend': 1 if day_of_week >= 5 else 0,
            'is_peak_hour': 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
        }

    @staticmethod
    def create_weather_features(temperature, humidity, rainfall):
        """Create weather impact features"""
        weather_score = 1.0
        if rainfall > 5:
            weather_score -= 0.3
        if temperature > 35 or temperature < 0:
            weather_score -= 0.2
        if humidity > 80:
            weather_score -= 0.1
        return {
            'weather_score': max(0, min(1, weather_score)),
            'is_bad_weather': 1 if (rainfall > 5 or temperature > 35 or temperature < 0) else 0
        }

    @staticmethod
    def create_traffic_features(traffic_level):
        """Create traffic features"""
        traffic_map = {'Low': 1, 'Medium': 2, 'High': 3}
        return {
            'traffic_score': traffic_map.get(traffic_level, 2),
            'traffic_encoded': traffic_map.get(traffic_level, 2) / 3
        }


feature_engineering = FeatureEngineering()