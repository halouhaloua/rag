<script lang="ts" setup>
import type { KnowledgeBase } from '#/api/core/rag';

import { computed } from 'vue';

import {
  Clock,
  Edit,
  Eye,
  FileText,
  List,
  MoreHorizontal,
  RefreshCw,
  Trash2,
  Upload,
} from '@vben/icons';

import {
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElMessage,
  ElMessageBox,
  ElTag,
  ElTooltip,
} from 'element-plus';

import { deleteKnowledgeBaseApi } from '#/api/core/rag';

const props = defineProps<{
  description: string;
  kb: KnowledgeBase;
}>();

const emit = defineEmits<{
  click: [];
  construct: [];
  deleted: [];
  edit: [];
  uploadSchema: [];
  viewGraph: [];
}>();

const statusType = computed(() => {
  if (props.kb.file_count > 0) return 'success';
  return 'info';
});

const statusLabel = computed(() => {
  if (props.kb.file_count > 0) return '已有文件';
  return '待上传文件';
});

async function handleDelete() {
  if (props.kb.kb_type === 'demo') return;
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${props.kb.name}」吗？此操作将同时删除关联的图谱数据，且不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    );
    await deleteKnowledgeBaseApi(props.kb.id);
    ElMessage.success('删除成功');
    emit('deleted');
  } catch {
    // cancelled
  }
}

function handleCommand(command: string) {
  switch (command) {
    case 'construct': {
      emit('construct');
      break;
    }
    case 'upload-schema': {
      emit('uploadSchema');
      break;
    }
    case 'view': {
      emit('viewGraph');
      break;
    }
  }
}
</script>

<template>
  <div class="doc-card" @click="emit('click')">
    <div class="card-header">
      <div class="card-icon">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      </div>
      <div class="card-title-section">
        <h4 class="doc-name">{{ kb.name }}</h4>
        <span class="doc-subtitle">{{
          kb.kb_type === 'demo' ? '系统演示' : '用户创建'
        }}</span>
      </div>
      <div class="card-actions">
        <ElTooltip content="编辑描述" placement="top">
          <ElButton
            circle
            size="small"
            class="action-btn"
            @click="emit('edit')"
          >
            <Edit style="width: 14px; height: 14px" />
          </ElButton>
        </ElTooltip>
        <ElTooltip content="删除" placement="top">
          <ElButton
            circle
            size="small"
            class="action-btn delete-btn"
            :disabled="kb.kb_type === 'demo'"
            @click="handleDelete"
          >
            <Trash2 style="width: 14px; height: 14px" />
          </ElButton>
        </ElTooltip>
        <ElDropdown trigger="click" @command="handleCommand">
          <ElButton circle size="small" class="action-btn">
            <MoreHorizontal style="width: 14px; height: 14px" />
          </ElButton>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem
                command="upload-schema"
                :disabled="kb.kb_type === 'demo'"
                :icon="Upload"
              >
                上传Schema
              </ElDropdownItem>
              <ElDropdownItem
                command="construct"
                :disabled="kb.kb_type === 'demo'"
                :icon="RefreshCw"
              >
                构建图谱
              </ElDropdownItem>
              <ElDropdownItem command="view" :icon="Eye">
                查看图谱
              </ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </div>
    </div>

    <div class="card-description">
      <p v-if="description" class="desc-text">{{ description }}</p>
      <p v-else class="desc-text empty">暂无描述</p>
    </div>

    <div class="card-status-row">
      <ElTag :type="statusType" size="small" effect="light">
        {{ statusLabel }}
      </ElTag>
      <span v-if="kb.kb_type === 'demo'" class="feature-tag demo-tag"
        >示例</span
      >
    </div>

    <div class="card-footer">
      <div class="footer-left">
        <span class="footer-item">
          <FileText style="width: 14px; height: 14px" />
          文件: {{ kb.file_count }}
        </span>
        <!-- <span class="footer-item">
          <List style="width: 14px; height: 14px" />
          分段: {{ kb.file_count * 3 }}
        </span> -->
      </div>
      <div class="footer-right">
        <span class="footer-item time">
          <Clock style="width: 14px; height: 14px" />
          {{ kb.sys_create_datetime?.slice(0, 10) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.doc-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
  background: var(--el-bg-color);
  /* border: 1px solid var(--el-border-color-lighter); */
  border-radius: 12px;
  transition: all 0.25s ease;
}

.doc-card:hover {
  border-color: var(--el-border-color);
  box-shadow: 0 4px 16px rgb(0 0 0 / 6%);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.card-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--el-color-primary);
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.card-title-section {
  flex: 1;
  min-width: 0;
}

.doc-name {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.doc-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.card-actions {
  display: flex;
  flex-shrink: 0;
  gap: 4px;
  align-items: center;
}

.action-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  color: var(--el-text-color-secondary);
  background: transparent;
  border: none;
}

.action-btn:hover {
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-lighter);
}

.action-btn.delete-btn:hover:not(:disabled) {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.card-description {
  min-height: 20px;
}

.desc-text {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-line-clamp: 2;
  font-size: 13px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
  -webkit-box-orient: vertical;
}

.desc-text.empty {
  font-style: italic;
  color: var(--el-text-color-placeholder);
}

.card-status-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.feature-tag {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
}

.demo-tag {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-7);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.footer-left {
  display: flex;
  gap: 16px;
  align-items: center;
}

.footer-right {
  display: flex;
  align-items: center;
}

.footer-item {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.footer-item.time {
  color: var(--el-text-color-placeholder);
}
</style>
