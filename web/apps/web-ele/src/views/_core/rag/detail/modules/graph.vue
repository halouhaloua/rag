<script lang="ts" setup>
import type { GraphData, KnowledgeBaseFile } from '#/api/core/rag';
import type { LayoutType } from '#/composables/useGraphLayout';

import { computed, onMounted, ref, watch } from 'vue';

import { ElMessage, ElOption, ElSelect } from 'element-plus';

import { getFileListApi, getGraphDataApi } from '#/api/core/rag';
import GraphToolbar from '#/components/rag/GraphToolbar.vue';
import GraphVisualization from '#/components/rag/GraphVisualization.vue';

const props = defineProps<{ kbId: string }>();

const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const graphData = ref<GraphData | null>(null);
const loading = ref(false);
const currentLayout = ref<LayoutType>('force');

const selectedFileName = computed(
  () => files.value.find((f) => f.id === selectedFileId.value)?.filename || '',
);

async function loadFiles() {
  const res = await getFileListApi(props.kbId);
  files.value = res.items.filter((f) => f.has_graph);
  if (files.value.length > 0 && !selectedFileId.value) {
    selectedFileId.value = files.value[0]!.id;
  }
}

async function loadGraph(fileId: string) {
  if (!fileId) return;
  loading.value = true;
  try {
    const res = await getGraphDataApi(props.kbId, fileId);
    graphData.value = res;
  } catch (error: any) {
    ElMessage.error(error.message || '加载图谱失败');
    graphData.value = null;
  } finally {
    loading.value = false;
  }
}

watch(selectedFileId, (fileId) => {
  if (fileId) loadGraph(fileId);
});

function onRefresh() {
  if (selectedFileId.value) {
    loadGraph(selectedFileId.value);
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
  loadFiles();
});
</script>

<template>
  <div class="graph-tab">
    <div class="file-selector">
      <span class="label">选择文件：</span>
      <ElSelect
        v-model="selectedFileId"
        placeholder="选择已构建图谱的文件"
        style="width: 280px"
        size="small"
      >
        <ElOption
          v-for="f in files"
          :key="f.id"
          :label="f.filename"
          :value="f.id"
        />
      </ElSelect>
      <span v-if="files.length === 0" class="no-data-hint">
        暂无已构建图谱的文件
      </span>
    </div>

    <div class="graph-wrapper">
      <GraphToolbar
        :current-layout="currentLayout"
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
</template>

<style scoped>
.graph-tab {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 220px);
  min-height: 500px;
  padding: 8px 0;
}

.file-selector {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.file-selector .label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.no-data-hint {
  margin-left: 12px;
  font-size: 13px;
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
