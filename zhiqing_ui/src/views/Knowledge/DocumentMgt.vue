<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/axios/index.js'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { UploadFilled, View, Document, List, Clock, Loading, Check, Close, Delete, CircleClose, Refresh, Search } from '@element-plus/icons-vue'
import Cookies from 'js-cookie'

// 加载状态
const loading = ref(false)
// 当前选中的知识库
const currentDatabase = ref(null)
// 上传对话框可见性
const uploadDialogVisible = ref(false)
// 分块方式选项
const chunkingOptions = [
  { label: 'Token分块 (基于真实Token计数)', value: 'token' },
  { label: '句子分块 (智能句子边界)', value: 'sentence' },
  { label: '段落分块 (段落边界)', value: 'paragraph' },
  { label: '章节分块 (标题层级)', value: 'chapter' },
  { label: '语义分块 (嵌入模型语义)', value: 'semantic' },
  { label: '递归分块 (层次化分割)', value: 'recursive' },
  { label: '滑动窗口分块 (重叠窗口)', value: 'sliding_window' },
  { label: '自定义分隔符分块', value: 'custom_delimiter' },
  { label: '固定长度分块 (字符数)', value: 'fixed_length' }
]
// 知识库列表
const databaseList = ref([])
// 文档列表
const documentList = ref([])
// 文件列表（上传用）
const fileList = ref([])
// 每页显示数量
const pageSize = ref(10)
// 当前页码
const currentPage = ref(1)
// 总记录数
const totalDocuments = ref(0)

// 上传表单
const uploadForm = reactive({
  database_id: '',
  chunking_method: 'token',
  chunk_size: 500,
  similarity_threshold: 0.7,
  overlap_size: 100,
  custom_delimiter: '\n\n',
  window_size: 3,
  step_size: 1,
  min_chunk_size: 50,
  max_chunk_size: 2000,
  files: [] // 改为支持多文件
})

// 上传表单验证规则
const uploadRules = {
  database_id: [{ required: true, message: '请选择知识库', trigger: 'change' }],
  chunking_method: [{ required: true, message: '请选择分块方式', trigger: 'change' }],
  chunk_size: [{ required: true, message: '请设置分块大小', trigger: 'blur' }],
  files: [{ 
    required: true, 
    validator: (rule, value, callback) => {
      if (!value || value.length === 0) {
        callback(new Error('请选择要上传的文件'))
      } else {
        callback()
      }
    }, 
    trigger: 'change' 
  }]
}

// 上传表单引用
const uploadFormRef = ref(null)

// 上传队列相关
const uploadQueue = ref([])
const isUploading = ref(false)
const queueDialogVisible = ref(false)
const queueStats = ref({
  pending: 0,
  processing: 0,
  completed: 0,
  failed: 0
})
const currentTask = ref(null)

// 是否显示分块大小滑块
const showChunkSizeSlider = computed(() => {
  return ['token', 'fixed_length', 'recursive', 'sliding_window'].includes(uploadForm.chunking_method)
})

// 是否显示自定义分隔符
const showCustomDelimiter = computed(() => {
  return uploadForm.chunking_method === 'custom_delimiter'
})

// 是否显示滑动窗口参数
const showSlidingWindowParams = computed(() => {
  return uploadForm.chunking_method === 'sliding_window'
})

// 是否显示章节分块参数
const showChapterParams = computed(() => {
  return uploadForm.chunking_method === 'chapter'
})

// 分块大小标签
const chunkSizeLabel = computed(() => {
  switch (uploadForm.chunking_method) {
    case 'token':
      return 'Token数量'
    case 'fixed_length':
      return '字符数量'
    case 'recursive':
      return '最大块大小'
    default:
      return '分块大小'
  }
})

// 分块大小范围
const chunkSizeRange = computed(() => {
  switch (uploadForm.chunking_method) {
    case 'token':
      return { min: 50, max: 4000, step: 50 }
    case 'fixed_length':
      return { min: 100, max: 8000, step: 100 }
    case 'recursive':
      return { min: 200, max: 6000, step: 50 }
    case 'sliding_window':
      return { min: 100, max: 3000, step: 50 }
    default:
      return { min: 100, max: 2000, step: 50 }
  }
})

// 网页上传分块大小相关计算属性
const showWebChunkSizeSlider = computed(() => {
  return ['token', 'fixed_length', 'recursive', 'sliding_window'].includes(webUploadForm.chunking_method)
})

const webChunkSizeLabel = computed(() => {
  switch (webUploadForm.chunking_method) {
    case 'token':
      return 'Token数量'
    case 'fixed_length':
      return '字符数量'
    case 'recursive':
      return '最大块大小'
    default:
      return '分块大小'
  }
})

const webChunkSizeRange = computed(() => {
  switch (webUploadForm.chunking_method) {
    case 'token':
      return { min: 50, max: 4000, step: 50 }
    case 'fixed_length':
      return { min: 100, max: 8000, step: 100 }
    case 'recursive':
      return { min: 200, max: 6000, step: 100 }
    case 'sliding_window':
      return { min: 100, max: 3000, step: 50 }
    default:
      return { min: 100, max: 2000, step: 50 }
  }
})

// 数据库上传分块大小相关计算属性


// 文档分块对话框可见性
const chunksDialogVisible = ref(false)
// 当前查看的文档
const currentDocument = ref(null)
// 文档分块列表
const documentChunks = ref([])
// 分块分页
const chunkCurrentPage = ref(1)
const chunkPageSize = ref(10)
const totalChunks = ref(0)
// 分块加载状态
const chunksLoading = ref(false)

// 网页上传相关
const webUploadDialogVisible = ref(false)
const isWebUploading = ref(false)
const webUploadFormRef = ref(null)

// 网页上传表单
const webUploadForm = reactive({
  database_id: '',
  url: '',
  title: '',
  chunking_method: 'semantic',
  chunk_size: 500,
  similarity_threshold: 0.7,
  min_chunk_size: 50,
  max_chunk_size: 2000
})

// 网页上传表单验证规则
const webUploadRules = {
  database_id: [{ required: true, message: '请选择知识库', trigger: 'change' }],
  url: [
    { required: true, message: '请输入网页地址', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL地址', trigger: 'blur' }
  ],
  chunking_method: [{ required: true, message: '请选择分块方式', trigger: 'change' }],
  chunk_size: [{ required: true, message: '请设置分块大小', trigger: 'blur' }]
}



// 文件格式显示控制
const showFormatDetails = ref(false)

// 切换格式详情显示
const toggleFormatDetails = () => {
  showFormatDetails.value = !showFormatDetails.value
}

// 队列操作相关的计算属性
const hasCompletedTasks = computed(() => {
  return uploadQueue.value.some(task => task.status === 'completed')
})

const hasFailedTasks = computed(() => {
  return uploadQueue.value.some(task => task.status === 'failed')
})

// 获取知识库列表
const fetchDatabaseList = async () => {
  try {
    loading.value = true
    const response = await axios.get('knowledge/database/list/')
    console.log('知识库列表API响应:', response)
    
    // 由于axios拦截器返回response.data，所以这里使用response.data
    if (response && response.data && response.data.list) {
      databaseList.value = response.data.list
    } else {
      databaseList.value = []
      console.warn('知识库列表数据结构异常:', response)
    }
    
    // 如果有知识库且尚未选择知识库，则默认选择第一个
    if (databaseList.value && databaseList.value.length > 0 && !currentDatabase.value) {
      currentDatabase.value = databaseList.value[0]
      await fetchDocumentList() // 等待文档列表加载完成
    } else {
      loading.value = false // 如果没有知识库或已选择，直接取消loading
    }
  } catch (error) {
    // axios拦截器已经处理了错误信息显示
    console.error('获取知识库列表失败:', error)
    loading.value = false // 发生错误时取消loading
  }
}

// 刷新知识库列表（专门用于更新文档数量）
const refreshDatabaseList = async () => {
  try {
    console.log('刷新知识库列表，更新文档数量...')
    const response = await axios.get('knowledge/database/list/')
    
    if (response && response.data && response.data.list) {
      // 更新知识库列表，保持当前选中的知识库
      const currentDbId = currentDatabase.value?.id
      databaseList.value = response.data.list
      
      // 如果之前有选中的知识库，重新设置选中状态
      if (currentDbId) {
        const updatedDb = databaseList.value.find(db => db.id === currentDbId)
        if (updatedDb) {
          currentDatabase.value = updatedDb
          console.log(`知识库 ${updatedDb.name} 文档数量已更新: ${updatedDb.doc_count || 0}`)
        }
      }
    }
  } catch (error) {
    console.error('刷新知识库列表失败:', error)
  }
}

// 智能进度调整：更合理的进度分布
const getAdjustedProgress = (progress) => {
  if (!progress || progress <= 0) return 0
  if (progress >= 100) return 100
  
  // 新的进度分配：文档处理占80%，其余平分20%
  if (progress <= 20) {
    // 初始化阶段：20%进度，占5%时间（快速）
    return Math.min(progress * 0.25, 100)
  } else if (progress <= 80) {
    // 文档处理阶段：60%进度，占80%时间（主要耗时）
    return Math.min(5 + (progress - 20) * 1.34, 100)
  } else {
    // 完成阶段：20%进度，占15%时间（中等速度）
    const remainingProgress = progress - 80
    return Math.min(85 + remainingProgress * 0.75, 100)
  }
}

// 获取文档列表
const fetchDocumentList = async () => {
  if (!currentDatabase.value) return

  try {
    loading.value = true
    const response = await axios.get(`knowledge/document/list/`, {
      params: {
        database_id: currentDatabase.value.id,
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    
    console.log('文档列表API响应:', response)
    
    // 由于axios拦截器返回response.data，所以这里使用response.data
    if (response && response.data && response.data.list) {
      documentList.value = response.data.list
      totalDocuments.value = response.data.total
    } else {
      documentList.value = []
      totalDocuments.value = 0
      console.warn('文档列表数据结构异常:', response)
    }
  } catch (error) {
    // axios拦截器已经处理了错误信息显示
    console.error('获取文档列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理知识库选择变化
const handleDatabaseChange = async (database) => {
  // 如果当前在配置管理页面，则返回文档管理页面
  if (currentConfigView.value) {
    currentConfigView.value = null
  }
  
  currentDatabase.value = database
  currentPage.value = 1
  await fetchDocumentList()
}

// 处理页码变化
const handleCurrentChange = async (page) => {
  currentPage.value = page
  await fetchDocumentList()
}

// 打开上传对话框
const openUploadDialog = () => {
  if (!currentDatabase.value) {
    ElMessage.warning('请先选择一个知识库')
    return
  }

  // 重置上传表单
  uploadForm.database_id = currentDatabase.value.id
  uploadForm.chunking_method = 'token'
  uploadForm.chunk_size = 500
  uploadForm.similarity_threshold = 0.7
  uploadForm.overlap_size = 100
  uploadForm.custom_delimiter = '---'
  uploadForm.window_size = 3
  uploadForm.step_size = 1
  uploadForm.min_chunk_size = 10
  uploadForm.max_chunk_size = 2000
  uploadForm.file = null
  fileList.value = []

  uploadDialogVisible.value = true
}

// 打开网页上传对话框
const openWebUploadDialog = () => {
  if (!currentDatabase.value) {
    ElMessage.warning('请先选择一个知识库')
    return
  }

  // 重置网页上传表单
  webUploadForm.database_id = currentDatabase.value.id
  webUploadForm.url = ''
  webUploadForm.title = ''
  webUploadForm.chunking_method = 'semantic'
  webUploadForm.chunk_size = 500
  webUploadForm.similarity_threshold = 0.7
  webUploadForm.min_chunk_size = 50
  webUploadForm.max_chunk_size = 2000

  webUploadDialogVisible.value = true
}



// 支持的文件格式配置
const supportedFileFormats = {
  // 文档格式
  'txt': { name: '纯文本文件', maxSize: 10 * 1024 * 1024, description: '支持 .txt 格式的纯文本文件' },
  'md': { name: 'Markdown文件', maxSize: 10 * 1024 * 1024, description: '支持 .md 格式的Markdown文档' },
  'rtf': { name: '富文本文件', maxSize: 20 * 1024 * 1024, description: '支持 .rtf 格式的富文本文档' },
  
  // Office 文档格式
  'docx': { name: 'Word文档', maxSize: 50 * 1024 * 1024, description: '支持 .docx 格式的Word文档' },
  'doc': { name: 'Word文档(旧版)', maxSize: 50 * 1024 * 1024, description: '支持 .doc 格式的旧版Word文档' },
  'xlsx': { name: 'Excel表格', maxSize: 50 * 1024 * 1024, description: '支持 .xlsx 格式的Excel表格' },
  'xls': { name: 'Excel表格(旧版)', maxSize: 50 * 1024 * 1024, description: '支持 .xls 格式的旧版Excel表格' },
  'pptx': { name: 'PowerPoint演示', maxSize: 50 * 1024 * 1024, description: '支持 .pptx 格式的PowerPoint演示文稿' },
  'ppt': { name: 'PowerPoint演示(旧版)', maxSize: 50 * 1024 * 1024, description: '支持 .ppt 格式的旧版PowerPoint演示文稿' },
  
  // PDF 格式
  'pdf': { name: 'PDF文档', maxSize: 100 * 1024 * 1024, description: '支持 .pdf 格式的PDF文档' },
  
  // 数据格式
  'csv': { name: 'CSV表格', maxSize: 20 * 1024 * 1024, description: '支持 .csv 格式的逗号分隔值文件' },
  'tsv': { name: 'TSV表格', maxSize: 20 * 1024 * 1024, description: '支持 .tsv 格式的制表符分隔值文件' },
  'json': { name: 'JSON数据', maxSize: 20 * 1024 * 1024, description: '支持 .json 格式的JSON数据文件' },
  'xml': { name: 'XML文档', maxSize: 20 * 1024 * 1024, description: '支持 .xml 格式的XML文档' },
  
  // 网页格式
  'html': { name: 'HTML网页', maxSize: 20 * 1024 * 1024, description: '支持 .html 格式的网页文件' },
  'htm': { name: 'HTML网页', maxSize: 20 * 1024 * 1024, description: '支持 .htm 格式的网页文件' },
  
  // 电子书格式
  'epub': { name: 'EPUB电子书', maxSize: 100 * 1024 * 1024, description: '支持 .epub 格式的电子书文件' },
  'mobi': { name: 'MOBI电子书', maxSize: 100 * 1024 * 1024, description: '支持 .mobi 格式的电子书文件' },
  
  // 其他格式
  'odt': { name: 'OpenDocument文本', maxSize: 50 * 1024 * 1024, description: '支持 .odt 格式的OpenDocument文本文件' },
  'ods': { name: 'OpenDocument表格', maxSize: 50 * 1024 * 1024, description: '支持 .ods 格式的OpenDocument表格文件' },
  'odp': { name: 'OpenDocument演示', maxSize: 50 * 1024 * 1024, description: '支持 .odp 格式的OpenDocument演示文件' },
  'pages': { name: 'Pages文档', maxSize: 50 * 1024 * 1024, description: '支持 .pages 格式的Pages文档文件' }
}

// 获取支持的文件格式列表
const getSupportedFormats = () => {
  return Object.keys(supportedFileFormats)
}

// 获取文件格式信息
const getFileFormatInfo = (extension) => {
  return supportedFileFormats[extension.toLowerCase()] || null
}

// 生成 accept 属性字符串
const getAcceptString = () => {
  const formats = getSupportedFormats()
  return formats.map(format => `.${format}`).join(',')
}

// 获取文件格式统计信息
const getFormatStats = () => {
  const formats = getSupportedFormats()
  const categories = {
    '文档格式': ['txt', 'md', 'rtf'],
    'Office格式': ['docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt'],
    'PDF格式': ['pdf'],
    '数据格式': ['csv', 'tsv', 'json', 'xml'],
    '网页格式': ['html', 'htm'],
    '电子书格式': ['epub', 'mobi'],
    '开放格式': ['odt', 'ods', 'odp', 'pages']
  }
  
  const stats = {}
  Object.entries(categories).forEach(([category, formatList]) => {
    stats[category] = formatList.filter(format => formats.includes(format)).length
  })
  
  return {
    total: formats.length,
    categories: stats
  }
}

// 文件头检测配置
const fileSignatures = {
  // PDF 文件头
  'pdf': ['25504446'],
  // Office 2007+ 文件头 (ZIP格式)
  'docx': ['504B0304', '504B0506', '504B0708'],
  'xlsx': ['504B0304', '504B0506', '504B0708'],
  'pptx': ['504B0304', '504B0506', '504B0708'],
  // Office 97-2003 文件头
  'doc': ['D0CF11E0'],
  'xls': ['D0CF11E0'],
  'ppt': ['D0CF11E0'],
  // 其他格式
  'zip': ['504B0304', '504B0506', '504B0708'],
  'rtf': ['7B5C727466'],
  'xml': ['3C3F786D6C', '3C786D6C'],
  'json': ['7B', '5B'],
  'html': ['3C21444F4354595045', '3C68746D6C', '3C48454144'],
  'htm': ['3C21444F4354595045', '3C68746D6C', '3C48454144']
}

// 检测文件头
const detectFileHeader = (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const arr = new Uint8Array(e.target.result)
      const header = Array.from(arr.slice(0, 8))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
        .toUpperCase()
      
      resolve(header)
    }
    reader.readAsArrayBuffer(file)
  })
}

// 验证文件格式
const validateFileFormat = async (file) => {
  const fileExtension = file.name.split('.').pop().toLowerCase()
  const fileFormatInfo = getFileFormatInfo(fileExtension)
  
  if (!fileFormatInfo) {
    return { valid: false, error: `不支持的文件格式: ${fileExtension}` }
  }
  
  // 检查文件大小
  if (file.size > fileFormatInfo.maxSize) {
    const maxSizeMB = (fileFormatInfo.maxSize / (1024 * 1024)).toFixed(1)
    return { valid: false, error: `${fileFormatInfo.name}大小不能超过 ${maxSizeMB}MB` }
  }
  
  // 对于某些格式，进行文件头检测
  if (['pdf', 'docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt'].includes(fileExtension)) {
    try {
      const header = await detectFileHeader(file)
      const expectedSignatures = fileSignatures[fileExtension] || []
      
      if (expectedSignatures.length > 0 && !expectedSignatures.some(sig => header.startsWith(sig))) {
        return { 
          valid: false, 
          error: `文件格式验证失败: ${file.name} 可能不是有效的 ${fileFormatInfo.name}`,
          warning: true
        }
      }
    } catch (error) {
      console.warn('文件头检测失败:', error)
      // 文件头检测失败不影响上传，只是给出警告
    }
  }
  
  return { valid: true, formatInfo: fileFormatInfo }
}

// 处理文件变化
const handleFileChange = async (uploadFile, uploadFiles) => {
  console.log('文件变化事件:', uploadFile, uploadFiles)
  
  try {
    // 验证文件格式
    const validation = await validateFileFormat(uploadFile)
    
    if (!validation.valid) {
      if (validation.warning) {
        ElMessage.warning(validation.error)
        // 警告情况下仍然允许上传
      } else {
        ElMessage.error(validation.error)
        return false
      }
    }
    
    // 显示文件格式信息
    if (validation.formatInfo) {
      ElMessage.success(`已选择 ${validation.formatInfo.name}: ${uploadFile.name}`)
    }
    
    fileList.value = uploadFiles
    uploadForm.files = uploadFiles.map(f => f.raw || f) // 支持多文件，兼容不同版本
    
    console.log('处理后的文件列表:', fileList.value)
    console.log('上传表单文件:', uploadForm.files)
    
  } catch (error) {
    console.error('文件验证失败:', error)
    ElMessage.error('文件验证失败，请重试')
    return false
  }
}

// 移除文件
const handleFileRemove = () => {
  fileList.value = []
  uploadForm.files = []
}

// 上传文档（使用队列）
const handleUpload = async () => {
  if (!uploadFormRef.value) return

  try {
    await uploadFormRef.value.validate()

    if (!uploadForm.files || uploadForm.files.length === 0) {
      ElMessage.warning('请选择要上传的文件')
      return
    }

    // 创建FormData对象
    const formData = new FormData()
    formData.append('database_id', uploadForm.database_id)
    formData.append('chunking_method', uploadForm.chunking_method)
    formData.append('chunk_size', uploadForm.chunk_size)
    
    // 根据分块方式添加特殊参数
    if (uploadForm.chunking_method === 'semantic') {
      formData.append('similarity_threshold', uploadForm.similarity_threshold)
    }
    if (['recursive', 'sliding_window'].includes(uploadForm.chunking_method)) {
      formData.append('overlap_size', uploadForm.overlap_size)
    }
    if (uploadForm.chunking_method === 'custom_delimiter') {
      formData.append('custom_delimiter', uploadForm.custom_delimiter)
      formData.append('min_chunk_size', uploadForm.min_chunk_size)
      formData.append('max_chunk_size', uploadForm.max_chunk_size)
    }
    if (uploadForm.chunking_method === 'sliding_window') {
      formData.append('window_size', uploadForm.window_size)
      formData.append('step_size', uploadForm.step_size)
    }
    if (['semantic', 'chapter'].includes(uploadForm.chunking_method)) {
      formData.append('min_chunk_size', uploadForm.min_chunk_size)
      formData.append('max_chunk_size', uploadForm.max_chunk_size)
    }
    
    // 支持多文件上传
    uploadForm.files.forEach((file, index) => {
      formData.append(`files`, file)
    })

    isUploading.value = true

    try {
      // 使用现有的文档上传API，支持多文件
      console.log('开始上传文件，文件数量:', uploadForm.files.length)
      console.log('文件列表:', uploadForm.files)
      
      const uploadPromises = uploadForm.files.map(async (file, index) => {
        console.log(`准备上传第 ${index + 1} 个文件:`, file.name || file)
        
        const singleFormData = new FormData()
        singleFormData.append('database_id', uploadForm.database_id)
        singleFormData.append('chunking_method', uploadForm.chunking_method)
        singleFormData.append('chunk_size', uploadForm.chunk_size)
        
        // 根据分块方式添加特殊参数
        if (uploadForm.chunking_method === 'semantic') {
          singleFormData.append('similarity_threshold', uploadForm.similarity_threshold)
        }
        if (['recursive', 'sliding_window'].includes(uploadForm.chunking_method)) {
          singleFormData.append('overlap_size', uploadForm.overlap_size)
        }
        if (uploadForm.chunking_method === 'custom_delimiter') {
          singleFormData.append('custom_delimiter', uploadForm.custom_delimiter)
          singleFormData.append('min_chunk_size', uploadForm.min_chunk_size)
          singleFormData.append('max_chunk_size', uploadForm.max_chunk_size)
        }
        if (uploadForm.chunking_method === 'sliding_window') {
          singleFormData.append('window_size', uploadForm.window_size)
          singleFormData.append('step_size', uploadForm.step_size)
        }
        if (['semantic', 'chapter'].includes(uploadForm.chunking_method)) {
          singleFormData.append('min_chunk_size', uploadForm.min_chunk_size)
          singleFormData.append('max_chunk_size', uploadForm.max_chunk_size)
        }
        
        singleFormData.append('file', file)
        
        // 调试FormData内容
        console.log(`FormData for file ${index + 1}:`)
        for (let [key, value] of singleFormData.entries()) {
          console.log(`${key}:`, value)
        }
        
        // 使用新的任务队列API
        return axios.post('knowledge/upload-task/create/', singleFormData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      })
      
      // 等待所有文件上传完成
      const responses = await Promise.all(uploadPromises)
      
      // 显示上传结果
      const successCount = responses.filter(r => r.code === 200).length
      const totalCount = uploadForm.files.length
      
      console.log('任务创建完成，成功数量:', successCount, '总数量:', totalCount)
      
      if (successCount === totalCount) {
        ElMessage.success(`所有文档任务创建成功！共 ${totalCount} 个文件已加入队列`)
        
        // 显示队列对话框
        queueDialogVisible.value = true
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
        
        // 立即刷新知识库列表，显示最新的队列状态
        await refreshDatabaseList()
        
        // 启动队列轮询，实时更新状态
        startQueuePolling()
        
        // 为每个新创建的任务启动监控
        responses.forEach(response => {
          if (response.code === 200 && response.data.task_id) {
            startTaskMonitoring(response.data.task_id)
          }
        })
      } else {
        ElMessage.warning(`部分文档任务创建成功：${successCount}/${totalCount}`)
        
        // 即使部分成功，也要启动轮询
        startQueuePolling()
        
        // 为成功的任务启动监控
        responses.forEach(response => {
          if (response.code === 200 && response.data.task_id) {
            startTaskMonitoring(response.data.task_id)
          }
        })
      }
      
      uploadDialogVisible.value = false
      
      // 清空文件列表
      fileList.value = []
      uploadForm.files = []

    } catch (error) {
      console.error('文档上传失败:', error)
    } finally {
      isUploading.value = false
    }
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

// 处理网页上传
const handleWebUpload = async () => {
  if (!webUploadFormRef.value) return

  try {
    await webUploadFormRef.value.validate()
    isWebUploading.value = true

    // 创建网页上传任务
    const webUploadData = {
      database_id: webUploadForm.database_id,
      url: webUploadForm.url,
      title: webUploadForm.title || '',
      chunking_method: webUploadForm.chunking_method,
      chunk_size: webUploadForm.chunk_size,
      similarity_threshold: webUploadForm.similarity_threshold,
      min_chunk_size: webUploadForm.min_chunk_size,
      max_chunk_size: webUploadForm.max_chunk_size
    }

    console.log('开始网页抓取任务:', webUploadData)

    // 调用网页抓取API（需要后端实现）
    const response = await axios.post('knowledge/web-crawl/create/', webUploadData, { timeout: 120000 })

    if (response.code === 200) {
      ElMessage.success('网页抓取任务创建成功！已加入队列')
      
      // 显示队列对话框
      queueDialogVisible.value = true
      
              // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
        
        // 立即刷新知识库列表，显示最新的队列状态
        await refreshDatabaseList()
        
        // 启动队列轮询，实时更新状态
        startQueuePolling()
        
        // 启动任务监控
        if (response.data.task_id) {
          startTaskMonitoring(response.data.task_id)
        }
      
      webUploadDialogVisible.value = false
    } else {
      ElMessage.error(`网页抓取任务创建失败: ${response.message}`)
    }

  } catch (error) {
    console.error('网页上传失败:', error)
    ElMessage.error('网页上传失败，请检查网络连接和参数设置')
  } finally {
    isWebUploading.value = false
  }
}



// 删除文档
const handleDeleteDocument = (document) => {
  ElMessageBox.confirm(
    `确认删除文档 "${document.title || document.filename}"？删除后不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error'
    }
  )
    .then(async () => {
      loading.value = true
      try {
        await axios.delete(`knowledge/document/${document.id}/delete/`)
        ElMessage.success('删除成功')

        // 刷新知识库列表，更新文档数量
        await fetchDatabaseList()

        // 刷新文档列表
        fetchDocumentList()
      } catch (error) {
        // axios拦截器已经处理了错误信息显示
        console.error('删除文档失败:', error)
      } finally {
        loading.value = false
      }
    })
    .catch(() => { })
}

// 队列任务操作方法
const handleDeleteTask = async (task) => {
  ElMessageBox.confirm(
    `确认删除任务 "${task.filename}"？删除后不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error'
    }
  )
    .then(async () => {
      try {
        // 调用删除任务API
        await axios.delete(`knowledge/upload-task/${task.task_id}/delete/`)
        ElMessage.success('任务删除成功')
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
      } catch (error) {
        console.error('删除任务失败:', error)
        ElMessage.error('删除任务失败，请重试')
      }
    })
    .catch(() => { })
}

const handleCancelTask = async (task) => {
  ElMessageBox.confirm(
    `确认取消正在处理的任务 "${task.filename}"？`,
    '警告',
    {
      confirmButtonText: '确定取消',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        // 调用取消任务API
        await axios.post(`knowledge/upload-task/${task.task_id}/cancel/`)
        ElMessage.success('任务取消成功')
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
      } catch (error) {
        console.error('取消任务失败:', error)
        ElMessage.error('取消任务失败，请重试')
      }
    })
    .catch(() => { })
}

const handleViewTaskResult = (task) => {
  // 查看任务结果，可以跳转到文档列表或显示详细信息
  ElMessage.info(`查看任务 "${task.filename}" 的结果`)
  // TODO: 实现查看任务结果的逻辑
}

const handleClearCompletedTasks = async () => {
  ElMessageBox.confirm(
    '确认清空所有已完成的任务？此操作不可恢复！',
    '警告',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        // 调用清空已完成任务API
        await axios.post('knowledge/upload-task/clear-completed/')
        ElMessage.success('已清空所有已完成的任务')
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
      } catch (error) {
        console.error('清空已完成任务失败:', error)
        ElMessage.error('清空失败，请重试')
      }
    })
    .catch(() => { })
}

const handleClearFailedTasks = async () => {
  ElMessageBox.confirm(
    '确认清空所有失败的任务？此操作不可恢复！',
    '警告',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        // 调用清空失败任务API
        await axios.post('knowledge/upload-task/clear-failed/')
        ElMessage.success('已清空所有失败的任务')
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
      } catch (error) {
        console.error('清空失败任务失败:', error)
        ElMessage.error('清空失败，请重试')
      }
    })
    .catch(() => { })
}

const handleClearAllTasks = async () => {
  ElMessageBox.confirm(
    '确认清空所有任务？此操作不可恢复！',
    '危险操作',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'error'
    }
  )
    .then(async () => {
      try {
        // 调用清空所有任务API
        await axios.post('knowledge/upload-task/clear-all/')
        ElMessage.success('已清空所有任务')
        
        // 刷新队列状态和任务列表
        await fetchQueueStatus()
        await fetchUploadTasks()
      } catch (error) {
        console.error('清空所有任务失败:', error)
        ElMessage.error('清空失败，请重试')
      }
    })
    .catch(() => { })
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (size < 1024) {
    return size + ' B'
  } else if (size < 1024 * 1024) {
    return (size / 1024).toFixed(2) + ' KB'
  } else if (size < 1024 * 1024 * 1024) {
    return (size / (1024 * 1024)).toFixed(2) + ' MB'
  } else {
    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }
}

// 获取分块方式的中文标签
const getChunkingMethodLabel = (method) => {
  const option = chunkingOptions.find(opt => opt.value === method)
  return option ? option.label : method
}

// 查看文档分块
const viewDocumentChunks = async (document) => {
  currentDocument.value = document
  chunkCurrentPage.value = 1
  chunksDialogVisible.value = true
  documentChunks.value = []
  await fetchDocumentChunks()
}

// 获取文档分块
const fetchDocumentChunks = async () => {
  if (!currentDocument.value) return

  try {
    chunksLoading.value = true
    const { data } = await axios.get(`knowledge/document/${currentDocument.value.id}/chunks/`, {
      params: {
        page: chunkCurrentPage.value,
        page_size: chunkPageSize.value
      }
    })
    console.log('分块API响应:', data)
    
    // 更新文档信息，包括分块方式等详细信息
    if (data?.document) {
      currentDocument.value = {
        ...currentDocument.value,
        ...data.document
      }
    }
    
    documentChunks.value = data?.chunks || []
    totalChunks.value = data?.total_chunks || currentDocument.value?.chunk_count || 0
  } catch (error) {
    documentChunks.value = []
    // axios拦截器已经处理了错误信息显示
    console.error('获取文档分块失败:', error)
  } finally {
    chunksLoading.value = false
  }
}

// 处理分块页码变化
const handleChunkPageChange = (page) => {
  chunkCurrentPage.value = page
  fetchDocumentChunks()
}

// 队列管理相关方法
const fetchQueueStatus = async () => {
  try {
    // 调用真正的队列状态API
    const response = await axios.get('knowledge/upload-task/queue-status/')
    if (response.code === 200) {
      const data = response.data
      queueStats.value = data.queue_stats
      currentTask.value = data.current_task
    } else {
      console.error('获取队列状态失败:', response.message)
      // 设置默认值
      queueStats.value = { pending: 0, processing: 0, completed: 0, failed: 0 }
      currentTask.value = null
    }
    
  } catch (error) {
    console.error('获取队列状态失败:', error)
    // 设置默认值
    queueStats.value = { pending: 0, processing: 0, completed: 0, failed: 0 }
    currentTask.value = null
  }
}

const fetchUploadTasks = async () => {
  try {
    // 调用真正的上传任务列表API
    const response = await axios.get('knowledge/upload-task/list/')
    if (response.code === 200) {
      uploadQueue.value = response.data.tasks || []
      console.log('获取上传任务列表成功:', uploadQueue.value.length, '个任务')
    } else {
      console.error('获取上传任务列表失败:', response.message)
      uploadQueue.value = []
    }
    
  } catch (error) {
    console.error('获取上传任务失败:', error)
    // 确保有默认值
    if (!uploadQueue.value) {
      uploadQueue.value = []
    }
  }
}

const startTaskMonitoring = (taskId) => {
  console.log(`启动任务 ${taskId} 监控...`)
  
  const checkTaskStatus = async () => {
    try {
      // 检查token是否还存在
      const token = Cookies.get('token')
      if (!token) {
        console.log(`Token不存在，停止任务${taskId}监控`)
        return
      }
      
      // 节流控制：避免过于频繁的任务状态更新
      const now = Date.now()
      if (now - lastTaskUpdate < TASK_UPDATE_THROTTLE) {
        return
      }
      lastTaskUpdate = now
      
      const response = await axios.get(`knowledge/upload-task/${taskId}/status/`)
      const task = response.data.task
      
      // 更新本地队列中的任务状态
      const index = uploadQueue.value.findIndex(t => t.task_id === taskId)
      if (index !== -1) {
        uploadQueue.value[index] = { ...uploadQueue.value[index], ...task }
        
        // 如果任务正在处理中，显示进度更新
        if (task.status === 'processing' && task.progress > 0) {
          console.log(`任务 ${task.filename} 进度更新: ${task.progress}%`)
        }
      }
      
      // 如果任务完成或失败，停止监控并刷新相关数据
      if (task.status === 'completed') {
        console.log(`任务 ${taskId} 完成，停止监控`)
        ElMessage.success(`文档 ${task.filename} 处理完成`)
        
        // 立即刷新知识库列表，更新文档数量
        await refreshDatabaseList()
        
        // 然后刷新其他相关数据
        await Promise.all([
          fetchDocumentList(),
          fetchQueueStatus(),
          fetchUploadTasks()
        ])
        
        return // 停止监控
      } else if (task.status === 'failed') {
        console.log(`任务 ${taskId} 失败，停止监控`)
        ElMessage.error(`文档 ${task.filename} 处理失败: ${task.error_message}`)
        
        // 刷新队列状态
        await fetchQueueStatus()
        return // 停止监控
      } else {
        // 继续监控，根据任务状态调整监控频率
        const interval = task.status === 'processing' ? 100 : 200  // 处理中100ms，等待中200ms
        setTimeout(checkTaskStatus, interval)
      }
    } catch (error) {
      // 401错误说明认证失败，停止监控
      if (error.response?.status === 401) {
        console.log(`认证失败，停止任务${taskId}监控`)
        return
      }
      console.error(`检查任务 ${taskId} 状态失败:`, error)
      
      // 错误后延迟重试
      setTimeout(checkTaskStatus, 10000)
    }
  }
  
  // 开始监控
  setTimeout(checkTaskStatus, 100)  // 100ms后开始监控，快速响应
}

const openQueueDialog = async () => {
  queueDialogVisible.value = true
  await fetchUploadTasks()
  await fetchQueueStatus()
}

const refreshQueueData = async () => {
  try {
    queueRefreshing.value = true
    console.log('手动刷新队列数据...')
    
    // 同时刷新队列状态、任务列表和知识库列表
    await Promise.all([
      fetchQueueStatus(),
      fetchUploadTasks(),
      refreshDatabaseList()
    ])
    
    ElMessage.success('队列状态和知识库信息已刷新')
  } catch (error) {
    console.error('刷新队列数据失败:', error)
    ElMessage.error('刷新队列状态失败')
  } finally {
    queueRefreshing.value = false
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case 'pending': return 'info'
    case 'processing': return 'warning'
    case 'completed': return 'success'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'pending': return '等待中'
    case 'processing': return '处理中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return '未知'
  }
}

// 队列状态轮询控制
let queuePollingInterval = null
const router = useRouter()

// 队列刷新状态
const queueRefreshing = ref(false)

// 高频轮询性能优化
let lastQueueUpdate = 0
let lastTaskUpdate = 0
const QUEUE_UPDATE_THROTTLE = 100  // 100ms节流，避免过于频繁的API调用
const TASK_UPDATE_THROTTLE = 50    // 50ms节流，任务状态更新节流

const startQueuePolling = () => {
  if (queuePollingInterval) return
  
  console.log('启动队列轮询，实时更新任务状态...')
  queuePollingInterval = setInterval(async () => {
    // 检查token是否还存在，如果不存在则停止轮询
    const token = Cookies.get('token')
    if (!token) {
      console.log('Token不存在，停止队列轮询')
      stopQueuePolling()
      return
    }
    
    try {
      // 节流控制：避免过于频繁的API调用
      const now = Date.now()
      if (now - lastQueueUpdate < QUEUE_UPDATE_THROTTLE) {
        return
      }
      lastQueueUpdate = now
      
      // 同时更新队列状态和任务列表
      await Promise.all([
        fetchQueueStatus(),
        fetchUploadTasks()
      ])
      
      // 如果有任务完成，刷新知识库列表以更新文档数量
      if (queueStats.value.completed > 0 || queueStats.value.failed > 0) {
        await refreshDatabaseList()
      }
      
      // 如果没有待处理或正在处理的任务，停止轮询
      if (queueStats.value.pending === 0 && queueStats.value.processing === 0) {
        console.log('所有任务已完成，停止队列轮询')
        stopQueuePolling()
        return
      }
      
      // 如果没有任务，降低刷新频率到60秒
      if (queueStats.value.pending === 0 && queueStats.value.processing === 0) {
        console.log('没有任务，降低刷新频率到60秒')
        // 清除当前的高频轮询
        clearInterval(queuePollingInterval)
        // 启动低频轮询
        queuePollingInterval = setInterval(async () => {
          await Promise.all([
            fetchQueueStatus(),
            fetchUploadTasks()
          ])
          // 检查是否有新任务
          if (queueStats.value.pending > 0 || queueStats.value.processing > 0) {
            console.log('检测到新任务，恢复高频轮询')
            clearInterval(queuePollingInterval)
            startQueuePolling()
          }
        }, 60000) // 60秒
      }
    } catch (error) {
      // 如果请求失败（比如401），停止轮询
      if (error.response?.status === 401) {
        console.log('认证失败，停止队列轮询')
        stopQueuePolling()
      } else {
        console.error('队列轮询更新失败:', error)
      }
    }
      }, 50) // 改为0.05秒轮询一次，实现流畅的实时更新
}

const stopQueuePolling = () => {
  if (queuePollingInterval) {
    clearInterval(queuePollingInterval)
    queuePollingInterval = null
    console.log('队列轮询已停止')
  }
}

// 监听路由变化，如果跳转到登录页则停止轮询
watch(() => router.currentRoute.value.name, (newRouteName) => {
  if (newRouteName === 'Login') {
    console.log('跳转到登录页，停止队列轮询')
    stopQueuePolling()
  }
})

// 监听token变化
watch(() => Cookies.get('token'), (newToken) => {
  if (!newToken) {
    console.log('Token被清除，停止队列轮询')
    stopQueuePolling()
  }
})

onMounted(async () => {
  // 注册全局清理函数
  if (window.globalPollingCleanup) {
    window.globalPollingCleanup.push(stopQueuePolling)
  }
  
  await fetchDatabaseList()
  await fetchQueueStatus()
  
  // 初始化停用词和敏感词列表
  await fetchStopWordsList()
  await fetchSensitiveWordsList()
  
  // 只有当有任务时才开始轮询
  if (queueStats.value.pending > 0 || queueStats.value.processing > 0) {
    startQueuePolling()
  }
})

// 组件卸载时清理定时器
onUnmounted(() => {
  stopQueuePolling()
  
  // 从全局清理器中移除
  if (window.globalPollingCleanup) {
    const index = window.globalPollingCleanup.indexOf(stopQueuePolling)
    if (index > -1) {
      window.globalPollingCleanup.splice(index, 1)
    }
  }
})

// 停用词库管理相关
const stopWordsDialogVisible = ref(false)
const stopWordsForm = reactive({
  id: null,
  word: '',
  language: 'chinese',
  category: 'general',
  description: ''
})
const stopWordsFormRef = ref(null)
const stopWordsList = ref([])
const stopWordsLoading = ref(false)
const stopWordsSearchForm = reactive({
  keyword: '',
  language: '',
  category: ''
})

// 敏感词过滤相关
const sensitiveWordsDialogVisible = ref(false)
const sensitiveWordsForm = reactive({
  id: null,
  word: '',
  level: 'medium',
  replacement: '***',
  category: 'general',
  description: ''
})
const sensitiveWordsFormRef = ref(null)
const sensitiveWordsList = ref([])
const sensitiveWordsLoading = ref(false)
const sensitiveWordsSearchForm = reactive({
  keyword: '',
  level: '',
  category: ''
})

// 停用词库管理方法
const openStopWordsDialog = (type, row = null) => {
  if (type === 'add') {
    Object.assign(stopWordsForm, {
      id: null,
      word: '',
      language: 'chinese',
      category: 'general',
      description: ''
    })
  } else {
    Object.assign(stopWordsForm, { ...row })
  }
  stopWordsDialogVisible.value = true
}

const handleStopWordsSubmit = async () => {
  if (!stopWordsFormRef.value) return
  
  try {
    await stopWordsFormRef.value.validate()
    
    if (stopWordsForm.id) {
      // 更新
      await axios.put(`knowledge/words/stop-words/${stopWordsForm.id}/update/`, stopWordsForm)
      ElMessage.success('停用词更新成功')
    } else {
      // 新增
      await axios.post('knowledge/words/stop-words/create/', stopWordsForm)
      ElMessage.success('停用词添加成功')
    }
    
    stopWordsDialogVisible.value = false
    await fetchStopWordsList()
  } catch (error) {
    console.error('停用词操作失败:', error)
    ElMessage.error('操作失败，请重试')
  }
}

const handleStopWordsDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除停用词 "${row.word}"？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`knowledge/words/stop-words/${row.id}/delete/`)
    ElMessage.success('删除成功')
    await fetchStopWordsList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

const fetchStopWordsList = async () => {
  try {
    stopWordsLoading.value = true
    const params = { ...stopWordsSearchForm }
    
    // 真实API调用
    const response = await axios.get('knowledge/words/stop-words/', { params })

    if (response.code === 200) {
      stopWordsList.value = response.data.list || []
    } else {
      ElMessage.error(response.message || '获取停用词列表失败')
    }
    
  } catch (error) {
    console.error('获取停用词列表失败:', error)
    ElMessage.error('获取停用词列表失败')
  } finally {
    stopWordsLoading.value = false
  }
}

// 敏感词过滤管理方法
const openSensitiveWordsDialog = (type, row = null) => {
  if (type === 'add') {
    Object.assign(sensitiveWordsForm, {
      id: null,
      word: '',
      level: 'medium',
      replacement: '***',
      category: 'general',
      description: ''
    })
  } else {
    Object.assign(sensitiveWordsForm, { ...row })
  }
  sensitiveWordsDialogVisible.value = true
}

const handleSensitiveWordsSubmit = async () => {
  if (!sensitiveWordsFormRef.value) return
  
  try {
    await sensitiveWordsFormRef.value.validate()
    
    if (sensitiveWordsForm.id) {
      // 更新
      await axios.put(`knowledge/words/sensitive-words/${sensitiveWordsForm.id}/update/`, sensitiveWordsForm)
      ElMessage.success('敏感词更新成功')
    } else {
      // 新增
      await axios.post('knowledge/words/sensitive-words/create/', sensitiveWordsForm)
      ElMessage.success('敏感词添加成功')
    }
    
    sensitiveWordsDialogVisible.value = false
    await fetchSensitiveWordsList()
  } catch (error) {
    console.error('敏感词操作失败:', error)
    ElMessage.error('操作失败，请重试')
  }
}

const handleSensitiveWordsDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除敏感词 "${row.word}"？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`knowledge/words/sensitive-words/${row.id}/delete/`)
    ElMessage.success('删除成功')
    await fetchSensitiveWordsList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

const fetchSensitiveWordsList = async () => {
  try {
    sensitiveWordsLoading.value = true
    const params = { ...sensitiveWordsSearchForm }
    
    // 真实API调用
    const response = await axios.get('knowledge/words/sensitive-words/', { params })

    if (response.code === 200) {
      sensitiveWordsList.value = response.data.list || []
    } else {
      ElMessage.error(response.message || '获取敏感词列表失败')
    }
    
  } catch (error) {
    console.error('获取敏感词列表失败:', error)
    ElMessage.error('获取敏感词列表失败')
  } finally {
    sensitiveWordsLoading.value = false
  }
}

// 配置管理视图控制
const currentConfigView = ref(null)

// 切换配置视图
const switchConfigView = (view) => {
  currentConfigView.value = view
  // 根据视图类型加载相应数据
  if (view === 'stopwords') {
    fetchStopWordsList()
  } else if (view === 'sensitive') {
    fetchSensitiveWordsList()
  }
}

// 表单验证规则
const stopWordsRules = {
  word: [
    { required: true, message: '请输入停用词', trigger: 'blur' },
    { min: 1, max: 50, message: '停用词长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  language: [
    { required: true, message: '请选择语言', trigger: 'change' }
  ],
  category: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ]
}

const sensitiveWordsRules = {
  word: [
    { required: true, message: '请输入敏感词', trigger: 'blur' },
    { min: 1, max: 50, message: '敏感词长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  level: [
    { required: true, message: '请选择敏感级别', trigger: 'blur' }
  ],
  replacement: [
    { required: true, message: '请输入替换词', trigger: 'blur' },
    { max: 20, message: '替换词长度不能超过 20 个字符', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择分类', trigger: 'blur' }
  ]
}
</script>

<template>
  <div class="document-manager-container">
    <div class="header">
      <div class="title">文档管理</div>
    </div>

    <div class="content-container" v-loading="loading">
      <!-- 左侧知识库列表 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>知识库列表</h3>
        </div>
        <div class="database-list">
          <div v-if="databaseList.length === 0" class="empty-state">
            <div class="empty-icon">📚</div>
            <div class="empty-text">暂无知识库</div>
          </div>
          <el-card v-for="db in databaseList" :key="db.id" class="database-card"
            :class="{ active: currentDatabase && currentDatabase.id === db.id }" @click="handleDatabaseChange(db)">
            <div class="database-info">
              <h4>{{ db.name }}</h4>
              <div class="database-detail">
                <span>文档数: {{ db.doc_count || 0 }}</span>
                <span>向量维度: {{ db.vector_dimension }}</span>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 配置管理按钮组 -->
        <div class="config-buttons">
          <div class="config-section">
            <h4>⚙️ 配置管理</h4>
            <div class="config-button-group">
              <el-card 
                class="config-card"
                :class="{ active: currentConfigView === 'stopwords' }"
                @click="switchConfigView('stopwords')"
              >
                <div class="config-card-content">
                  <div class="config-icon">🛑</div>
                  <div class="config-info">
                    <div class="config-title">停用词库管理</div>
                    <div class="config-desc">过滤无意义的常用词汇</div>
                  </div>
                </div>
              </el-card>
              <el-card 
                class="config-card"
                :class="{ active: currentConfigView === 'sensitive' }"
                @click="switchConfigView('sensitive')"
              >
                <div class="config-card-content">
                  <div class="config-icon">🚫</div>
                  <div class="config-info">
                    <div class="config-title">敏感词过滤</div>
                    <div class="config-desc">替换不当或敏感内容</div>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧主内容区域 -->
      <div class="main-content">
        <!-- 配置管理视图 -->
        <div v-if="currentConfigView" class="config-management-view">
          <div class="config-header">
            <h3>
              <span v-if="currentConfigView === 'stopwords'">🛑 停用词库管理</span>
              <span v-else-if="currentConfigView === 'sensitive'">🚫 敏感词过滤管理</span>
            </h3>
            <div class="config-header-actions">
              <el-button 
                v-if="currentConfigView === 'stopwords'"
                type="primary" 
                @click="openStopWordsDialog('add')"
              >
                添加停用词
              </el-button>
              <el-button 
                v-else-if="currentConfigView === 'sensitive'"
                type="primary" 
                @click="openSensitiveWordsDialog('add')"
              >
                添加敏感词
              </el-button>
              <el-button 
                type="info" 
                @click="currentConfigView === 'stopwords' ? fetchStopWordsList() : fetchSensitiveWordsList()"
              >
                刷新
              </el-button>
              <el-button @click="currentConfigView = null" type="text">
                返回文档管理
              </el-button>
            </div>
          </div>

          <!-- 停用词管理界面 -->
          <div v-if="currentConfigView === 'stopwords'" class="config-content">
            <!-- 搜索过滤 -->
            <div class="search-filters">
              <el-input 
                v-model="stopWordsSearchForm.keyword" 
                placeholder="搜索停用词" 
                style="width: 200px; margin-right: 16px;"
                @input="fetchStopWordsList"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select 
                v-model="stopWordsSearchForm.language" 
                placeholder="语言" 
                style="width: 120px; margin-right: 16px;"
                @change="fetchStopWordsList"
              >
                <el-option label="全部语言" value="" />
                <el-option label="中文" value="chinese" />
                <el-option label="英文" value="english" />
                <el-option label="混合" value="mixed" />
              </el-select>
              <el-select 
                v-model="stopWordsSearchForm.category" 
                placeholder="分类" 
                style="width: 120px;"
                @change="fetchStopWordsList"
              >
                <el-option label="全部分类" value="" />
                <el-option label="通用" value="general" />
                <el-option label="技术" value="technical" />
                <el-option label="学术" value="academic" />
                <el-option label="商业" value="business" />
              </el-select>
            </div>

            <!-- 停用词列表 -->
            <div class="words-table-container">
              <div v-if="stopWordsLoading" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                加载中...
              </div>
              <div v-else-if="stopWordsList.length === 0" class="empty-words">
                <el-empty description="暂无停用词" />
              </div>
              <el-table v-else :data="stopWordsList" style="width: 100%" border>
                <el-table-column prop="word" label="停用词" min-width="120" />
                <el-table-column prop="language" label="语言" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.language === 'chinese' ? 'success' : 'warning'">
                      {{ row.language === 'chinese' ? '中文' : row.language === 'english' ? '英文' : '混合' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="category" label="分类" width="100">
                  <template #default="{ row }">
                    <el-tag type="info" effect="plain">{{ row.category }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" text @click="openStopWordsDialog('edit', row)">
                      编辑
                    </el-button>
                    <el-button size="small" type="danger" text @click="handleStopWordsDelete(row)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 敏感词管理界面 -->
          <div v-else-if="currentConfigView === 'sensitive'" class="config-content">
            <!-- 搜索过滤 -->
            <div class="search-filters">
              <el-input 
                v-model="sensitiveWordsSearchForm.keyword" 
                placeholder="搜索敏感词" 
                style="width: 200px; margin-right: 16px;"
                @input="fetchSensitiveWordsList"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select 
                v-model="sensitiveWordsSearchForm.level" 
                placeholder="敏感级别" 
                style="width: 120px; margin-right: 16px;"
                @change="fetchSensitiveWordsList"
              >
                <el-option label="全部级别" value="" />
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
              </el-select>
              <el-select 
                v-model="sensitiveWordsSearchForm.category" 
                placeholder="分类" 
                style="width: 120px;"
                @change="fetchSensitiveWordsList"
              >
                <el-option label="全部分类" value="" />
                <el-option label="通用" value="general" />
                <el-option label="政治" value="political" />
                <el-option label="商业" value="business" />
                <el-option label="技术" value="technical" />
              </el-select>
            </div>

            <!-- 敏感词列表 -->
            <div class="words-table-container">
              <div v-if="sensitiveWordsLoading" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                加载中...
              </div>
              <div v-else-if="sensitiveWordsList.length === 0" class="empty-words">
                <el-empty description="暂无敏感词" />
              </div>
              <el-table v-else :data="sensitiveWordsList" style="width: 100%" border>
                <el-table-column prop="word" label="敏感词" min-width="120" />
                <el-table-column prop="level" label="级别" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.level === 'high' ? 'danger' : row.level === 'medium' ? 'warning' : 'success'">
                      {{ row.level === 'high' ? '高' : row.level === 'medium' ? '中' : '低' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="replacement" label="替换词" width="120" />
                <el-table-column prop="category" label="分类" width="100">
                  <template #default="{ row }">
                    <el-tag type="info" effect="plain">{{ row.category }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" text @click="openSensitiveWordsDialog('edit', row)">
                      编辑
                    </el-button>
                    <el-button size="small" type="danger" text @click="handleSensitiveWordsDelete(row)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>

        <!-- 文档管理视图 -->
        <div v-else class="documents-view">
          <div class="documents-header">
            <h3>{{ currentDatabase ? currentDatabase.name : '请选择知识库' }} - 文档列表</h3>
            <div class="header-actions">
              <el-badge v-if="queueStats.pending > 0" :value="queueStats.pending" class="queue-badge">
                <el-button type="info" plain @click="openQueueDialog" :disabled="!currentDatabase">
                  <el-icon><List /></el-icon>
                  上传队列
                </el-button>
              </el-badge>
              <el-button v-else type="info" plain @click="openQueueDialog" :disabled="!currentDatabase">
                <el-icon><List /></el-icon>
                上传队列
              </el-button>
              <el-button type="primary" :icon="UploadFilled" @click="openUploadDialog" 
                         :disabled="!currentDatabase" :loading="isUploading">
                上传文档
              </el-button>
              <el-button type="success" :icon="UploadFilled" @click="openWebUploadDialog" 
                         :disabled="!currentDatabase">
                上传网页地址
              </el-button>
            </div>
          </div>

        <div class="documents-list">
          <div v-if="documentList.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="empty-text">暂无文档</div>
            <div class="empty-hint">点击右上角"上传文档"按钮添加文档</div>
          </div>
          <el-table v-else :data="documentList" style="width: 100%">
            <el-table-column prop="filename" label="文件名" min-width="200"></el-table-column>
            <el-table-column prop="file_type" label="文件类型" width="120"></el-table-column>
            <el-table-column label="文件大小" width="120">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块数量" width="120">
              <template #default="{ row }">
                <el-tag type="success" effect="plain" class="chunk-count-tag">
                  {{ row.chunk_count || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="上传时间" width="180"></el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button size="small" type="primary" plain :icon="View" @click="viewDocumentChunks(row)"
                    :disabled="!row.chunk_count" class="action-button">
                    查看分块
                  </el-button>
                  <el-button size="small" type="danger" :icon="Document" @click="handleDeleteDocument(row)"
                    class="action-button">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination" v-if="documentList.length > 0">
            <el-pagination layout="total, prev, pager, next" :total="totalDocuments" :current-page="currentPage"
              :page-size="pageSize" @current-change="handleCurrentChange" />
          </div>
        </div>
        </div>
      </div>
    </div>

    <!-- 上传文档对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档" width="600px" destroy-on-close>
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="选择知识库" prop="database_id">
          <el-select v-model="uploadForm.database_id" placeholder="请选择知识库">
            <el-option v-for="db in databaseList" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="分块方式" prop="chunking_method">
          <el-select v-model="uploadForm.chunking_method" placeholder="请选择分块方式">
            <el-option v-for="option in chunkingOptions" :key="option.value" :label="option.label"
              :value="option.value" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="showChunkSizeSlider" :label="chunkSizeLabel" prop="chunk_size">
          <el-slider 
            v-model="uploadForm.chunk_size" 
            :min="chunkSizeRange.min" 
            :max="chunkSizeRange.max" 
            :step="chunkSizeRange.step" 
            show-input 
            show-stops 
          />
          <span class="chunk-size-tip">{{ chunkSizeLabel }}: {{ uploadForm.chunk_size }}</span>
        </el-form-item>

        <!-- 语义分块特殊参数 -->
        <el-form-item v-if="uploadForm.chunking_method === 'semantic'" label="相似度阈值">
          <el-slider 
            v-model="uploadForm.similarity_threshold" 
            :min="0.1" 
            :max="0.9" 
            :step="0.1" 
            show-input 
          />
          <span class="chunk-size-tip">相似度阈值: {{ uploadForm.similarity_threshold }}</span>
        </el-form-item>

        <!-- 递归分块和滑动窗口重叠参数 -->
        <el-form-item v-if="['recursive', 'sliding_window'].includes(uploadForm.chunking_method)" label="重叠大小">
          <el-slider 
            v-model="uploadForm.overlap_size" 
            :min="0" 
            :max="500" 
            :step="50" 
            show-input 
          />
          <span class="chunk-size-tip">重叠字符数: {{ uploadForm.overlap_size }}</span>
        </el-form-item>

        <!-- 自定义分隔符参数 -->
        <el-form-item v-if="showCustomDelimiter" label="自定义分隔符">
          <el-input 
            v-model="uploadForm.custom_delimiter" 
            placeholder="请输入分隔符，如：\n\n 或 ### 或 ====" 
          />
          <span class="chunk-size-tip">
            常用分隔符：\n\n (双换行)、### (三级标题)、---- (分割线)
          </span>
        </el-form-item>

        <!-- 滑动窗口特殊参数 -->
        <template v-if="showSlidingWindowParams">
          <el-form-item label="窗口大小">
            <el-input-number 
              v-model="uploadForm.window_size" 
              :min="2" 
              :max="10" 
              style="width: 100%" 
            />
            <span class="chunk-size-tip">每个窗口包含的句子数量</span>
          </el-form-item>
          
          <el-form-item label="步长">
            <el-input-number 
              v-model="uploadForm.step_size" 
              :min="1" 
              :max="5" 
              style="width: 100%" 
            />
            <span class="chunk-size-tip">窗口移动的步长</span>
          </el-form-item>
        </template>

        <!-- 语义分块和章节分块的大小限制 -->
        <template v-if="['semantic', 'chapter'].includes(uploadForm.chunking_method)">
          <el-form-item label="最小块大小">
            <el-input-number 
              v-model="uploadForm.min_chunk_size" 
              :min="20" 
              :max="500" 
              style="width: 100%" 
            />
            <span class="chunk-size-tip">最小分块字符数</span>
          </el-form-item>
          
          <el-form-item label="最大块大小">
            <el-input-number 
              v-model="uploadForm.max_chunk_size" 
              :min="500" 
              :max="10000" 
              style="width: 100%" 
            />
            <span class="chunk-size-tip">最大分块字符数</span>
          </el-form-item>
        </template>

        <el-form-item label="选择文件">
          <el-upload class="upload-file" :auto-upload="false" :limit="10" :multiple="true" :on-change="handleFileChange"
            :on-remove="handleFileRemove" :file-list="fileList" 
            :accept="getAcceptString()">
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                <div class="upload-limits">
                  <span>📏 文件大小限制：根据格式不同，最大支持 10MB-100MB</span>
                  <br>
                  <span>📁 最多可同时选择 10 个文件</span>
                </div>
                <div v-if="fileList.length > 0" class="selected-files">
                  <span style="color: #409EFF; font-weight: bold;">
                    ✅ 已选择 {{ fileList.length }} 个文件
                  </span>
                </div>
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="文件格式支持">
          <div class="format-stats-display">
            <div class="stats-summary">
              <el-tag type="success" size="large">
                总计支持 {{ getFormatStats().total }} 种文件格式
              </el-tag>
            </div>
            <div class="stats-breakdown">
              <el-tag v-for="(count, category) in getFormatStats().categories" 
                      :key="category" 
                      :type="count > 0 ? 'info' : 'info'" 
                      effect="plain" 
                      class="category-tag">
                {{ category }}: {{ count }}
              </el-tag>
            </div>
            
            <!-- 折叠/展开按钮 -->
            <div class="format-toggle">
              <div class="toggle-hint">
                <span class="hint-text">💡 点击下方按钮查看支持的具体文件格式</span>
              </div>
              <el-button 
                type="text" 
                @click="toggleFormatDetails" 
                class="toggle-button">
                <el-icon :class="showFormatDetails ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></el-icon>
                {{ showFormatDetails ? '收起详细格式' : '查看详细格式' }}
              </el-button>
            </div>
            
            <!-- 详细格式列表（可折叠） -->
            <el-collapse-transition>
              <div v-show="showFormatDetails" class="supported-formats-list">
                <div class="format-category-item">
                  <span class="category-title">📄 文档格式：</span>
                  <span class="format-list">.txt, .md, .rtf</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">📊 Office格式：</span>
                  <span class="format-list">.docx, .doc, .xlsx, .xls, .pptx, .ppt</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">📖 PDF格式：</span>
                  <span class="format-list">.pdf</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">📋 数据格式：</span>
                  <span class="format-list">.csv, .tsv, .json, .xml</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">🌐 网页格式：</span>
                  <span class="format-list">.html, .htm</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">📚 电子书格式：</span>
                  <span class="format-list">.epub, .mobi</span>
                </div>
                <div class="format-category-item">
                  <span class="category-title">🔓 开放格式：</span>
                  <span class="format-list">.odt, .ods, .odp, .pages</span>
                </div>
              </div>
            </el-collapse-transition>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpload" :loading="isUploading">
            {{ isUploading ? '上传中...' : `上传 ${fileList.length > 0 ? fileList.length : 0} 个文件` }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 上传队列对话框 -->
    <el-dialog v-model="queueDialogVisible" title="文档上传队列" width="70%" destroy-on-close>
      <div class="queue-stats">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="stat-card pending">
              <div class="stat-icon">
                <el-icon><Clock /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ queueStats.pending }}</div>
                <div class="stat-label">等待中</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card processing">
              <div class="stat-icon">
                <el-icon><Loading /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ queueStats.processing }}</div>
                <div class="stat-label">处理中</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card completed">
              <div class="stat-icon">
                <el-icon><Check /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ queueStats.completed }}</div>
                <div class="stat-label">已完成</div>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card failed">
              <div class="stat-icon">
                <el-icon><Close /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ queueStats.failed }}</div>
                <div class="stat-label">失败</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <div v-if="currentTask" class="current-task">
        <h4>当前处理任务</h4>
        <el-card>
          <div class="task-info">
            <div class="task-header">
              <div class="task-name">{{ currentTask.filename }}</div>
              <div class="task-status">
                <el-tag type="warning" size="small">处理中</el-tag>
              </div>
            </div>
            
            <div class="task-details">
              <div class="detail-row">
                <span class="detail-label">文件大小:</span>
                <span class="detail-value">{{ currentTask.file_size_formatted || '未知' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">分块方法:</span>
                <span class="detail-value">{{ currentTask.chunking_method || '未知' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">开始时间:</span>
                <span class="detail-value">{{ currentTask.started_at || '未知' }}</span>
              </div>
              <div class="detail-row" v-if="currentTask.status_message">
                <span class="detail-label">当前状态:</span>
                <span class="detail-value status-message">{{ currentTask.status_message }}</span>
              </div>
            </div>
            
            <div class="task-progress-section">
              <div class="progress-header">
                <span>处理进度</span>
                <span class="progress-percentage">{{ currentTask.progress }}%</span>
              </div>
              
              <!-- 智能进度条：前快后慢 -->
              <div class="smart-progress-container">
                <el-progress 
                  :percentage="getAdjustedProgress(currentTask.progress)" 
                  :status="currentTask.progress === 100 ? 'success' : null"
                  :stroke-width="8"
                  :show-text="false"
                  class="smart-progress real-time-progress"
                />
                
                <!-- 进度阶段指示器 -->
                <div class="progress-stages">
                  <div class="stage-indicator" :class="{ active: currentTask.progress >= 5 }">
                    <span class="stage-dot"></span>
                    <span class="stage-label">初始化</span>
                  </div>
                  <div class="stage-indicator" :class="{ active: currentTask.progress >= 20 }">
                    <span class="stage-dot"></span>
                    <span class="stage-label">文档处理</span>
                  </div>
                  <div class="stage-indicator" :class="{ active: currentTask.progress >= 80 }">
                    <span class="stage-dot"></span>
                    <span class="stage-label">完成阶段</span>
                  </div>
                </div>
              </div>
              
              <div class="progress-info" v-if="currentTask.estimated_remaining_time">
                <el-icon><Clock /></el-icon>
                <span>预估剩余时间: {{ currentTask.estimated_remaining_time }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

              <div class="queue-list">
          <div class="queue-header">
            <div class="header-left">
              <h4>任务列表</h4>
            </div>
            <div class="header-right">
              <el-button 
                size="small" 
                type="primary" 
                :icon="Refresh"
                @click="refreshQueueData"
                :loading="queueRefreshing"
                class="refresh-btn">
                刷新状态
              </el-button>
              <div class="queue-summary">
                <span class="summary-item">
                  <el-tag type="info" size="small">总计: {{ uploadQueue.length }}</el-tag>
                </span>
                <span class="summary-item">
                  <el-tag type="success" size="small">已完成: {{ queueStats.completed }}</el-tag>
                </span>
                <span class="summary-item">
                  <el-tag type="warning" size="small">处理中: {{ queueStats.processing }}</el-tag>
                </span>
                <span class="summary-item">
                  <el-tag type="danger" size="small">失败: {{ queueStats.failed }}</el-tag>
                </span>
              </div>
            </div>
          </div>
        <el-table :data="uploadQueue" style="width: 100%" max-height="400">
          <el-table-column prop="filename" label="文件名" min-width="200"></el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusColor(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="150">
            <template #default="{ row }">
              <el-progress 
                v-if="row.status === 'processing'" 
                :percentage="row.progress || 0" 
                :stroke-width="6"
                :show-text="false"
              />
              <span v-else-if="row.status === 'completed'" class="progress-text">100%</span>
              <span v-else-if="row.status === 'failed'" class="progress-text error">失败</span>
              <span v-else class="progress-text">等待中</span>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分块数" width="100">
            <template #default="{ row }">
              {{ row.chunk_count || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180"></el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <el-text v-if="row.error_message" type="danger" size="small">
                {{ row.error_message }}
              </el-text>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <div class="queue-actions">
                <el-button 
                  v-if="row.status === 'pending' || row.status === 'failed'"
                  size="small" 
                  type="danger" 
                  :icon="Delete"
                  @click="handleDeleteTask(row)"
                  class="action-button">
                  删除
                </el-button>
                <el-button 
                  v-if="row.status === 'processing'"
                  size="small" 
                  type="warning" 
                  :icon="CircleClose"
                  @click="handleCancelTask(row)"
                  class="action-button">
                  取消
                </el-button>
                <el-button 
                  v-if="row.status === 'completed'"
                  size="small" 
                  type="success" 
                  :icon="View"
                  @click="handleViewTaskResult(row)"
                  class="action-button">
                  查看
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 队列操作按钮 -->
        <div class="queue-actions-bar">
                      <div class="queue-actions-left">
              <el-button 
                type="danger" 
                :icon="Delete"
                @click="handleClearCompletedTasks"
                :disabled="!hasCompletedTasks"
                size="small">
                清空已完成
              </el-button>
              <el-button 
                type="warning" 
                :icon="CircleClose"
                @click="handleClearFailedTasks"
                :disabled="!hasFailedTasks"
                size="small">
                清空失败任务
              </el-button>
            </div>
            <div class="queue-actions-right">
              <el-button 
                type="danger" 
                :icon="Refresh"
                @click="handleClearAllTasks"
                :disabled="uploadQueue.length === 0"
                size="small">
                清空所有任务
              </el-button>
            </div>
        </div>
      </div>
    </el-dialog>

    <!-- 文档分块查看对话框 -->
    <el-dialog v-model="chunksDialogVisible" :title="currentDocument ? `${currentDocument.filename} - 分块详情` : '分块详情'"
      width="60%" destroy-on-close class="chunks-dialog">
      <div v-if="currentDocument" class="chunks-dialog-header">
        <div class="chunks-info">
          <div class="info-item">
            <span class="info-label">文件类型:</span>
            <el-tag size="small" effect="plain">{{ currentDocument.file_type || '-' }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">文件大小:</span>
            <span>{{ formatFileSize(currentDocument.file_size || 0) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">分块数量:</span>
            <el-tag type="success" size="small">{{ currentDocument.chunk_count || 0 }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">分块方式:</span>
            <el-tag type="info" size="small">{{ getChunkingMethodLabel(currentDocument.chunking_method) || '-' }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">分块大小:</span>
            <span>{{ currentDocument.chunk_size || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上传时间:</span>
            <span>{{ currentDocument.create_time || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="chunks-content" v-loading="chunksLoading">
        <template v-if="documentChunks && documentChunks.length > 0">
          <div v-for="(chunk, index) in documentChunks" :key="chunk.id || index" class="chunk-card">
            <div class="chunk-header">
              <div class="chunk-index">
                分块 #{{ (chunkCurrentPage - 1) * chunkPageSize + index + 1 }}
              </div>
              <div class="chunk-id">ID: {{ chunk.id || '-' }}</div>
            </div>
            <div class="chunk-text">{{ chunk.content || '(无文本内容)' }}</div>
            <div class="chunk-meta">
              <span class="meta-item">
                <span class="meta-label">Token数:</span>
                <span>{{ chunk.token_count || '-' }}</span>
              </span>
              <span class="meta-item">
                <span class="meta-label">位置:</span>
                <span>{{ chunk.position || '-' }}</span>
              </span>
            </div>
          </div>
        </template>
        <div v-else class="empty-state">
          <div class="empty-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="empty-text">暂无分块数据</div>
        </div>

        <!-- 分块分页 -->
        <div class="pagination chunks-pagination" v-if="totalChunks > 0">
          <el-pagination layout="total, sizes, prev, pager, next" :total="totalChunks" :current-page="chunkCurrentPage"
            :page-size="chunkPageSize" :page-sizes="[5, 10, 20, 50]" @current-change="handleChunkPageChange"
            @size-change="
              (size) => {
                chunkPageSize = size
                fetchDocumentChunks()
              }
            " />
        </div>
      </div>
    </el-dialog>

    <!-- 上传网页地址对话框 -->
    <el-dialog v-model="webUploadDialogVisible" title="上传网页地址" width="600px" destroy-on-close>
      <el-form ref="webUploadFormRef" :model="webUploadForm" :rules="webUploadRules" label-width="100px">
        <el-form-item label="选择知识库" prop="database_id">
          <el-select v-model="webUploadForm.database_id" placeholder="请选择知识库">
            <el-option v-for="db in databaseList" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="网页地址" prop="url">
          <el-input v-model="webUploadForm.url" placeholder="请输入网页地址，如: https://example.com" />
        </el-form-item>

        <el-form-item label="网页标题" prop="title">
          <el-input v-model="webUploadForm.title" placeholder="请输入网页标题（可选）" />
        </el-form-item>

        <el-form-item label="分块方式" prop="chunking_method">
          <el-select v-model="webUploadForm.chunking_method" placeholder="请选择分块方式">
            <el-option v-for="option in chunkingOptions" :key="option.value" :label="option.label"
              :value="option.value" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="showWebChunkSizeSlider" :label="webChunkSizeLabel" prop="chunk_size">
          <el-slider 
            v-model="webUploadForm.chunk_size" 
            :min="webChunkSizeRange.min" 
            :max="webChunkSizeRange.max" 
            :step="webChunkSizeRange.step" 
            show-input 
            show-stops 
          />
          <span class="chunk-size-tip">{{ webChunkSizeLabel }}: {{ webUploadForm.chunk_size }}</span>
        </el-form-item>

        <el-form-item v-if="webUploadForm.chunking_method === 'semantic'" label="相似度阈值">
          <el-slider 
            v-model="webUploadForm.similarity_threshold" 
            :min="0.1" 
            :max="0.9" 
            :step="0.1" 
            show-input 
            show-stops 
          />
        </el-form-item>

        <el-form-item v-if="webUploadForm.chunking_method === 'semantic'" label="最小分块大小">
          <el-input-number v-model="webUploadForm.min_chunk_size" :min="10" :max="1000" />
        </el-form-item>

        <el-form-item v-if="webUploadForm.chunking_method === 'semantic'" label="最大分块大小">
          <el-input-number v-model="webUploadForm.max_chunk_size" :min="100" :max="5000" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="webUploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleWebUpload" :loading="isWebUploading">
            开始抓取
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 停用词管理对话框 -->
    <el-dialog v-model="stopWordsDialogVisible" :title="stopWordsForm.id ? '编辑停用词' : '添加停用词'" width="500px" destroy-on-close>
      <el-form ref="stopWordsFormRef" :model="stopWordsForm" :rules="stopWordsRules" label-width="80px">
        <el-form-item label="停用词" prop="word">
          <el-input v-model="stopWordsForm.word" placeholder="请输入停用词" />
        </el-form-item>
        
        <el-form-item label="语言" prop="language">
          <el-select v-model="stopWordsForm.language" placeholder="选择语言" style="width: 100%">
            <el-option label="中文" value="chinese" />
            <el-option label="英文" value="english" />
            <el-option label="混合" value="mixed" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-select v-model="stopWordsForm.category" placeholder="选择分类" style="width: 100%">
            <el-option label="通用" value="general" />
            <el-option label="技术" value="technical" />
            <el-option label="学术" value="academic" />
            <el-option label="商业" value="business" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input v-model="stopWordsForm.description" type="textarea" :rows="3" placeholder="可选：添加描述信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="stopWordsDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleStopWordsSubmit">
            {{ stopWordsForm.id ? '更新' : '添加' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 敏感词管理对话框 -->
    <el-dialog v-model="sensitiveWordsDialogVisible" :title="sensitiveWordsForm.id ? '编辑敏感词' : '添加敏感词'" width="500px" destroy-on-close>
      <el-form ref="sensitiveWordsFormRef" :model="sensitiveWordsForm" :rules="sensitiveWordsRules" label-width="80px">
        <el-form-item label="敏感词" prop="word">
          <el-input v-model="sensitiveWordsForm.word" placeholder="请输入敏感词" />
        </el-form-item>
        
        <el-form-item label="级别" prop="level">
          <el-select v-model="sensitiveWordsForm.level" placeholder="选择敏感级别" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="替换词" prop="replacement">
          <el-input v-model="sensitiveWordsForm.replacement" placeholder="替换为的文本，如：***" />
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-select v-model="sensitiveWordsForm.category" placeholder="选择分类" style="width: 100%">
            <el-option label="通用" value="general" />
            <el-option label="政治" value="political" />
            <el-option label="商业" value="business" />
            <el-option label="技术" value="technical" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input v-model="sensitiveWordsForm.description" type="textarea" :rows="3" placeholder="可选：添加描述信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="sensitiveWordsDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSensitiveWordsSubmit">
            {{ sensitiveWordsForm.id ? '更新' : '添加' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.document-manager-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
}

.header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 2px solid #ebeef5;
  padding-bottom: 16px;
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  position: relative;
  padding-left: 12px;
}

.title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8%;
  height: 84%;
  width: 4px;
  background-color: #409eff;
  border-radius: 2px;
}

.content-container {
  display: flex;
  flex: 1;
  gap: 24px;
  height: calc(100vh - 140px);
  overflow: hidden;
}

.sidebar {
  width: 300px;
  min-width: 300px;
  background-color: white;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
  background-color: #f5f7fa;
  border-radius: 8px 8px 0 0;
}

.sidebar-header h3 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 16px;
}

.database-list {
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  scrollbar-width: thin;
  /* 细滚动条 */
}

.database-card {
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  overflow: hidden;
  border-radius: 6px;
}

.database-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.database-card.active {
  border-left: 4px solid #409eff;
  background-color: #ecf5ff;
}

.database-info h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 15px;
}

.database-detail {
  display: flex;
  justify-content: space-between;
  color: #606266;
  font-size: 13px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 16px;
}

.documents-header h3 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 18px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 新增按钮样式 */
.header-actions .el-button[type="success"] {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  border-color: #67c23a;
  color: white;
}

.header-actions .el-button[type="success"]:hover {
  background: linear-gradient(135deg, #5daf34, #73c25d);
  border-color: #5daf34;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
}

.header-actions .el-button[type="warning"] {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
  border-color: #e6a23c;
  color: white;
}

.header-actions .el-button[type="warning"]:hover {
  background: linear-gradient(135deg, #cf9236, #d4a556);
  border-color: #cf9236;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.3);
}

.documents-header .el-button {
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.documents-header .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.queue-badge {
  margin-left: 8px;
}

.documents-list {
  margin-top: 16px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  /* 细滚动条 */
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.upload-file {
  width: 100%;
  border: 2px dashed #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  transition: all 0.3s;
}

.upload-file:hover {
  border-color: #409eff;
}

/* 文件格式说明样式 */
.format-info {
  margin-bottom: 16px;
}

.format-info strong {
  color: #303133;
  font-size: 14px;
  margin-bottom: 8px;
  display: block;
}

.format-categories {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
}

.format-category {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.category-title {
  color: #606266;
  font-weight: 500;
  min-width: 80px;
}

.format-list {
  color: #409eff;
  font-family: 'Courier New', monospace;
  background-color: #f0f9ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.upload-limits {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 6px;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
}

.selected-files {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: #f0f9ff;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

/* 格式统计显示样式 */
.format-stats-display {
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
}

.format-stats-display:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.stats-summary {
  margin-bottom: 16px;
  text-align: center;
}

.stats-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.category-tag {
  margin: 2px;
  font-size: 12px;
  padding: 4px 8px;
}

/* 格式切换按钮样式 */
.format-toggle {
  margin-top: 16px;
  text-align: center;
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
}

.toggle-hint {
  margin-bottom: 12px;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  font-style: italic;
}

.toggle-button {
  color: #409eff;
  font-size: 13px;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.3s;
}

.toggle-button:hover {
  background-color: #f0f9ff;
  color: #337ecc;
}

.toggle-button .el-icon {
  margin-right: 4px;
}

/* 支持格式列表样式 */
.supported-formats-list {
  margin-top: 16px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.format-category-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.format-category-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.format-category-item .category-title {
  color: #606266;
  font-weight: 500;
  min-width: 100px;
  font-size: 13px;
}

.format-category-item .format-list {
  color: #409eff;
  font-family: 'Courier New', monospace;
  background-color: #f0f9ff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  flex: 1;
}

.chunk-size-tip {
  display: block;
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
  font-weight: 500;
}

:deep(.el-table) {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #2c3e50;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background-color: #fafafa;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: #ecf5ff;
}

:deep(.el-pagination) {
  margin-top: auto;
  padding-top: 16px;
}

:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background-color: #f5f7fa;
  padding: 16px 20px;
  margin: 0;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

/* 新增对话框样式 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

/* 网页上传表单样式 */
.web-upload-form .el-form-item {
  margin-bottom: 20px;
}

.web-upload-form .el-input {
  width: 100%;
}

/* 数据库上传表单样式 */


:deep(.el-dialog__footer) {
  border-top: 1px solid #ebeef5;
  padding: 16px 20px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-button--danger) {
  transition: all 0.3s;
}

:deep(.el-button--danger:hover) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

:deep(.el-select) {
  width: 100%;
}

/* 自定义空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
  color: #c0c4cc;
}

.empty-icon .el-icon {
  font-size: 48px;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
}

.empty-hint {
  font-size: 14px;
  color: #909399;
  text-align: center;
}

:deep(.el-empty) {
  padding: 40px 0;
}

.chunks-dialog {
  margin-top: 5vh;
}

.chunks-dialog-header {
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}

.chunks-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-right: 16px;
}

.info-label {
  color: #606266;
  font-weight: 500;
  margin-right: 8px;
}

.chunks-content {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
}

.chunk-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.chunk-card:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.chunk-index {
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.chunk-id {
  color: #909399;
  font-size: 13px;
}

.chunk-text {
  padding: 12px;
  background-color: #f9fafc;
  border-radius: 4px;
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #ebeef5;
}

.chunk-meta {
  display: flex;
  justify-content: space-between;
  color: #606266;
  font-size: 13px;
}

.meta-item {
  display: flex;
  align-items: center;
}

.meta-label {
  font-weight: 500;
  margin-right: 4px;
  color: #909399;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.action-button {
  padding: 6px 12px;
}

.chunk-count-tag {
  min-width: 50px;
  text-align: center;
  font-weight: 500;
}

.chunks-pagination {
  margin-top: 24px;
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}

:deep(.chunks-dialog .el-dialog__body) {
  padding: 16px 24px 24px;
}

:deep(.el-dialog__header) {
  padding: 16px 24px;
}

:deep(.el-tag) {
  border-radius: 4px;
}

:deep(.el-empty) {
  padding: 32px 0;
}

:deep(.el-loading-mask) {
  position: absolute;
  z-index: 100;
  border-radius: 8px;
  margin: 0;
  box-sizing: border-box;
}

/* 添加或修改分块内容相关的样式 */
.chunks-content {
  margin-top: 16px;
}

.chunk-card {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.chunk-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  border-bottom: 1px dashed #e0e0e0;
  padding-bottom: 8px;
}

.chunk-index {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

.chunk-id {
  color: #909399;
  font-size: 13px;
}

.chunk-text {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin: 12px 0;
  padding: 10px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  overflow-x: auto;
}

.chunk-meta {
  display: flex;
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.meta-item {
  margin-right: 16px;
  display: flex;
  align-items: center;
}

.meta-label {
  margin-right: 4px;
  font-weight: 500;
  color: #909399;
}

/* 对话框样式优化 */
.chunks-dialog {
  max-width: 90vw;
}

.chunks-dialog-header {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.chunks-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-label {
  margin-right: 8px;
  color: #909399;
  font-weight: 500;
}

.chunks-pagination {
  margin-top: 20px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .chunks-info {
    flex-direction: column;
    gap: 8px;
  }

  .chunk-header {
    flex-direction: column;
    gap: 4px;
  }
}

/* 滚动条样式统一 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 队列对话框样式 */
.queue-stats {
  margin-bottom: 24px;
  padding: 16px;
  background-color: #f9fafc;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  transition: all 0.3s ease;
  cursor: default;
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  font-size: 18px;
}

.stat-card.pending .stat-icon {
  background-color: #f4f4f5;
  color: #909399;
}

.stat-card.processing .stat-icon {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.stat-card.completed .stat-icon {
  background-color: #f0f9ff;
  color: #67c23a;
}

.stat-card.failed .stat-icon {
  background-color: #fef0f0;
  color: #f56c6c;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.queue-badge {
  margin-right: 12px;
}

:deep(.queue-badge .el-badge__content) {
  background-color: #f56c6c;
  border: none;
  font-size: 12px;
  height: 18px;
  line-height: 18px;
  padding: 0 6px;
  min-width: 18px;
}

.current-task {
  margin-bottom: 24px;
}

.current-task h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-weight: 600;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-name {
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.task-progress {
  width: 100%;
}

.queue-list h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-weight: 600;
}

.progress-text {
  font-size: 12px;
  color: #606266;
}

.progress-text.error {
  color: #f56c6c;
}

:deep(.el-statistic__content) {
  font-size: 24px;
  font-weight: 600;
}

:deep(.el-statistic__title) {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

/* 队列操作相关样式 */
.queue-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.queue-actions .action-button {
  padding: 4px 8px;
  font-size: 12px;
}

.queue-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.queue-actions-left {
  display: flex;
  gap: 12px;
}

.queue-actions-right {
  display: flex;
  gap: 12px;
}

.queue-actions-bar .el-button {
  font-size: 12px;
  padding: 6px 12px;
}

.queue-actions-bar .el-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 队列头部样式 */
.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.queue-header h4 {
  margin: 0;
  color: #303133;
  font-weight: 600;
}

.queue-summary {
  display: flex;
  gap: 8px;
  align-items: center;
}

.summary-item {
  display: flex;
  align-items: center;
}

/* 配置按钮样式 */
.config-buttons {
  background-color: white;
  border-radius: 8px;
  margin-top: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #ebeef5;
  overflow: hidden;
}

.config-section {
  padding: 16px 20px;
}

.config-section h4 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-button-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-card {
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  overflow: hidden;
  border-radius: 6px;
  margin-bottom: 0;
}

.config-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.config-card.active {
  border-left: 4px solid #409eff;
  background-color: #ecf5ff;
}

.config-card-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
}

.config-icon {
  font-size: 20px;
  width: 22px;
  text-align: center;
}

.config-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.config-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.config-desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.2;
}

.config-button.active {
  background-color: #409eff;
  border-color: #409eff;
  color: white;
  transform: translateX(4px);
}

.config-button:hover:not(.active) {
  background-color: #f0f9ff;
  border-color: #409eff;
  color: #409eff;
}

/* 配置管理视图样式 */
.config-management-view {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #ebeef5;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #ebeef5;
}

.config-header h3 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.config-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

/* 搜索过滤样式 */
.search-filters {
  display: flex;
  align-items: center;
  padding: 16px 0;
  margin-bottom: 20px;
  gap: 16px;
  border-bottom: 1px solid #ebeef5;
}

.search-filters .el-input,
.search-filters .el-select {
  margin-bottom: 0;
}

/* 表格容器样式 */
.words-table-container {
  flex: 1;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
  gap: 8px;
}

.empty-words {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .search-filters {
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .config-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .config-header-actions {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .config-content {
    padding: 16px;
  }
  
  .search-filters {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-filters .el-input,
  .search-filters .el-select {
    width: 100% !important;
  }
}

/* 队列对话框样式 */
.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.header-left h4 {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-btn {
  margin-right: 8px;
}

.queue-summary {
  display: flex;
  gap: 8px;
  align-items: center;
}

.current-task {
  margin-bottom: 20px;
}

.current-task h4 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.task-info {
  padding: 16px;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.task-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.task-status {
  margin-left: 16px;
}

.task-details {
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 500;
  color: #606266;
  min-width: 80px;
}

.detail-value {
  color: #303133;
  text-align: right;
  flex: 1;
}

.status-message {
  color: #409eff;
  font-style: italic;
}

.task-progress-section {
  margin-top: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-percentage {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}

.progress-info .el-icon {
  font-size: 14px;
}

/* 智能进度条样式 */
.smart-progress-container {
  margin-bottom: 16px;
}

.smart-progress {
  margin-bottom: 12px;
}

.progress-stages {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding: 0 4px;
}

.stage-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  opacity: 0.4;
  transition: all 0.3s ease;
}

.stage-indicator.active {
  opacity: 1;
}

.stage-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #409eff;
  transition: all 0.3s ease;
}

.stage-indicator.active .stage-dot {
  background-color: #67c23a;
  transform: scale(1.2);
}

.stage-label {
  font-size: 10px;
  color: #909399;
  text-align: center;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.stage-indicator.active .stage-label {
  color: #67c23a;
  font-weight: 500;
}

.progress-note {
  font-size: 11px;
  color: #909399;
  font-style: italic;
  margin-left: 8px;
}

/* 进度条动画效果 */
.smart-progress .el-progress-bar__outer {
  transition: all 0.3s ease;
}

.smart-progress .el-progress-bar__inner {
  transition: all 0.5s ease;
  background: linear-gradient(90deg, #409eff 0%, #67c23a 100%);
}

/* 实时进度条效果 */
.real-time-progress .el-progress-bar__inner {
  transition: all 0.05s ease;  /* 0.05秒的快速过渡 */
  background: linear-gradient(90deg, #409eff 0%, #67c23a 100%);
  position: relative;
  overflow: hidden;
}

.real-time-progress .el-progress-bar__inner::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
  animation: shimmer 1s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .progress-stages {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .stage-label {
    font-size: 9px;
  }
}
</style>
