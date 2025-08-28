import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from ..utils.text_filter import TextFilter
from ..models import StopWord, SensitiveWord
from zhiqing_server.utils.response_code import ResponseCode

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class TextFilterView(View):
    """文本过滤API视图"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_filter = TextFilter()
        self._load_filter_words()
    
    def _load_filter_words(self):
        """加载过滤词库"""
        try:
            # 加载停用词
            stop_words = StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description')
            self.text_filter.load_stop_words(list(stop_words))
            
            # 加载敏感词
            sensitive_words = SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description')
            self.text_filter.load_sensitive_words(list(sensitive_words))
            
            logger.info("过滤词库加载完成")
        except Exception as e:
            logger.error(f"加载过滤词库失败: {e}")
    
    def post(self, request, *args, **kwargs):
        """处理文本过滤请求"""
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            filter_type = data.get('filter_type', 'both')  # 'stopwords', 'sensitive', 'both'
            
            if not text:
                return JsonResponse(
                    ResponseCode.BAD_REQUEST.to_dict(message='请提供要过滤的文本')
                )
            
            # 使用LlamaParse进行文本过滤
            result = self.text_filter.filter_text_with_llamaparse(text, filter_type)
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(
                    data={
                        'filter_result': result,
                        'filter_type': filter_type,
                        'capabilities': self.text_filter.get_filter_statistics()
                    }
                )
            )
            
        except json.JSONDecodeError:
            return JsonResponse(
                ResponseCode.BAD_REQUEST.to_dict(message='JSON格式错误')
            )
        except Exception as e:
            logger.error(f"文本过滤失败: {e}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f'文本过滤失败: {str(e)}')
            )

@method_decorator(csrf_exempt, name='dispatch')
class TextFilterTestView(View):
    """文本过滤测试API视图"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_filter = TextFilter()
        self._load_filter_words()
    
    def _load_filter_words(self):
        """加载过滤词库"""
        try:
            # 加载停用词
            stop_words = StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description')
            self.text_filter.load_stop_words(list(stop_words))
            
            # 加载敏感词
            sensitive_words = SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description')
            self.text_filter.load_sensitive_words(list(sensitive_words))
            
            logger.info("过滤词库加载完成")
        except Exception as e:
            logger.error(f"加载过滤词库失败: {e}")
    
    def post(self, request, *args, **kwargs):
        """处理文本过滤测试请求"""
        try:
            data = json.loads(request.body)
            test_text = data.get('test_text', '')
            
            if not test_text:
                return JsonResponse(
                    ResponseCode.BAD_REQUEST.to_dict(message='请提供测试文本')
                )
            
            # 测试所有过滤功能
            test_result = self.text_filter.test_filter(test_text)
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(
                    data={
                        'test_result': test_result,
                        'capabilities': self.text_filter.get_filter_statistics()
                    }
                )
            )
            
        except json.JSONDecodeError:
            return JsonResponse(
                ResponseCode.BAD_REQUEST.to_dict(message='JSON格式错误')
            )
        except Exception as e:
            logger.error(f"文本过滤测试失败: {e}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f'文本过滤测试失败: {str(e)}')
            )

@method_decorator(csrf_exempt, name='dispatch')
class TextFilterBatchView(View):
    """批量文本过滤API视图"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_filter = TextFilter()
        self._load_filter_words()
    
    def _load_filter_words(self):
        """加载过滤词库"""
        try:
            # 加载停用词
            stop_words = StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description')
            self.text_filter.load_stop_words(list(stop_words))
            
            # 加载敏感词
            sensitive_words = SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description')
            self.text_filter.load_sensitive_words(list(sensitive_words))
            
            logger.info("过滤词库加载完成")
        except Exception as e:
            logger.error(f"加载过滤词库失败: {e}")
    
    def post(self, request, *args, **kwargs):
        """处理批量文本过滤请求"""
        try:
            data = json.loads(request.body)
            texts = data.get('texts', [])
            filter_type = data.get('filter_type', 'both')
            
            if not texts or not isinstance(texts, list):
                return JsonResponse(
                    ResponseCode.BAD_REQUEST.to_dict(message='请提供要过滤的文本列表')
                )
            
            if len(texts) > 100:  # 限制批量处理数量
                return JsonResponse(
                    ResponseCode.BAD_REQUEST.to_dict(message='批量处理文本数量不能超过100个')
                )
            
            # 批量处理文本
            batch_results = []
            for i, text in enumerate(texts):
                try:
                    result = self.text_filter.filter_text_with_llamaparse(text, filter_type)
                    batch_results.append({
                        'index': i,
                        'text': text,
                        'result': result
                    })
                except Exception as e:
                    logger.error(f"处理第{i}个文本失败: {e}")
                    batch_results.append({
                        'index': i,
                        'text': text,
                        'error': str(e)
                    })
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(
                    data={
                        'batch_results': batch_results,
                        'total_count': len(texts),
                        'success_count': len([r for r in batch_results if 'error' not in r]),
                        'filter_type': filter_type,
                        'capabilities': self.text_filter.get_filter_statistics()
                    }
                )
            )
            
        except json.JSONDecodeError:
            return JsonResponse(
                ResponseCode.BAD_REQUEST.to_dict(message='JSON格式错误')
            )
        except Exception as e:
            logger.error(f"批量文本过滤失败: {e}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f'批量文本过滤失败: {str(e)}')
            )

@method_decorator(csrf_exempt, name='dispatch')
class TextFilterStatsView(View):
    """文本过滤统计API视图"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_filter = TextFilter()
        self._load_filter_words()
    
    def _load_filter_words(self):
        """加载过滤词库"""
        try:
            # 加载停用词
            stop_words = StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description')
            self.text_filter.load_stop_words(list(stop_words))
            
            # 加载敏感词
            sensitive_words = SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description')
            self.text_filter.load_sensitive_words(list(sensitive_words))
            
            logger.info("过滤词库加载完成")
        except Exception as e:
            logger.error(f"加载过滤词库失败: {e}")
    
    def get(self, request, *args, **kwargs):
        """获取过滤统计信息"""
        try:
            # 获取数据库统计
            stop_words_count = StopWord.objects.filter(is_active=True).count()
            sensitive_words_count = SensitiveWord.objects.filter(is_active=True).count()
            
            # 获取过滤器能力信息
            filter_capabilities = self.text_filter.get_filter_statistics()
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(
                    data={
                        'database_stats': {
                            'stop_words_count': stop_words_count,
                            'sensitive_words_count': sensitive_words_count,
                            'total_words': stop_words_count + sensitive_words_count
                        },
                        'filter_capabilities': filter_capabilities,
                        'llamaparse_status': {
                            'available': filter_capabilities['llamaparse_available'],
                            'description': 'LlamaParse智能文本分析引擎'
                        }
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"获取过滤统计失败: {e}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f'获取过滤统计失败: {str(e)}')
            )

# 函数式视图，用于简单的文本过滤
@csrf_exempt
@require_http_methods(["POST"])
def filter_text_simple(request):
    """简单的文本过滤接口"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        filter_type = data.get('filter_type', 'both')
        
        if not text:
            return JsonResponse(
                ResponseCode.BAD_REQUEST.to_dict(message='请提供要过滤的文本')
            )
        
        # 创建文本过滤器实例
        text_filter = TextFilter()
        
        # 加载过滤词库
        stop_words = StopWord.objects.filter(is_active=True).values('word', 'language', 'category', 'description')
        text_filter.load_stop_words(list(stop_words))
        
        sensitive_words = SensitiveWord.objects.filter(is_active=True).values('word', 'level', 'replacement', 'category', 'description')
        text_filter.load_sensitive_words(list(sensitive_words))
        
        # 执行过滤
        result = text_filter.filter_text_with_llamaparse(text, filter_type)
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(
                data={
                    'filter_result': result,
                    'filter_type': filter_type
                }
            )
        )
        
    except json.JSONDecodeError:
        return JsonResponse(
            ResponseCode.BAD_REQUEST.to_dict(message='JSON格式错误')
        )
    except Exception as e:
        logger.error(f"简单文本过滤失败: {e}")
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f'文本过滤失败: {str(e)}')
        )
