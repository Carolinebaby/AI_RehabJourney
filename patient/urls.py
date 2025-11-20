from django.urls import path
from . import views
urlpatterns = [
    path('', views.index_view, name='pt_index'),

    path('chat/', views.chat_view, name='pt_chat'),
    path('contact/', views.contact_view, name='pt_contact'),
    path('get_messages/<int:user_id>/', views.get_messages, name='pt_get_messages'),
    path('send_message/', views.send_message, name='pt_send_message'),
    path('send_file/', views.send_file_view, name='pt_send_file'),
    path('contact_info/<int:user_id>/', views.contact_info_view, name='pt_contact_info'),

    path('health_data/', views.health_data_view, name='pt_health_data'),
    path('add_health_data/', views.add_health_data_view, name='pt_add_health_data'),

    path('personal_info/', views.personal_info_view, name='pt_personal_info'),
    path('modify_info/', views.modify_info_view, name='pt_modify_info'),

    path('health_plan/', views.health_plan_view, name='pt_health_plan'),
    path('add_health_plan/', views.add_health_plan_view, name='pt_add_health_plan'),
    path('delete_health_plans/', views.delete_health_plans_view, name='pt_delete_health_plans'),
    path('edit_health_plan/', views.edit_health_plan_view, name='pt_edit_health_plan'),
    path('update_plan_status/', views.update_plan_status_view, name='pt_update_plan_status'),

    path('medication_record/', views.medication_record_view, name='pt_medication_record'),
    path('add_medication_record/', views.add_medication_record_view, name='pt_add_medication_record'),
    path('ai_analyze_health/', views.ai_analyze_health_view, name='pt_ai_analyze_health'),
]