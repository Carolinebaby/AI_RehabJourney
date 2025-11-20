"""
数据库存储的模型的定义

定义的模型：AccountBase, Doctor, Patient, DoctorPatient, HealthPlan, HealthData, MedicationRecord, Message
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver


class AccountBase(AbstractUser):
    """
    自定义用户模型，扩展了默认的 Django AbstractUser。

    属性：username, password, first_name, last_name, email, is_staff, is_active, date_joined, objects

    拓展属性：birthday, phone_number, gender, avatar, user_type
    """
    # 基本信息
    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    gender = models.BooleanField(
        _("Gender"),
        choices=[(True, "Male"), (False, "Female")],
        default=False,
        help_text=_("Designates whether the user is male or female."),
    )

    # 头像存储的地址
    avatar = ProcessedImageField(upload_to='avatar',
                                 default='avatar/user.png',
                                 verbose_name='头像',
                                 processors=[ResizeToFill(100, 100)])

    # 用户类型，具有预定义的选择项：医生、患者 或 管理员(不出现在注册地方)
    user_type = models.CharField(
        max_length=10,
        choices=[
            ("doctor", "医生"),
            ("patient", "患者"),
            ("admin", "管理员"),
        ],
        default="patient",
    )

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",  # Use a unique related_name
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        verbose_name=_("groups"),
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_set",  # Use a unique related_name
        blank=True,
        help_text=_("Specific permissions for this user."),
        verbose_name=_("user permissions"),
    )

    def __str__(self):
        return self.username or self.email


# 创建新用户前修改默认头像地址
@receiver(post_save, sender=AccountBase)
def set_default_avatar(sender, instance, created, **kwargs):
    if created:
        if instance.gender is True and instance.user_type == "doctor":
            instance.avatar = 'avatar/doctor_male.png'
        elif instance.gender is False and instance.user_type == "doctor":
            instance.avatar = 'avatar/doctor_female.png'
        elif instance.gender is True:
            instance.avatar = 'avatar/male.png'
        else:
            instance.avatar = 'avatar/female.png'

        instance.save()


class Doctor(models.Model):
    """
    医生模型, 存储医生的身份信息

    与 AccountBase 模型一对一关联，用于存储与用户相关的健康档案。

    属性：user, hospital, specialization, license_number, position
    """
    user = models.OneToOneField(
        AccountBase, on_delete=models.CASCADE, primary_key=True, related_name="doctor_profile"
    )
    hospital = models.CharField(max_length=100)  # 医院
    specialization = models.CharField(max_length=100)  # 专业领域
    license_number = models.CharField(max_length=100, unique=True)  # 医师执照编号
    position = models.CharField(  # 职位
        max_length=20,
        choices=[
            ("chief", "主任"),
            ("associate_chief", "副主任"),
            ("attending", "主治医生"),
            ("resident", "住院医师"),
            ("consultant", "顾问医师"),
            ("intern", "实习医师"),
            ("other", "其他"),
        ],
        default="other",
    )

    def __str__(self):
        return f"{self.user.username} ({self.specialization})"


class Patient(models.Model):
    """
    患者模型，表示患者的详细信息。

    与 AccountBase 模型一对一关联，用于存储与用户相关的健康档案。

    属性：user, height, medical_history, family_history, current_diagnosis, medications, allergy_info, living_habits, occupation, educational_level
    """
    user = models.OneToOneField(
        AccountBase, on_delete=models.CASCADE, primary_key=True, related_name="patient_profile"
    )
    height = models.DecimalField(  # 身高，单位：米
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.5), MaxValueValidator(2.5)],
    )
    blood_type = models.CharField(  # 血型
        max_length=4,
        choices=[("A", "A型血"), ("B", "B型血"), ("O", "O型血"), ("AB", "AB型血")]
    )
    medical_history = models.TextField(blank=True)  # 病史
    family_history = models.TextField(blank=True)  # 家族病史
    current_diagnosis = models.TextField(blank=True)  # 当前诊断
    medications = models.TextField(blank=True)  # 用药情况
    allergy_info = models.TextField(blank=True)  # 过敏信息
    living_habits = models.TextField(blank=True)  # 生活习惯：是否抽烟、喝酒、熬夜、暴饮暴食
    occupation = models.CharField(max_length=20, blank=True)  # 职业
    educational_level = models.CharField(
        max_length=15,
        choices=[
            ('none', '无学历'),
            ('primary', '小学'),
            ('secondary', '中学'),
            ('high_school', '高中'),
            ('associate', '大专'),
            ('bachelor', '本科'),
            ('master', '硕士'),
            ('doctorate', '博士')
        ],
        default='none',
        help_text="患者的教育水平"
    )

    def __str__(self):
        return self.user.username


class DoctorPatient(models.Model):
    """
    医生-患者关系表

    属性：start_date, end_date, therapeutic_goal
    """
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="doctor_patient_relationships"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="doctor_patient_relationships"
    )

    start_date = models.DateField()  # 开始时间
    end_date = models.DateField(blank=True, null=True)  # 结束时间
    therapeutic_goal = models.TextField(blank=True)  # 治疗目标

    def clean(self):
        if not self.doctor or not self.patient:
            raise ValidationError("Both doctor and patient must be provided.")
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date must be after start date.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor.user.username} - {self.patient.user.username}"


class HealthPlan(models.Model):
    """
    健康计划模型

    属性：doctor_patient, title, description, created_by, created_at, due_time, frequency, status
    """
    doctor_patient = models.ForeignKey(
        DoctorPatient,
        on_delete=models.CASCADE,
        related_name="health_plans",
        null=True,  # 数据库中允许存储 NULL 值
        blank=True  # 表单中允许该字段为空
    )

    title = models.CharField(max_length=100)  # 计划名称
    description = models.TextField(blank=True)  # 计划描述
    created_by = models.CharField(max_length=20, default="自己")  # 创建者
    start_time = models.DateTimeField(null=True) # 开始时间
    due_time = models.DateTimeField(null=True)  # 结束时间
    frequency = models.IntegerField(default=1, help_text="每几天完成一次")  # 频率, 1 代表每天都做, 2 代表 每隔一天完成一次
    last_complete_time = models.DateTimeField(blank=True, null=True) # 上一次完成的时间

    status = models.CharField(  # 健康计划状态
        max_length=12,
        choices=[
            ("uncompleted", "进行中"),
            ("expired", "结束"),
            ("not_start", "未开始"),
        ],
    )

    def __str__(self):
        return f"{self.title}"


class HealthData(models.Model):
    """
    健康数据模型

    属性：patient, record_time, heart_rate, weight, systolic_bp, diastolic_bp, body_temperature, blood_sugar,
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="health_data_records"
    )

    record_time = models.DateTimeField(auto_now_add=True, )  # 记录时间
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # 体重
    heart_rate = models.IntegerField(blank=True, null=True)  # 心率
    systolic_bp = models.PositiveIntegerField(blank=True, null=True)  # 收缩压
    diastolic_bp = models.PositiveIntegerField(blank=True, null=True)  # 舒张压
    body_temperature = models.DecimalField(max_digits=4, decimal_places=2)  # 体温
    blood_sugar = models.DecimalField(max_digits=5, decimal_places=2)  # 血糖
    extra_data = models.TextField(blank=True)  # 补充额外数据

    def __str__(self):
        return f"Health data for {self.patient.user.username} at {self.record_time}"


class MedicationRecord(models.Model):
    """
    药物摄入记录

    属性：patient, drug, dosage, record_time, notes
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="medication_records"
    )
    drug = models.CharField(max_length=100)  # 药物名称
    dosage = models.CharField(max_length=20)  # 摄入量字符串表示
    record_time = models.DateTimeField(auto_now_add=True, )  # 记录时间
    notes = models.TextField(blank=True)  # 补充内容，比如不良反应

    def __str__(self):
        return f"Medication record for {self.patient.user.username} on {self.record_time}"


class Message(models.Model):
    """
    消息模型

    属性：sender, receiver, message_type, text_content, file_url, send_time
    """
    sender = models.ForeignKey(
        AccountBase, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        AccountBase, on_delete=models.CASCADE, related_name="received_messages"
    )
    message_type = models.CharField(
        max_length=10, choices=[("text", "文本消息"), ("file", "文件消息")]
    )
    text_content = models.TextField(blank=True)  # 文本消息的内容
    file_url = models.URLField(blank=True, null=True)  # 文件消息的文件存储地址
    send_time = models.DateTimeField(auto_now_add=True)  # 发送时间

    def clean(self):
        if not self.text_content and not self.file_url:
            raise ValidationError("text_content 和 file_url 都没有提供")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.send_time}"
