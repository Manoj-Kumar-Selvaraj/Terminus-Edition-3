from django.urls import path

from checkout import views as checkout_views
from controlplane import views as health_views

urlpatterns = [
    path("healthz", health_views.healthz),
    path("readyz", health_views.readyz),
    path("api/checkout/place", checkout_views.place_order),
    path("api/orders/<str:order_ref>", checkout_views.order_detail),
    path("api/orders/<str:order_ref>/pay", checkout_views.capture_payment),
    path("api/shoppers/<str:shopper_ref>/confirmation", checkout_views.confirmation),
]
