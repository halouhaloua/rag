<script lang="ts" setup>
import { ref, computed } from 'vue';
import { ElDialog, ElUpload, ElButton, ElMessage } from 'element-plus';
import { updateFileSchemaApi } from '#/api/core/rag';
import type { KnowledgeBaseFile } from '#/api/core/rag';

const props = defineProps<{ kbId: string }>();
const emit = defineEmits<{ updated: [] }>();

const visible = ref(false);
const currentFile = ref<KnowledgeBaseFile | null>(null);
const saving = ref(false);
const mode = ref<'file' | 'edit'>('file');
const pendingFile = ref<File | null>(null);
const fileList = ref<any[]>([]);
const jsonContent = ref('');
const isJsonValid = ref(true);

const exampleSchema = {
  Nodes: ['person', 'location', 'organization', 'event', 'concept'],
  Relations: ['part_of', 'located_in', 'created_by', 'participates_in', 'belongs_to'],
  Attributes: ['name', 'date', 'type', 'description'],
};

const canSubmit = computed(() => {
  if (mode.value === 'file') return pendingFile.value !== null;
  return jsonContent.value.trim() !== '' && isJsonValid.value;
});

function open(file: KnowledgeBaseFile) {
  currentFile.value = file;
  mode.value = 'file';
  jsonContent.value = file.schema_json
    ? JSON.stringify(file.schema_json, null, 2)
    : '';
  isJsonValid.value = true;
  fileList.value = [];
  pendingFile.value = null;
  visible.value = true;
}

function close() {
  visible.value = false;
  fileList.value = [];
  pendingFile.value = null;
  jsonContent.value = '';
  isJsonValid.value = true;
  mode.value = 'file';
}

function handleFileChange(file: any) {
  fileList.value = [file];
  pendingFile.value = file.raw;
}

function validateJson() {
  if (!jsonContent.value.trim()) {
    isJsonValid.value = true;
    return;
  }
  try {
    JSON.parse(jsonContent.value);
    isJsonValid.value = true;
  } catch {
    isJsonValid.value = false;
  }
}

function formatJson() {
  if (!jsonContent.value.trim()) {
    ElMessage.warning('编辑器为空');
    return;
  }
  try {
    const parsed = JSON.parse(jsonContent.value);
    jsonContent.value = JSON.stringify(parsed, null, 2);
    isJsonValid.value = true;
    ElMessage.success('格式化成功');
  } catch {
    ElMessage.error('JSON格式错误，无法格式化');
    isJsonValid.value = false;
  }
}

function clearEditor() {
  jsonContent.value = '';
  isJsonValid.value = true;
}

function loadExample() {
  jsonContent.value = JSON.stringify(exampleSchema, null, 2);
  isJsonValid.value = true;
}

async function handleSave() {
  if (!currentFile.value) return;
  saving.value = true;
  try {
    let schema: Record<string, any>;
    if (mode.value === 'file') {
      if (!pendingFile.value) return;
      const text = await pendingFile.value.text();
      schema = JSON.parse(text);
    } else {
      schema = JSON.parse(jsonContent.value);
    }
    await updateFileSchemaApi(props.kbId, currentFile.value.id, schema);
    ElMessage.success('Schema 更新成功');
    close();
    emit('updated');
  } catch (err: any) {
    if (err instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误，请检查');
    } else {
      ElMessage.error(err.message || '保存失败');
    }
  } finally {
    saving.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="`编辑 Schema - ${currentFile?.filename || ''}`"
    width="600px"
    :close-on-click-modal="false"
    @close="close"
  >
    <div class="schema-desc">
      上传JSON格式的Schema文件，用于约束知识图谱的实体类型。
    </div>

    <div class="example-block">
      <div class="example-title">示例格式：</div>
      <pre class="example-code">{
  "Nodes": ["Person", "Company", "Product"],
  "Relations": ["works_for", "produces"],
  "Attributes": ["name", "date", "description"]
}</pre>
    </div>

    <div class="mode-switch">
      <ElButton
        :type="mode === 'file' ? 'primary' : 'default'"
        @click="mode = 'file'"
      >
        文件上传
      </ElButton>
      <ElButton
        :type="mode === 'edit' ? 'primary' : 'default'"
        @click="mode = 'edit'"
      >
        手动编辑
      </ElButton>
    </div>

    <div v-if="mode === 'file'" class="upload-section">
      <ElUpload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="fileList"
        accept=".json"
        :limit="1"
      >
        <div style="padding:24px;text-align:center">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--el-text-color-secondary)">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
          </svg>
          <p style="font-weight:600;color:var(--el-text-color-primary)">拖拽Schema文件到此处</p>
          <p style="color:var(--el-text-color-secondary)">或 <span style="font-weight:600;color:var(--el-color-primary)">点击上传</span></p>
          <p style="margin-top:8px;font-size:12px;color:var(--el-text-color-secondary)">仅支持 .json 格式文件</p>
        </div>
      </ElUpload>
    </div>

    <div v-else class="edit-section">
      <div class="editor-header">
        <span class="editor-label">Schema编辑器</span>
        <ElButton v-if="!isJsonValid" type="danger" link size="small">
          JSON格式错误
        </ElButton>
      </div>
      <div
        class="json-editor-wrapper"
        :class="{ 'has-error': !isJsonValid }"
      >
        <textarea
          v-model="jsonContent"
          class="json-editor"
          placeholder='请输入JSON格式的Schema，例如：&#10;{&#10;  "Nodes": ["Person", "Company"],&#10;  "Relations": ["works_for"],&#10;  "Attributes": ["name", "date"]&#10;}'
          @input="validateJson"
        />
      </div>
      <div class="editor-toolbar">
        <ElButton link size="small" @click="formatJson">格式化</ElButton>
        <ElButton link size="small" @click="clearEditor">清空</ElButton>
        <ElButton link size="small" @click="loadExample">加载示例</ElButton>
      </div>
    </div>

    <template #footer>
      <ElButton @click="close">取消</ElButton>
      <ElButton
        type="primary"
        :loading="saving"
        :disabled="!canSubmit"
        @click="handleSave"
      >
        {{ saving ? '保存中...' : '保存' }}
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
.schema-desc {
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.example-block {
  padding: 14px;
  margin-bottom: 16px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.example-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.example-code {
  padding: 12px;
  margin: 0;
  overflow-x: auto;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.mode-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.mode-switch .el-button {
  flex: 1;
}

.upload-section {
  margin-bottom: 8px;
}

.edit-section {
  margin-bottom: 8px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.editor-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.json-editor-wrapper {
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  transition: border-color 0.2s;
}

.json-editor-wrapper:focus-within {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
}

.json-editor-wrapper.has-error {
  border-color: var(--el-color-danger);
}

.json-editor-wrapper.has-error:focus-within {
  box-shadow: 0 0 0 2px var(--el-color-danger-light-8);
}

.json-editor {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  resize: vertical;
  outline: none;
  background: var(--el-fill-color-lighter);
  border: none;
}

.json-editor::placeholder {
  color: var(--el-text-color-placeholder);
}

.editor-toolbar {
  display: flex;
  gap: 6px;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.editor-toolbar .el-button {
  color: var(--el-text-color-secondary);
}

.editor-toolbar .el-button:hover {
  color: var(--el-color-primary);
}
</style>
