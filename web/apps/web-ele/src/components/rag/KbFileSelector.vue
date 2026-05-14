<script lang="ts" setup>
import type { KnowledgeBase, KnowledgeBaseFile } from '#/api/core/rag';

import { ref, watch } from 'vue';

import { ElButton, ElDialog, ElEmpty } from 'element-plus';

import { getFileListApi } from '#/api/core/rag';

const props = defineProps<{
  kbs: KnowledgeBase[];
  modelValue: boolean;
  selectedFileId: string;
  selectedKbId: string;
}>();

const emit = defineEmits<{
  select: [kbId: string, fileId: string];
  'update:modelValue': [value: boolean];
}>();

const tempKbId = ref(props.selectedKbId);
const tempFileId = ref(props.selectedFileId);
const files = ref<KnowledgeBaseFile[]>([]);
const loadingFiles = ref(false);

watch(
  () => props.modelValue,
  async (v) => {
    if (v) {
      tempKbId.value = props.selectedKbId;
      tempFileId.value = props.selectedFileId;
      if (props.selectedKbId) {
        await loadFiles(props.selectedKbId);
      }
    }
  },
);

async function loadFiles(kbId: string) {
  loadingFiles.value = true;
  try {
    const res = await getFileListApi(kbId);
    files.value = res.items.filter((f) => f.has_graph);
  } catch {
    files.value = [];
  } finally {
    loadingFiles.value = false;
  }
}

async function selectKb(kbId: string) {
  tempKbId.value = kbId;
  tempFileId.value = '';
  await loadFiles(kbId);
}

function selectFile(fileId: string) {
  tempFileId.value = fileId;
}

function handleConfirm() {
  if (tempKbId.value && tempFileId.value) {
    emit('select', tempKbId.value, tempFileId.value);
  }
  emit('update:modelValue', false);
}

function handleCancel() {
  emit('update:modelValue', false);
}
</script>

<template>
  <ElDialog
    class="kb-file-selector-dialog"
    :model-value="modelValue"
    title="选择知识库和文件"
    width="760px"
    @close="handleCancel"
  >
    <div class="selector-body">
      <div class="col">
        <div class="col-title">知识库</div>
        <div class="col-list">
          <div
            v-for="kb in kbs"
            :key="kb.id"
            class="col-item"
            :class="[{ active: tempKbId === kb.id }]"
            @click="selectKb(kb.id)"
          >
            <span class="item-name">{{ kb.name }}</span>
            <span class="item-meta">{{ kb.file_count }} 文件</span>
          </div>
          <ElEmpty v-if="kbs.length === 0" description="暂无知识库" />
        </div>
      </div>
      <div class="col">
        <div class="col-title">文件（已构建图谱）</div>
        <div class="col-list">
          <div
            v-for="f in files"
            :key="f.id"
            class="col-item"
            :class="[{ active: tempFileId === f.id }]"
            @click="selectFile(f.id)"
          >
            <span class="item-name">{{ f.filename }}</span>
          </div>
          <ElEmpty v-if="!tempKbId" description="请先选择知识库" />
          <ElEmpty v-else-if="loadingFiles" description="加载中..." />
          <ElEmpty
            v-else-if="files.length === 0"
            description="该知识库无已构建图谱的文件"
          />
        </div>
      </div>
    </div>
    <template #footer>
      <ElButton @click="handleCancel">取消</ElButton>
      <ElButton
        type="primary"
        :disabled="!tempKbId || !tempFileId"
        @click="handleConfirm"
      >
        确认
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
.kb-file-selector-dialog :deep(.el-dialog) {
  border-radius: 24px;
}

.kb-file-selector-dialog :deep(.el-dialog__header) {
  padding: 22px 24px 10px;
}

.kb-file-selector-dialog :deep(.el-dialog__body) {
  padding: 8px 24px 18px;
}

.kb-file-selector-dialog :deep(.el-dialog__footer) {
  padding: 0 24px 24px;
}

.selector-body {
  display: flex;
  gap: 16px;
  height: 360px;
}

.col {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.col-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.col-list {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 18px;
}

.col-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.15s;
}

.col-item:last-child {
  border-bottom: none;
}

.col-item:hover {
  background: var(--el-color-primary-light-9);
}

.col-item.active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-left: 3px solid var(--el-color-primary);
}

.item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  white-space: nowrap;
}

.item-meta {
  flex-shrink: 0;
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
</style>
