<script lang="ts" setup>
import { ref } from 'vue';
import { ElDialog, ElUpload, ElButton, ElMessage } from 'element-plus';
import { uploadFilesApi } from '#/api/core/rag';

const props = defineProps<{ kbId: string }>();
const emit = defineEmits<{ complete: [] }>();

const visible = ref(false);
const fileList = ref<any[]>([]);
const schemaFile = ref<File | null>(null);
const uploading = ref(false);

function open() {
  visible.value = true;
  fileList.value = [];
  schemaFile.value = null;
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请至少选择一个文件');
    return;
  }
  uploading.value = true;
  try {
    const files = fileList.value.map((f) => f.raw);
    await uploadFilesApi(props.kbId, files, schemaFile.value);
    ElMessage.success(`上传成功 (${files.length} 个文件)`);
    visible.value = false;
    emit('complete');
  } catch (err: any) {
    ElMessage.error(err.message || '上传失败');
  } finally {
    uploading.value = false;
  }
}

function handleSchemaSelect(file: File | undefined) {
  schemaFile.value = file || null;
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    title="上传文件"
    width="560px"
    :close-on-click-modal="false"
  >
    <div class="upload-section">
      <label class="section-label">选择文档文件</label>
      <ElUpload
        v-model:file-list="fileList"
        multiple
        drag
        :auto-upload="false"
        accept=".txt,.pdf,.doc,.docx,.csv,.xls,.xlsx,.md"
      >
        <div class="upload-hint">
          <div class="upload-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </div>
          <div>拖拽文件到此处，或点击选择</div>
          <div class="upload-types">支持: TXT, PDF, DOC, DOCX, CSV, XLS, XLSX, MD</div>
        </div>
      </ElUpload>
    </div>

    <div class="upload-section">
      <label class="section-label">Schema 定义（可选）</label>
      <ElUpload
        :auto-upload="false"
        accept=".json"
        :limit="1"
        :on-change="(f) => handleSchemaSelect(f.raw)"
        :on-remove="() => handleSchemaSelect(undefined)"
      >
        <template #trigger>
          <ElButton>选择 Schema JSON</ElButton>
        </template>
        <template #tip>
          <div class="el-upload__tip">JSON 格式: {"Nodes":[], "Relations":[], "Attributes":[]}</div>
        </template>
      </ElUpload>
    </div>

    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" :loading="uploading" @click="handleUpload">
        {{ uploading ? '上传中...' : '开始上传' }}
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
.upload-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
}

.upload-hint {
  padding: 20px;
  text-align: center;
}

.upload-icon {
  margin-bottom: 8px;
  font-size: 40px;
}

.upload-types {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
