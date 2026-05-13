<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import { Plus, Search } from '@vben/icons';
import { ElButton, ElInput, ElMessage } from 'element-plus';
import { getKnowledgeBaseListApi, type KnowledgeBase } from '#/api/core/rag';
import DocCard from './modules/doc-card.vue';
import DescriptionEditor from './modules/description-editor.vue';

defineOptions({ name: 'DocumentView' });

const router = useRouter();
const kbs = ref<KnowledgeBase[]>([]);
const searchQuery = ref('');
const loading = ref(false);
const descEditorRef = ref<InstanceType<typeof DescriptionEditor>>();

const filteredKbs = computed(() => {
  if (!searchQuery.value.trim()) return kbs.value;
  const q = searchQuery.value.toLowerCase();
  return kbs.value.filter(
    (kb) => kb.name.toLowerCase().includes(q) || (kb.description || '').toLowerCase().includes(q),
  );
});

async function loadKbs() {
  loading.value = true;
  try {
    const res = await getKnowledgeBaseListApi({ page: 1, pageSize: 200 });
    kbs.value = res.items;
  } catch {
    ElMessage.error('加载知识库列表失败');
  } finally {
    loading.value = false;
  }
}

function handleCardClick(kb: KnowledgeBase) {
  router.push(`/rag/knowledge-base/${kb.id}`);
}

function openEdit(kb: KnowledgeBase) {
  descEditorRef.value?.open(kb);
}

onMounted(() => {
  loadKbs();
});
</script>

<template>
  <Page>
    <div class="document-view">
      <div class="page-header">
        <div class="header-left">
          <h2>文档管理</h2>
          <span class="doc-count">{{ filteredKbs.length }} 个知识库</span>
        </div>
        <div class="header-right">
          <ElInput
            v-model="searchQuery"
            placeholder="搜索知识库..."
            clearable
            :prefix-icon="Search"
            style="width: 240px"
          />
          <ElButton type="primary" :icon="Plus" @click="router.push('/rag/knowledge-base')">
            新建知识库
          </ElButton>
        </div>
      </div>

      <div v-loading="loading" class="doc-grid">
        <div v-if="filteredKbs.length === 0 && !loading" class="empty-state">
          <div style="padding:60px 0;color:var(--el-text-color-secondary);text-align:center">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="margin-bottom:16px">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            <p>{{ searchQuery ? '未找到匹配的知识库' : '暂无知识库' }}</p>
            <ElButton v-if="!searchQuery" type="primary" style="margin-top:12px" @click="router.push('/rag/knowledge-base')">
              创建第一个知识库
            </ElButton>
          </div>
        </div>
        <DocCard
          v-for="kb in filteredKbs"
          :key="kb.id"
          :kb="kb"
          :description="kb.description || ''"
          @click="handleCardClick(kb)"
          @edit="openEdit(kb)"
          @deleted="loadKbs"
        />
      </div>
    </div>

    <DescriptionEditor ref="descEditorRef" @saved="loadKbs" />
  </Page>
</template>

<style scoped>
.document-view {
  padding: 8px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.doc-count {
  padding: 4px 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-lighter);
  border-radius: 12px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.doc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.empty-state {
  grid-column: 1 / -1;
}
</style>
