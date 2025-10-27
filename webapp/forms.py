from django import forms
from .models import Document

class DocumentUploadForm(forms.ModelForm):
    shared = forms.BooleanField(
        required=False,
        label="Make this document public",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta:
        model = Document
        fields = ["title", "file", "shared"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter document title"
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }
