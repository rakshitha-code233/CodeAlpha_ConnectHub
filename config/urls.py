"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, reverse_lazy
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from social import views
from social.forms import LoginForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path(
        'login/',
        LoginView.as_view(
            template_name='social/auth_form.html',
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
            extra_context={
                'title': 'Welcome back',
                'eyebrow': 'Your community is waiting',
                'intro': 'Pick up where you left off and see what your people are sharing.',
                'submit_label': 'Log in',
                'forgot_password_url': reverse_lazy('password_reset'),
                'alternate_prompt': "Don't have an account?",
            },
        ),
        name='login',
    ),
    path(
        'password-reset/',
        PasswordResetView.as_view(
            template_name='social/auth_form.html',
            email_template_name='social/registration/password_reset_email.txt',
            html_email_template_name='social/registration/password_reset_email.html',
            subject_template_name='social/registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
            extra_context={
                'title': 'Reset your password',
                'eyebrow': 'Account recovery',
                'intro': "Enter the email address linked to your account and we'll send you a reset link.",
                'submit_label': 'Send reset link',
                'alternate_prompt': 'Remembered your password?',
                'alternate_url': reverse_lazy('login'),
                'alternate_label': 'Log in',
            },
        ),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        PasswordResetDoneView.as_view(
            template_name='social/password_reset_status.html',
            extra_context={
                'title': 'Check your inbox',
                'eyebrow': 'One more step',
                'status_message': "If an account matches that email address, we've sent instructions to reset its password.",
                'status_detail': 'Please check your inbox and spam folder. The reset link expires for your security.',
            },
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='social/auth_form.html',
            success_url=reverse_lazy('password_reset_complete'),
            extra_context={
                'title': 'Choose a new password',
                'eyebrow': 'Almost there',
                'intro': 'Create a new password for your ConnectHub account.',
                'password_reset_confirm': True,
                'submit_label': 'Save new password',
                'alternate_prompt': 'Need to start again?',
                'alternate_url': reverse_lazy('password_reset'),
                'alternate_label': 'Request a new link',
            },
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        PasswordResetCompleteView.as_view(
            template_name='social/password_reset_status.html',
            extra_context={
                'title': 'Password updated',
                'eyebrow': 'You’re all set',
                'status_message': 'Your password has been changed successfully.',
                'status_detail': 'Use your new password the next time you log in.',
                'action_url': reverse_lazy('login'),
                'action_label': 'Back to log in',
            },
        ),
        name='password_reset_complete',
    ),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('users/<str:username>/', views.profile, name='profile'),
    path('posts/create/', views.create_post, name='create_post'),
    path(
        'posts/<int:post_id>/comments/',
        views.create_comment,
        name='create_comment',
    ),
    path('posts/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('users/<int:user_id>/follow/', views.toggle_follow, name='toggle_follow'),
]
