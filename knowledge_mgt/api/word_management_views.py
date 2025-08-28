"""
停用词和敏感词管理API视图
"""

import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
import json

from zhiqing_server.utils.response_code import ResponseCode
from zhiqing_server.utils.auth_utils import jwt_required, get_user_from_request
from knowledge_mgt.models import StopWord, SensitiveWord

logger = logging.getLogger(__name__)

# 停用词管理API
@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def stop_words_list(request):
    """获取停用词列表"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        keyword = request.GET.get('keyword', '').strip()
        language = request.GET.get('language', '').strip()
        category = request.GET.get('category', '').strip()
        
        queryset = StopWord.objects.all()
        
        if keyword:
            queryset = queryset.filter(
                Q(word__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
        
        if language:
            queryset = queryset.filter(language=language)
        if category:
            queryset = queryset.filter(category=category)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        stop_words = []
        for word in page_obj:
            stop_words.append({
                'id': word.id,
                'word': word.word,
                'language': word.language,
                'language_display': word.get_language_display(),
                'category': word.category,
                'category_display': word.get_category_display(),
                'description': word.description,
                'is_active': word.is_active,
                'priority': word.priority,
                'created_at': word.created_at.strftime("%Y-%m-%d %H:%M:%S") if word.created_at else None,
            })
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                data={
                    'list': stop_words,
                    'total': paginator.count,
                    'page': page,
                    'page_size': page_size,
                }
            )
        )
        
    except Exception as e:
        logger.error(f"获取停用词列表失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取停用词列表失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def stop_word_create(request):
    """创建停用词"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        data = json.loads(request.body)
        word = data.get('word', '').strip()
        language = data.get('language', 'chinese')
        category = data.get('category', 'general')
        description = data.get('description', '').strip()
        
        if not word:
            return JsonResponse(
                ResponseCode.PARAM_ERROR.to_dict(message="停用词不能为空"),
                status=400
            )
        
        if StopWord.objects.filter(word=word, language=language).exists():
            return JsonResponse(
                ResponseCode.PARAM_ERROR.to_dict(message="该停用词已存在"),
                status=400
            )
        
        stop_word = StopWord.objects.create(
            word=word,
            language=language,
            category=category,
            description=description,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="停用词创建成功")
        )
        
    except Exception as e:
        logger.error(f"创建停用词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"创建停用词失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required()
def stop_word_update(request, word_id):
    """更新停用词"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        try:
            stop_word = StopWord.objects.get(id=word_id)
        except StopWord.DoesNotExist:
            return JsonResponse(
                ResponseCode.NOT_FOUND.to_dict(message="停用词不存在"),
                status=404
            )
        
        data = json.loads(request.body)
        
        if 'word' in data:
            stop_word.word = data['word'].strip()
        if 'language' in data:
            stop_word.language = data['language']
        if 'category' in data:
            stop_word.category = data['category']
        if 'description' in data:
            stop_word.description = data['description'].strip()
        if 'is_active' in data:
            stop_word.is_active = data['is_active']
        if 'priority' in data:
            stop_word.priority = data['priority']
        
        stop_word.updated_by_id = user_id
        stop_word.save()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="停用词更新成功")
        )
        
    except Exception as e:
        logger.error(f"更新停用词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"更新停用词失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required()
def stop_word_delete(request, word_id):
    """删除停用词"""
    try:
        try:
            stop_word = StopWord.objects.get(id=word_id)
        except StopWord.DoesNotExist:
            return JsonResponse(
                ResponseCode.NOT_FOUND.to_dict(message="停用词不存在"),
                status=404
            )
        
        stop_word.delete()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="停用词删除成功")
        )
        
    except Exception as e:
        logger.error(f"删除停用词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"删除停用词失败: {str(e)}"),
            status=500
        )

# 敏感词管理API
@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def sensitive_words_list(request):
    """获取敏感词列表"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        keyword = request.GET.get('keyword', '').strip()
        level = request.GET.get('level', '').strip()
        category = request.GET.get('category', '').strip()
        
        queryset = SensitiveWord.objects.all()
        
        if keyword:
            queryset = queryset.filter(
                Q(word__icontains=keyword) | 
                Q(replacement__icontains=keyword) |
                Q(description__icontains=keyword)
            )
        
        if level:
            queryset = queryset.filter(level=level)
        if category:
            queryset = queryset.filter(category=category)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        sensitive_words = []
        for word in page_obj:
            sensitive_words.append({
                'id': word.id,
                'word': word.word,
                'level': word.level,
                'level_display': word.get_level_display(),
                'replacement': word.replacement,
                'category': word.category,
                'category_display': word.get_category_display(),
                'description': word.description,
                'is_active': word.is_active,
                'priority': word.priority,
                'created_at': word.created_at.strftime("%Y-%m-%d %H:%M:%S") if word.created_at else None,
            })
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                data={
                    'list': sensitive_words,
                    'total': paginator.count,
                    'page': page,
                    'page_size': page_size,
                }
            )
        )
        
    except Exception as e:
        logger.error(f"获取敏感词列表失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"获取敏感词列表失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def sensitive_word_create(request):
    """创建敏感词"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        data = json.loads(request.body)
        word = data.get('word', '').strip()
        level = data.get('level', 'medium')
        replacement = data.get('replacement', '***').strip()
        category = data.get('category', 'general')
        description = data.get('description', '').strip()
        
        if not word:
            return JsonResponse(
                ResponseCode.PARAM_ERROR.to_dict(message="敏感词不能为空"),
                status=400
            )
        
        if not replacement:
            return JsonResponse(
                ResponseCode.PARAM_ERROR.to_dict(message="替换词不能为空"),
                status=400
            )
        
        if SensitiveWord.objects.filter(word=word).exists():
            return JsonResponse(
                ResponseCode.PARAM_ERROR.to_dict(message="该敏感词已存在"),
                status=400
            )
        
        sensitive_word = SensitiveWord.objects.create(
            word=word,
            level=level,
            replacement=replacement,
            category=category,
            description=description,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="敏感词创建成功")
        )
        
    except Exception as e:
        logger.error(f"创建敏感词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"创建敏感词失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required()
def sensitive_word_update(request, word_id):
    """更新敏感词"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        try:
            sensitive_word = SensitiveWord.objects.get(id=word_id)
        except SensitiveWord.DoesNotExist:
            return JsonResponse(
                ResponseCode.NOT_FOUND.to_dict(message="敏感词不存在"),
                status=404
            )
        
        data = json.loads(request.body)
        
        if 'word' in data:
            sensitive_word.word = data['word'].strip()
        if 'level' in data:
            sensitive_word.level = data['level']
        if 'replacement' in data:
            sensitive_word.replacement = data['replacement'].strip()
        if 'category' in data:
            sensitive_word.category = data['category']
        if 'description' in data:
            sensitive_word.description = data['description'].strip()
        if 'is_active' in data:
            sensitive_word.is_active = data['is_active']
        if 'priority' in data:
            sensitive_word.priority = data['priority']
        
        sensitive_word.updated_by_id = user_id
        sensitive_word.save()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="敏感词更新成功")
        )
        
    except Exception as e:
        logger.error(f"更新敏感词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"更新敏感词失败: {str(e)}"),
            status=500
        )

@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required()
def sensitive_word_delete(request, word_id):
    """删除敏感词"""
    try:
        try:
            sensitive_word = SensitiveWord.objects.get(id=word_id)
        except SensitiveWord.DoesNotExist:
            return JsonResponse(
                ResponseCode.NOT_FOUND.to_dict(message="敏感词不存在"),
                status=404
            )
        
        sensitive_word.delete()
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(message="敏感词删除成功")
        )
        
    except Exception as e:
        logger.error(f"删除敏感词失败: {str(e)}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"删除敏感词失败: {str(e)}"),
            status=500
        )
