<script lang="ts" setup>
import type {
  GraphData,
  KnowledgeBase,
  KnowledgeBaseFile,
} from '#/api/core/rag';
import type { LayoutType } from '#/composables/useGraphLayout';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import {
  getFileListApi,
  getGraphDataApi,
  getKnowledgeBaseListApi,
} from '#/api/core/rag';
import GraphToolbar from '#/components/rag/GraphToolbar.vue';
import GraphVisualization from '#/components/rag/GraphVisualization.vue';
import KbFileSelector from '#/components/rag/KbFileSelector.vue';

defineOptions({ name: 'GraphView' });

const kbs = ref<KnowledgeBase[]>([]);
const selectedKbId = ref('');
const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const graphData = ref<GraphData | null>(null);
const loading = ref(false);
const currentLayout = ref<LayoutType>('force');
const showSelector = ref(false);

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

function onKbFileSelect(kbId: string, fileId: string) {
  selectedKbId.value = kbId;
  selectedFileId.value = fileId;
}

onMounted(() => {
  loadKbs();
});
</script>

<template>
  <Page auto-content-height>
    <div class="graph-view">
      <div class="graph-wrapper">
        <GraphToolbar
          :current-layout="currentLayout"
          :kb-name="selectedKbName"
          :file-label="selectedFileName"
          :loading="loading"
          @open-selector="showSelector = true"
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
    <KbFileSelector
      v-model="showSelector"
      :kbs="kbs"
      :selected-kb-id="selectedKbId"
      :selected-file-id="selectedFileId"
      @select="onKbFileSelect"
    />
  </Page>
</template>

<style scoped>
.graph-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.graph-wrapper {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
</style>
