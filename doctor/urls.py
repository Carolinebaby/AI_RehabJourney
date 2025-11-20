from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='dr_index'),

    path('patient_manage/', views.patient_manage_view, name='dr_patient_manage'),
    path('fetch_patient/', views.fetch_patient_view, name='dr_fetch_patient'),
    path('add_patient/', views.add_patient_view, name='dr_add_patient'),
    path('patient_manage/patient_info/<int:user_id>/', views.patient_info_view, name='dr_patient_info'),
    path('patient_manage/patient_info/update_patient_info', views.update_patient_info_view, name='dr_patient_update_patient_info'),
    path('check_patient_username/', views.check_patient_username_view, name='dr_check_patient_username'),

    path('chat/', views.chat_view, name='dr_chat'),
    path('get_messages/<int:user_id>/', views.get_messages_view, name='dr_get_messages'),
    path('send_message/', views.send_message_view, name='dr_send_message'),
    path('send_file/', views.send_file_view, name='dr_send_file'),

    path('personal_info/', views.personal_info_view, name='dr_personal_info'),
    path('modify_info/', views.modify_info_view, name='dr_modify_info'),

    path('patient_health_plan/', views.patient_health_plan_view, name='dr_patient_health_plan'),
    path('add_patient_health_plan/<int:user_id>/', views.add_patient_health_plan_view,
         name='dr_add_patient_health_plan'),
    path('delete_health_plans/', views.delete_health_plans_view, name='dr_delete_health_plans'),
    path('edit_health_plan/', views.edit_health_plan_view, name='dr_edit_health_plan'),

]
