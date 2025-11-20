"""
定义网站的基本登录注册功能
"""

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login
import json
from django.http import JsonResponse
from django.contrib import messages
from .form import *
from .models import *


def index_view(request):
    return render(request, 'core/index.html')


def about_view(request):
    return render(request, 'core/about.html')


def login_view(request):
    """
    登录功能函数
    """
    from datetime import timedelta
    if request.method == 'POST':
        # 获取用户名和密码
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 登录成功
            auth_login(request, user)  # 使用 Django 提供的 auth_login 方法自动管理 session
            messages.success(request, f"登录成功！欢迎回来，{user.username}")

            # 将用户的相关信息存入 session
            request.session['is_login'] = True
            request.session['user_type'] = user.user_type
            request.session['username'] = user.username

            # 设置会话过期时间（例如，1 天）
            request.session.set_expiry(timedelta(days=1).total_seconds())

            # 根据用户类型跳转到不同页面
            if user.user_type == 'doctor':
                return redirect('/doctor/')
            elif user.user_type == 'patient':
                return redirect('pt_index')
            else:
                return redirect('/')  # 默认跳转

        else:
            # 登录失败，设置错误信息
            error_message = "用户名或密码输入错误，请重试。"
            return render(request, "core/login.html", {"error_message": error_message})

    return render(request, "core/login.html")


def signup_view(request):
    from django.utils.timezone import now
    if request.method == 'POST':
        # 用户表单
        user_form = UserSignupForm(request.POST)

        if user_form.is_valid():
            # 保存用户对象
            user = user_form.save(commit=False)
            user.set_password(user.password)  # 确保密码加密
            user.save()

            # 根据用户类型选择表单
            user_type = user.user_type

            if user_type == 'doctor':
                doctor_form = DoctorProfileForm(request.POST)
                if doctor_form.is_valid():
                    doctor = doctor_form.save(commit=False)
                    doctor.user = user  # 绑定到用户
                    doctor.save()
                    messages.success(request, "医生注册成功！")
                    return redirect('login')  # 注册成功后跳转到登录
                else:
                    messages.error(request, "医生信息表单有误，请检查输入！")
                    return render(request, 'core/signup.html', {
                        'user_form': user_form,
                        'doctor_form': doctor_form,
                    })

            elif user_type == 'patient':
                patient_form = PatientProfileForm(request.POST)
                if patient_form.is_valid():
                    patient = patient_form.save(commit=False)
                    patient.user = user  # 绑定到用户
                    patient.save()
                    messages.success(request, "患者注册成功！")
                    default_dr = Doctor.objects.get(user__username='default')
                    DoctorPatient.objects.create(
                        doctor=default_dr,
                        patient=patient,
                        start_date=now().date(),  # 注册时间
                        therapeutic_goal="default"  # 默认治疗目标
                    )
                    return redirect('login')  # 注册成功后跳转到登录
                else:
                    messages.error(request, "患者信息表单有误，请检查输入！")
                    return render(request, 'core/signup.html', {
                        'user_form': user_form,
                        'patient_form': patient_form,
                    })

            else:
                # 用户类型不匹配
                messages.error(request, "无效的用户类型，请选择医生或患者！")
                return render(request, 'core/signup.html', {
                    'user_form': user_form,
                })
        else:
            # 用户表单验证失败
            messages.error(request, "用户表单有误，请检查输入！")
            return render(request, 'core/signup.html', {
                'user_form': user_form,
            })

    else:
        # 初始化表单
        user_form = UserSignupForm()
        doctor_form = DoctorProfileForm()
        patient_form = PatientProfileForm()

    return render(request, "core/signup.html", {
        'user_form': user_form,
        'doctor_form': doctor_form,
        'patient_form': patient_form,
    })


@csrf_exempt
def check_username(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '')
        exists = AccountBase.objects.filter(username=username).exists()
        return JsonResponse({'exists': exists})


@csrf_exempt
def check_email(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email', '')
        exists = AccountBase.objects.filter(email=email).exists()
        return JsonResponse({'exists': exists})



def logout_view(request):
    from django.contrib.auth import logout
    # 退出当前用户的会话
    logout(request)
    # 重定向到首页或登录页
    return redirect('index')