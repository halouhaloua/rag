<script lang="ts" setup>
import type {
  GraphData,
  KnowledgeBase,
  KnowledgeBaseFile,
} from '#/api/core/rag';
import type { LayoutType } from '#/composables/useGraphLayout';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElMessage, ElOption, ElSelect } from 'element-plus';

import {
  getFileListApi,
  getGraphDataApi,
  getKnowledgeBaseListApi,
} from '#/api/core/rag';
import GraphToolbar from '#/components/rag/GraphToolbar.vue';
import GraphVisualization from '#/components/rag/GraphVisualization.vue';

defineOptions({ name: 'GraphView' });

const kbs = ref<KnowledgeBase[]>([]);
const selectedKbId = ref('');
const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const graphData = ref<GraphData | null>(null);
const loading = ref(false);
const currentLayout = ref<LayoutType>('force');

const selectedKbName = computed(
  () => kbs.value.find((kb) => kb.id === selectedKbId.value)?.name || '',
);
const selectedFileName = computed(
  () => files.value.find((f) => f.id === selectedFileId.value)?.filename || '',
);

async function loadKbs() {
  const res = await getKnowledgeBaseListApi({ page: 1, pageSize: 200 });
  kbs.value = res.items;
}

async function loadFiles(kbId: string) {
  if (!kbId) {
    files.value = [];
    return;
  }
  const res = await getFileListApi(kbId);
  files.value = res.items.filter((f) => f.has_graph);
}

async function loadGraph(kbId: string, fileId: string) {
  if (!kbId || !fileId) return;
  loading.value = true;
  try {
    const res = await getGraphDataApi(kbId, fileId);
    graphData.value = res;
  } catch (error: any) {
    ElMessage.error(error.message || '加载图谱失败');
    graphData.value = null;
  } finally {
    loading.value = false;
  }
}

watch(selectedKbId, (kbId) => {
  selectedFileId.value = '';
  graphData.value = null;
  loadFiles(kbId);
});

watch(selectedFileId, (fileId) => {
  if (fileId && selectedKbId.value) {
    loadGraph(selectedKbId.value, fileId);
  } else {
    graphData.value = null;
  }
});

function onRefresh() {
  if (selectedKbId.value && selectedFileId.value) {
    loadGraph(selectedKbId.value, selectedFileId.value);
  } else {
    ElMessage.warning('请先选择知识库和文件');
  }
}

function onLayoutChange(layout: LayoutType) {
  currentLayout.value = layout;
}

const graphVizRef = ref<InstanceType<typeof GraphVisualization> | null>(null);

function onReset() {
  graphVizRef.value?.resetView();
}

function onColorSchemeChange() {
  graphVizRef.value?.updateColors();
}

onMounted(() => {
  loadKbs();
});
</script>

<template>
  <Page>
    <div class="graph-view">
      <div class="selector-bar">
        <div class="selector-item">
          <span class="label">知识库：</span>
          <ElSelect
            v-model="selectedKbId"
            placeholder="选择知识库"
            style="width: 200px"
            size="small"
            clearable
          >
            <ElOption
              v-for="kb in kbs"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </ElSelect>
        </div>
        <div class="selector-item">
          <span class="label">文件：</span>
          <ElSelect
            v-model="selectedFileId"
            placeholder="选择已构建图谱的文件"
            style="width: 240px"
            size="small"
            :disabled="!selectedKbId"
            clearable
          >
            <ElOption
              v-for="f in files"
              :key="f.id"
              :label="f.filename"
              :value="f.id"
            />
          </ElSelect>
        </div>
      </div>

      <div v-if="!selectedFileId" class="empty-hint">
        请先选择知识库和已构建图谱的文件
      </div>

      <div v-else class="graph-wrapper">
        <GraphToolbar
          :current-layout="currentLayout"
          :kb-name="selectedKbName"
          :file-label="selectedFileName"
          :loading="loading"
          @refresh="onRefresh"
          @reset="onReset"
          @color-scheme-change="onColorSchemeChange"
          @layout-change="onLayoutChange"
        />
        <GraphVisualization
          ref="graphVizRef"
          :graph-data="graphData"
          :loading="loading"
          :layout="currentLayout"
        />
      </div>
    </div>
  </Page>
</template>

<style scoped>
.graph-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}

.selector-bar {
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  align-items: center;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}

.selector-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.selector-item .label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.empty-hint {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

.graph-wrapper {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
</style>
