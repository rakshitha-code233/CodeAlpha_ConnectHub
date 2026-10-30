from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "bio")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "bio": forms.Textarea(attrs={"rows": 4, "maxlength": 160}),
        }


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "placeholder": "Your username"}
        )
        self.fields["password"].widget.attrs.update(
            {"autocomplete": "current-password", "placeholder": "Your password"}
        )


class RegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "placeholder": "Choose a username"}
        )
        self.fields["email"].widget.attrs.update(
            {"autocomplete": "email", "placeholder": "you@example.com"}
        )
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
