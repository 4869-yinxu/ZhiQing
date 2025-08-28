<template>
  <div class="duplicate-check-container">
    <div class="header">
      <div class="title">知识查重看板（批量）</div>
    </div>

    <div class="content-wrapper" v-loading="loading">
      <div class="grid">
        <!-- 左侧：批量查重配置 -->
        <div class="left-panel">
          <el-card class="panel-card">
            <template #header>
              <div class="card-header"><span>批量查重配置</span></div>
            </template>
            <el-form label-width="110px">
              <el-form-item label="选择知识库">
                <el-select v-model="form.knowledge_id" placeholder="请选择知识库" style="width: 100%">
                  <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                      <span>{{ kb.name }}</span>
                      <div>
                        <el-tag type="info" size="small">{{ kb.doc_count || 0 }}文档</el-tag>
                        <el-tag size="small" style="margin-left: 4px;">{{ kb.vector_dimension }}维</el-tag>
                        <el-tag v-if="kb.embedding_model_name" type="success" size="small" style="margin-left: 4px;">
                          {{ getModelTypeLabel(kb.embedding_model_type) }}
                        </el-tag>
                      </div>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <!-- 当前知识库信息 -->
              <el-form-item v-if="currentKnowledgeBase" label="知识库信息">
                <div class="kb-info">
                  <div class="kb-info-row">
                    <span class="label">名称:</span>
                    <span class="value">{{ currentKnowledgeBase.name }}</span>
                  </div>
                  <div class="kb-info-row">
                    <span class="label">向量维度:</span>
                    <span class="value">{{ currentKnowledgeBase.vector_dimension }}维</span>
                  </div>
                  <div class="kb-info-row">
                    <span class="label">索引类型:</span>
                    <span class="value">{{ currentKnowledgeBase.index_type }}</span>
                  </div>
                  <div class="kb-info-row" v-if="currentKnowledgeBase.embedding_model_name">
                    <span class="label">嵌入模型:</span>
                    <span class="value">
                      <el-tag :type="getModelTypeColor(currentKnowledgeBase.embedding_model_type)" size="small">
                        {{ currentKnowledgeBase.embedding_model_name }}
                      </el-tag>
                      <span class="model-type">{{ getModelTypeLabel(currentKnowledgeBase.embedding_model_type) }}</span>
                    </span>
                  </div>
                  <div class="kb-info-row" v-else>
                    <span class="label">嵌入模型:</span>
                    <span class="value">
                      <el-tag type="warning" size="small">未绑定模型</el-tag>
                    </span>
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="相似度阈值">
                <el-slider v-model="form.similarity_threshold" :min="0.5" :max="0.95" :step="0.05" show-input show-stops />
              </el-form-item>

              <el-form-item label="最小分块(字)">
                <el-input-number v-model="form.min_chunk_size" :min="10" :max="2000" style="width: 100%" />
              </el-form-item>

              <el-form-item label="最大分组数">
                <el-input-number v-model="form.max_results" :min="1" :max="200" style="width: 100%" />
              </el-form-item>

              <el-form-item>
                <el-button type="warning" :disabled="!form.knowledge_id" :loading="batching" @click="handleBatchCheck">
                  扫描知识库
                </el-button>
                <el-button @click="resetBatch">清空结果</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 右侧：批量查重结果 -->
        <div class="right-panel">
          <el-card class="panel-card">
            <template #header>
              <div class="card-header">
                <span>批量查重结果</span>
                <div v-if="batchStats" class="stat-tags">
                  <el-tag type="info">分块 {{ batchStats.total_chunks }}</el-tag>
                  <el-tag style="margin-left: 6px;">分组 {{ batchStats.duplicate_groups }}</el-tag>
                  <el-tag type="success" style="margin-left: 6px;">重复片段 {{ batchStats.duplicate_chunks }}</el-tag>
                </div>
              </div>
            </template>
            <div>
              <el-empty v-if="batchGroups.length === 0 && hasBatch" description="未发现重复分组" />
              <el-empty v-else-if="batchGroups.length === 0 && !hasBatch" description="请在左侧配置后点击“扫描知识库”" />
              <el-collapse v-else>
                <el-collapse-item v-for="(group, gi) in batchGroups" :key="gi" :name="`g-${gi}`" :title="`分组 #${gi+1} （${group.length} 条）`">
                  <div class="group-items">
                    <div v-for="chunk in group" :key="chunk.id" class="group-item">
                      <el-tag size="small" type="info">{{ chunk.filename }}</el-tag>
                      <span class="group-content">{{ chunk.content }}</span>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from '@/axios/index.js'

const loading = ref(false)

// 知识库与表单
const knowledgeBases = ref([])
const form = reactive({
  knowledge_id: null,
  similarity_threshold: 0.8,
  min_chunk_size: 50,
  max_results: 50,
})

// 批量查重状态
const batching = ref(false)
const hasBatch = ref(false)
const batchGroups = ref([])
const batchStats = ref(null)

// 计算当前选中的知识库
const currentKnowledgeBase = computed(() => {
  if (!form.knowledge_id) return null
  return knowledgeBases.value.find(kb => kb.id === form.knowledge_id)
})

// 获取模型类型标签
const getModelTypeLabel = (modelType) => {
  const typeMap = {
    'local': '本地模型',
    'online': '在线模型',
    'dashscope': '通义千问',
    'openai': 'OpenAI',
    'zhipuai': '智谱AI',
    'baichuan': '百川AI'
  }
  return typeMap[modelType] || modelType
}

// 获取模型类型颜色
const getModelTypeColor = (modelType) => {
  const colorMap = {
    'local': 'info',
    'online': 'success',
    'dashscope': 'primary',
    'openai': 'warning',
    'zhipuai': 'danger',
    'baichuan': 'success'
  }
  return colorMap[modelType] || 'info'
}

const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    const res = await axios.get('knowledge/database/list/')
    if (res.code === 200) {
      knowledgeBases.value = res.data.list || []
    }
  } catch (e) {
    ElMessage.error('加载知识库失败')
  } finally {
    loading.value = false
  }
}

const handleBatchCheck = async () => {
  if (!form.knowledge_id) return
  try {
    batching.value = true
    hasBatch.value = true

    const fd = new FormData()
    fd.append('knowledge_id', String(form.knowledge_id))
    fd.append('similarity_threshold', String(form.similarity_threshold))
    fd.append('min_chunk_size', String(form.min_chunk_size))
    fd.append('max_results', String(form.max_results))

    const res = await axios.post('/knowledge/duplicate-check/batch/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res.code === 200) {
      batchGroups.value = res.data.duplicate_groups || []
      batchStats.value = res.data.statistics || null
      if (batchGroups.value.length === 0) {
        ElMessage.info('未发现重复内容分组')
      } else {
        ElMessage.success(`发现 ${batchGroups.value.length} 个重复分组`)
      }
    } else {
      ElMessage.error(res.message || '批量查重失败')
    }
  } catch (e) {
    ElMessage.error('批量查重失败')
  } finally {
    batching.value = false
  }
}

const resetBatch = () => {
  batchGroups.value = []
  batchStats.value = null
  hasBatch.value = false
}

watch(() => form.knowledge_id, () => {
  resetBatch()
})

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.duplicate-check-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
}
.header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 16px; border-bottom: 2px solid #ebeef5; padding-bottom: 12px; }
.title { font-size: 20px; font-weight: 600; color: #2c3e50; position: relative; padding-left: 10px; }
.title::before { content: ''; position: absolute; left: 0; top: 10%; height: 80%; width: 4px; background-color: #409eff; border-radius: 2px; }

.content-wrapper { flex: 1; overflow: hidden; }
.grid { display:grid; grid-template-columns: 360px 1fr; gap: 16px; height:100%; }
.left-panel, .right-panel { overflow: auto; padding-right: 4px; display:flex; flex-direction:column; gap: 16px; }
.panel-card { border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.card-header { display:flex; align-items:center; justify-content:space-between; font-weight:600; color:#2c3e50; }
.stat-tags { display:flex; gap:6px; align-items:center; }
.group-items { display:flex; flex-direction:column; gap:8px; }
.group-item { display:flex; gap:8px; align-items:flex-start; }
.group-content { color:#303133; }

/* 知识库信息样式 */
.kb-info { background: #f8f9fa; border-radius: 6px; padding: 12px; }
.kb-info-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.kb-info-row:last-child { margin-bottom: 0; }
.kb-info-row .label { color: #606266; font-size: 13px; }
.kb-info-row .value { color: #303133; font-size: 13px; font-weight: 500; }
.kb-info-row .model-type { margin-left: 8px; color: #909399; font-size: 12px; }

/* Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }

@media (max-width: 1024px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
