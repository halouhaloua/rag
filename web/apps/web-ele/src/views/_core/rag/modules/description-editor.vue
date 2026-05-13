<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { ElDialog, ElForm, ElFormItem, ElInput, ElButton } from 'element-plus';
import { updateKnowledgeBaseApi } from '#/api/core/rag';
import type { KnowledgeBase } from '#/api/core/rag';

const emit = defineEmits<{
  saved: [];
}>();

const visible = ref(false);
const saving = ref(false);
const currentKb = ref<KnowledgeBase | null>(null);
const formData = reactive({ name: '', description: '' });

function open(kb: KnowledgeBase) {
  currentKb.value = kb;
  formData.name = kb.name;
  formData.description = kb.description || '';
  visible.value = true;
}

async function handleSave() {
  if (!currentKb.value) return;
  saving.value = true;
  try {
    await updateKnowledgeBaseApi(currentKb.value.id, { description: formData.description || undefined });
    visible.value = false;
    emit('saved');
  } catch {
    // error handled by request client
  } finally {
    saving.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    title="编辑知识库描述"
    width="500px"
    :close-on-click-modal="false"
  >
    <ElForm label-position="top">
      <ElFormItem label="名称">
        <ElInput v-model="formData.name" disabled />
      </ElFormItem>
      <ElFormItem label="描述">
        <ElInput
          v-model="formData.description"
          type="textarea"
          :rows="4"
          placeholder="请输入知识库描述"
          maxlength="500"
          show-word-limit
        />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" :loading="saving" @click="handleSave">确定</ElButton>
    </template>
  </ElDialog>
</template>
