"""
实现普通用户的基本功能：查看健康计划，健康数据记录，医患交流，个人信息查看和修改

在每个视图函数加入自定装饰器，防止越权访问
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from core.models import AccountBase, Doctor, Patient, DoctorPatient, HealthData, HealthPlan, Message, MedicationRecord
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse



# 自定义装饰器：要求用户为患者
def patient_required(view_func):
    from django.http import HttpResponseForbidden
    @login_required  # 确保用户已登录
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'patient':  # 根据 user_type 判断是否为患者
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@patient_required
def index_view(request):
    return render(request, 'patient/index.html')


####################################################################################################
# 患者功能板块1：健康计划管理                                                                           #
####################################################################################################
@patient_required
def health_plan_view(request):
    """
    展示用户的健康计划列表
    """
    from django.utils import timezone
    # 获取当前患者相关的健康计划
    health_plans = HealthPlan.objects.filter(doctor_patient__patient__user=request.user)
    today_plans = []
    # 自动判断健康计划的状态
    for plan in health_plans:
        if plan.start_time and plan.start_time > timezone.now():
            plan.status = "not_start"
            plan.save()
        elif plan.status == "uncompleted" and plan.due_time and plan.due_time < timezone.now():
            plan.status = "expired"
            plan.save()
    now = timezone.now()
    for plan in health_plans:
        if plan.start_time <= now <= plan.due_time and (
                plan.frequency == 0 or (now - plan.start_time).days % plan.frequency == 0):
            today_plans.append(plan)

    context = {'all_plans': health_plans, 'today_plans': today_plans, 'today': timezone.now().date()}
    return render(request, 'patient/health_plan.html', context)


# 健康计划添加（用户个人添加，使用注册时候创建的 default 关系作为 健康计划的dr_pt关系输入）
@patient_required
def add_health_plan_view(request):
    from django.shortcuts import get_object_or_404
    from django.shortcuts import redirect
    from datetime import datetime
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        start_time = request.POST.get('start_time')
        due_time = request.POST.get('due_time')

        # 检查 start_time 和 due_time 是否为有效字符串
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                start_time = None
        if due_time:
            try:
                due_time = datetime.fromisoformat(due_time)
            except ValueError:
                due_time = None

        frequency = request.POST.get('frequency')

        # 查找默认医生与当前患者的关系
        default_doctor = get_object_or_404(Doctor, user__username='default')
        doctor_patient = DoctorPatient.objects.filter(
            doctor=default_doctor,
            patient__user=request.user
        ).first()

        if not doctor_patient:
            # 如果找不到默认关系，可以抛出异常或者根据业务逻辑处理
            raise ValueError("Default doctor-patient relationship not found.")

        # 保存健康计划
        health_plan = HealthPlan(
            doctor_patient=doctor_patient,
            title=title,
            description=description,
            start_time=start_time,
            due_time=due_time,
            frequency=frequency,
            created_by="自己",
            status="uncompleted",
        )
        health_plan.save()

        return redirect('pt_health_plan')


# 删除自己创建的健康计划
@patient_required
def delete_health_plans_view(request):
    if request.method == 'POST':
        # 获取选择的健康计划 ID 列表
        selected_plans = request.POST.getlist('plans[]')  # 获取传递的所有计划 ID

        if not selected_plans:
            return JsonResponse({'status': 'error', 'message': '没有选中的计划'})

        # 删除健康计划
        HealthPlan.objects.filter(id__in=selected_plans).delete()

        return JsonResponse({'status': 'success', 'message': '删除成功'})
    return JsonResponse({'status': 'error'})


# 修改自己创建的健康计划
@patient_required
def edit_health_plan_view(request):
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")  # 获取要修改的健康计划 ID
        title = request.POST.get("edit_title")
        description = request.POST.get("edit_description")
        start_time = request.POST.get("edit_start_time")
        due_time = request.POST.get("edit_due_time")
        frequency = request.POST.get("edit_frequency")

        try:
            # 获取对应的健康计划并更新
            plan = HealthPlan.objects.get(id=plan_id, doctor_patient__patient__user=request.user)
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


# 更新今日计划的状态
@patient_required
def update_plan_status_view(request):
    import json
    if request.method == "POST":
        try:
            # 获取请求体中的 JSON 数据
            data = json.loads(request.body)

            plan_id = data.get("plan_id")
            is_checked = data.get("is_checked")

            # 获取健康计划对象
            plan = HealthPlan.objects.get(id=plan_id, doctor_patient__patient__user=request.user)

            # 根据复选框状态更新计划
            if is_checked:
                plan.last_complete_time = timezone.now()
            else:
                plan.last_complete_time = None

            plan.save()

            return JsonResponse({'status': 'success', 'message': '计划状态更新成功'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})


####################################################################################################
# 患者功能板块2：健康数据记录、药物摄入记录                                                                #
####################################################################################################
@patient_required
def health_data_view(request):
    import json
    # 获取当前用户的健康记录
    health_data_records = HealthData.objects.filter(patient=request.user.patient_profile).order_by('-record_time')[
                          :10]

    # 准备图表数据
    chart_data = {
        "weight": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [float(record.weight) if record.weight else None for record in health_data_records],
                "type": "line",
                "name": "体重"
            }]
        },
        "systolic_bp": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [record.systolic_bp if record.systolic_bp else None for record in health_data_records],
                "type": "line",
                "name": "收缩压"
            }]
        },
        "diastolic_bp": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [record.diastolic_bp if record.diastolic_bp else None for record in health_data_records],
                "type": "line",
                "name": "舒张压"
            }]
        },
        "heart_rate": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [record.heart_rate if record.heart_rate else None for record in health_data_records],
                "type": "line",
                "name": "心率"
            }]
        },
        "body_temperature": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [float(record.body_temperature) if record.body_temperature else None for record in
                         health_data_records],
                "type": "line",
                "name": "体温"
            }]
        },
        "blood_sugar": {
            "xAxis": {"type": "category",
                      "data": [record.record_time.strftime('%Y-%m-%d') for record in health_data_records]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [float(record.blood_sugar) if record.blood_sugar else None for record in
                         health_data_records],
                "type": "line",
                "name": "血糖"
            }]
        }
    }

    # 将数据传递给模板
    return render(request, "patient/health_data.html", {
        'health_data_records': health_data_records,
        'chart_data_json': json.dumps(chart_data)  # 将图表数据传递给模板
    })


@patient_required
def add_health_data_view(request):
    """
    添加个人健康数据
    """
    from django.utils.timezone import now
    from datetime import datetime
    if request.method == "POST":
        # 获取表单数据
        record_time = request.POST.get('record_time', None)
        weight = request.POST.get('weight', None)
        systolic_bp = request.POST.get('systolic_bp', None)
        diastolic_bp = request.POST.get('diastolic_bp', None)
        heart_rate = request.POST.get('heart_rate', None)
        body_temperature = request.POST.get('body_temperature', None)
        blood_sugar = request.POST.get('blood_sugar', None)
        extra_data = request.POST.get('extra_data', None)

        patient = request.user.patient_profile

        # 校验数据
        if not body_temperature or not blood_sugar:
            return JsonResponse({"error": "体温和血糖是必填项"}, status=400)

        # 转换数据类型
        try:
            if weight:
                weight = float(weight)
            if systolic_bp:
                systolic_bp = int(systolic_bp)
            if diastolic_bp:
                diastolic_bp = int(diastolic_bp)
            if heart_rate:
                heart_rate = int(heart_rate)
            if body_temperature:
                body_temperature = float(body_temperature)
            if blood_sugar:
                blood_sugar = float(blood_sugar)
        except ValueError:
            return JsonResponse({"error": "数据格式错误"}, status=400)

        # 记录时间处理
        if not record_time:
            record_time = now()
        else:
            try:
                record_time = datetime.fromisoformat(record_time)
            except ValueError:
                return JsonResponse({"error": "无效的时间格式"}, status=400)

        # 保存记录
        health_data = HealthData(
            patient=patient,
            record_time=record_time,
            weight=weight,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            heart_rate=heart_rate,
            body_temperature=body_temperature,
            blood_sugar=blood_sugar,
            extra_data=extra_data
        )
        health_data.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True}, status=201)

            # 对于普通表单提交（非 AJAX 请求），重定向到列表页面
        return redirect("pt_health_data")

    return render(request, "patient/health_data.html")


@patient_required
def medication_record_view(request):
    medication_records = MedicationRecord.objects.filter(patient=request.user.patient_profile).order_by('-record_time')[
                         :10]

    return render(request, "patient/medication_record.html", {
        'medication_records': medication_records
    })


@patient_required
def add_medication_record_view(request):
    from django.utils.timezone import now
    from datetime import datetime
    from django.http import JsonResponse

    if request.method == "POST":
        # 获取表单数据
        record_time = request.POST.get('record_time', None)
        drug = request.POST.get('drug', None)
        dosage = request.POST.get('dosage', None)
        notes = request.POST.get('notes', '')

        patient = request.user.patient_profile

        # 校验数据
        if not drug or not dosage:
            return JsonResponse({"error": "药物名称和剂量是必填项"}, status=400)

        # 记录时间处理
        if not record_time:
            record_time = now()
        else:
            try:
                record_time = datetime.fromisoformat(record_time)
            except ValueError:
                return JsonResponse({"error": "无效的时间格式"}, status=400)

        # 保存记录
        medication_record = MedicationRecord(
            patient=patient,
            drug=drug,
            dosage=dosage,
            record_time=record_time,
            notes=notes
        )
        medication_record.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True}, status=201)

        # 对于普通表单提交（非 AJAX 请求），重定向到药物记录页面
        return redirect("pt_medication_record")

    return render(request, "patient/medication_record.html")


####################################################################################################
# 患者功能板块3：医患交流板块                                                                           #
####################################################################################################
@patient_required
def chat_view(request):
    from django.db.models import Q
    # 获取当前用户关联的聊天对象，并排除自己和自己聊天的情况
    doctor_patient_list = DoctorPatient.objects.filter(
        (
                (Q(doctor__user=request.user) & ~Q(patient__user=request.user)) |
                (Q(patient__user=request.user) & ~Q(doctor__user=request.user))
        ) & ~Q(doctor__user__username="default")  # 排除 default 医生
    ).select_related('doctor__user', 'patient__user')

    # 渲染模板并传递聊天对象列表
    return render(
        request,
        "patient/chat.html",
        {"doctor_patient_list": doctor_patient_list}
    )


@patient_required
def get_messages(request, user_id):
    from django.db.models import Q
    import os
    from django.conf import settings
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


@patient_required
def send_message(request):
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
@patient_required
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


def contact_view(request):
    from django.db.models import Q
    # 获取当前用户关联的聊天对象，并排除自己和自己聊天的情况
    doctor_patient_list = DoctorPatient.objects.filter(
        (
                (Q(doctor__user=request.user) & ~Q(patient__user=request.user)) |
                (Q(patient__user=request.user) & ~Q(doctor__user=request.user))
        ) & ~Q(doctor__user__username="default")  # 排除 default 医生
    ).select_related('doctor__user', 'patient__user')

    # 渲染模板并传递聊天对象列表
    return render(
        request,
        "patient/contact.html",
        {"doctor_patient_list": doctor_patient_list}
    )


def contact_info_view(request, user_id):
    from datetime import date
    if not request.user.is_authenticated:
        return JsonResponse({'error': '未登录'}, status=403)

    try:
        user = AccountBase.objects.get(id=user_id)
    except AccountBase.DoesNotExist:
        return JsonResponse({'error': '用户不存在'}, status=404)

    # 计算年龄
    if user.birthday:
        today = date.today()
        age = today.year - user.birthday.year - (
                (today.month, today.day) < (user.birthday.month, user.birthday.day)
        )
    else:
        age = "未知"

    # 性别和用户类型
    gender = "男" if user.gender else "女"
    user_type_display = dict(AccountBase._meta.get_field('user_type').choices).get(user.user_type, "未知")

    # 额外信息
    if user.user_type == "doctor":
        profile = user.doctor_profile
        extra_info = f"""
            <div>
                <h2 class="text-2xl font-bold mb-2">医生信息</h2>
                <p><strong>医院:</strong> {profile.hospital}</p>
                <p><strong>专长:</strong> {profile.specialization}</p>
                <p><strong>执照编号:</strong> {profile.license_number}</p>
                <p><strong>职称:</strong> {dict(Doctor._meta.get_field('position').choices).get(profile.position, "未知")}</p>
            </div>
        """
    elif user.user_type == "patient":
        profile = user.patient_profile
        extra_info = f"""
            <div>
                <h2 class="text-2xl font-bold mb-2">患者信息</h2>
                <p><strong>身高:</strong> {profile.height} 米</p>
                <p><strong>家族病史:</strong> {profile.family_history or "无"}</p>
                <p><strong>当前诊断:</strong> {profile.current_diagnosis or "无"}</p>
                <p><strong>病史:</strong> {profile.medical_history or "无"}</p>
                <p><strong>正在服用的药物:</strong> {profile.medications or "无"}</p>
            </div>
        """
    else:
        extra_info = "<p>无其他信息</p>"

    # 返回 JSON 数据
    return JsonResponse({
        'last_name': user.last_name,
        'first_name': user.first_name,
        'age': age,
        'gender': gender,
        'phone_number': user.phone_number,
        'user_type_display': user_type_display,
        'avatar': user.avatar.url,
        'extra_info': extra_info,
    })


####################################################################################################
# 患者功能板块4：个人信息展示                                                                           #
####################################################################################################
@patient_required
def personal_info_view(request):
    user = request.user
    return render(request, 'patient/personal_info.html', {
        'user': user
    })


@patient_required
def modify_info_view(request):
    user = request.user

    if request.method == "POST":
        user.birthday = request.POST.get("birthday")
        user.gender = request.POST.get("gender") == "True"
        user.phone_number = request.POST.get("phone_number")
        if request.FILES.get("avatar"):
            user.avatar = request.FILES.get("avatar")
        user.save()

        # 更新患者信息
        if user.user_type == "patient":
            patient_profile = user.patient_profile
            patient_profile.living_habits = request.POST.get("living_habits")  # 这里修改了
            patient_profile.blood_type = request.POST.get("blood_type")
            patient_profile.educational_level = request.POST.get("educational_level")  # 这里修改了
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

        return redirect("pt_personal_info")  # 重定向到个人信息页面

    return render(
        request,
        "patient/modify_info.html",
        {"user": user}
    )


####################################################################################################
# 补充功能：基于大语言模型的健康数据分析功能                                                                           #
####################################################################################################
from ollama import chat
from ollama import ChatResponse
import re
from html import escape

# 处理 AI 输出的内容，** 转为<strong>，空行处理
def clean_ai_output(text):
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        line = escape(line)
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        processed_lines.append(line)

    return '\n'.join(processed_lines)

@patient_required
def ai_analyze_health_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "仅支持 POST 请求"})

    user = request.user
    record = HealthData.objects.filter(patient=request.user.patient_profile).order_by('-record_time')[:10]
    if not record:
        return JsonResponse({"status": "success", "result": "您并未记录您的健康数据，请增加您近期健康数据后再进行分析。"})

    text = "以下是患者近期健康记录：\n"
    for r in record:
        text += (
            f"【记录时间】{r.record_time}\n"
            f"体重：{r.weight} kg\n"
            f"血压：{r.systolic_bp}/{r.diastolic_bp} mmHg\n"
            f"心率：{r.heart_rate} bpm\n"
            f"体温：{r.body_temperature} ℃\n"
            f"血糖：{r.blood_sugar} mmol/L\n"
            f"其他：{r.extra_data}\n"
            f"---\n"
        )
    text += "请你根据患者近期健康数据分析这位患者近期健康状况"

    message = [ {
        'role': 'user',
        'content': text
        }
    ]

    try:
        response: ChatResponse = chat(
            model='deepseek-r1:1.5b',
            messages=[
                {"role": "system",
                 "content": "假设你是一位经验丰富的医生，能够根据患者近期健康数据判断患者的身体状况，回答的时候，不要以第三人称视角回答，直接把提问者当成患者。以 “患者，您好！” 开头"},
                {
                    "role": "user",
                    "content": text
                }
            ],
            stream=False
        )
        result = response["message"]["content"]
        result = clean_ai_output(result)
        print(result)
        return JsonResponse(
            {
                "status": "success",
                "result": result
            }
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
