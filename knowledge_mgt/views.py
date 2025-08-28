"""
知识库管理模块视图
"""

from django.shortcuts import render
from django.http import JsonResponse

def knowledge_home(request):
    """知识库管理首页"""
    return JsonResponse({'message': '知识库管理模块'})

def knowledge_management(request):
    """知识库管理页面"""
    return JsonResponse({'message': '知识库管理'})

def document_management(request):
    """文档管理页面"""
    return JsonResponse({'message': '文档管理'})

def recall_test(request):
    """召回测试页面"""
    return JsonResponse({'message': '召回测试'})

def database_list(request):
    """知识库列表页面"""
    return JsonResponse({'message': '知识库列表'})

def database_detail(request, db_id):
    """知识库详情页面"""
    return JsonResponse({'message': f'知识库详情 {db_id}'})

def document_list(request):
    """文档列表页面"""
    return JsonResponse({'message': '文档列表'})

def document_detail(request, doc_id):
    """文档详情页面"""
    return JsonResponse({'message': f'文档详情 {doc_id}'})
