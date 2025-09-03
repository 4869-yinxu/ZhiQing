# ZhiQing

[英文](./README_EN.md) | 中文

一个基于RAG（Retrieval-Augmented Generation）技术的智能知识管理系统，支持多种大语言模型和嵌入模型的集成与管理。

## 版本信息

**当前版本**: v0.0.1

## 在线演示

**演示地址**: [http://172.22.182.54/](http://172.22.182.54/)

*演示环境仅供体验，请勿上传敏感信息*



## 项目简介

ZhiQing 是一个现代化的知识管理平台，通过RAG技术将传统的文档管理与AI问答能力相结合，为用户提供智能化的知识检索和问答体验。

## 主要功能

### 核心功能
- **智能问答**: 基于知识库内容的AI问答系统
- **文档管理**: 支持多种格式文档的上传、解析和管理
- **知识库管理**: 灵活的知识库创建、编辑和权限控制
- **向量检索**: 高效的语义检索和相似度匹配
- **知识查重**: 智能识别重复或相似的知识片段
- **召回检索测试**: 支持向量检索质量测试和参数调优
- **文档上传队列**: 支持批量文档上传和进度监控

### 高级特性
- **智能分块**: 支持10种分块方式，包括Token、句子、段落、章节、语义等
- **实时监控**: 智能进度预估和任务状态实时监控
- **多模型支持**: 支持本地和云端多种嵌入模型
- **文本清洗**: 智能停用词过滤和敏感词替换
- **批量处理**: 支持大规模文档的批量上传和处理
- **智能调度**: 任务队列管理和智能资源分配

### 模型管理
- **大语言模型管理**: 支持OpenAI、百度、智谱AI等多种LLM服务商
- **嵌入模型管理**: 支持在线API和本地部署的嵌入模型
- **模型配置**: 灵活的模型参数配置和性能优化
- **模型测试**: 内置模型连接测试和性能评估
- **动态模型加载**: 支持按需加载本地嵌入模型
- **多模型协同**: 支持大小模型协同工作

### 系统管理
- **用户权限管理**: 基于角色的访问控制
- **系统监控**: 服务器资源监控和模型状态管理
- **配置管理**: 系统参数和环境配置管理
- **任务队列管理**: 智能任务调度和进度监控
- **实时监控看板**: 系统状态实时监控和告警

## 技术架构

### 前端技术栈
- **框架**: Vue 3 + Composition API
- **UI组件**: Element Plus
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由管理**: Vue Router

### 后端技术栈
- **框架**: Django + Django REST Framework
- **数据库**: SQLite/PostgreSQL/MySQL
- **向量数据库**: FAISS向量索引，支持多种相似度计算
- **AI集成**: 支持多种LLM和嵌入模型API
- **文档处理**: 支持PDF、Word、Markdown、Excel等多种格式
- **文本分块**: 支持Token、句子、段落、章节、语义等多种分块方式

## 快速开始

### 环境要求
- Node.js >= 22.0.0
- Python >= 3.12
- Git
- 内存: 建议8GB以上
- 存储: 建议20GB以上可用空间
- GPU: 可选，支持CUDA加速（推荐）

### 安装步骤

#### 方法一：自动安装（推荐）

1. **克隆项目**
```bash
git clone https://gitee.com/4869-yinxu/ZhiQing.git
cd ZhiQing
```

2. **安装前端依赖**
```bash
cd zhiqing_ui
npm install
```

3. **配置环境变量**
```bash
cd ../
# 复制环境配置文件
cp .env.dev .env
# 编辑配置文件，配置必要的API密钥和数据库连接信息
```

4. **自动安装后端依赖**

**Windows用户**:
```bash
cd ../
# 双击运行或在命令行中执行
install.bat
```

**Linux/macOS用户**:
```bash
cd ../
# 给脚本执行权限
chmod +x install.sh
# 运行安装脚本
./install.sh
```

**手动运行安装脚本**:
```bash
cd ../
# 升级pip
python -m pip install --upgrade pip
# 运行安装脚本
python install_requirements.py
```

#### 方法二：手动安装

1. **克隆项目**
```bash
git clone https://gitee.com/4869-yinxu/ZhiQing.git
cd ZhiQing
```

2. **安装前端依赖**
```bash
cd zhiqing_ui
npm install
```

3. **配置环境变量**
```bash
cd ../
# 复制环境配置文件
cp .env.dev .env
# 编辑配置文件，配置必要的API密钥和数据库连接信息
```

4. **安装后端依赖**
```bash
cd ../
# 安装基础依赖
pip install -r requirements.txt

# 根据您的系统选择PyTorch版本：

# CPU版本
pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu

# 或GPU版本（如果有NVIDIA GPU）
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision==0.20.1+cu121 GPUtil==1.4.0 --index-url https://download.pytorch.org/whl/cu121
```

### 依赖安装说明

本项目提供了依赖安装工具，可以根据您的系统GPU情况自动选择合适的PyTorch版本。

#### 系统要求
- Python 3.12 或更高版本
- pip (Python包管理器)

#### 安装过程
1. **基础依赖安装**: 安装所有通用依赖包
2. **GPU检测**: 自动检测系统是否有NVIDIA GPU
3. **PyTorch安装**: 根据GPU情况选择合适版本
   - 有GPU: 安装CUDA版本 (torch==2.5.1+cu121)
   - 无GPU: 安装CPU版本 (torch==2.7.1+cpu)
4. **安装验证**: 验证所有依赖是否正确安装

#### 故障排除

**常见问题**:

1. **Python版本过低**
   - 确保使用Python 3.12或更高版本
   - 运行 `python --version` 检查版本

2. **pip版本过旧**
   - 运行 `python -m pip install --upgrade pip` 升级pip

3. **网络连接问题**
   - 使用国内镜像源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **GPU检测错误**
   - 确保安装了NVIDIA驱动
   - 运行 `nvidia-smi` 检查GPU状态

5. **CUDA版本不匹配**
   - 检查CUDA版本：`nvcc --version`
   - 根据CUDA版本选择对应的PyTorch版本

**验证安装**:
```python
import torch
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU数量: {torch.cuda.device_count()}")
    print(f"当前GPU: {torch.cuda.get_device_name(0)}")
```

### 环境配置

1. **环境变量配置**

```bash
# 复制配置文件
cp .env.dev .env
# 编辑配置文件，修改数据库连接配置和其他必要信息
# 主要需要配置：
# - 数据库连接信息（DATABASE_URL）
# - API密钥配置（OpenAI、百度、智谱AI等）
# - 向量模型配置
# - 系统运行参数
```

2. **启动服务**

前端开发服务器:
```bash
cd zhiqing_ui
npm run dev
# 前端将在 http://localhost:3000 启动
```

后端服务器:
```bash
python manage.py runserver
# 后端API将在 http://localhost:8000 启动
```

3. **访问系统**
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- 管理后台: http://localhost:8000/admin

## 配置说明

### 模型配置
系统支持多种大语言模型和嵌入模型的配置：

- **在线API模型**: 需要配置相应的API密钥
  - OpenAI GPT系列
  - 百度文心一言
  - 智谱AI ChatGLM
  - 通义千问
- **本地部署模型**: 需要指定模型路径和服务地址
  - BGE-Large-ZH
  - Sentence-Transformers
  - 自定义HuggingFace模型
- **模型参数**: 支持温度、最大Token数等参数调整
- **动态模型加载**: 支持按需加载和模型切换

### 系统配置
- **数据库配置**: 支持SQLite、PostgreSQL、MySQL
- **向量数据库配置**: FAISS索引配置和相似度计算方式
- **文件存储配置**: 本地存储和云存储支持
- **日志配置**: 分级日志记录和日志轮转
- **缓存配置**: Redis缓存支持（可选）
- **任务队列配置**: Celery异步任务处理（可选）

## 使用指南

### 创建知识库
1. 登录系统后进入知识库管理页面
2. 点击"新建知识库"按钮
3. 填写知识库基本信息（名称、描述、类型）
4. 选择合适的嵌入模型和向量维度
5. 配置访问权限和分块参数
6. 设置知识库标签和分类

### 上传文档
1. 进入目标知识库
2. 点击"上传文档"按钮
3. 选择支持的文档格式（PDF、Word、Markdown、Excel等）
4. 选择分块方式（Token、句子、段落、章节、语义等）
5. 配置分块参数（大小、重叠、阈值等）
6. 等待文档解析、清洗、分段和向量化处理
7. 监控处理进度和预估完成时间

### 智能问答
1. 选择目标知识库
2. 在问答界面输入问题
3. 系统将基于知识库内容进行语义检索
4. 结合大语言模型生成准确答案
5. 提供答案来源和相似度信息

### 知识查重
1. 进入知识查重看板
2. 选择目标知识库
3. 输入查询文本或上传文档
4. 设置相似度阈值
5. 执行查重分析
6. 查看重复内容详情和位置信息

### 召回检索测试
1. 选择测试知识库
2. 输入测试查询文本
3. 调整相似度阈值
4. 查看检索结果和召回质量
5. 优化检索参数

## 开发指南

### 项目结构
```
ZhiQing/
├── zhiqing_ui/              # 前端项目
│   ├── src/
│   │   ├── components/      # 公共组件
│   │   ├── views/           # 页面组件
│   │   ├── router/          # 路由配置
│   │   └── axios/           # API接口
│   ├── public/              # 静态资源
│   └── package.json         # 前端依赖配置
├── zhiqing_server/          # Django后端服务
│   ├── settings.py          # 项目配置
│   ├── urls.py              # 主路由配置
│   └── wsgi.py              # WSGI配置
├── system_mgt/              # 系统管理模块
│   ├── models.py            # 用户和权限模型
│   ├── api/                 # 系统管理API
│   └── utils/               # 系统工具
├── knowledge_mgt/           # 知识管理模块
│   ├── models.py            # 知识库和文档模型
│   ├── api/                 # 知识管理API
│   ├── utils/               # 知识处理工具
│   └── document_processor/  # 文档处理器
├── chat_mgt/                # 对话管理模块
│   ├── models.py            # 对话模型
│   ├── api/                 # 对话API
│   └── utils/               # 对话工具
├── models/                   # 本地模型存储
├── requirements.txt          # Python基础依赖
├── install_requirements.py   # 依赖安装脚本
├── install.bat               # Windows安装脚本
└── install.sh                # Linux/macOS安装脚本
```

### 代码规范
- 前端遵循Vue 3官方风格指南
- 后端遵循Django最佳实践
- 使用ESLint和Prettier进行代码格式化
- 提交信息遵循Conventional Commits规范

## 部署说明

### 开发环境部署
1. 克隆项目并安装依赖
2. 配置环境变量
3. 启动前后端服务
4. 访问系统进行测试

### 生产环境部署
1. **环境准备**
   - 安装Python 3.12+和Node.js 22.0.0+
   - 配置数据库（推荐PostgreSQL）
   - 配置Redis缓存（可选）
   - 配置Nginx反向代理

2. **前端部署**
   ```bash
   cd zhiqing_ui
   npm run build
   # 将dist目录部署到Web服务器
   ```

3. **后端部署**
   ```bash
   # 使用Gunicorn启动
   pip install gunicorn
   gunicorn zhiqing_server.wsgi:application --bind 0.0.0.0:8000
   ```

4. **系统配置**
   - 配置环境变量
   - 配置数据库连接
   - 配置静态文件服务
   - 配置日志记录

### Docker部署

#### 快速开始

1. **克隆项目并进入目录**
```bash
git clone <repository-url>
cd ZhiQing
```

2. **配置环境变量**
```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量（根据需要修改）
vim .env
```

3. **启动服务**
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

#### 详细说明

**开发环境部署：**
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**生产环境部署：**
```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 查看生产环境服务状态
docker-compose -f docker-compose.prod.yml ps

# 停止生产环境服务
docker-compose -f docker-compose.prod.yml down
```

**单独构建镜像：**
```bash
# 构建后端镜像
docker build -t zhiqing-backend .

# 构建前端镜像
docker build -t zhiqing-frontend ./zhiqing_ui

# 运行单个容器
docker run -d \
  --name zhiqing-backend \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  zhiqing-backend
```

#### 服务说明

- **后端服务**: 端口8000，Django应用
- **前端服务**: 端口80，Vue.js应用
- **MySQL数据库**: 端口3306
- **Redis缓存**: 端口6379
- **Nginx代理**: 端口8080（开发环境）或80/443（生产环境）

#### 数据持久化

以下目录会被挂载到宿主机，确保数据持久化：
- `./data` - 文档数据
- `./models` - AI模型文件
- `./media` - 媒体文件
- `./logs` - 日志文件
- `mysql_data` - MySQL数据（Docker卷）
- `redis_data` - Redis数据（Docker卷）

#### 健康检查

访问以下端点检查服务状态：
- 后端健康检查: `http://localhost:8000/health/`
- 前端页面: `http://localhost:80`
- 完整应用: `http://localhost:8080`（通过Nginx代理）

#### 故障排除

```bash
# 查看容器日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mysql

# 进入容器调试
docker-compose exec backend bash
docker-compose exec mysql mysql -u root -p

# 重新构建镜像
docker-compose build --no-cache

# 清理所有容器和卷
docker-compose down -v
docker system prune -a
```




## 联系我们

如果您有疑问或建议，请通过以下方式联系我们：

- 提交Issue
- 发送邮件
- 项目讨论区

### 微信社区

扫描二维码加入我们的微信社区，与其他开发者交流经验：

![微信群二维码](./docs/images/wechat-group-qr.jpg)

*群二维码会定期更新，如果二维码过期，请联系作者*




**注意**: 首次安装可能需要较长时间，特别是下载PyTorch等大型包时，请耐心等待。