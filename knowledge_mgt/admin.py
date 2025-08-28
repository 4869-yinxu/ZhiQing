from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import StopWord, SensitiveWord

@admin.register(StopWord)
class StopWordAdmin(admin.ModelAdmin):
    """停用词管理界面"""
    list_display = [
        'word', 'language', 'category', 'is_active', 'priority', 
        'created_by', 'created_at', 'updated_at'
    ]
    list_filter = [
        'language', 'category', 'is_active', 'priority', 'created_at'
    ]
    search_fields = ['word', 'description']
    list_editable = ['is_active', 'priority']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('word', 'language', 'category', 'description')
        }),
        ('状态设置', {
            'fields': ('is_active', 'priority')
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
        ('更新信息', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """保存模型时自动设置创建人和更新人"""
        if not change:  # 新建
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related('created_by', 'updated_by')
    
    def get_list_display(self, request):
        """根据用户权限动态调整显示字段"""
        list_display = list(super().get_list_display(request))
        if not request.user.is_superuser:
            # 非超级用户隐藏创建人和更新人字段
            if 'created_by' in list_display:
                list_display.remove('created_by')
            if 'updated_by' in list_display:
                list_display.remove('updated_by')
        return list_display
    
    actions = ['activate_words', 'deactivate_words', 'set_high_priority']
    
    def activate_words(self, request, queryset):
        """批量启用停用词"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功启用 {updated} 个停用词')
    activate_words.short_description = '批量启用选中的停用词'
    
    def deactivate_words(self, request, queryset):
        """批量禁用停用词"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个停用词')
    deactivate_words.short_description = '批量禁用选中的停用词'
    
    def set_high_priority(self, request, queryset):
        """批量设置高优先级"""
        updated = queryset.update(priority=100)
        self.message_user(request, f'成功设置 {updated} 个停用词为高优先级')
    set_high_priority.short_description = '批量设置高优先级'


@admin.register(SensitiveWord)
class SensitiveWordAdmin(admin.ModelAdmin):
    """敏感词管理界面"""
    list_display = [
        'word', 'level', 'replacement', 'category', 'is_active', 
        'priority', 'created_by', 'created_at', 'updated_at'
    ]
    list_filter = [
        'level', 'category', 'is_active', 'priority', 'created_at'
    ]
    search_fields = ['word', 'replacement', 'description']
    list_editable = ['is_active', 'priority', 'replacement']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('word', 'level', 'replacement', 'category', 'description')
        }),
        ('状态设置', {
            'fields': ('is_active', 'priority')
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
        ('更新信息', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """保存模型时自动设置创建人和更新人"""
        if not change:  # 新建
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related('created_by', 'updated_by')
    
    def get_list_display(self, request):
        """根据用户权限动态调整显示字段"""
        list_display = list(super().get_list_display(request))
        if not request.user.is_superuser:
            # 非超级用户隐藏创建人和更新人字段
            if 'created_by' in list_display:
                list_display.remove('created_by')
            if 'updated_by' in list_display:
                list_display.remove('updated_by')
        return list_display
    
    def replacement_display(self, obj):
        """美化替换词显示"""
        if obj.replacement:
            return format_html(
                '<span style="background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{}</span>',
                obj.replacement
            )
        return '-'
    replacement_display.short_description = '替换词'
    
    actions = ['activate_words', 'deactivate_words', 'set_high_priority', 'set_high_level']
    
    def activate_words(self, request, queryset):
        """批量启用敏感词"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功启用 {updated} 个敏感词')
    activate_words.short_description = '批量启用选中的敏感词'
    
    def deactivate_words(self, request, queryset):
        """批量禁用敏感词"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个敏感词')
    deactivate_words.short_description = '批量禁用选中的敏感词'
    
    def set_high_priority(self, request, queryset):
        """批量设置高优先级"""
        updated = queryset.update(priority=100)
        self.message_user(request, f'成功设置 {updated} 个敏感词为高优先级')
    set_high_priority.short_description = '批量设置高优先级'
    
    def set_high_level(self, request, queryset):
        """批量设置高敏感级别"""
        updated = queryset.update(level='high')
        self.message_user(request, f'成功设置 {updated} 个敏感词为高级别')
    set_high_level.short_description = '批量设置高敏感级别'
