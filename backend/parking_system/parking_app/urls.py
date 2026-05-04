from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import csrf_exempt
from . import views

router = DefaultRouter()
router.register(r'zones', views.ParkingZoneViewSet)
router.register(r'slots', views.ParkingSlotViewSet)
router.register(r'sessions', views.ParkingSessionViewSet)

urlpatterns = [
    # HTML pages
    path('', views.intro_page, name='intro'),
    path('map/', views.home_page, name='map'),
    path('dashboard/', views.dashboard_page, name='dashboard'),
    path('admin/', views.admin_redirect, name='admin'),

    # Authentication pages (standard forms)
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    path('my-bookings/', views.my_bookings_page, name='my_bookings'),
    path('api/cancel-session/<str:session_id>/', views.CancelSessionView.as_view(), name='cancel_session'),

    # API endpoints (GET)
    path('api/', views.APIHomeView.as_view(), name='api-home'),
    path('api/dashboard/', views.DashboardView.as_view(), name='api-dashboard'),
    path('api/live/', views.LiveParkingView.as_view(), name='api-live'),
    path('api/zone-stats/', views.ZoneStatisticsView.as_view(), name='api-zone-stats'),
    path('api/search-slots/', views.SearchSlotsView.as_view(), name='api-search-slots'),
    path('api/test/', views.TestAPIView.as_view(), name='api-test'),
    path('api/invoice/<str:session_id>/', views.InvoiceView.as_view(), name='invoice'),

    # POST endpoints
    path('api/nearest/', csrf_exempt(views.NearestParkingView.as_view()), name='api-nearest'),
    path('api/allocate/', csrf_exempt(views.AllocationView.as_view()), name='api-allocate'),
    path('api/reserve/', csrf_exempt(views.ReservationView.as_view()), name='api-reserve'),

    # Payment endpoints
    path('api/initiate-payment/', csrf_exempt(views.InitiatePaymentView.as_view()), name='initiate-payment'),
    path('api/payment-success/', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('api/payment-failure/', views.PaymentFailureView.as_view(), name='payment-failure'),
    path('api/payment-verify/', csrf_exempt(views.PaymentVerifyView.as_view()), name='payment-verify'),

    # Social auth
    path('accounts/', include('allauth.urls')),

    # DRF router
    path('api/', include(router.urls)),
]