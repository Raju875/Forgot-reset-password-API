from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from datetime import timedelta
from users.models import VerificationCode
from utils.time_zones import TimeZoneUtil
from users.api.v1.serializers import ForgetPasswordSerializer, VerificationCodeSerializer, ResetPasswordSerializer

User = get_user_model()

    
class ForgetPasswordView(ModelViewSet):
    permission_classes = [permissions.AllowAny, ]
    http_method_names = ['post']
    serializer_class = ForgetPasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = request.data['email']
        user = User.objects.get(email=email)
        if not user:
            return Response({"error": _("Your entered email number does not exist. "
                                        "Please enter a valid email or Create New Account.")}, 
                                         status=status.HTTP_400_BAD_REQUEST)
        try:
            code = VerificationCode.generate_code_for_user(user)
            email_context = {
                "email": email,
                "code": code
            }
            html_content = render_to_string(
                'forget_password.html', email_context)

            # Send mail using Gmail
            send_mail(
                subject='Forget Password',
                message= None,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_content
            )

             # Send mail using Sendgrid
            message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=email,
                subject='Forget Password',
                html_content=html_content)
            sg = SendGridAPIClient('SG Client API key')
            response = sg.send(message)
            print(response.status_code)

            return Response({"success": True, 
                             "message": _("A mail is sent to " + email + ". Please check it."),
                             "data": email_context},
                              status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False, 
                             "message": e.args}, 
                              status=status.HTTP_400_BAD_REQUEST)


class VerificationViewSet(ModelViewSet):
    permission_classes = [permissions.AllowAny, ]
    http_method_names = ['post']
    serializer_class = VerificationCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = request.data['email']
        code = request.data['code']
        user_code = VerificationCode.objects.filter(code=code, is_used=False, user__email=email).first()
        if not user_code:
            return Response({"success": False,
                             "message": _('Invalid Code! Please provide a valid verification code')},
                              status=status.HTTP_400_BAD_REQUEST)

        now = TimeZoneUtil.get_datetime()
        expired_date = TimeZoneUtil.utc_to_timezone(user_code.updated_at + timedelta(minutes=60))
        if expired_date < now:
            return Response({"success": False,
                             "message": _("Token expired!")},
                              status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, 
                        'data': {"email": email, "code": code}},
                         status=status.HTTP_200_OK)


class ResetPasswordSetView(ModelViewSet):
    permission_classes = [permissions.AllowAny, ]
    http_method_names = ['post']
    serializer_class = ResetPasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = request.data['email']
        code = request.data['code']
        user_code = VerificationCode.objects.filter(code=code, is_used=False, user__email=email).first()

        if not user_code:
            return Response({"success": False,
                             "message": _('Invalid Code!  Please try again.')},
                              status=status.HTTP_400_BAD_REQUEST)

        expired_date = TimeZoneUtil.utc_to_timezone(user_code.updated_at + timedelta(minutes=60))
        now = TimeZoneUtil.get_datetime()
        if expired_date < now:
            return Response({"success": False,
                             "message": _("Token expired!")}, 
                              status=status.HTTP_400_BAD_REQUEST)

        if request.data['password'] != request.data['confirm_password']:
            return Response({"success": False,
                             "message": _("Those passwords don't match.")}, 
                             status=status.HTTP_400_BAD_REQUEST)
 
        user = user_code.user
        user.set_password(request.data['password'])
        user.save()

        user_code.is_used = True
        user_code.save()

        return Response({"success": True, 
                         "message": _("Password update successfully.")}, 
                         status=status.HTTP_201_CREATED)
