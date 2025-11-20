"""
优化管理员界面，对展示内容作一定展示优化
"""

from django.contrib import admin
from .models import AccountBase, Doctor, Patient, DoctorPatient, HealthPlan, HealthData, MedicationRecord, Message

# 自定义用户管理界面
class AccountBaseAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'user_type', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('date_joined',)
    list_per_page = 20


# 医生模型管理
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'hospital', 'specialization', 'position')
    list_filter = ('hospital', 'specialization', 'position')
    search_fields = ('user__username', 'hospital', 'specialization')
    ordering = ('user__username',)
    list_per_page = 20


# 患者模型管理
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'height', 'blood_type', 'occupation', 'educational_level')
    list_filter = ('blood_type', 'educational_level')
    search_fields = ('user__username', 'occupation')
    ordering = ('user__username',)
    list_per_page = 20


# 医生与患者关系管理
class DoctorPatientAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'start_date', 'end_date', 'therapeutic_goal')
    list_filter = ('doctor', 'patient', 'start_date', 'end_date')
    search_fields = ('doctor__user__username', 'patient__user__username')
    ordering = ('start_date',)
    list_per_page = 20


# 健康计划模型管理
class HealthPlanAdmin(admin.ModelAdmin):
    list_display = ('doctor_patient', 'title', 'created_by', 'status', 'start_time', 'due_time', 'frequency')
    list_filter = ('status', 'doctor_patient')
    search_fields = ('title', 'created_by')
    ordering = ('start_time',)
    list_per_page = 20


# 健康数据模型管理
class HealthDataAdmin(admin.ModelAdmin):
    list_display = ('patient', 'record_time', 'weight', 'heart_rate', 'systolic_bp', 'diastolic_bp', 'body_temperature', 'blood_sugar')
    list_filter = ('patient', 'record_time')
    search_fields = ('patient__user__username',)
    ordering = ('record_time',)
    list_per_page = 20


# 药物摄入记录模型管理
class MedicationRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'drug', 'dosage', 'record_time', 'notes')
    list_filter = ('patient', 'drug')
    search_fields = ('drug', 'patient__user__username')
    ordering = ('record_time',)
    list_per_page = 20


# 消息模型管理
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'send_time', 'text_content', 'file_url')
    list_filter = ('message_type', 'send_time')
    search_fields = ('sender__username', 'receiver__username', 'text_content')
    ordering = ('send_time',)
    list_per_page = 20


# 注册模型
admin.site.register(AccountBase, AccountBaseAdmin)
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(DoctorPatient, DoctorPatientAdmin)
admin.site.register(HealthPlan, HealthPlanAdmin)
admin.site.register(HealthData, HealthDataAdmin)
admin.site.register(MedicationRecord, MedicationRecordAdmin)
admin.site.register(Message, MessageAdmin)
