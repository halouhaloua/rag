<script lang="ts" setup>
import type { KnowledgeBase } from '#/api/core/rag';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Edit } from '@vben/icons';

import { ElButton, ElMessage, ElTabPane, ElTabs } from 'element-plus';

import { getKnowledgeBaseDetailApi } from '#/api/core/rag';

import FilesTab from './modules/files.vue';
import GraphTab from './modules/graph.vue';
import QaTab from './modules/qa.vue';

defineOptions({ name: 'KnowledgeBaseDetail' });

const route = useRoute();
const router = useRouter();
const kbId = computed(() => route.params.kbId as string);
const kb = ref<KnowledgeBase | null>(null);
const loading = ref(true);
const activeTab = ref('files');

onMounted(async () => {
  if (!kbId.value) {
    router.push('/rag/knowledge-base');
    return;
  }
  try {
    kb.value = await getKnowledgeBaseDetailApi(kbId.value);
  } catch {
    ElMessage.error('知识库不存在');
    router.push('/rag/knowledge-base');
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <Page auto-content-height>
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="kb" class="flex h-full flex-col">
      <div class="kb-header">
        <div class="kb-info">
          <h2 class="kb-title">{{ kb.name }}</h2>
          <p v-if="kb.description" class="kb-desc">{{ kb.description }}</p>
          <div class="kb-meta">
            <span>文件数: {{ kb.file_count }}</span>
            <span class="sep">|</span>
            <span>类型: {{ kb.kb_type === 'demo' ? '演示' : '用户' }}</span>
          </div>
        </div>
        <ElButton
          type="primary"
          :icon="Edit"
          @click="$router.push('/rag/knowledge-base')"
        >
          返回列表
        </ElButton>
      </div>

      <ElTabs v-model="activeTab" class="kb-tabs">
        <ElTabPane label="文件管理" name="files">
          <FilesTab :kb-id="kb.id" />
        </ElTabPane>
        <ElTabPane label="知识图谱" name="graph">
          <GraphTab :kb-id="kb.id" />
        </ElTabPane>
        <ElTabPane label="问答测试" name="qa">
          <QaTab :kb-id="kb.id" />
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>

<style scoped>
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--el-text-color-secondary);
}

.kb-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}

.kb-title {
  margin: 0 0 4px;
  font-size: 20px;
}

.kb-desc {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.kb-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.sep {
  margin: 0 8px;
}

.kb-tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding: 0 8px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}

.kb-tabs :deep(.el-tabs__content) {
  flex: 1;
}

.kb-tabs :deep(.el-tab-pane) {
  height: 100%;
}
</style>
