<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { ElDialog, ElForm, ElFormItem, ElInput, ElButton, ElMessage } from 'element-plus';
import type { KnowledgeBase } from '#/api/core/rag';

const emit = defineEmits<{
  save: [data: { name: string; description?: string }, editId?: string];
}>();

const visible = ref(false);
const editId = ref<string | undefined>();
const formData = reactive({
  name: '',
  description: '',
});

function open(row?: KnowledgeBase) {
  if (row) {
    editId.value = row.id;
    formData.name = row.name;
    formData.description = row.description || '';
  } else {
    editId.value = undefined;
    formData.name = '';
    formData.description = '';
  }
  visible.value = true;
}

function handleSave() {
  if (!formData.name.trim()) {
    ElMessage.warning('请输入知识库名称');
    return;
  }
  emit('save', { name: formData.name.trim(), description: formData.description.trim() || undefined }, editId.value);
  visible.value = false;
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="editId ? '编辑知识库' : '创建知识库'"
    width="500px"
    :close-on-click-modal="false"
  >
    <ElForm label-width="80px">
      <ElFormItem label="名称" required>
        <ElInput
          v-model="formData.name"
          placeholder="例如: 高中数学知识库"
          maxlength="200"
          show-word-limit
        />
      </ElFormItem>
      <ElFormItem label="描述">
        <ElInput
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="可选: 知识库描述"
          maxlength="500"
          show-word-limit
        />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" @click="handleSave">保存</ElButton>
    </template>
  </ElDialog>
</template>
