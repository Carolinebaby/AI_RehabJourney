"""
定义基本表单类型
"""

from django import forms
from core.models import AccountBase, Doctor, Patient

class UserSignupForm(forms.ModelForm):
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = AccountBase
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'birthday', 'gender', 'phone_number', 'user_type']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError("密码和确认密码不一致")
        return cleaned_data

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['hospital', 'specialization', 'license_number', 'position']

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['height', 'blood_type', 'family_history', 'current_diagnosis', 'medical_history', 'allergy_info', 'medications', 'living_habits', 'occupation', 'educational_level']
