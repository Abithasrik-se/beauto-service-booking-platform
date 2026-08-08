from django import forms

from .models import Booking


class BookingForm(forms.ModelForm):
    """Used on the "book this package" screen. `package` is set in the
    view from the URL, not shown as a field here."""

    class Meta:
        model = Booking
        fields = ["address", "latitude", "longitude", "slot_start", "slot_end", "notes"]
        widgets = {
            "slot_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "slot_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Any preferences or instructions..."}),
            "address": forms.TextInput(attrs={"placeholder": "Flat / house no., street, area, city"}),
        }
        help_texts = {
            "latitude": "Pin your location's latitude (from Google Maps 'copy coordinates')",
            "longitude": "Pin your location's longitude",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("slot_start"), cleaned.get("slot_end")
        if start and end and end <= start:
            raise forms.ValidationError("Slot end time must be after the start time.")
        return cleaned


class RescheduleForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["slot_start", "slot_end"]
        widgets = {
            "slot_start": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "slot_end": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("slot_start"), cleaned.get("slot_end")
        if start and end and end <= start:
            raise forms.ValidationError("Slot end time must be after the start time.")
        return cleaned
