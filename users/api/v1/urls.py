from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register("forget-password", views.ForgetPasswordView, basename="forget_password")
router.register("code-verification", views.VerificationViewSet, basename="code_verification")
router.register("reset-password", views.ResetPasswordSetView, basename="reset_password")

urlpatterns = [
    path("", include(router.urls)),
]
