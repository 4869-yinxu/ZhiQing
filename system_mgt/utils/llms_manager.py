import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# 设置日志
logger = logging.getLogger(__name__)


def _auto_select_device() -> str:
    """自动检测并返回最合适的设备: 'cuda' > 'mps' > 'cpu'"""
    try:
        import torch  # type: ignore
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            return 'cuda'
        # Apple Silicon
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'
    except Exception:
        pass
    return 'cpu'

class LLMsManager:
    """LLMs模型管理器 - 使用LlamaIndex原生方式"""
    
    def __init__(self):
        self.current_llm = None
        self.current_embed_model = None
        self.knowledge_base_models = {}  # 存储知识库对应的embedding模型
        
    def initialize_embedding(self, model_type: str, model_config: Dict[str, Any]) -> bool:
        """初始化Embedding模型"""
        try:
            if model_type == "dashscope":
                # 阿里云通义千问Embedding
                from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
                # 依赖环境变量 DASHSCOPE_API_KEY，由 LlamaIndex 内部读取
                self.current_embed_model = DashScopeEmbedding(
                    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V1
                )
                # 设置为全局默认embedding模型
                try:
                    from llama_index import ServiceContext
                    ServiceContext.from_defaults(embed_model=self.current_embed_model)
                except ImportError:
                    try:
                        from llama_index.core import Settings
                        Settings.embed_model = self.current_embed_model
                    except ImportError:
                        logger.warning("无法设置全局embedding模型，但模型初始化成功")
                logger.info(f"成功初始化DashScope Embedding: {model_config.get('name')}")
                
            elif model_type == "openai":
                # OpenAI官方Embedding模型
                from llama_index.embeddings.openai import OpenAIEmbedding
                import os
                api_key = model_config.get('api_key') or os.getenv('OPENAI_API_KEY')
                self.current_embed_model = OpenAIEmbedding(
                    model=model_config.get('model_name', 'text-embedding-3-small'),
                    api_key=api_key,
                    api_base=model_config.get('api_url') if model_config.get('api_url') else None
                )
                # 设置为全局默认embedding模型
                try:
                    from llama_index import ServiceContext
                    ServiceContext.from_defaults(embed_model=self.current_embed_model)
                except ImportError:
                    try:
                        from llama_index.core import Settings
                        Settings.embed_model = self.current_embed_model
                    except ImportError:
                        logger.warning("无法设置全局embedding模型，但模型初始化成功")
                logger.info(f"成功初始化OpenAI Embedding: {model_config.get('name')}")
                
            elif model_type == "zhipuai":
                # 智谱AI Embedding模型
                from llama_index.embeddings.zhipuai import ZhipuAIEmbedding
                import os
                api_key = model_config.get('api_key') or os.getenv('ZHIPUAI_API_KEY')
                self.current_embed_model = ZhipuAIEmbedding(
                    model_name=model_config.get('model_name', 'embedding-2'),
                    api_key=api_key
                )
                # 设置为全局默认embedding模型
                try:
                    from llama_index import ServiceContext
                    ServiceContext.from_defaults(embed_model=self.current_embed_model)
                except ImportError:
                    try:
                        from llama_index.core import Settings
                        Settings.embed_model = self.current_embed_model
                    except ImportError:
                        logger.warning("无法设置全局embedding模型，但模型初始化成功")
                logger.info(f"成功初始化智谱AI Embedding: {model_config.get('name')}")
                
            elif model_type == "baichuan":
                # 百度千帆 Embedding模型
                from llama_index.embeddings.baichuan import BaichuanEmbedding
                import os
                api_key = model_config.get('api_key') or os.getenv('BAICHUAN_API_KEY')
                self.current_embed_model = BaichuanEmbedding(
                    model_name=model_config.get('model_name', 'embedding-v1'),
                    api_key=api_key
                )
                # 设置为全局默认embedding模型
                try:
                    from llama_index import ServiceContext
                    ServiceContext.from_defaults(embed_model=self.current_embed_model)
                except ImportError:
                    try:
                        from llama_index.core import Settings
                        Settings.embed_model = self.current_embed_model
                    except ImportError:
                        logger.warning("无法设置全局embedding模型，但模型初始化成功")
                logger.info(f"成功初始化百度千帆 Embedding: {model_config.get('name')}")
                
            elif model_type == "sentence_transformers":
                # HuggingFace Sentence Transformers模型
                try:
                    # 尝试多种导入方式以兼容不同版本的LlamaIndex
                    try:
                        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                        logger.info("使用 llama_index.embeddings.huggingface.HuggingFaceEmbedding")
                    except ImportError:
                        try:
                            from llama_index.embeddings import HuggingFaceEmbedding
                            logger.info("使用 llama_index.embeddings.HuggingFaceEmbedding")
                        except ImportError:
                            from llama_index import HuggingFaceEmbedding
                            logger.info("使用 llama_index.HuggingFaceEmbedding")
                    
                    model_path = model_config.get('local_path')
                    if model_path and os.path.exists(model_path):
                        device = _auto_select_device()
                        logger.info(f"使用 HuggingFaceEmbedding 设备: {device}")
                        self.current_embed_model = HuggingFaceEmbedding(
                            model_name=model_path,
                            device=device
                        )
                        # 设置为全局默认embedding模型
                        try:
                            from llama_index.core import Settings
                            Settings.embed_model = self.current_embed_model
                            logger.info("Settings.embed_model 设置成功")
                        except ImportError as e:
                            logger.warning(f"无法设置全局embedding模型: {e}")
                        logger.info(f"成功初始化Sentence Transformers Embedding: {model_config.get('name')}")
                    else:
                        logger.error(f"本地模型路径不存在: {model_path}")
                        return False
                except ImportError as e:
                    logger.error(f"无法导入 HuggingFaceEmbedding: {e}")
                    return False
                except Exception as e:
                    logger.error(f"初始化HuggingFaceEmbedding失败: {str(e)}")
                    return False
                
            else:
                logger.error(f"不支持的Embedding类型: {model_type}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"初始化Embedding失败: {str(e)}")
            return False
    
    def load_knowledge_base_model(self, knowledge_base_id: int, model_config: Dict[str, Any]) -> bool:
        """为特定知识库加载embedding模型"""
        try:
            model_type = model_config.get('model_type', 'dashscope')
            
            if model_type == "dashscope":
                # 阿里云通义千问Embedding
                from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
                # 依赖环境变量 DASHSCOPE_API_KEY，由 LlamaIndex 内部读取
                embed_model = DashScopeEmbedding(
                    model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V1
                )
                
            elif model_type == "openai":
                # OpenAI官方Embedding模型
                from llama_index.embeddings.openai import OpenAIEmbedding
                embed_model = OpenAIEmbedding(
                    model=model_config.get('model_name', 'text-embedding-3-small'),
                    api_key=model_config.get('api_key'),
                    api_base=model_config.get('api_url') if model_config.get('api_url') else None
                )
                
            elif model_type == "huggingface":
                # HuggingFace本地模型
                try:
                    # 尝试多种导入方式以兼容不同版本的LlamaIndex
                    try:
                        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                        logger.info("使用 llama_index.embeddings.huggingface.HuggingFaceEmbedding")
                    except ImportError:
                        try:
                            from llama_index.embeddings import HuggingFaceEmbedding
                            logger.info("使用 llama_index.embeddings.HuggingFaceEmbedding")
                        except ImportError:
                            from llama_index import HuggingFaceEmbedding
                            logger.info("使用 llama_index.HuggingFaceEmbedding")
                    
                    model_path = model_config.get('local_path')
                    if model_path and os.path.exists(model_path):
                        device = _auto_select_device()
                        logger.info(f"使用 HuggingFaceEmbedding 设备: {device}")
                        embed_model = HuggingFaceEmbedding(
                            model_name=model_path,
                            device=device
                        )
                    else:
                        logger.error(f"本地模型路径不存在: {model_path}")
                        return False
                except ImportError as e:
                    logger.error(f"无法导入 HuggingFaceEmbedding: {e}")
                    return False
                except Exception as e:
                    logger.error(f"初始化HuggingFaceEmbedding失败: {str(e)}")
                    return False
                    
            elif model_type == "sentence_transformers":
                # HuggingFace Sentence Transformers模型
                try:
                    # 尝试多种导入方式以兼容不同版本的LlamaIndex
                    try:
                        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                        logger.info("使用 llama_index.embeddings.huggingface.HuggingFaceEmbedding")
                    except ImportError:
                        try:
                            from llama_index.embeddings import HuggingFaceEmbedding
                            logger.info("使用 llama_index.embeddings.HuggingFaceEmbedding")
                        except ImportError:
                            from llama_index import HuggingFaceEmbedding
                            logger.info("使用 llama_index.HuggingFaceEmbedding")
                    
                    model_path = model_config.get('local_path')
                    if model_path and os.path.exists(model_path):
                        device = _auto_select_device()
                        logger.info(f"使用 HuggingFaceEmbedding 设备: {device}")
                        embed_model = HuggingFaceEmbedding(
                            model_name=model_path,
                            device=device
                        )
                    else:
                        logger.error(f"本地模型路径不存在: {model_path}")
                        return False
                except ImportError as e:
                    logger.error(f"无法导入 HuggingFaceEmbedding: {e}")
                    return False
                except Exception as e:
                    logger.error(f"初始化HuggingFaceEmbedding失败: {str(e)}")
                    return False
                    
            else:
                logger.error(f"不支持的Embedding类型: {model_type}")
                return False
            
            # 存储知识库对应的模型
            self.knowledge_base_models[knowledge_base_id] = embed_model
            logger.info(f"成功为知识库 {knowledge_base_id} 加载 {model_type} Embedding模型: {model_config.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"为知识库 {knowledge_base_id} 加载Embedding模型失败: {str(e)}")
            return False
    
    def get_knowledge_base_model(self, knowledge_base_id: int):
        """获取知识库对应的embedding模型"""
        return self.knowledge_base_models.get(knowledge_base_id)
    
    def ensure_knowledge_base_model_loaded(self, knowledge_base_id: int, model_config: Dict[str, Any]) -> bool:
        """确保知识库的embedding模型已加载（按需加载）"""
        # 如果已经加载了，直接返回
        if knowledge_base_id in self.knowledge_base_models:
            return True
        
        # 否则加载模型
        return self.load_knowledge_base_model(knowledge_base_id, model_config)
    
    def get_current_embed_model(self):
        """获取当前激活的embedding模型"""
        return self.current_embed_model
    
    def set_active_knowledge_base(self, knowledge_base_id: int) -> bool:
        """设置当前活跃的知识库embedding模型"""
        try:
            if knowledge_base_id in self.knowledge_base_models:
                self.current_embed_model = self.knowledge_base_models[knowledge_base_id]
                logger.info(f"已设置 current_embed_model: {type(self.current_embed_model)}")
                
                # 设置为全局默认embedding模型
                try:
                    from llama_index.core import Settings
                    logger.info("尝试使用 Settings.embed_model")
                    Settings.embed_model = self.current_embed_model
                    logger.info("Settings.embed_model 设置成功")
                except ImportError as e:
                    logger.warning(f"Settings 导入失败: {e}")
                    logger.warning("无法设置全局embedding模型，但模型激活成功")
                except Exception as e:
                    logger.error(f"Settings.embed_model 设置失败: {e}")
                    logger.warning("无法设置全局embedding模型，但模型激活成功")
                
                logger.info(f"成功激活知识库 {knowledge_base_id} 的Embedding模型")
                return True
            else:
                logger.error(f"知识库 {knowledge_base_id} 的Embedding模型未加载")
                logger.error(f"已加载的模型: {list(self.knowledge_base_models.keys())}")
                return False
        except Exception as e:
            logger.error(f"激活知识库 {knowledge_base_id} 的Embedding模型失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def test_embedding(self, test_text: str) -> Dict[str, Any]:
        """测试Embedding功能"""
        try:
            if not self.current_embed_model:
                return {"success": False, "error": "Embedding模型未初始化"}
            
            embedding = self.current_embed_model.get_text_embedding(test_text)
            return {
                "success": True,
                "embedding": embedding,
                "dimension": len(embedding),
                "model": str(self.current_embed_model.__class__.__name__)
            }
            
        except Exception as e:
            logger.error(f"Embedding测试失败: {str(e)}")
            return {"success": False, "error": str(e)}

# 全局实例
llms_manager = LLMsManager()
