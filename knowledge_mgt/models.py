from django.db import models
from django.utils import timezone

# Create your models here.

# 自定义用户模型，引用实际的user表
class CustomUser(models.Model):
    """自定义用户模型，引用实际的user表"""
    id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=255)
    email = models.CharField(max_length=255, null=True, blank=True)
    real_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    role_id = models.IntegerField()
    status = models.IntegerField(default=1)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user'
        managed = False  # 告诉Django不要管理这个表

class StopWord(models.Model):
    """停用词库管理模型"""
    
    LANGUAGE_CHOICES = [
        ('chinese', '中文'),
        ('english', '英文'),
        ('mixed', '混合'),
    ]
    
    CATEGORY_CHOICES = [
        ('general', '通用'),
        ('technical', '技术'),
        ('academic', '学术'),
        ('business', '商业'),
        ('medical', '医疗'),
        ('legal', '法律'),
        ('other', '其他'),
    ]
    
    word = models.CharField(max_length=100, verbose_name='停用词')
    language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='chinese',
        verbose_name='语言类型'
    )
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='general',
        verbose_name='分类'
    )
    description = models.TextField(blank=True, null=True, verbose_name='描述信息')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_stop_words',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='updated_stop_words',
        verbose_name='更新人'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'stop_words'
        verbose_name = '停用词'
        verbose_name_plural = '停用词'
        unique_together = ['word', 'language']
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['language']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.word} ({self.get_language_display()})"
    
    def get_display_name(self):
        """获取显示名称"""
        return f"{self.word} - {self.get_language_display()} - {self.get_category_display()}"


class SensitiveWord(models.Model):
    """敏感词过滤管理模型"""
    
    LEVEL_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
    ]
    
    CATEGORY_CHOICES = [
        ('general', '通用'),
        ('political', '政治'),
        ('business', '商业'),
        ('technical', '技术'),
        ('personal', '个人隐私'),
        ('other', '其他'),
    ]
    
    word = models.CharField(max_length=100, unique=True, verbose_name='敏感词')
    level = models.CharField(
        max_length=10, 
        choices=LEVEL_CHOICES, 
        default='medium',
        verbose_name='敏感级别'
    )
    replacement = models.CharField(
        max_length=100, 
        default='***',
        verbose_name='替换词'
    )
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='general',
        verbose_name='分类'
    )
    description = models.TextField(blank=True, null=True, verbose_name='描述信息')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_sensitive_words',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='updated_sensitive_words',
        verbose_name='更新人'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'sensitive_words'
        verbose_name = '敏感词'
        verbose_name_plural = '敏感词'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.word} ({self.get_level_display()})"
    
    def get_display_name(self):
        """获取显示名称"""
        return f"{self.word} - {self.get_level_display()} - {self.get_category_display()}"
    
    def get_replacement_display(self):
        """获取替换词显示"""
        return self.replacement if self.replacement else '***'
