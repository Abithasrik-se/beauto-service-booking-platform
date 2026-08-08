from django import forms

from services.models import Service, ServicePackage, ServiceCategory


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()


class ServiceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["category", "name", "description", "platform_fee", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ServicePackageForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ServicePackage
        fields = ["name", "description", "price", "duration_minutes", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class ServiceCategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ["name", "icon", "order"]
