"""
SmartPark Database Initialization Script
Kathmandu Valley - Complete Parking Zone Coverage (350+ ZONES)
"""

import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings')
django.setup()

from parking_app.models import ParkingZone, ParkingSlot
from django.contrib.auth.models import User

# ============================================
# REASONABLE PRICE MAPPING BY ZONE TYPE
# ============================================
REASONABLE_PRICES = {
    'park': 20,
    'government': 25,
    'hospital': 30,
    'educational': 25,
    'heritage': 35,
    'commercial': 35,
    'shopping': 30,
    'cinema': 30,
    'office': 35,
    'airport': 50,
    'regular': 30,
    'default': 30
}


def get_reasonable_price(zone_type):
    """Get reasonable price based on zone type"""
    return REASONABLE_PRICES.get(zone_type, REASONABLE_PRICES['default'])


def init_database():
    print("=" * 70)
    print("🚗 SMART PARKING SYSTEM - FULL KATHMANDU VALLEY COVERAGE (350+ ZONES)")
    print("=" * 70)

    # Delete existing data
    print("🗑️ Clearing existing data...")
    ParkingSlot.objects.all().delete()
    ParkingZone.objects.all().delete()
    print("✅ Existing data cleared")
    print("")

    # ============================================================
    # 150+ ZONES COVERING ALL MUNICIPALITIES OF KATHMANDU DISTRICT
    # Includes: Kathmandu Metropolitan, Lalitpur Metropolitan,
    # Bhaktapur Municipality, Kirtipur Municipality, Madhyapur Thimi,
    # and all major areas (Thamel, Boudha, Pashupati, Airport, etc.)
    # ============================================================
    zones_data = [
        # ========== KATHMANDU METROPOLITAN CITY (Wards 1-32) ==========
        {'zone_id': 'KMC1', 'name': 'Kathmandu Durbar Square', 'zone_type': 'heritage', 'capacity': 40,
         'hourly_rate': 50, 'lat': 27.7042, 'lng': 85.3070},
        {'zone_id': 'KMC2', 'name': 'Thamel Chowk', 'zone_type': 'commercial', 'capacity': 60, 'hourly_rate': 50,
         'lat': 27.7150, 'lng': 85.3110},
        {'zone_id': 'KMC3', 'name': 'New Road Gate', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 50,
         'lat': 27.7030, 'lng': 85.3120},
        {'zone_id': 'KMC4', 'name': 'Basantapur', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.7035, 'lng': 85.3080},
        {'zone_id': 'KMC5', 'name': 'Asan Bazar', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 45,
         'lat': 27.7060, 'lng': 85.3050},
        {'zone_id': 'KMC6', 'name': 'Indrachowk', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.7070, 'lng': 85.3060},
        {'zone_id': 'KMC7', 'name': 'Ratna Park', 'zone_type': 'park', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7020, 'lng': 85.3160},
        {'zone_id': 'KMC8', 'name': 'Tundikhel', 'zone_type': 'park', 'capacity': 60, 'hourly_rate': 25,
         'lat': 27.7000, 'lng': 85.3100},
        {'zone_id': 'KMC9', 'name': 'Singha Durbar', 'zone_type': 'government', 'capacity': 55, 'hourly_rate': 30,
         'lat': 27.6980, 'lng': 85.3200},
        {'zone_id': 'KMC10', 'name': 'Babar Mahal', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6950, 'lng': 85.3150},
        {'zone_id': 'KMC11', 'name': 'Maitighar', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6930, 'lng': 85.3160},
        {'zone_id': 'KMC12', 'name': 'Baneshwor', 'zone_type': 'commercial', 'capacity': 60, 'hourly_rate': 45,
         'lat': 27.6900, 'lng': 85.3350},
        {'zone_id': 'KMC13', 'name': 'Gaushala', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.7050, 'lng': 85.3450},
        {'zone_id': 'KMC14', 'name': 'Chabahil', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7150, 'lng': 85.3500},
        {'zone_id': 'KMC15', 'name': 'Boudha Stupa', 'zone_type': 'heritage', 'capacity': 70, 'hourly_rate': 45,
         'lat': 27.7210, 'lng': 85.3450},
        {'zone_id': 'KMC16', 'name': 'Pashupatinath', 'zone_type': 'heritage', 'capacity': 80, 'hourly_rate': 45,
         'lat': 27.7100, 'lng': 85.3480},
        {'zone_id': 'KMC17', 'name': 'Gokarna Forest', 'zone_type': 'park', 'capacity': 45, 'hourly_rate': 50,
         'lat': 27.7300, 'lng': 85.4000},
        {'zone_id': 'KMC18', 'name': 'Sankhamul', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7000, 'lng': 85.3300},
        {'zone_id': 'KMC19', 'name': 'Sinamangal', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.7000, 'lng': 85.3550},
        {'zone_id': 'KMC20', 'name': 'Airport Area', 'zone_type': 'airport', 'capacity': 150, 'hourly_rate': 60,
         'lat': 27.6970, 'lng': 85.3590},
        {'zone_id': 'KMC21', 'name': 'Koteshwor', 'zone_type': 'commercial', 'capacity': 50, 'hourly_rate': 40,
         'lat': 27.6850, 'lng': 85.3550},
        {'zone_id': 'KMC22', 'name': 'Jadibuti', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6800, 'lng': 85.3600},
        {'zone_id': 'KMC23', 'name': 'Lokanthali', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.6700, 'lng': 85.3650},
        {'zone_id': 'KMC24', 'name': 'Balkumari', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6750, 'lng': 85.3400},
        {'zone_id': 'KMC25', 'name': 'Thapathali', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.6900, 'lng': 85.3250},
        {'zone_id': 'KMC26', 'name': 'Tripureshwor', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6950, 'lng': 85.3200},
        {'zone_id': 'KMC27', 'name': 'Kalimati', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7050, 'lng': 85.3000},
        {'zone_id': 'KMC28', 'name': 'Balaju', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7200, 'lng': 85.2900},
        {'zone_id': 'KMC29', 'name': 'Gongabu', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7300, 'lng': 85.3050},
        {'zone_id': 'KMC30', 'name': 'Kalanki', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.6950, 'lng': 85.2800},
        {'zone_id': 'KMC31', 'name': 'Thankot', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6800, 'lng': 85.2400},
        {'zone_id': 'KMC32', 'name': 'Swayambhu', 'zone_type': 'heritage', 'capacity': 50, 'hourly_rate': 40,
         'lat': 27.7150, 'lng': 85.2900},

        # ========== LALITPUR METROPOLITAN CITY ==========
        {'zone_id': 'LMC1', 'name': 'Patan Durbar Square', 'zone_type': 'heritage', 'capacity': 45, 'hourly_rate': 45,
         'lat': 27.6730, 'lng': 85.3250},
        {'zone_id': 'LMC2', 'name': 'Labim Mall', 'zone_type': 'shopping', 'capacity': 70, 'hourly_rate': 40,
         'lat': 27.6880, 'lng': 85.3320},
        {'zone_id': 'LMC3', 'name': 'Pulchowk Campus', 'zone_type': 'educational', 'capacity': 55, 'hourly_rate': 35,
         'lat': 27.6780, 'lng': 85.3310},
        {'zone_id': 'LMC4', 'name': 'Kupondole', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.6840, 'lng': 85.3280},
        {'zone_id': 'LMC5', 'name': 'Jawalakhel', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6750, 'lng': 85.3220},
        {'zone_id': 'LMC6', 'name': 'Lagankhel', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6780, 'lng': 85.3250},
        {'zone_id': 'LMC7', 'name': 'Satdobato', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.6700, 'lng': 85.3350},
        {'zone_id': 'LMC8', 'name': 'Godawari', 'zone_type': 'park', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6100, 'lng': 85.3700},
        {'zone_id': 'LMC9', 'name': 'Khumaltar', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6650, 'lng': 85.3200},
        {'zone_id': 'LMC10', 'name': 'Sanepa', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6800, 'lng': 85.3300},

        # ========== BHAKTAPUR MUNICIPALITY ==========
        {'zone_id': 'BKT1', 'name': 'Bhaktapur Durbar Square', 'zone_type': 'heritage', 'capacity': 55,
         'hourly_rate': 40, 'lat': 27.6720, 'lng': 85.4280},
        {'zone_id': 'BKT2', 'name': 'Changunarayan Temple', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7000, 'lng': 85.4280},
        {'zone_id': 'BKT3', 'name': 'Suryavinayak', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.6600, 'lng': 85.4200},
        {'zone_id': 'BKT4', 'name': 'Thimi (Madhyapur)', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.6800, 'lng': 85.3900},
        {'zone_id': 'BKT5', 'name': 'Nagarkot Viewpoint', 'zone_type': 'heritage', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.7150, 'lng': 85.5200},

        # ========== KIRTIPUR MUNICIPALITY ==========
        {'zone_id': 'KIR1', 'name': 'Kirtipur Village', 'zone_type': 'heritage', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.6780, 'lng': 85.2850},
        {'zone_id': 'KIR2', 'name': 'TU Kirtipur Campus', 'zone_type': 'educational', 'capacity': 70, 'hourly_rate': 30,
         'lat': 27.6780, 'lng': 85.2800},
        {'zone_id': 'KIR3', 'name': 'Chobhar', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6600, 'lng': 85.2600},

        # ========== HOSPITALS (15) ==========
        {'zone_id': 'HOSP1', 'name': 'Bir Hospital', 'zone_type': 'hospital', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.7000, 'lng': 85.3180},
        {'zone_id': 'HOSP2', 'name': 'Teaching Hospital (TUTH)', 'zone_type': 'hospital', 'capacity': 40,
         'hourly_rate': 35, 'lat': 27.7220, 'lng': 85.3320},
        {'zone_id': 'HOSP3', 'name': 'Norvic Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.7140, 'lng': 85.3240},
        {'zone_id': 'HOSP4', 'name': 'Mediciti Hospital', 'zone_type': 'hospital', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.6800, 'lng': 85.3400},
        {'zone_id': 'HOSP5', 'name': 'Patan Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6700, 'lng': 85.3260},
        {'zone_id': 'HOSP6', 'name': 'B&B Hospital', 'zone_type': 'hospital', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.6850, 'lng': 85.3350},
        {'zone_id': 'HOSP7', 'name': 'Nepal Mediciti', 'zone_type': 'hospital', 'capacity': 50, 'hourly_rate': 45,
         'lat': 27.6770, 'lng': 85.3380},
        {'zone_id': 'HOSP8', 'name': 'Grande Hospital', 'zone_type': 'hospital', 'capacity': 45, 'hourly_rate': 50,
         'lat': 27.7250, 'lng': 85.2900},
        {'zone_id': 'HOSP9', 'name': 'Kanti Children Hospital', 'zone_type': 'hospital', 'capacity': 30,
         'hourly_rate': 30, 'lat': 27.7050, 'lng': 85.3150},
        {'zone_id': 'HOSP10', 'name': 'Civil Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6900, 'lng': 85.3000},
        {'zone_id': 'HOSP11', 'name': 'Om Hospital', 'zone_type': 'hospital', 'capacity': 25, 'hourly_rate': 40,
         'lat': 27.7100, 'lng': 85.3280},
        {'zone_id': 'HOSP12', 'name': 'Neuro Hospital', 'zone_type': 'hospital', 'capacity': 30, 'hourly_rate': 45,
         'lat': 27.6950, 'lng': 85.3250},
        {'zone_id': 'HOSP13', 'name': 'Vayodha Hospital', 'zone_type': 'hospital', 'capacity': 28, 'hourly_rate': 40,
         'lat': 27.6780, 'lng': 85.3420},
        {'zone_id': 'HOSP14', 'name': 'Star Hospital', 'zone_type': 'hospital', 'capacity': 32, 'hourly_rate': 38,
         'lat': 27.7150, 'lng': 85.3100},
        {'zone_id': 'HOSP15', 'name': 'Bhaktapur Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6720, 'lng': 85.4280},

        # ========== SHOPPING MALLS (20) ==========
        {'zone_id': 'MALL1', 'name': 'City Center Mall', 'zone_type': 'shopping', 'capacity': 90, 'hourly_rate': 40,
         'lat': 27.6950, 'lng': 85.3220},
        {'zone_id': 'MALL2', 'name': 'Civil Mall', 'zone_type': 'shopping', 'capacity': 80, 'hourly_rate': 45,
         'lat': 27.6920, 'lng': 85.3260},
        {'zone_id': 'MALL3', 'name': 'Durbar Mall', 'zone_type': 'shopping', 'capacity': 60, 'hourly_rate': 45,
         'lat': 27.6800, 'lng': 85.3100},
        {'zone_id': 'MALL4', 'name': 'Bhatbhateni Banasthali', 'zone_type': 'shopping', 'capacity': 55,
         'hourly_rate': 35, 'lat': 27.7100, 'lng': 85.3050},
        {'zone_id': 'MALL5', 'name': 'Bhatbhateni Kalanki', 'zone_type': 'shopping', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.6950, 'lng': 85.2850},
        {'zone_id': 'MALL6', 'name': 'Big Mart Chakrapath', 'zone_type': 'shopping', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7250, 'lng': 85.3400},
        {'zone_id': 'MALL7', 'name': 'BG Mall Baneshwor', 'zone_type': 'shopping', 'capacity': 65, 'hourly_rate': 45,
         'lat': 27.6900, 'lng': 85.3280},
        {'zone_id': 'MALL8', 'name': 'Lotes Mall Kupondole', 'zone_type': 'shopping', 'capacity': 60, 'hourly_rate': 45,
         'lat': 27.6850, 'lng': 85.3300},
        {'zone_id': 'MALL9', 'name': 'City Square Kamaladi', 'zone_type': 'shopping', 'capacity': 75, 'hourly_rate': 50,
         'lat': 27.7100, 'lng': 85.3150},
        {'zone_id': 'MALL10', 'name': 'Khumaltar Mall', 'zone_type': 'shopping', 'capacity': 50, 'hourly_rate': 40,
         'lat': 27.6650, 'lng': 85.3200},
        {'zone_id': 'MALL11', 'name': 'Nepal Life Mall', 'zone_type': 'shopping', 'capacity': 45, 'hourly_rate': 45,
         'lat': 27.6800, 'lng': 85.3220},
        {'zone_id': 'MALL12', 'name': 'Ace Mall', 'zone_type': 'shopping', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.6920, 'lng': 85.3350},
        {'zone_id': 'MALL13', 'name': 'Ghar Plaza', 'zone_type': 'shopping', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7000, 'lng': 85.3100},
        {'zone_id': 'MALL14', 'name': 'Bluebird Mall', 'zone_type': 'shopping', 'capacity': 50, 'hourly_rate': 45,
         'lat': 27.6880, 'lng': 85.3250},
        {'zone_id': 'MALL15', 'name': 'Chakrapath Mall', 'zone_type': 'shopping', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.7300, 'lng': 85.3350},
        {'zone_id': 'MALL16', 'name': 'Gongabu Mall', 'zone_type': 'shopping', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7300, 'lng': 85.3050},
        {'zone_id': 'MALL17', 'name': 'New Road Gate', 'zone_type': 'shopping', 'capacity': 35, 'hourly_rate': 50,
         'lat': 27.7030, 'lng': 85.3120},
        {'zone_id': 'MALL18', 'name': 'Thamel Square', 'zone_type': 'shopping', 'capacity': 55, 'hourly_rate': 50,
         'lat': 27.7150, 'lng': 85.3100},
        {'zone_id': 'MALL19', 'name': 'Jawalakhel Mall', 'zone_type': 'shopping', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.6750, 'lng': 85.3220},
        {'zone_id': 'MALL20', 'name': 'Labim Mall', 'zone_type': 'shopping', 'capacity': 70, 'hourly_rate': 40,
         'lat': 27.6880, 'lng': 85.3320},

        # ========== CINEMAS (8) ==========
        {'zone_id': 'CINE1', 'name': 'QFX Civil Mall', 'zone_type': 'cinema', 'capacity': 45, 'hourly_rate': 45,
         'lat': 27.6920, 'lng': 85.3260},
        {'zone_id': 'CINE2', 'name': 'Big Movies Jai Nepal', 'zone_type': 'cinema', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.7030, 'lng': 85.3150},
        {'zone_id': 'CINE3', 'name': 'QFX Kumari', 'zone_type': 'cinema', 'capacity': 50, 'hourly_rate': 45,
         'lat': 27.6840, 'lng': 85.3200},
        {'zone_id': 'CINE4', 'name': 'Fcube Cinemas', 'zone_type': 'cinema', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6880, 'lng': 85.3350},
        {'zone_id': 'CINE5', 'name': 'Ranjan Cinema', 'zone_type': 'cinema', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7040, 'lng': 85.3120},
        {'zone_id': 'CINE6', 'name': 'QFX Chhaya Center', 'zone_type': 'cinema', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.7000, 'lng': 85.3150},
        {'zone_id': 'CINE7', 'name': 'INOX Civil Mall', 'zone_type': 'cinema', 'capacity': 45, 'hourly_rate': 45,
         'lat': 27.6920, 'lng': 85.3260},
        {'zone_id': 'CINE8', 'name': 'Movie Garden', 'zone_type': 'cinema', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7100, 'lng': 85.3080},

        # ========== EDUCATIONAL INSTITUTIONS (15) ==========
        {'zone_id': 'EDU1', 'name': 'Pulchowk Campus (IOE)', 'zone_type': 'educational', 'capacity': 55,
         'hourly_rate': 35, 'lat': 27.6780, 'lng': 85.3310},
        {'zone_id': 'EDU2', 'name': 'TU Kirtipur', 'zone_type': 'educational', 'capacity': 70, 'hourly_rate': 30,
         'lat': 27.6780, 'lng': 85.2800},
        {'zone_id': 'EDU3', 'name': 'KU Medical School', 'zone_type': 'educational', 'capacity': 50, 'hourly_rate': 30,
         'lat': 27.7200, 'lng': 85.3500},
        {'zone_id': 'EDU4', 'name': 'Nepal Law Campus', 'zone_type': 'educational', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.6980, 'lng': 85.3180},
        {'zone_id': 'EDU5', 'name': 'St. Xavier College', 'zone_type': 'educational', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7100, 'lng': 85.3250},
        {'zone_id': 'EDU6', 'name': 'Kathmandu University Arts', 'zone_type': 'educational', 'capacity': 35,
         'hourly_rate': 30, 'lat': 27.7200, 'lng': 85.2950},
        {'zone_id': 'EDU7', 'name': 'Padma Kanya Campus', 'zone_type': 'educational', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7050, 'lng': 85.3120},
        {'zone_id': 'EDU8', 'name': 'Amrit Science Campus', 'zone_type': 'educational', 'capacity': 35,
         'hourly_rate': 30, 'lat': 27.7000, 'lng': 85.3150},
        {'zone_id': 'EDU9', 'name': 'Kathmandu School of Law', 'zone_type': 'educational', 'capacity': 30,
         'hourly_rate': 30, 'lat': 27.6950, 'lng': 85.3200},
        {'zone_id': 'EDU10', 'name': 'Nepal Engineering College', 'zone_type': 'educational', 'capacity': 45,
         'hourly_rate': 35, 'lat': 27.6800, 'lng': 85.3380},
        {'zone_id': 'EDU11', 'name': 'Himalaya College', 'zone_type': 'educational', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7100, 'lng': 85.3300},
        {'zone_id': 'EDU12', 'name': 'Prime College', 'zone_type': 'educational', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.6850, 'lng': 85.3450},
        {'zone_id': 'EDU13', 'name': 'Kathmandu College of Management', 'zone_type': 'educational', 'capacity': 35,
         'hourly_rate': 35, 'lat': 27.7000, 'lng': 85.3280},
        {'zone_id': 'EDU14', 'name': 'Nepal Commerce Campus', 'zone_type': 'educational', 'capacity': 40,
         'hourly_rate': 30, 'lat': 27.6980, 'lng': 85.3220},
        {'zone_id': 'EDU15', 'name': 'Public Youth Campus', 'zone_type': 'educational', 'capacity': 35,
         'hourly_rate': 30, 'lat': 27.6950, 'lng': 85.3180},

        # ========== GOVERNMENT OFFICES (10) ==========
        {'zone_id': 'GOV1', 'name': 'Singha Durbar', 'zone_type': 'government', 'capacity': 60, 'hourly_rate': 30,
         'lat': 27.6980, 'lng': 85.3200},
        {'zone_id': 'GOV2', 'name': 'Lalitpur Metropolitan Office', 'zone_type': 'government', 'capacity': 40,
         'hourly_rate': 30, 'lat': 27.6750, 'lng': 85.3240},
        {'zone_id': 'GOV3', 'name': 'KMC Office', 'zone_type': 'government', 'capacity': 50, 'hourly_rate': 30,
         'lat': 27.7050, 'lng': 85.3100},
        {'zone_id': 'GOV4', 'name': 'District Admin Office', 'zone_type': 'government', 'capacity': 45,
         'hourly_rate': 30, 'lat': 27.7020, 'lng': 85.3150},
        {'zone_id': 'GOV5', 'name': 'Police HQ', 'zone_type': 'government', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.6950, 'lng': 85.3220},
        {'zone_id': 'GOV6', 'name': 'Patan High Court', 'zone_type': 'government', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6720, 'lng': 85.3280},
        {'zone_id': 'GOV7', 'name': 'Finance Ministry', 'zone_type': 'government', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7000, 'lng': 85.3180},
        {'zone_id': 'GOV8', 'name': 'Education Ministry', 'zone_type': 'government', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7100, 'lng': 85.3150},
        {'zone_id': 'GOV9', 'name': 'Health Ministry', 'zone_type': 'government', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7050, 'lng': 85.3200},
        {'zone_id': 'GOV10', 'name': 'Agriculture Ministry', 'zone_type': 'government', 'capacity': 35,
         'hourly_rate': 30, 'lat': 27.6950, 'lng': 85.3250},

        # ========== OFFICE COMPLEXES (10) ==========
        {'zone_id': 'OFF1', 'name': 'Trade Tower', 'zone_type': 'office', 'capacity': 40, 'hourly_rate': 50,
         'lat': 27.6900, 'lng': 85.3250},
        {'zone_id': 'OFF2', 'name': 'Nabil Bank HQ', 'zone_type': 'office', 'capacity': 35, 'hourly_rate': 50,
         'lat': 27.7100, 'lng': 85.3150},
        {'zone_id': 'OFF3', 'name': 'Hulas Tower', 'zone_type': 'office', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.6850, 'lng': 85.3300},
        {'zone_id': 'OFF4', 'name': 'World Trade Center', 'zone_type': 'office', 'capacity': 45, 'hourly_rate': 55,
         'lat': 27.7000, 'lng': 85.3200},
        {'zone_id': 'OFF5', 'name': 'Naxal Business Park', 'zone_type': 'office', 'capacity': 35, 'hourly_rate': 50,
         'lat': 27.7120, 'lng': 85.3180},
        {'zone_id': 'OFF6', 'name': 'Lalitpur Corporate Centre', 'zone_type': 'office', 'capacity': 30,
         'hourly_rate': 45, 'lat': 27.6750, 'lng': 85.3300},
        {'zone_id': 'OFF7', 'name': 'City Office Complex', 'zone_type': 'office', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.6950, 'lng': 85.3220},
        {'zone_id': 'OFF8', 'name': 'Baneshwor Business Hub', 'zone_type': 'office', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.6900, 'lng': 85.3350},
        {'zone_id': 'OFF9', 'name': 'Kamaladi Corporate', 'zone_type': 'office', 'capacity': 30, 'hourly_rate': 50,
         'lat': 27.7100, 'lng': 85.3130},
        {'zone_id': 'OFF10', 'name': 'Thapathali Complex', 'zone_type': 'office', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.7000, 'lng': 85.3250},

        # ========== PARKS (6) ==========
        {'zone_id': 'PARK1', 'name': 'Ratna Park', 'zone_type': 'park', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7020, 'lng': 85.3160},
        {'zone_id': 'PARK2', 'name': 'Tundikhel', 'zone_type': 'park', 'capacity': 55, 'hourly_rate': 25,
         'lat': 27.7000, 'lng': 85.3100},
        {'zone_id': 'PARK3', 'name': 'Basantapur Park', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7030, 'lng': 85.3080},
        {'zone_id': 'PARK4', 'name': 'Baudha Park', 'zone_type': 'park', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7210, 'lng': 85.3450},
        {'zone_id': 'PARK5', 'name': 'Lalitpur Park', 'zone_type': 'park', 'capacity': 28, 'hourly_rate': 25,
         'lat': 27.6750, 'lng': 85.3260},
        {'zone_id': 'PARK6', 'name': 'Bhaktapur Park', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6720, 'lng': 85.4280},
    ]

    # ============================================================
    # ADDITIONAL MUNICIPALITIES (Tarkeshwor, Budhanilkantha, Gokarneshwor, etc.)
    # ============================================================
    additional_zones = [
        # ----- TARKESHWOR MUNICIPALITY -----
        {'zone_id': 'TAR1', 'name': 'Tarkeshwor Chowk', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7450, 'lng': 85.2800},
        {'zone_id': 'TAR2', 'name': 'Lolang Bazar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.7500, 'lng': 85.2700},
        {'zone_id': 'TAR3', 'name': 'Jarankhu', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7550, 'lng': 85.2750},
        {'zone_id': 'TAR4', 'name': 'Kavresthali', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 30,
         'lat': 27.7400, 'lng': 85.2850},
        {'zone_id': 'TAR5', 'name': 'Manmaiju', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7480, 'lng': 85.2900},
        {'zone_id': 'TAR6', 'name': 'Panga', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.7420, 'lng': 85.2950},
        {'zone_id': 'TAR7', 'name': 'Jitpurphedi', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7600, 'lng': 85.2650},
        {'zone_id': 'TAR8', 'name': 'Futung', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.7700, 'lng': 85.2600},
        {'zone_id': 'TAR9', 'name': 'Kakani', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7800, 'lng': 85.2500},
        {'zone_id': 'TAR10', 'name': 'Bhadrakali Temple', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 30,
         'lat': 27.7460, 'lng': 85.2820},
        {'zone_id': 'TAR11', 'name': 'Okhaldhunga', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7520, 'lng': 85.2780},
        {'zone_id': 'TAR12', 'name': 'Gairigaun', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7580, 'lng': 85.2720},

        # ----- BUDHANILKANTHA MUNICIPALITY -----
        {'zone_id': 'BUD1', 'name': 'Budhanilkantha Temple', 'zone_type': 'heritage', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.7600, 'lng': 85.3500},
        {'zone_id': 'BUD2', 'name': 'Kapan Monastery', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7350, 'lng': 85.3550},
        {'zone_id': 'BUD3', 'name': 'Golfutar', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7500, 'lng': 85.3400},
        {'zone_id': 'BUD4', 'name': 'Bishnumati River Side', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7450, 'lng': 85.3450},
        {'zone_id': 'BUD5', 'name': 'Sallaghari', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7550, 'lng': 85.3550},
        {'zone_id': 'BUD6', 'name': 'Khadka Bhadrakali', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7650, 'lng': 85.3600},
        {'zone_id': 'BUD7', 'name': 'Tikathali', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7580, 'lng': 85.3650},
        {'zone_id': 'BUD8', 'name': 'Mahadevsthan', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7700, 'lng': 85.3550},

        # ----- GOKARNESHWAR MUNICIPALITY -----
        {'zone_id': 'GOK1', 'name': 'Gokarna Safari Park', 'zone_type': 'park', 'capacity': 60, 'hourly_rate': 40,
         'lat': 27.7300, 'lng': 85.4000},
        {'zone_id': 'GOK2', 'name': 'Jorpati', 'zone_type': 'commercial', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.7250, 'lng': 85.3800},
        {'zone_id': 'GOK3', 'name': 'Mulpani', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7200, 'lng': 85.3900},
        {'zone_id': 'GOK4', 'name': 'Gothatar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7100, 'lng': 85.3850},
        {'zone_id': 'GOK5', 'name': 'Bansbari', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7250, 'lng': 85.3700},
        {'zone_id': 'GOK6', 'name': 'Chhagal', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7150, 'lng': 85.3950},
        {'zone_id': 'GOK7', 'name': 'Sundarijal', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7400, 'lng': 85.4200},
        {'zone_id': 'GOK8', 'name': 'Nanglebhare', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7350, 'lng': 85.4100},

        # ----- KAGESHWORI MANOHARA MUNICIPALITY -----
        {'zone_id': 'KAG1', 'name': 'Kageshwori Temple', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7000, 'lng': 85.3750},
        {'zone_id': 'KAG2', 'name': 'Manohara River', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6950, 'lng': 85.3800},
        {'zone_id': 'KAG3', 'name': 'Aloknagar', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7050, 'lng': 85.3700},
        {'zone_id': 'KAG4', 'name': 'Kritipur', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7100, 'lng': 85.3650},
        {'zone_id': 'KAG5', 'name': 'Thali', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6900, 'lng': 85.3850},
        {'zone_id': 'KAG6', 'name': 'Gagalphedi', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7150, 'lng': 85.3750},
        {'zone_id': 'KAG7', 'name': 'Sano Gaucharan', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7080, 'lng': 85.3720},

        # ----- SHANKHARAPUR MUNICIPALITY -----
        {'zone_id': 'SHA1', 'name': 'Shankharapur Chowk', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7600, 'lng': 85.4200},
        {'zone_id': 'SHA2', 'name': 'Indrayani Temple', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7550, 'lng': 85.4250},
        {'zone_id': 'SHA3', 'name': 'Pakhapati', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.7650, 'lng': 85.4300},
        {'zone_id': 'SHA4', 'name': 'Laprak', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7700, 'lng': 85.4400},
        {'zone_id': 'SHA5', 'name': 'Bajrayogini Temple', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7580, 'lng': 85.4180},
        {'zone_id': 'SHA6', 'name': 'Khadichaur', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7620, 'lng': 85.4350},

        # ----- NAGARJUN MUNICIPALITY -----
        {'zone_id': 'NAG1', 'name': 'Nagarjun Forest', 'zone_type': 'park', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.7400, 'lng': 85.2600},
        {'zone_id': 'NAG2', 'name': 'Ichangu Narayan', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7350, 'lng': 85.2650},
        {'zone_id': 'NAG3', 'name': 'Sitapaila', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7300, 'lng': 85.2700},
        {'zone_id': 'NAG4', 'name': 'Machhegaun', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7450, 'lng': 85.2550},
        {'zone_id': 'NAG5', 'name': 'Bhajangal', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7500, 'lng': 85.2500},
        {'zone_id': 'NAG6', 'name': 'Halchowk', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7350, 'lng': 85.2750},

        # ----- TOKHA MUNICIPALITY -----
        {'zone_id': 'TOK1', 'name': 'Tokha Chowk', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 30,
         'lat': 27.7550, 'lng': 85.3100},
        {'zone_id': 'TOK2', 'name': 'Dhapasi', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7400, 'lng': 85.3100},
        {'zone_id': 'TOK3', 'name': 'Chuchepati', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7350, 'lng': 85.3200},
        {'zone_id': 'TOK4', 'name': 'Gongabu Bus Park', 'zone_type': 'commercial', 'capacity': 60, 'hourly_rate': 35,
         'lat': 27.7300, 'lng': 85.3050},
        {'zone_id': 'TOK5', 'name': 'Bhattedanda', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7450, 'lng': 85.3250},
        {'zone_id': 'TOK6', 'name': 'Jorpati Bridge', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7250, 'lng': 85.3150},
        {'zone_id': 'TOK7', 'name': 'Mahankal', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7500, 'lng': 85.3150},

        # ----- DAKSHINKALI MUNICIPALITY -----
        {'zone_id': 'DAK1', 'name': 'Dakshinkali Temple', 'zone_type': 'heritage', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.6100, 'lng': 85.2800},
        {'zone_id': 'DAK2', 'name': 'Pharping', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.6200, 'lng': 85.2750},
        {'zone_id': 'DAK3', 'name': 'Bajra Barahi', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6150, 'lng': 85.2850},
        {'zone_id': 'DAK4', 'name': 'Bungmati', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6250, 'lng': 85.2900},
        {'zone_id': 'DAK5', 'name': 'Karyabinayak', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6300, 'lng': 85.2950},
        {'zone_id': 'DAK6', 'name': 'Champadevi', 'zone_type': 'park', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6050, 'lng': 85.2700},
        {'zone_id': 'DAK7', 'name': 'Chapagaun', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6400, 'lng': 85.3200},
        {'zone_id': 'DAK8', 'name': 'Badikhel', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.6200, 'lng': 85.3400},

        # ----- CHANDRAGIRI MUNICIPALITY -----
        {'zone_id': 'CHA1', 'name': 'Chandragiri Hill', 'zone_type': 'park', 'capacity': 70, 'hourly_rate': 50,
         'lat': 27.6700, 'lng': 85.2500},
        {'zone_id': 'CHA2', 'name': 'Thankot Market', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 30,
         'lat': 27.6800, 'lng': 85.2400},
        {'zone_id': 'CHA3', 'name': 'Matatirtha', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6750, 'lng': 85.2550},
        {'zone_id': 'CHA4', 'name': 'Sangla', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6900, 'lng': 85.2450},
        {'zone_id': 'CHA5', 'name': 'Balambu', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6950, 'lng': 85.2350},
        {'zone_id': 'CHA6', 'name': 'Naikap', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6850, 'lng': 85.2450},
        {'zone_id': 'CHA7', 'name': 'Dahachok', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7000, 'lng': 85.2300},

        # ----- MADHYAPUR THIMI (more) -----
        {'zone_id': 'THI1', 'name': 'Thimi Bazar', 'zone_type': 'commercial', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.6800, 'lng': 85.3900},
        {'zone_id': 'THI2', 'name': 'Sano Thimi', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.6850, 'lng': 85.3950},
        {'zone_id': 'THI3', 'name': 'Balkot', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.6750, 'lng': 85.3850},
        {'zone_id': 'THI4', 'name': 'Kaushaltar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6700, 'lng': 85.3800},
        {'zone_id': 'THI5', 'name': 'Nagarjun Temple (Thimi)', 'zone_type': 'heritage', 'capacity': 30,
         'hourly_rate': 30, 'lat': 27.6820, 'lng': 85.3920},
        {'zone_id': 'THI6', 'name': 'Lokanthali (Thimi)', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6850, 'lng': 85.3880},
        {'zone_id': 'THI7', 'name': 'Chardobato', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6780, 'lng': 85.3950},
        {'zone_id': 'THI8', 'name': 'Narephant', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6900, 'lng': 85.3850},

        # ----- Additional zones for Kathmandu Metropolitan (more areas) -----
        {'zone_id': 'KMC33', 'name': 'Naxal', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.7120, 'lng': 85.3180},
        {'zone_id': 'KMC34', 'name': 'Lainchaur', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.7180, 'lng': 85.3150},
        {'zone_id': 'KMC35', 'name': 'Maharajgunj', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7220, 'lng': 85.3350},
        {'zone_id': 'KMC36', 'name': 'Dillibazar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7080, 'lng': 85.3280},
        {'zone_id': 'KMC37', 'name': 'Putalisadak', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.7050, 'lng': 85.3180},
        {'zone_id': 'KMC38', 'name': 'Lazimpat', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 45,
         'lat': 27.7150, 'lng': 85.3220},
        {'zone_id': 'KMC39', 'name': 'Panipokhari', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7200, 'lng': 85.3250},
        {'zone_id': 'KMC40', 'name': 'Baluwatar', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.7200, 'lng': 85.3250},
        {'zone_id': 'KMC41', 'name': 'Khalandu', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7100, 'lng': 85.3100},
        {'zone_id': 'KMC42', 'name': 'Jamal', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7080, 'lng': 85.3120},
        {'zone_id': 'KMC43', 'name': 'Bhotahiti', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 35,
         'lat': 27.7050, 'lng': 85.3060},
        {'zone_id': 'KMC44', 'name': 'Teku', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6980, 'lng': 85.3100},
        {'zone_id': 'KMC45', 'name': 'Minbhawan', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.6900, 'lng': 85.3250},
        {'zone_id': 'KMC46', 'name': 'New Baneshwor', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6880, 'lng': 85.3380},
        {'zone_id': 'KMC47', 'name': 'Shankhamul', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.6950, 'lng': 85.3280},
        {'zone_id': 'KMC48', 'name': 'Kumaripati', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6800, 'lng': 85.3320},
        {'zone_id': 'KMC49', 'name': 'Sanogaucharan', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7000, 'lng': 85.3400},
        {'zone_id': 'KMC50', 'name': 'Tinkune', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.6850, 'lng': 85.3450},
        {'zone_id': 'KMC51', 'name': 'Kapan', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7350, 'lng': 85.3550},
        {'zone_id': 'KMC52', 'name': 'Dhumbarahi', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7250, 'lng': 85.2900},
        {'zone_id': 'KMC53', 'name': 'Anamnagar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7100, 'lng': 85.3250},
        {'zone_id': 'KMC54', 'name': 'Naya Baneshwor', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 40,
         'lat': 27.6880, 'lng': 85.3350},
        {'zone_id': 'KMC55', 'name': 'Mahankal', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7500, 'lng': 85.3150},
        {'zone_id': 'KMC56', 'name': 'Bishalnagar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7150, 'lng': 85.3200},
        {'zone_id': 'KMC57', 'name': 'Gairidhara', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.7200, 'lng': 85.3180},
        {'zone_id': 'KMC58', 'name': 'Chakrapath', 'zone_type': 'commercial', 'capacity': 45, 'hourly_rate': 35,
         'lat': 27.7300, 'lng': 85.3400},
        {'zone_id': 'KMC59', 'name': 'Samakhusi', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7300, 'lng': 85.2950},
        {'zone_id': 'KMC60', 'name': 'Swoyambhu Road', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7150, 'lng': 85.2900},

        # ----- Additional zones for Lalitpur Metropolitan -----
        {'zone_id': 'LMC11', 'name': 'Hattiban', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6600, 'lng': 85.3400},
        {'zone_id': 'LMC12', 'name': 'Dhobighat', 'zone_type': 'commercial', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.6850, 'lng': 85.3400},
        {'zone_id': 'LMC13', 'name': 'Ekantakuna', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.6700, 'lng': 85.3280},
        {'zone_id': 'LMC14', 'name': 'Krishna Galli', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.6740, 'lng': 85.3260},
        {'zone_id': 'LMC15', 'name': 'Mangal Bazar', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 45,
         'lat': 27.6720, 'lng': 85.3240},
        {'zone_id': 'LMC16', 'name': 'Sankhamul (Lalitpur)', 'zone_type': 'commercial', 'capacity': 30,
         'hourly_rate': 35, 'lat': 27.6780, 'lng': 85.3400},
        {'zone_id': 'LMC17', 'name': 'Nakkhu', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6600, 'lng': 85.3500},
        {'zone_id': 'LMC18', 'name': 'Bungamati', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6250, 'lng': 85.2900},
        {'zone_id': 'LMC19', 'name': 'Khokana', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6350, 'lng': 85.2950},
        {'zone_id': 'LMC20', 'name': 'Thecho', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6450, 'lng': 85.3000},
        {'zone_id': 'LMC21', 'name': 'Sunakothi', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6500, 'lng': 85.3100},
        {'zone_id': 'LMC22', 'name': 'Chapagaun', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6400, 'lng': 85.3200},
        {'zone_id': 'LMC23', 'name': 'Lubhu', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6400, 'lng': 85.3800},
        {'zone_id': 'LMC24', 'name': 'Lamatar', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6300, 'lng': 85.3500},
        {'zone_id': 'LMC25', 'name': 'Badikhel', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.6200, 'lng': 85.3400},
        {'zone_id': 'LMC26', 'name': 'Imadol', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6650, 'lng': 85.3450},
        {'zone_id': 'LMC27', 'name': 'Tikathali', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6700, 'lng': 85.3500},
        {'zone_id': 'LMC28', 'name': 'Chaughada', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6550, 'lng': 85.3350},
        {'zone_id': 'LMC29', 'name': 'Thaiba', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6450, 'lng': 85.3250},

        # ----- Additional zones for Bhaktapur Municipality -----
        {'zone_id': 'BKT6', 'name': 'Kamal Binayak', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 30,
         'lat': 27.6700, 'lng': 85.4300},
        {'zone_id': 'BKT7', 'name': 'Changu Narayan Museum', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7020, 'lng': 85.4300},
        {'zone_id': 'BKT8', 'name': 'Dattatreya Square', 'zone_type': 'heritage', 'capacity': 30, 'hourly_rate': 40,
         'lat': 27.6730, 'lng': 85.4290},
        {'zone_id': 'BKT9', 'name': 'Taumadhi Square', 'zone_type': 'heritage', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.6720, 'lng': 85.4260},
        {'zone_id': 'BKT10', 'name': 'Pottery Square', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 35,
         'lat': 27.6710, 'lng': 85.4270},
        {'zone_id': 'BKT11', 'name': 'Kautunja', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6850, 'lng': 85.4100},
        {'zone_id': 'BKT12', 'name': 'Sipadol', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6900, 'lng': 85.4400},
        {'zone_id': 'BKT13', 'name': 'Nankhel', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6950, 'lng': 85.4450},
        {'zone_id': 'BKT14', 'name': 'Sudal', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.7000, 'lng': 85.4500},
        {'zone_id': 'BKT15', 'name': 'Chamati', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.7100, 'lng': 85.4600},
        {'zone_id': 'BKT16', 'name': 'Dadhikot', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6800, 'lng': 85.4400},
        {'zone_id': 'BKT17', 'name': 'Kharipati', 'zone_type': 'commercial', 'capacity': 25, 'hourly_rate': 25,
         'lat': 27.6750, 'lng': 85.4450},

        # ----- Additional KIRTIPUR zones -----
        {'zone_id': 'KIR4', 'name': 'Bagbazaar', 'zone_type': 'commercial', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.6800, 'lng': 85.2820},
        {'zone_id': 'KIR5', 'name': 'Panga', 'zone_type': 'commercial', 'capacity': 30, 'hourly_rate': 25,
         'lat': 27.6850, 'lng': 85.2780},
        {'zone_id': 'KIR6', 'name': 'Layaku', 'zone_type': 'heritage', 'capacity': 25, 'hourly_rate': 30,
         'lat': 27.6770, 'lng': 85.2860},
        {'zone_id': 'KIR7', 'name': 'Naya Bazaar (Kirtipur)', 'zone_type': 'commercial', 'capacity': 35,
         'hourly_rate': 30, 'lat': 27.6790, 'lng': 85.2830},

        # ----- Additional HOSPITALS -----
        {'zone_id': 'HOSP16', 'name': 'Tarkeshwor Hospital', 'zone_type': 'hospital', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.7450, 'lng': 85.2800},
        {'zone_id': 'HOSP17', 'name': 'Gokarna Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 35,
         'lat': 27.7300, 'lng': 85.4000},
        {'zone_id': 'HOSP18', 'name': 'Nagarjun Hospital', 'zone_type': 'hospital', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7400, 'lng': 85.2600},
        {'zone_id': 'HOSP19', 'name': 'Tokha Hospital', 'zone_type': 'hospital', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7550, 'lng': 85.3100},
        {'zone_id': 'HOSP20', 'name': 'Chandragiri Hospital', 'zone_type': 'hospital', 'capacity': 35,
         'hourly_rate': 35, 'lat': 27.6800, 'lng': 85.2400},
        {'zone_id': 'HOSP21', 'name': 'Madhyapur Hospital', 'zone_type': 'hospital', 'capacity': 30, 'hourly_rate': 30,
         'lat': 27.6800, 'lng': 85.3900},
        {'zone_id': 'HOSP22', 'name': 'Budhanilkantha Hospital', 'zone_type': 'hospital', 'capacity': 30,
         'hourly_rate': 30, 'lat': 27.7600, 'lng': 85.3520},
        {'zone_id': 'HOSP23', 'name': 'Shankharapur Hospital', 'zone_type': 'hospital', 'capacity': 25,
         'hourly_rate': 25, 'lat': 27.7620, 'lng': 85.4220},

        # ----- Additional SHOPPING MALLS -----
        {'zone_id': 'MALL21', 'name': 'Tokha City Center', 'zone_type': 'shopping', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.7500, 'lng': 85.3150},
        {'zone_id': 'MALL22', 'name': 'Budhanilkantha Mall', 'zone_type': 'shopping', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.7600, 'lng': 85.3500},
        {'zone_id': 'MALL23', 'name': 'Kavresthali Mall', 'zone_type': 'shopping', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7400, 'lng': 85.2850},
        {'zone_id': 'MALL24', 'name': 'Lolang Shopping', 'zone_type': 'shopping', 'capacity': 35, 'hourly_rate': 30,
         'lat': 27.7500, 'lng': 85.2700},
        {'zone_id': 'MALL25', 'name': 'Jorpati Complex', 'zone_type': 'shopping', 'capacity': 50, 'hourly_rate': 35,
         'lat': 27.7250, 'lng': 85.3800},
        {'zone_id': 'MALL26', 'name': 'Sankhamul Mall', 'zone_type': 'shopping', 'capacity': 40, 'hourly_rate': 35,
         'lat': 27.7000, 'lng': 85.3300},
        {'zone_id': 'MALL27', 'name': 'Sinamangal Plaza', 'zone_type': 'shopping', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7000, 'lng': 85.3550},
        {'zone_id': 'MALL28', 'name': 'Koteshwor Mall', 'zone_type': 'shopping', 'capacity': 45, 'hourly_rate': 40,
         'lat': 27.6850, 'lng': 85.3550},

        # ----- Additional EDUCATIONAL INSTITUTIONS -----
        {'zone_id': 'EDU16', 'name': 'Tarkeshwor Academy', 'zone_type': 'educational', 'capacity': 35,
         'hourly_rate': 25, 'lat': 27.7450, 'lng': 85.2820},
        {'zone_id': 'EDU17', 'name': 'Budhanilkantha School', 'zone_type': 'educational', 'capacity': 45,
         'hourly_rate': 30, 'lat': 27.7600, 'lng': 85.3520},
        {'zone_id': 'EDU18', 'name': 'Gokarna College', 'zone_type': 'educational', 'capacity': 40, 'hourly_rate': 30,
         'lat': 27.7320, 'lng': 85.3950},
        {'zone_id': 'EDU19', 'name': 'Nagarjun School', 'zone_type': 'educational', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.7420, 'lng': 85.2620},
        {'zone_id': 'EDU20', 'name': 'Tokha Campus', 'zone_type': 'educational', 'capacity': 40, 'hourly_rate': 25,
         'lat': 27.7580, 'lng': 85.3120},
        {'zone_id': 'EDU21', 'name': 'Shankharapur College', 'zone_type': 'educational', 'capacity': 30,
         'hourly_rate': 25, 'lat': 27.7620, 'lng': 85.4240},
        {'zone_id': 'EDU22', 'name': 'Madhyapur Campus', 'zone_type': 'educational', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.6820, 'lng': 85.3920},
        {'zone_id': 'EDU23', 'name': 'Dakshinkali School', 'zone_type': 'educational', 'capacity': 30,
         'hourly_rate': 25, 'lat': 27.6200, 'lng': 85.2780},
        {'zone_id': 'EDU24', 'name': 'Chandragiri Academy', 'zone_type': 'educational', 'capacity': 30,
         'hourly_rate': 25, 'lat': 27.6750, 'lng': 85.2520},

        # ----- Additional CINEMAS -----
        {'zone_id': 'CINE9', 'name': 'Tokha Cinemas', 'zone_type': 'cinema', 'capacity': 35, 'hourly_rate': 40,
         'lat': 27.7520, 'lng': 85.3140},
        {'zone_id': 'CINE10', 'name': 'Budhanilkantha Movies', 'zone_type': 'cinema', 'capacity': 40, 'hourly_rate': 45,
         'lat': 27.7580, 'lng': 85.3480},
        {'zone_id': 'CINE11', 'name': 'Gokarna Cineplex', 'zone_type': 'cinema', 'capacity': 45, 'hourly_rate': 45,
         'lat': 27.7280, 'lng': 85.3980},
        {'zone_id': 'CINE12', 'name': 'Kavresthali Cinema', 'zone_type': 'cinema', 'capacity': 30, 'hourly_rate': 35,
         'lat': 27.7420, 'lng': 85.2870},

        # ----- Additional PARKS -----
        {'zone_id': 'PARK7', 'name': 'Kavresthali Park', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 20,
         'lat': 27.7420, 'lng': 85.2870},
        {'zone_id': 'PARK8', 'name': 'Jarankhu Park', 'zone_type': 'park', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.7550, 'lng': 85.2750},
        {'zone_id': 'PARK9', 'name': 'Budhanilkantha Park', 'zone_type': 'park', 'capacity': 35, 'hourly_rate': 25,
         'lat': 27.7620, 'lng': 85.3550},
        {'zone_id': 'PARK10', 'name': 'Tokha Park', 'zone_type': 'park', 'capacity': 30, 'hourly_rate': 20,
         'lat': 27.7600, 'lng': 85.3180},
        {'zone_id': 'PARK11', 'name': 'Chandragiri Park', 'zone_type': 'park', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.6700, 'lng': 85.2500},
        {'zone_id': 'PARK12', 'name': 'Pharping Park', 'zone_type': 'park', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.6200, 'lng': 85.2750},

        # ----- Additional GOVERNMENT OFFICES -----
        {'zone_id': 'GOV11', 'name': 'Tarkeshwor Ward Office', 'zone_type': 'government', 'capacity': 25,
         'hourly_rate': 20, 'lat': 27.7460, 'lng': 85.2810},
        {'zone_id': 'GOV12', 'name': 'Budhanilkantha Ward Office', 'zone_type': 'government', 'capacity': 30,
         'hourly_rate': 20, 'lat': 27.7610, 'lng': 85.3510},
        {'zone_id': 'GOV13', 'name': 'Gokarna Ward Office', 'zone_type': 'government', 'capacity': 30,
         'hourly_rate': 20, 'lat': 27.7310, 'lng': 85.3960},
        {'zone_id': 'GOV14', 'name': 'Tokha Ward Office', 'zone_type': 'government', 'capacity': 25, 'hourly_rate': 20,
         'lat': 27.7560, 'lng': 85.3110},
        {'zone_id': 'GOV15', 'name': 'Chandragiri Ward Office', 'zone_type': 'government', 'capacity': 30,
         'hourly_rate': 20, 'lat': 27.6820, 'lng': 85.2420},
        {'zone_id': 'GOV16', 'name': 'Shankharapur Ward Office', 'zone_type': 'government', 'capacity': 25,
         'hourly_rate': 20, 'lat': 27.7600, 'lng': 85.4200},
        {'zone_id': 'GOV17', 'name': 'Dakshinkali Ward Office', 'zone_type': 'government', 'capacity': 25,
         'hourly_rate': 20, 'lat': 27.6100, 'lng': 85.2800},
    ]

    # Append additional zones to the main list
    zones_data.extend(additional_zones)

    total_zones = len(zones_data)
    print(f"📊 Creating {total_zones} zones with reasonable prices...")
    print("")

    zones = []
    for zd in zones_data:
        # Get reasonable price based on zone type (instead of using old hourly_rate)
        reasonable_price = get_reasonable_price(zd['zone_type'])

        zone = ParkingZone.objects.create(
            zone_id=zd['zone_id'],
            name=zd['name'],
            zone_type=zd['zone_type'],
            capacity=zd['capacity'],
            hourly_rate=reasonable_price,  # ← Using reasonable price instead of old rate
            location_x=zd['lng'],
            location_y=zd['lat'],
            address=f"{zd['name']}, Kathmandu Valley",
            occupied=0,
            is_active=True
        )
        zones.append(zone)
        print(f"   ✅ Created zone: {zone.zone_id} - {zone.name} (Rs {reasonable_price}/hour)")

    print("")
    print(f"✅ Created {len(zones)} zones")
    print("")

    # Create slots for each zone
    total_slots = 0
    for zone in zones:
        print(f"📍 Creating {zone.capacity} slots for {zone.name} ({zone.zone_id})...")

        for i in range(1, zone.capacity + 1):
            slot_number = f"{zone.zone_id}{i:03d}"

            # Choose slot type based on zone type
            if zone.zone_type in ['airport', 'shopping', 'commercial']:
                r = random.random()
                if r < 0.40:
                    slot_type = 'Regular'
                elif r < 0.60:
                    slot_type = 'Premium'
                elif r < 0.80:
                    slot_type = 'Compact'
                else:
                    slot_type = 'EV'
            elif zone.zone_type == 'hospital':
                r = random.random()
                if r < 0.50:
                    slot_type = 'Regular'
                elif r < 0.70:
                    slot_type = 'Premium'
                elif r < 0.85:
                    slot_type = 'Compact'
                else:
                    slot_type = 'EV'
            elif zone.zone_type in ['heritage', 'cinema']:
                r = random.random()
                if r < 0.45:
                    slot_type = 'Regular'
                elif r < 0.65:
                    slot_type = 'Premium'
                elif r < 0.80:
                    slot_type = 'Compact'
                else:
                    slot_type = 'EV'
            else:
                r = random.random()
                if r < 0.55:
                    slot_type = 'Regular'
                elif r < 0.75:
                    slot_type = 'Premium'
                elif r < 0.90:
                    slot_type = 'Compact'
                else:
                    slot_type = 'EV'

            # Ensure enough Compact slots for motorcycles (every 4th slot)
            if i % 4 == 0:
                slot_type = 'Compact'
            # Ensure enough EV slots (every 10th slot)
            if i % 10 == 0:
                slot_type = 'EV'

            # 70% available, 30% occupied for initial demo
            if i <= int(zone.capacity * 0.70):
                status = 'available'
            else:
                status = 'occupied'

            slot = ParkingSlot.objects.create(
                slot_number=slot_number,
                zone=zone,
                slot_type=slot_type,
                status=status,
                sensor_id=f"SENSOR_{slot_number}",
                location_x=zone.location_x + random.uniform(-0.0005, 0.0005),
                location_y=zone.location_y + random.uniform(-0.0005, 0.0005)
            )
            total_slots += 1

        zone.occupied = zone.slots.filter(status='occupied').count()
        zone.save()
        print(f"   ✅ Created {zone.capacity} slots for {zone.name} (Total slots so far: {total_slots})")

    print("")

    # Create admin user
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@smartpark.com', 'admin123')
        print("✅ Admin user created: admin / admin123")
    else:
        print("ℹ️ Admin user already exists")

    print("")
    print("=" * 70)
    print("📊 DATABASE SUMMARY")
    print("=" * 70)
    print(f"Total Zones: {ParkingZone.objects.count()}")
    print(f"Total Slots: {ParkingSlot.objects.count()}")
    print(f"Available Slots: {ParkingSlot.objects.filter(status='available').count()}")
    print(f"Occupied Slots: {ParkingSlot.objects.filter(status='occupied').count()}")
    print(f"Reserved Slots: {ParkingSlot.objects.filter(status='reserved').count()}")
    print("=" * 70)

    print("")
    print("📊 Vehicle Compatibility Summary:")
    print("-" * 50)

    vehicle_data = [
        ('Sedan', ['Regular', 'Premium']),
        ('SUV', ['Regular', 'Premium']),
        ('Compact', ['Compact', 'Regular']),
        ('EV', ['EV', 'Regular']),
        ('Motorcycle', ['Compact', 'Regular']),
    ]

    for vehicle, types in vehicle_data:
        count = ParkingSlot.objects.filter(status='available', slot_type__in=types).count()
        print(f"✅ {vehicle}: {count} available slots")

    print("")
    print("📊 Price Summary by Zone Type:")
    print("-" * 50)
    for zone_type, price in REASONABLE_PRICES.items():
        if zone_type != 'default':
            count = ParkingZone.objects.filter(zone_type=zone_type).count()
            print(f"  {zone_type.upper()}: Rs {price}/hour ({count} zones)")

    print("")
    print("=" * 70)
    print("✅ Initialization Complete!")
    print("=" * 70)
    print("")
    print("🔧 To run the server:")
    print("   python manage.py runserver")
    print("")
    print("🌐 Access the application:")
    print("   Home: http://localhost:8000/")
    print("   Dashboard: http://localhost:8000/dashboard/")
    print("   Live Map: http://localhost:8000/map/")
    print("   Admin: http://localhost:8000/admin/")
    print("=" * 70)


if __name__ == '__main__':
    init_database()