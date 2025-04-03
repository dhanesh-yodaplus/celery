# accounts/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from .forms import UserRegistrationForm
from unittest.mock import patch
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator

class UserRegistrationTests(TestCase):

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertIsInstance(response.context['form'], UserRegistrationForm)

    def test_register_view_post_valid(self):
        data = {
            'username': 'testuser',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
            'email': 'testuser@example.com',
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/thankyou.html')
        # Check if the user is created but inactive
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_active)
        # Check if the email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('subject', mail.outbox[0])  # Ensure an email is sent

    def test_register_view_post_invalid(self):
        data = {
            'username': 'testuser',
            'password1': 'testpassword123',
            'password2': 'testpassword12',  # Passwords don't match
            'email': 'testuser@example.com',
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'password2', 'The two password fields didn’t match.')

class UserVerificationTests(TestCase):

    @patch('django.core.mail.send_mail')
    def test_verify_email_valid(self, mock_send_mail):
        # Creating a user first
        user = User.objects.create_user(username='testuser', email='testuser@example.com', password='testpassword123')
        user.is_active = False
        user.save()

        # Generate token and uid for email verification
        uidb64 = urlsafe_base64_encode(str(user.pk).encode())
        token = default_token_generator.make_token(user)
        verification_url = reverse('verify_email') + f'?uid={uidb64}&token={token}'

        # Simulate the email verification click
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "✅ Your account has been verified successfully!")

        # Check that the user is now active
        user.refresh_from_db()
        self.assertTrue(user.is_active)


    def test_verify_email_invalid_uid(self):
        # Generate an invalid verification link
        verification_url = reverse('verify_email') + '?uid=invalid&token=invalid'
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "❌ Verification link is invalid or expired.")

    def test_verify_email_invalid_token(self):
        # Create user and generate token and uid for verification
        user = User.objects.create_user(username='testuser', email='testuser@example.com', password='testpassword123')
        user.is_active = False
        user.save()

        uidb64 = urlsafe_base64_encode(str(user.pk).encode())
        invalid_token = 'invalid-token'  # Invalid token for this user
        verification_url = reverse('verify_email') + f'?uid={uidb64}&token={invalid_token}'

        # Simulate the email verification click
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "❌ Verification link is invalid or expired.")
