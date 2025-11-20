"""
实现医生角色的功能：查看患者信息、为患者定制健康计划、和患者实时沟通、个人信息修改

在每个视图函数前加入自定义装饰器，限定角色必须是医生才能访问这些界面，防止越权访问
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

from core.models import *
from django.views.decorators.csrf import csrf_exempt


# 自定义装饰器：要求用户为医生
def doctor_required(view_func):
    from django.http import HttpResponseForbidden
    @login_required  # 确保用户已登录
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'doctor':  # 根据 user_type 判断是否为医生
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@doctor_required
def index_view(request):
    return render(request, 'doctor/index.html')


####################################################################################################
# 医生功能板块1：患者管理（添加/删除）                                                                    #
####################################################################################################
@doctor_required
def patient_manage_view(request):
    return render(request, "doctor/patient_manage.html")


@doctor_required
@csrf_exempt
def fetch_patient_view(request):
    """
    查看所有患者的信息
    """
    if request.method == "POST":
        doctor = get_object_or_404(Doctor, user=request.user)
        relationships = doctor.doctor_patient_relationships.select_related('patient__user').order_by('start_date')

        data = [
            {
                "id": rel.id,
                "patient_id": rel.patient.user.id,
                "avatar": rel.patient.user.avatar.url,
                "first_name": rel.patient.user.first_name,
                "last_name": rel.patient.user.last_name,
                "age": rel.patient.user.birthday and (timezone.now().year - rel.patient.user.birthday.year),
                "gender": "男" if rel.patient.user.gender else "女",
                "current_diagnosis": rel.patient.current_diagnosis,
                "therapeutic_goal": rel.therapeutic_goal,
                "start_date": rel.start_date.strftime("%Y-%m-%d"),
                "end_date": rel.end_date.strftime("%Y-%m-%d") if rel.end_date else None,
            }
            for rel in relationships
        ]

        return JsonResponse({"patients": data})
    return HttpResponseBadRequest("Invalid request method.")


@doctor_required
def add_patient_view(request):
    """
    添加患者（即，添加 DoctorPatient 关系）

    需要信息： doctor, patient, start_date, end_date, therapeutic_goal
    """
    if request.method == "POST":
        doctor = get_object_or_404(Doctor, user=request.user)

        patient_username = request.POST.get('username')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        therapeutic_goal = request.POST.get('therapeutic_goal')

        try:
            patient_user = AccountBase.objects.get(username=patient_username)
            patient = get_object_or_404(Patient, user=patient_user)
        except AccountBase.DoesNotExist:
            return JsonResponse({"error": "患者的用户名不存在."})

        # 创建新的医患关系
        DoctorPatient.objects.get_or_create(
            doctor=doctor,
            patient=patient,
            start_date=start_date,
            end_date=end_date if end_date else None,
            therapeutic_goal=therapeutic_goal,
        )

        return JsonResponse({"success": "患者添加成功."})

    return render(request, 'doctor/patient_manage.html')


@doctor_required
def check_patient_username_view(request):
    """
    检测 想要添加用户名 是否合法（1. 存在 2. 为患者）
    """
    import json
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username')

            user = AccountBase.objects.get(username=username)
            if not hasattr(user, 'patient_profile'):
                return JsonResponse({"valid": False, "message": "用户名无效"})

            doctor = request.user.doctor_profile
            existing_relationship = DoctorPatient.objects.filter(doctor=doctor, patient__user=user).exists()
            if existing_relationship:
                return JsonResponse({"valid": False, "message": "该患者已在你管理患者的名单中"})

            return JsonResponse({"valid": True})

        except AccountBase.DoesNotExist:
            return JsonResponse({"valid": False, "message": "用户名不存在"})

        except json.JSONDecodeError:
            return JsonResponse({"valid": False, "message": "无效请求"}, status=400)

    return JsonResponse({"valid": False, "message": "无效请求"}, status=400)


@doctor_required
def patient_info_view(request, user_id):
    """
    患者信息展示
    :param request: 前端的请求
    :param user_id: 想要展示患者的 id
    """
    from django.shortcuts import render, get_object_or_404
    # 获取患者信息
    user = get_object_or_404(AccountBase, id=user_id)
    patient = get_object_or_404(Patient, user=user)
    doctor = Doctor.objects.get(user=request.user)
    dp = DoctorPatient.objects.get(doctor=doctor, patient=patient)
    # 获取该患者的健康数据记录
    health_data_records = HealthData.objects.filter(patient=patient).order_by('-record_time')[:10]  # 取最近的10条记录

    # 获取该患者的最近药物摄入记录
    medication_records = MedicationRecord.objects.filter(patient=patient).order_by('-record_time')[:10]  # 取最近的10条药物记录

    # 传递患者信息、健康数据和药物记录到模板
    context = {
        'patient': patient,
        'therapeutic_goal': dp.therapeutic_goal,
        'health_data': health_data_records,
        'medication_records': medication_records,  # 新增药物记录
    }

    return render(request, 'doctor/patient_info.html', context)


@csrf_exempt
def update_patient_info_view(request):
    """
    医生可以修改 当前诊断信息和治疗目标：
    """
    import json
    if request.method == 'POST':
        try:
            # 解析请求中的 JSON 数据
            data = json.loads(request.body)
            user_id = data.get('patient_id')
            field = data.get('field')
            new_value = data.get('new_value')

            # 打印请求和传入的数据
            print(request.user.id, user_id, field, new_value)

            # 获取患者对象
            patient = Patient.objects.get(user__id=user_id)  # 根据 user_id 获取患者
            doctor = Doctor.objects.get(user=request.user)
            # 获取对应的医生-患者关系
            try:
                dp = DoctorPatient.objects.get(doctor=doctor, patient=patient)
            except DoctorPatient.DoesNotExist:
                return JsonResponse({"status": "error", "message": "医生与该患者无关联"})

            # 根据 field 动态更新相应的字段
            if field == 'current_diagnosis':
                patient.current_diagnosis = new_value
            elif field == 'therapeutic_goal':
                dp.therapeutic_goal = new_value
            else:
                return JsonResponse({"status": "error", "message": "无效字段"})

            # 保存更改
            patient.save()
            dp.save()

            return JsonResponse({"status": "success", "message": "信息更新成功"})

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "无效的请求数据"})
        except Patient.DoesNotExist:
            return JsonResponse({"status": "error", "message": "患者不存在"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})


####################################################################################################
# 医生功能板块2：患者健康计划查看、修改                                                                   #
####################################################################################################
@doctor_required
def patient_health_plan_view(request):
    """
    医生所管理的所有病人的所有健康计划展示
    """
    # 获取当前登录医生的所有病人
    doctor_patient_relationships = DoctorPatient.objects.filter(doctor__user=request.user)

    # 为每个病人获取所有 doctor_patient 关系下的健康计划，并根据起始时间排序
    patient_health_plans = []
    for relationship in doctor_patient_relationships:
        patient = relationship.patient
        dr_pt = DoctorPatient.objects.filter(patient=patient)
        health_plans = []

        for dp in dr_pt:
            # 获取当前 doctor_patient 关系的健康计划，并按照 start_time 排序
            plans = HealthPlan.objects.filter(doctor_patient=dp).order_by('start_time')

            for plan in plans:
                if plan.start_time and plan.start_time > timezone.now():
                    plan.status = "not_start"
                    plan.save()
                elif plan.status == "uncompleted" and plan.due_time and plan.due_time < timezone.now():
                    plan.status = "expired"
                    plan.save()
                # 如果当前 doctor_patient 的医生是请求中的医生，则修改创建者为 "我"
                if dp.doctor.user == request.user and plan.created_by != "自己":
                    plan.created_by = "我"  # 临时修改，仅在视图中使用，不保存到数据库

                health_plans.append(plan)

        # 获取当前病人对应的所有健康计划，按照 start_time 排序
        patient_health_plans.append({
            "patient": relationship.patient.user,
            "health_plans": health_plans
        })

    return render(request, "doctor/patient_health_plan.html", {"patient_health_plans": patient_health_plans})


@doctor_required
def add_patient_health_plan_view(request, user_id):
    """
    为选定患者添加健康计划
    :param request: 前端请求
    :param user_id: 选定患者的 user_id
    """
    from django.utils import timezone
    patient = get_object_or_404(Patient, user_id=user_id)
    doctor = get_object_or_404(Doctor, user=request.user)
    # 查找关联的 DoctorPatient 实例，确保根据患者找到相关医生和患者关系
    doctor_patient = DoctorPatient.objects.filter(patient=patient, doctor=doctor).first()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        start_time = request.POST.get('start_time')
        due_time = request.POST.get('due_time')
        frequency = request.POST.get('frequency')

        # 将字符串转换为日期时间格式
        if due_time:
            due_time = timezone.datetime.fromisoformat(due_time)

        # 创建新的健康计划
        health_plan = HealthPlan(
            doctor_patient=doctor_patient,
            title=title,
            description=description,
            due_time=due_time,
            created_by=request.user.doctor_profile.get_position_display(),  # 使用当前医生的职位作为 created_by
            start_time=start_time,
            frequency=frequency,
            status='uncompleted',  # 默认状态
        )
        health_plan.save()

        return redirect('dr_patient_health_plan')


@doctor_required
def delete_health_plans_view(request):
    """
    删除自己添加的计划
    """
    if request.method == 'POST':
        # 获取选择的健康计划 ID 列表
        selected_plans = request.POST.getlist('plans[]')  # 获取传递的所有计划 ID

        if not selected_plans:
            return JsonResponse({'status': 'error', 'message': '没有选中的计划'})

        # 获取与当前医生相关的健康计划
        health_plans_to_delete = HealthPlan.objects.filter(id__in=selected_plans)

        # 检查健康计划的创建者是否为该医生
        for plan in health_plans_to_delete:
            if plan.doctor_patient is None or plan.doctor_patient.doctor.user != request.user:
                return JsonResponse({'status': 'error', 'message': f'健康计划 {plan.title} 不是由您创建，无法删除'})

        # 执行删除操作
        health_plans_to_delete.delete()
        return JsonResponse({'status': 'success', 'message': '删除成功'})
    return JsonResponse({'status': 'error'})


@doctor_required
def edit_health_plan_view(request):
    """
    修改自己创建的计划
    """
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")  # 获取要修改的健康计划 ID
        title = request.POST.get("edit_title")
        description = request.POST.get("edit_description")
        start_time = request.POST.get("edit_start_time")
        due_time = request.POST.get("edit_due_time")
        frequency = request.POST.get("edit_frequency")

        # 打印 debug 信息，确保 plan_id 正确
        print(f"Received plan_id: {plan_id}")

        try:
            # 获取对应的健康计划并更新
            plan = HealthPlan.objects.get(id=plan_id, doctor_patient__doctor__user=request.user)
            plan.title = title
            plan.description = description
            plan.start_time = start_time
            plan.due_time = due_time
            plan.frequency = frequency
            plan.save()

            return JsonResponse({"status": "success", "message": "健康计划修改成功"})
        except HealthPlan.DoesNotExist:
            return JsonResponse({"status": "error", "message": "健康计划不存在"})

    return JsonResponse({"status": "error", "message": "无效的请求"})


####################################################################################################
# 医生功能板块3：医患交流                                                                              #
####################################################################################################

@doctor_required
def chat_view(request):
    """
    聊天界面
    """
    from django.db.models import Q
    # 获取当前用户关联的聊天对象，并排除自己和自己聊天的情况
    patient_list = DoctorPatient.objects.filter(
        (Q(doctor__user=request.user) & ~Q(patient__user=request.user))
    ).select_related('doctor__user', 'patient__user')

    # 渲染模板并传递聊天对象列表
    return render(
        request,
        "doctor/chat.html",
        {"patient_list": patient_list}
    )


@doctor_required
def get_messages_view(request, user_id):
    """
    获取聊天记录
    :param request: 请求
    :param user_id: 聊天对象的 user_id
    """
    import os
    from django.db.models import Q
    from urllib.parse import unquote  # 用于解码 URL 编码的中文文件名

    if request.user.is_authenticated:
        # 验证聊天对象合法性
        is_valid_user = DoctorPatient.objects.filter(
            (Q(doctor__user=request.user) & Q(patient__user__id=user_id)) |
            (Q(patient__user=request.user) & Q(doctor__user__id=user_id))
        ).exists()

        if not is_valid_user:
            return JsonResponse({'error': 'Invalid chat partner'}, status=400)

        # 获取消息
        messages = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver__id=user_id)) |
            (Q(sender__id=user_id) & Q(receiver=request.user))
        ).order_by('send_time')

        response_data = []
        for msg in messages:
            if msg.message_type == "file":
                # 获取相对路径
                file_url = msg.file_url
                file_name = unquote(os.path.basename(file_url))
                # 解码文件名（URL编码）
                if msg.text_content:
                    file_name = msg.text_content

                response_data.append({
                    'sender__id': msg.sender.id,
                    'receiver__id': msg.receiver.id,
                    'message_type': msg.message_type,
                    'file_url': file_url,  # 返回文件的相对路径
                    'file_name': file_name,  # 中文文件名
                    'send_time': msg.send_time.strftime('%Y-%m-%d %H:%M:%S'),
                })
            else:
                response_data.append({
                    'sender__id': msg.sender.id,
                    'receiver__id': msg.receiver.id,
                    'message_type': msg.message_type,
                    'text_content': msg.text_content,
                    'send_time': msg.send_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

        return JsonResponse({'messages': response_data})
    return JsonResponse({'error': 'Unauthorized'}, status=401)


@doctor_required
def send_message_view(request):
    """
    发送消息

    注：在这里实现的是非实时发送消息，即只调用这个函数的话，并不会刷新对方的界面，实时通信的功能在前端使用 js 后端使用 channels 实现 websocket 通信。
    """
    import json
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        text_content = data.get('text_content')

        # 校验数据并存储新消息
        if receiver_id and text_content:
            Message.objects.create(
                sender=request.user,
                receiver_id=receiver_id,
                text_content=text_content,
                message_type='text'
            )
            return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
@doctor_required
def send_file_view(request):
    """
    发送文件
    """
    from django.core.files.storage import default_storage
    from django.utils.timezone import now
    import os
    import uuid

    # 定义允许的文件类型
    ALLOWED_FILE_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'],
        'video': ['video/mp4', 'video/avi', 'video/mkv', 'video/mov'],
        'document': ['application/pdf', 'application/msword',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'audio': ['audio/mpeg', 'audio/ogg', 'audio/wav']
    }

    if request.method == "POST":
        try:
            sender = request.user
            receiver_id = request.POST.get('receiver_id')
            file = request.FILES.get('file')

            # 校验数据
            if not receiver_id or not file:
                return JsonResponse({'success': False, 'error': 'Missing receiver_id or file'}, status=400)

            # 获取接收者实例
            try:
                receiver = AccountBase.objects.get(id=receiver_id)
            except AccountBase.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Receiver not found'}, status=404)

            # 校验文件类型
            file_type = file.content_type
            if not any(file_type in types for types in ALLOWED_FILE_TYPES.values()):
                return JsonResponse({'success': False, 'error': 'Invalid file type'}, status=400)

            # 文件存储路径
            folder_path = f"chat_files/{now().strftime('%Y%m%d')}/"
            original_file_name = file_name = file.name
            file_path = os.path.join(folder_path, file_name)

            # 检查文件是否已存在，若存在，修改文件名
            while default_storage.exists(file_path):
                # 如果文件已存在，生成新的唯一文件名
                file_name = f"{uuid.uuid4().hex}_{file.name}"  # 生成唯一的文件名
                file_path = os.path.join(folder_path, file_name)

            # 保存文件
            file_path = default_storage.save(file_path, file)
            file_url = default_storage.url(file_path)

            Message.objects.create(
                sender=sender,
                receiver=receiver,
                text_content=original_file_name,
                message_type="file",
                file_url=file_url,
            )

            return JsonResponse({
                'success': True,
                'file_url': file_url,
                'file_name': original_file_name,
                'file_size': file.size // 1024  # 文件大小，单位为KB
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


####################################################################################################
# 医生功能板块4：个人信息查看/修改                                                                       #
####################################################################################################
@doctor_required
def personal_info_view(request):
    """
    个人信息展示
    """
    user = request.user
    return render(request, 'doctor/personal_info.html', {
        'user': user
    })


@doctor_required
def modify_info_view(request):
    """
    修改个人信息
    """
    user = request.user

    if request.method == "POST":
        # 如果用户名唯一或未修改用户名，继续更新用户信息
        user.birthday = request.POST.get("birthday")
        user.gender = request.POST.get("gender") == "True"
        user.phone_number = request.POST.get("phone_number")
        if request.FILES.get("avatar"):
            user.avatar = request.FILES.get("avatar")
        user.save()

        # 更新患者信息
        if user.user_type == "patient":
            patient_profile = user.patient_profile
            patient_profile.height = request.POST.get("height")
            patient_profile.family_history = request.POST.get("family_history")
            patient_profile.current_diagnosis = request.POST.get("current_diagnosis")
            patient_profile.medical_history = request.POST.get("medical_history")
            patient_profile.medications = request.POST.get("medications")
            patient_profile.save()

        # 更新医生信息
        elif user.user_type == "doctor":
            doctor_profile = user.doctor_profile
            doctor_profile.hospital = request.POST.get("hospital")
            doctor_profile.specialization = request.POST.get("specialization")
            doctor_profile.license_number = request.POST.get("license_number")
            doctor_profile.position = request.POST.get("position")
            doctor_profile.save()

        return redirect("dr_personal_info")  # 重定向到个人信息页面

    return render(
        request,
        "doctor/modify_info.html",
        {"user": user},
    )
