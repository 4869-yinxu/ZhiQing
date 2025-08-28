# ZhiQing

English | [Chinese](README.md)

An intelligent knowledge management system based on RAG (Retrieval-Augmented Generation) technology, supporting integration and management of multiple large language models and embedding models.

## Version Information

**Current Version**: v0.0.1

## Online Demo

**Demo URL**: [http://115.120.244.180:8080/](http://115.120.244.180:8080/)

*Demo environment is for experience only, please do not upload sensitive information*

## Project Introduction

ZhiQing is a modern knowledge management platform that combines traditional document management with AI Q&A capabilities through RAG technology, providing users with intelligent knowledge retrieval and Q&A experience.

## Key Features

### Core Functions
- **Intelligent Q&A**: AI Q&A system based on knowledge base content
- **Document Management**: Upload, parsing and management of multiple format documents
- **Knowledge Base Management**: Flexible knowledge base creation, editing and permission control
- **Vector Retrieval**: Efficient semantic retrieval and similarity matching
- **Knowledge Duplicate Check**: Intelligent identification of duplicate or similar knowledge fragments
- **Recall Retrieval Testing**: Support for vector retrieval quality testing and parameter tuning
- **Document Upload Queue**: Support for batch document upload and progress monitoring

### Model Management
- **Large Language Model Management**: Support for multiple LLM service providers like OpenAI, Baidu, Zhipu AI, etc.
- **Embedding Model Management**: Support for online API and locally deployed embedding models
- **Model Configuration**: Flexible model parameter configuration and performance optimization
- **Model Testing**: Built-in model connection testing and performance evaluation
- **Dynamic Model Loading**: Support for on-demand loading of local embedding models
- **Multi-Model Collaboration**: Support for large and small model collaborative work

### System Management
- **User Permission Management**: Role-based access control
- **System Monitoring**: Server resource monitoring and model status management
- **Configuration Management**: System parameters and environment configuration management
- **Task Queue Management**: Intelligent task scheduling and progress monitoring
- **Real-time Monitoring Dashboard**: Real-time system status monitoring and alerts

## Technical Architecture

### Frontend Tech Stack
- **Framework**: Vue 3 + Composition API
- **UI Components**: Element Plus
- **Build Tool**: Vite
- **State Management**: Pinia
- **Routing**: Vue Router

### Backend Tech Stack
- **Framework**: Django + Django REST Framework
- **Database**: SQLite/PostgreSQL/MySQL
- **Vector Database**: FAISS vector indexing with multiple similarity calculation methods
- **AI Integration**: Support for multiple LLM and embedding model APIs
- **Document Processing**: Support for PDF, Word, Markdown, Excel and other formats
- **Text Chunking**: Support for Token, sentence, paragraph, chapter, semantic and other chunking methods

## Quick Start

### Environment Requirements
- Node.js >= 22.0.0
- Python >= 3.12
- Git
- Memory: Recommended 8GB or more
- Storage: Recommended 20GB or more available space
- GPU: Optional, supports CUDA acceleration (recommended)

### Installation Steps

#### Method 1: Automatic Installation (Recommended)

1. **Clone Project**
```bash
git clone https://gitee.com/4869-yinxu/ZhiQing.git
cd ZhiQing
```

2. **Install Frontend Dependencies**
```bash
cd open_ragbook_ui
npm install
```

3. **Configure Environment Variables**
```bash
cd ../
# Copy environment configuration file
cp .env.dev .env
# Edit configuration file, configure necessary API keys and database connection information
```

4. **Automatic Backend Dependencies Installation**

**Windows Users**:
```bash
cd ../
# Double-click to run or execute in command line
install.bat
```

**Linux/macOS Users**:
```bash
cd ../
# Give script execution permission
chmod +x install.sh
# Run installation script
./install.sh
```

**Manual Script Execution**:
```bash
cd ../
# Upgrade pip
python -m pip install --upgrade pip
# Run installation script
python install_requirements.py
```

#### Method 2: Manual Installation

1. **Clone Project**
```bash
git clone https://gitee.com/4869-yinxu/ZhiQing.git
cd ZhiQing
```

2. **Install Frontend Dependencies**
```bash
cd open_ragbook_ui
npm install
```

3. **Configure Environment Variables**
```bash
cd ../
# Copy environment configuration file
cp .env.dev .env
# Edit configuration file, configure necessary API keys and database connection information
```

4. **Install Backend Dependencies**
```bash
cd ../
# Install basic dependencies
pip install -r requirements.txt

# Choose PyTorch version based on your system:

# CPU version
pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Or GPU version (if you have NVIDIA GPU)
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision==0.20.1+cu121 GPUtil==1.4.0 --index-url https://download.pytorch.org/whl/cu121
```

### Dependencies Installation Guide

This project provides dependency installation tools that can automatically select the appropriate PyTorch version based on your system's GPU situation.

#### System Requirements
- Python 3.12 or higher
- pip (Python package manager)

#### Installation Process
1. **Basic Dependencies Installation**: Install all common dependency packages
2. **GPU Detection**: Automatically detect if the system has NVIDIA GPU
3. **PyTorch Installation**: Choose appropriate version based on GPU situation
   - With GPU: Install CUDA version (torch==2.5.1+cu121)
   - Without GPU: Install CPU version (torch==2.7.1+cpu)
4. **Installation Verification**: Verify all dependencies are correctly installed

#### Troubleshooting

**Common Issues**:

1. **Python Version Too Low**
   - Ensure using Python 3.12 or higher
   - Run `python --version` to check version

2. **pip Version Too Old**
   - Run `python -m pip install --upgrade pip` to upgrade pip

3. **Network Connection Issues**
   - Use domestic mirror source: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **GPU Detection Error**
   - Ensure NVIDIA drivers are installed
   - Run `nvidia-smi` to check GPU status

5. **CUDA Version Mismatch**
   - Check CUDA version: `nvcc --version`
   - Choose corresponding PyTorch version based on CUDA version

**Verify Installation**:
```python
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Count: {torch.cuda.device_count()}")
    print(f"Current GPU: {torch.cuda.get_device_name(0)}")
```

### Environment Configuration

1. **Environment Variables Configuration**

```bash
# Copy configuration file
cp .env.dev .env
# Edit configuration file, modify database connection and other necessary information
# Main configurations needed:
# - Database connection information (DATABASE_URL)
# - API key configuration (OpenAI, Baidu, Zhipu AI, etc.)
# - Vector model configuration
# - System operation parameters
```

2. **Start Services**

Frontend development server:
```bash
cd open_ragbook_ui
npm run dev
# Frontend will start at http://localhost:3000
```

Backend server:
```bash
python manage.py runserver
# Backend API will start at http://localhost:8000
```

3. **Access System**
- Frontend Interface: http://localhost:3000
- Backend API: http://localhost:8000
- Admin Backend: http://localhost:8000/admin

## Configuration Guide

### Model Configuration
The system supports configuration of multiple large language models and embedding models:

- **Online API Models**: Require configuration of corresponding API keys
  - OpenAI GPT series
  - Baidu Wenxin Yiyan
  - Zhipu AI ChatGLM
  - Tongyi Qianwen
- **Locally Deployed Models**: Need to specify model path and service address
  - BGE-Large-ZH
  - Sentence-Transformers
  - Custom HuggingFace models
- **Model Parameters**: Support adjustment of temperature, max tokens and other parameters
- **Dynamic Model Loading**: Support for on-demand loading and model switching

### System Configuration
- **Database Configuration**: Support for SQLite, PostgreSQL, MySQL
- **Vector Database Configuration**: FAISS index configuration and similarity calculation methods
- **File Storage Configuration**: Local storage and cloud storage support
- **Logging Configuration**: Hierarchical logging and log rotation
- **Cache Configuration**: Redis cache support (optional)
- **Task Queue Configuration**: Celery asynchronous task processing (optional)

## User Guide

### Creating Knowledge Base
1. Login to the system and go to knowledge base management page
2. Click "Create Knowledge Base" button
3. Fill in basic knowledge base information (name, description, type)
4. Select appropriate embedding model and vector dimensions
5. Configure access permissions and chunking parameters
6. Set knowledge base tags and categories

### Uploading Documents
1. Enter target knowledge base
2. Click "Upload Document" button
3. Select supported document formats (PDF, Word, Markdown, Excel, etc.)
4. Choose chunking method (Token, sentence, paragraph, chapter, semantic, etc.)
5. Configure chunking parameters (size, overlap, threshold, etc.)
6. Wait for document parsing, cleaning, chunking and vectorization processing
7. Monitor processing progress and estimated completion time

### Intelligent Q&A
1. Select target knowledge base
2. Enter questions in the Q&A interface
3. System will perform semantic retrieval based on knowledge base content
4. Combine with large language model to generate accurate answers
5. Provide answer sources and similarity information

### Knowledge Duplicate Check
1. Enter knowledge duplicate check dashboard
2. Select target knowledge base
3. Input query text or upload documents
4. Set similarity threshold
5. Execute duplicate check analysis
6. View duplicate content details and location information

### Recall Retrieval Testing
1. Select test knowledge base
2. Input test query text
3. Adjust similarity threshold
4. View retrieval results and recall quality
5. Optimize retrieval parameters

## Development Guide

### Project Structure
```
ZhiQing/
├── open_ragbook_ui/          # Frontend project
│   ├── src/
│   │   ├── components/      # Common components
│   │   ├── views/           # Page components
│   │   ├── router/          # Route configuration
│   │   └── axios/           # API interfaces
│   ├── public/              # Static resources
│   └── package.json         # Frontend dependencies
├── zhiqing_server/          # Django backend service
│   ├── settings.py          # Project configuration
│   ├── urls.py              # Main route configuration
│   └── wsgi.py              # WSGI configuration
├── system_mgt/              # System management module
│   ├── models.py            # User and permission models
│   ├── api/                 # System management API
│   └── utils/               # System utilities
├── knowledge_mgt/           # Knowledge management module
│   ├── models.py            # Knowledge base and document models
│   ├── api/                 # Knowledge management API
│   ├── utils/               # Knowledge processing utilities
│   └── document_processor/  # Document processors
├── chat_mgt/                # Chat management module
│   ├── models.py            # Chat models
│   ├── api/                 # Chat API
│   └── utils/               # Chat utilities
├── models/                   # Local model storage
├── requirements.txt          # Python basic dependencies
├── install_requirements.py   # Dependencies installation script
├── install.bat               # Windows installation script
└── install.sh                # Linux/macOS installation script
```

### Code Standards
- Frontend follows Vue 3 official style guide
- Backend follows Django best practices
- Use ESLint and Prettier for code formatting
- Commit messages follow Conventional Commits specification

## Deployment Guide

### Development Environment Deployment
1. Clone project and install dependencies
2. Configure environment variables
3. Start frontend and backend services
4. Access system for testing

### Production Environment Deployment
1. **Environment Preparation**
   - Install Python 3.12+ and Node.js 22.0.0+
   - Configure database (recommended PostgreSQL)
   - Configure Redis cache (optional)
   - Configure Nginx reverse proxy

2. **Frontend Deployment**
   ```bash
   cd open_ragbook_ui
   npm run build
   # Deploy dist directory to web server
   ```

3. **Backend Deployment**
   ```bash
   # Use Gunicorn to start
   pip install gunicorn
   gunicorn zhiqing_server.wsgi:application --bind 0.0.0.0:8000
   ```

4. **System Configuration**
   - Configure environment variables
   - Configure database connection
   - Configure static file service
   - Configure logging

### Docker Deployment
```bash
# Build image
docker build -t zhiqing .

# Run container
docker run -d \
  --name zhiqing \
  -p 8000:8000 \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  zhiqing

# Use Docker Compose (recommended)
docker-compose up -d
```

### Cloud Server Deployment
1. **Alibaba Cloud/Tencent Cloud, etc.**
   - Choose 2-core 4GB or higher configuration
   - Install Docker and Docker Compose
   - Configure security group to open ports
   - Use domain name and SSL certificate

2. **Server Configuration Recommendations**
   - CPU: 2 cores or more
   - Memory: 4GB or more
   - Storage: 50GB or more SSD
   - Network: 5Mbps or higher bandwidth

## Contributing

Welcome to submit Issues and Pull Requests to help improve the project.

### Development Environment Setup
1. Fork project to your GitHub account
2. Clone your Fork to local
3. Create feature branch: `git checkout -b feature/your-feature`
4. Install dependencies and configure environment
5. Develop and test

### Submission Process
1. Submit changes: `git commit -m "feat: add new feature"`
2. Push to your Fork: `git push origin feature/your-feature`
3. Create Pull Request on GitHub
4. Wait for code review and merge

### Code Standards
- Follow PEP 8 Python code standards
- Use meaningful variable and function names
- Add necessary comments and docstrings
- Write unit tests to cover new features

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Contact

If you have questions or suggestions, please contact us through:

- Submit Issue
- Send email
- Project discussion area

### WeChat Community

Scan the QR code to join our WeChat community and exchange experiences with other developers:

![WeChat Group QR Code](./docs/images/wechat-group-qr.jpg)

*Group QR code will be updated regularly. If the QR code expires, please contact the author*

### Contact Author

For technical support or business cooperation, you can directly contact the author:

![Author WeChat QR Code](./docs/images/author-wechat-qr.jpg)

*Please note: Open RAGBook when adding*

## Changelog

### v0.0.1 (2025-06-15)
- **Official Release**
- **New Features**:
  - Recall retrieval testing: Support vector retrieval quality testing and parameter tuning
  - Document upload queue system: Support batch document upload and progress monitoring
  - Professional chunking methods: Added chapter chunking, semantic chunking, sliding window chunking and other strategies
  - Custom delimiter chunking: Support user-defined delimiters for document chunking
  - Knowledge duplicate check: Intelligent identification of duplicate or similar knowledge fragments
  - Real-time monitoring dashboard: System status monitoring and task progress tracking
- **Optimizations**:
  - Refactored API code, reduced duplicate code by 60%+
  - Optimized document chunking algorithms, improved chunking quality
  - Enhanced user interface, improved user experience
  - Optimized error handling and user prompts
  - Intelligent progress estimation with "fast at beginning, slow at end" strategy
- **Bug Fixes**:
  - Fixed knowledge base name uniqueness check issue
  - Fixed user information retrieval issue during document upload
  - Fixed frontend error message display issue
  - Fixed sensitive word filtering for Chinese text
  - Fixed chunking method display in frontend
- **Documentation Updates**:
  - Improved installation documentation and troubleshooting guide
  - Optimized dependency installation process
  - Added online demo address
  - Enhanced project structure documentation

### v0.0.1-beta (2025-05-30)
- Initial version release
- Implemented basic RAG Q&A functionality
- Support for multiple large language model integration
- Implemented embedding model management
- Completed user permission system
- Implemented knowledge base management functionality

---

**Note**: Initial installation may take a long time, especially when downloading large packages like PyTorch. Please be patient.