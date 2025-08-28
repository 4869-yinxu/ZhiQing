"""
知识库管理模块URL配置
"""

from django.urls import path
from . import views
from .api import document_views, knowledge_views, vector_management_views, upload_task_views, recall_views, duplicate_check_views, word_management_views, text_filter_views

app_name = 'knowledge_mgt'

# API路由
urlpatterns = [
    # 文档管理API
    path('document/upload/', document_views.upload_document, name='document_upload'),
    path('document/list/', document_views.document_list_api, name='document_list_api'),
    path('document/<int:doc_id>/', document_views.document_detail_api, name='document_detail_api'),
    path('document/<int:doc_id>/delete/', document_views.document_delete_api, name='document_delete_api'),
    path('document/<int:doc_id>/chunks/', document_views.document_chunks_api, name='document_chunks_api'),
    path('document/supported-formats/', document_views.get_supported_formats_api, name='supported_formats_api'),
    path('document/processor-info/', document_views.get_processor_info_api, name='processor_info_api'),
    
    # 知识库管理API
    path('database/list/', knowledge_views.knowledge_database_list, name='knowledge_database_list'),
    path('database/check-name/', knowledge_views.check_knowledge_database_name, name='check_knowledge_database_name'),
    path('database/', knowledge_views.create_knowledge_database, name='create_knowledge_database'),
    path('database/<int:knowledge_id>/', knowledge_views.update_knowledge_database, name='update_knowledge_database'),
    path('database/<int:knowledge_id>/delete/', knowledge_views.delete_knowledge_database, name='delete_knowledge_database'),
    
    # 向量管理API
    path('vector/index-info/', vector_management_views.get_vector_index_info, name='get_vector_index_info'),
    path('vector/list-indexes/', vector_management_views.list_user_vector_indexes, name='list_user_vector_indexes'),
    path('vector/rebuild-index/', vector_management_views.rebuild_vector_index, name='rebuild_vector_index'),
    path('vector/cleanup-index/', vector_management_views.cleanup_vector_index, name='cleanup_vector_index'),
    path('vector/delete-vectors/', vector_management_views.delete_vectors, name='delete_vectors'),
    path('vector/statistics/', vector_management_views.get_vector_statistics, name='get_vector_statistics'),
    
    # 文档上传任务队列API
    path('upload-task/create/', upload_task_views.create_upload_task, name='create_upload_task'),
    path('upload-task/queue-status/', upload_task_views.get_queue_status, name='get_queue_status'),
    path('upload-task/list/', upload_task_views.get_upload_tasks, name='get_upload_tasks'),
    path('upload-task/<str:task_id>/status/', upload_task_views.get_task_status, name='get_task_status'),
    path('upload-task/<str:task_id>/delete/', upload_task_views.delete_upload_task, name='delete_upload_task'),
    path('upload-task/<str:task_id>/cancel/', upload_task_views.cancel_upload_task, name='cancel_upload_task'),
    path('upload-task/<str:task_id>/detail/', upload_task_views.get_task_detail, name='get_task_detail'),
    path('upload-task/clear-completed/', upload_task_views.clear_completed_tasks, name='clear_completed_tasks'),
    path('upload-task/clear-failed/', upload_task_views.clear_failed_tasks, name='clear_failed_tasks'),
    path('upload-task/clear-all/', upload_task_views.clear_all_tasks, name='clear_all_tasks'),
    
    # 召回检索测试API
    path('recall/test', recall_views.recall_test, name='recall_test_api'),

    # 网页抓取与导入API
    path('web-crawl/create/', document_views.create_web_crawl, name='create_web_crawl'),
    
    # 知识查重看板API
    path('duplicate-check/content/', duplicate_check_views.check_duplicate_content, name='check_duplicate_content'),
    path('duplicate-check/batch/', duplicate_check_views.batch_check_duplicates, name='batch_check_duplicates'),
    path('duplicate-check/statistics/', duplicate_check_views.get_duplicate_statistics, name='get_duplicate_statistics'),
    path('duplicate-check/trace-source/', duplicate_check_views.trace_content_source, name='trace_content_source'),
    
    # 词库管理API
    path('words/stop-words/', word_management_views.stop_words_list, name='stop_words_list'),
    path('words/stop-words/create/', word_management_views.stop_word_create, name='stop_word_create'),
    path('words/stop-words/<int:word_id>/update/', word_management_views.stop_word_update, name='stop_word_update'),
    path('words/stop-words/<int:word_id>/delete/', word_management_views.stop_word_delete, name='stop_word_delete'),
    
    path('words/sensitive-words/', word_management_views.sensitive_words_list, name='sensitive_words_list'),
    path('words/sensitive-words/create/', word_management_views.sensitive_word_create, name='sensitive_word_create'),
    path('words/sensitive-words/<int:word_id>/update/', word_management_views.sensitive_word_update, name='sensitive_word_update'),
    path('words/sensitive-words/<int:word_id>/delete/', word_management_views.sensitive_word_delete, name='sensitive_word_delete'),
    
    # 文本过滤API (LlamaParse)
    path('text-filter/filter/', text_filter_views.TextFilterView.as_view(), name='text_filter'),
    path('text-filter/test/', text_filter_views.TextFilterTestView.as_view(), name='text_filter_test'),
    path('text-filter/batch/', text_filter_views.TextFilterBatchView.as_view(), name='text_filter_batch'),
    path('text-filter/stats/', text_filter_views.TextFilterStatsView.as_view(), name='text_filter_stats'),
    path('text-filter/simple/', text_filter_views.filter_text_simple, name='text_filter_simple'),
]

# 页面路由
page_patterns = [
    path('', views.knowledge_home, name='knowledge_home'),
    path('knowledge/', views.knowledge_management, name='knowledge_management'),
    path('document/', views.document_management, name='document_management'),
    path('recall/', views.recall_test, name='recall_test'),
]

urlpatterns += page_patterns
