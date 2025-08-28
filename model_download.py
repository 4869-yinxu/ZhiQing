#模型下载
from modelscope import snapshot_download
model_dir = snapshot_download('BAAI/bge-large-zh-v1.5', cache_dir='./models')