from django.shortcuts import render
from django.contrib.auth.models import User
from .forms import UserRegistrationForm
from .tasks import send_verification_email  
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # user needs to verify via email
            user.save()

            # Queue email sending via Celery
            send_verification_email.delay(user.id)

            return render(request, 'accounts/thankyou.html')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request):
    uidb64 = request.GET.get('uid')
    token = request.GET.get('token')

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return HttpResponse("✅ Your account has been verified successfully!")
    else:
        return HttpResponse("❌ Verification link is invalid or expired.")
