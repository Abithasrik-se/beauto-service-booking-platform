from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import User, BeauticianProfile, ServiceSkill


class BootstrapFormMixin:
    """Adds Bootstrap's `form-control` class to every field so templates
    can stay simple ({{ field }}) instead of hand-styling every input."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()


class StyledAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Used by all three login views — same widget, different view logic."""
    pass


class CustomerSignupForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=15)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data.get("phone", "")
        user.role = User.ROLE_CUSTOMER
        user.is_active = False  # gated by email verification
        if commit:
            user.save()
        return user


class BeauticianSignupForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=15)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    skills = forms.CharField(
        required=True,
        help_text="Comma separated, e.g. Makeup, Mehndi, Hair Styling",
    )
    address = forms.CharField(required=True, max_length=255)
    latitude = forms.FloatField(help_text="Base location latitude (from Google Maps)")
    longitude = forms.FloatField(help_text="Base location longitude")
    service_radius_km = forms.FloatField(initial=15, help_text="How far you'll travel, in km")
    available_from = forms.TimeField(initial="09:00", widget=forms.TimeInput(attrs={"type": "time"}))
    available_to = forms.TimeField(initial="19:00", widget=forms.TimeInput(attrs={"type": "time"}))

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data.get("phone", "")
        user.role = User.ROLE_BEAUTICIAN
        user.is_active = False  # gated by email verification AND admin approval
        if commit:
            user.save()
            profile = BeauticianProfile.objects.create(
                user=user,
                bio=self.cleaned_data.get("bio", ""),
                address=self.cleaned_data["address"],
                latitude=self.cleaned_data["latitude"],
                longitude=self.cleaned_data["longitude"],
                service_radius_km=self.cleaned_data["service_radius_km"],
                available_from=self.cleaned_data["available_from"],
                available_to=self.cleaned_data["available_to"],
            )
            skill_names = [s.strip() for s in self.cleaned_data["skills"].split(",") if s.strip()]
            for name in skill_names:
                skill, _ = ServiceSkill.objects.get_or_create(name__iexact=name, defaults={"name": name})
                profile.skills.add(skill)
        return user


class BeauticianProfileForm(BootstrapFormMixin, forms.ModelForm):
    skills_text = forms.CharField(
        required=True, label="Skills",
        help_text="Comma separated, e.g. Makeup, Mehndi, Hair Styling",
    )

    class Meta:
        model = BeauticianProfile
        fields = [
            "bio", "profile_photo", "address", "latitude", "longitude",
            "service_radius_km", "available_from", "available_to",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "available_from": forms.TimeInput(attrs={"type": "time"}),
            "available_to": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["skills_text"].initial = ", ".join(s.name for s in self.instance.skills.all())
        self.fields["profile_photo"].widget.attrs["class"] = "form-control"

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            profile.skills.clear()
            names = [s.strip() for s in self.cleaned_data["skills_text"].split(",") if s.strip()]
            for name in names:
                skill, _ = ServiceSkill.objects.get_or_create(name__iexact=name, defaults={"name": name})
                profile.skills.add(skill)
        return profile


class TOTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=6, label="6-digit code",
        widget=forms.TextInput(attrs={
            "class": "form-control", "autocomplete": "one-time-code",
            "inputmode": "numeric", "placeholder": "123456",
        }),
    )
