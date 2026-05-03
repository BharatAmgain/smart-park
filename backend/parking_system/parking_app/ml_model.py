"""
Machine Learning Model for Parking Availability Prediction
Uses Random Forest Classifier Algorithm
"""
import numpy as np
import pandas as pd
import joblib
import os
import json
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


class ParkingAvailabilityPredictor:
    """
    Random Forest Classifier for predicting parking slot availability

    Features used:
    - Time features: hour, day_of_week, is_weekend, month
    - Weather features: temperature, humidity, rainfall
    - Event features: is_holiday, is_event_nearby
    - Location features: zone_id, slot_type
    - Traffic features: traffic_level
    """

    def __init__(self, models_dir=None):
        self.models_dir = models_dir or Path(__file__).parent.parent / 'ml_models'
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_names = [
            'hour', 'day_of_week', 'is_weekend', 'month',
            'temperature', 'humidity', 'rainfall', 'is_holiday',
            'is_event_nearby', 'nearby_events_count', 'traffic_level_encoded',
            'zone_encoded', 'slot_type_encoded'
        ]

        self.load_model()

    def generate_training_data(self, n_samples=5000):
        """Generate synthetic training data for parking availability"""
        np.random.seed(42)

        data = []
        for _ in range(n_samples):
            hour = np.random.randint(0, 24)
            day_of_week = np.random.randint(0, 7)
            is_weekend = 1 if day_of_week >= 5 else 0
            month = np.random.randint(1, 13)

            temperature = np.random.normal(25, 5)
            humidity = np.random.normal(60, 15)
            rainfall = np.random.exponential(0.5)
            is_holiday = np.random.choice([0, 1], p=[0.95, 0.05])
            is_event_nearby = np.random.choice([0, 1], p=[0.8, 0.2])
            nearby_events_count = np.random.poisson(0.5)

            traffic_level = np.random.choice(['Low', 'Medium', 'High'], p=[0.3, 0.5, 0.2])
            zone = np.random.choice(['A', 'B', 'C', 'D', 'E'])
            slot_type = np.random.choice(['Regular', 'Compact', 'EV', 'Handicap'], p=[0.6, 0.2, 0.1, 0.1])

            # Calculate probability of availability based on features
            base_prob = 0.5

            # Time-based adjustments
            if 9 <= hour <= 11 or 14 <= hour <= 17:  # Peak hours
                base_prob -= 0.3
            elif hour < 7 or hour > 21:  # Late night
                base_prob += 0.3
            elif 12 <= hour <= 13:  # Lunch time
                base_prob -= 0.1

            # Weekend adjustment
            if is_weekend:
                base_prob += 0.2

            # Weather adjustment
            if rainfall > 2:
                base_prob -= 0.2
            if temperature > 35 or temperature < 0:
                base_prob -= 0.15

            # Event adjustment
            if is_event_nearby:
                base_prob -= 0.25

            # Zone adjustment
            premium_zones = ['D', 'E']
            if zone in premium_zones:
                base_prob += 0.1

            # Ensure probability is in [0, 1]
            probability = np.clip(base_prob + np.random.normal(0, 0.1), 0, 1)
            is_available = np.random.binomial(1, probability)

            data.append({
                'hour': hour,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'month': month,
                'temperature': temperature,
                'humidity': humidity,
                'rainfall': rainfall,
                'is_holiday': is_holiday,
                'is_event_nearby': is_event_nearby,
                'nearby_events_count': nearby_events_count,
                'traffic_level': traffic_level,
                'zone': zone,
                'slot_type': slot_type,
                'is_available': is_available
            })

        return pd.DataFrame(data)

    def train_model(self, force_retrain=False):
        """Train the Random Forest model"""
        print("🔄 Training Random Forest model for parking prediction...")

        # Check if model already exists
        model_path = self.models_dir / 'parking_model.pkl'
        if model_path.exists() and not force_retrain:
            print("✅ Model already exists. Loading existing model...")
            self.load_model()
            return True

        # Generate training data
        df = self.generate_training_data(10000)

        # Encode categorical variables
        categorical_cols = ['traffic_level', 'zone', 'slot_type']
        for col in categorical_cols:
            le = LabelEncoder()
            df[f'{col}_encoded'] = le.fit_transform(df[col])
            self.label_encoders[col] = le

        # Prepare features
        X = df[['hour', 'day_of_week', 'is_weekend', 'month', 'temperature', 'humidity',
                'rainfall', 'is_holiday', 'is_event_nearby', 'nearby_events_count',
                'traffic_level_encoded', 'zone_encoded', 'slot_type_encoded']]
        y = df['is_available']

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

        # Train Random Forest Classifier
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=12,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )

        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        print(f"📊 Random Forest Model Accuracy: {accuracy:.4f}")
        print("\n📋 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Not Available', 'Available']))

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("\n🎯 Top 5 Important Features:")
        for idx, row in feature_importance.head(5).iterrows():
            print(f"   - {row['feature']}: {row['importance']:.4f}")

        # Save model
        self.save_model()

        # Save feature importance
        feature_importance.to_csv(self.models_dir / 'feature_importance.csv', index=False)

        # Save model info
        model_info = {
            'algorithm': 'RandomForestClassifier',
            'accuracy': float(accuracy),
            'training_date': datetime.now().isoformat(),
            'n_estimators': 100,
            'max_depth': 12,
            'features': self.feature_names,
            'feature_importance': feature_importance.to_dict('records')
        }

        with open(self.models_dir / 'model_info.json', 'w') as f:
            json.dump(model_info, f, indent=2)

        print("✅ Random Forest model trained and saved successfully!")
        return True

    def save_model(self):
        """Save the trained model and scaler"""
        joblib.dump(self.model, self.models_dir / 'parking_model.pkl')
        joblib.dump(self.scaler, self.models_dir / 'scaler.pkl')
        joblib.dump(self.label_encoders, self.models_dir / 'label_encoders.pkl')

    def load_model(self):
        """Load the trained model"""
        model_path = self.models_dir / 'parking_model.pkl'
        scaler_path = self.models_dir / 'scaler.pkl'
        encoders_path = self.models_dir / 'label_encoders.pkl'

        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                if encoders_path.exists():
                    self.label_encoders = joblib.load(encoders_path)
                print("✅ Random Forest model loaded successfully!")
                return True
            except Exception as e:
                print(f"⚠️ Error loading model: {e}")
                return False
        else:
            print("⚠️ No existing model found. Training new model...")
            return self.train_model()

    def predict_availability(self, features):
        """
        Predict parking availability for given features

        Args:
            features: dict with keys like 'hour', 'day_of_week', 'zone_id', etc.

        Returns:
            dict with prediction results
        """
        if self.model is None:
            self.load_model()

        try:
            # Prepare feature vector
            feature_vector = self.prepare_features(features)

            # Scale features
            feature_scaled = self.scaler.transform([feature_vector])

            # Get prediction
            prediction = self.model.predict(feature_scaled)[0]
            probability = self.model.predict_proba(feature_scaled)[0]

            # Get confidence
            confidence = max(probability)

            result = {
                'is_available': bool(prediction),
                'availability_probability': float(probability[1] if len(probability) > 1 else probability[0]),
                'confidence': float(confidence),
                'prediction': 'Available' if prediction else 'Likely Occupied',
                'recommendation': self.get_recommendation(features, prediction, confidence)
            }

            return result

        except Exception as e:
            print(f"⚠️ Prediction error: {e}")
            return {
                'is_available': True,
                'availability_probability': 0.5,
                'confidence': 0.5,
                'prediction': 'Unknown',
                'recommendation': 'Please check manually'
            }

    def prepare_features(self, features):
        """Prepare features for model input"""
        # Default values
        hour = features.get('hour', datetime.now().hour)
        day_of_week = features.get('day_of_week', datetime.now().weekday())
        is_weekend = 1 if day_of_week >= 5 else 0
        month = features.get('month', datetime.now().month)
        temperature = features.get('temperature', 25)
        humidity = features.get('humidity', 60)
        rainfall = features.get('rainfall', 0)
        is_holiday = features.get('is_holiday', 0)
        is_event_nearby = features.get('is_event_nearby', 0)
        nearby_events_count = features.get('nearby_events_count', 0)
        traffic_level = features.get('traffic_level', 'Medium')
        zone = features.get('zone_id', 'A')
        slot_type = features.get('slot_type', 'Regular')

        # Encode categorical features
        traffic_encoded = self.label_encoders.get('traffic_level', LabelEncoder())
        zone_encoded = self.label_encoders.get('zone', LabelEncoder())
        slot_encoded = self.label_encoders.get('slot_type', LabelEncoder())

        try:
            traffic_val = traffic_encoded.transform([traffic_level])[0] if hasattr(traffic_encoded, 'transform') else 1
        except:
            traffic_val = 1

        try:
            zone_val = zone_encoded.transform([zone])[0] if hasattr(zone_encoded, 'transform') else 0
        except:
            zone_val = 0

        try:
            slot_val = slot_encoded.transform([slot_type])[0] if hasattr(slot_encoded, 'transform') else 0
        except:
            slot_val = 0

        return [
            hour, day_of_week, is_weekend, month,
            temperature, humidity, rainfall, is_holiday,
            is_event_nearby, nearby_events_count,
            traffic_val, zone_val, slot_val
        ]

    def get_recommendation(self, features, prediction, confidence):
        """Generate recommendation based on prediction"""
        if prediction:
            if confidence > 0.8:
                return "High confidence: Parking likely available. Proceed to park."
            elif confidence > 0.6:
                return "Medium confidence: Parking may be available. Check nearby slots."
            else:
                return "Low confidence prediction. Consider alternative parking zones."
        else:
            if confidence > 0.8:
                return "High confidence: Parking likely occupied. Try nearby zones."
            elif confidence > 0.6:
                return "Medium confidence: Parking may be occupied. Check availability."
            else:
                return "Low confidence prediction. Check parking manually."

    def predict_batch(self, features_list):
        """Predict for multiple feature sets"""
        results = []
        for features in features_list:
            results.append(self.predict_availability(features))
        return results

    def get_peak_hours_prediction(self, zone_id='A'):
        """Predict availability for all hours of the day"""
        predictions = []
        current_day = datetime.now().weekday()

        for hour in range(24):
            features = {
                'hour': hour,
                'day_of_week': current_day,
                'zone_id': zone_id,
                'slot_type': 'Regular',
                'temperature': 25,
                'humidity': 60,
                'rainfall': 0
            }
            result = self.predict_availability(features)
            predictions.append({
                'hour': hour,
                'availability_probability': result['availability_probability'],
                'prediction': result['prediction']
            })

        return predictions


# Global instance
predictor = ParkingAvailabilityPredictor()