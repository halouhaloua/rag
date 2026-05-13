<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { ElButton, ElMessage, ElMessageBox, ElTag, ElTable, ElTableColumn, ElDialog, ElProgress } from 'element-plus';
import { Plus, Trash2 } from '@vben/icons';
import type { KnowledgeBaseFile } from '#/api/core/rag';
import {
  getFileListApi,
  deleteFileApi,
  reconstructGraphApi,
} from '#/api/core/rag';
import { useGraphProgress } from '#/composables/useGraphProgress';
import UploadDialog from './upload-dialog.vue';
import SchemaEditor from './schema-editor.vue';

const props = defineProps<{ kbId: string }>();

const files = ref<KnowledgeBaseFile[]>([]);
const loading = ref(false);
const constructingId = ref<string | null>(null);
const progressMessage = ref('');
const uploadDialogRef = ref<InstanceType<typeof UploadDialog>>();
const schemaEditorRef = ref<InstanceType<typeof SchemaEditor>>();

const { showProgressDialog, progress, constructWithProgress } = useGraphProgress();

async function loadFiles() {
  loading.value = true;
  try {
    const res = await getFileListApi(props.kbId);
    files.value = res.items;
  } catch (err: any) {
    ElMessage.error(err.message || '加载文件列表失败');
  } finally {
    loading.value = false;
  }
}

async function handleDelete(file: KnowledgeBaseFile) {
  try {
    await ElMessageBox.confirm(
      `确定删除文件「${file.filename}」？图谱数据将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    );
    await deleteFileApi(props.kbId, file.id);
    ElMessage.success('删除成功');
    loadFiles();
  } catch {
    // cancelled
  }
}

async function handleConstructGraph(file: KnowledgeBaseFile) {
  constructingId.value = file.id;

  try {
    if (file.has_graph) {
      // Rebuild: delete old graph first via API, then reconstruct
      await reconstructGraphApi(props.kbId, file.id);
      ElMessage.success('图谱重建成功');
    } else {
      // First-time build with WebSocket progress
      await constructWithProgress(
        props.kbId,
        file.id,
        (msg, _pct) => { progressMessage.value = msg; },
      );
      ElMessage.success('图谱构建成功');
    }
    loadFiles();
  } catch (err: any) {
    ElMessage.error(err.message || '构建失败');
  } finally {
    constructingId.value = null;
    progressMessage.value = '';
  }
}

function handleUploadComplete() {
  loadFiles();
}

function handleEditSchema(file: KnowledgeBaseFile) {
  schemaEditorRef.value?.open(file);
}

onMounted(() => {
  loadFiles();
});
</script>

<template>
  <div class="files-tab">
    <div class="tab-toolbar">
      <ElButton type="primary" :icon="Plus" @click="uploadDialogRef?.open()">
        上传文件
      </ElButton>
    </div>

    <ElTable :data="files" v-loading="loading" stripe border style="width: 100%">
      <ElTableColumn prop="filename" label="文件名" min-width="200" />
      <ElTableColumn prop="file_type" label="类型" width="80" />
      <ElTableColumn prop="file_size" label="大小" width="100">
        <template #default="{ row }">
          <template v-if="row.file_size < 1048576">
            {{ (row.file_size / 1024).toFixed(1) }} KB
          </template>
          <template v-else>
            {{ (row.file_size / 1048576).toFixed(1) }} MB
          </template>
        </template>
      </ElTableColumn>
      <ElTableColumn label="图谱状态" width="120">
        <template #default="{ row }">
          <ElTag :type="row.has_graph ? 'success' : 'info'" size="small">
            {{ row.has_graph ? '已构建' : '未构建' }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <ElButton
            link
            type="primary"
            :loading="constructingId === row.id"
            :disabled="constructingId === row.id"
            @click="handleConstructGraph(row)"
          >
            {{ row.has_graph ? '重建图谱' : '构建图谱' }}
          </ElButton>
          <ElButton
            v-if="row.has_graph"
            link
            type="primary"
            @click="handleEditSchema(row)"
          >
            Schema
          </ElButton>
          <ElButton link type="danger" :icon="Trash2" @click="handleDelete(row)">
            删除
          </ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <UploadDialog
      ref="uploadDialogRef"
      :kb-id="kbId"
      @complete="handleUploadComplete"
    />
    <SchemaEditor ref="schemaEditorRef" :kb-id="kbId" @updated="loadFiles" />

    <!-- Progress Dialog -->
    <ElDialog
      v-model="showProgressDialog"
      title="构建图谱"
      :close-on-click-modal="false"
      :show-close="false"
      width="400px"
    >
      <div style=" padding: 20px;text-align: center">
        <ElProgress
          :percentage="progress"
          :status="progress === 100 ? 'success' : undefined"
          :stroke-width="12"
        />
        <p style="margin-top: 12px; color: var(--el-text-color-secondary)">
          {{ progressMessage || '正在构建图谱...' }}
        </p>
      </div>
    </ElDialog>
  </div>
</template>

<style scoped>
.files-tab {
  padding: 16px 4px;
}

.tab-toolbar {
  margin-bottom: 12px;
}
</style>
