<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { ElButton, ElSelect, ElOption, ElMessage } from 'element-plus';
import { getFileListApi, getIRCoTStatusApi, setIRCoTEnabledApi, type KnowledgeBaseFile } from '#/api/core/rag';
import ChatArea from '#/components/rag/ChatArea.vue';
import { useChat } from '#/composables/useChat';

const props = defineProps<{ kbId: string }>();

const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const ircotEnabled = ref(false);

const { messages, isStreaming, sendQuestion, clearMessages } = useChat();

onMounted(() => {
  getIRCoTStatusApi().then((cfg) => {
    ircotEnabled.value = cfg.enable_ircot;
  }).catch(() => {
    ircotEnabled.value = false;
  });
});

function handleIrcotToggle(v: boolean) {
  ircotEnabled.value = v;
  setIRCoTEnabledApi(v).catch(() => {});
}

async function loadFiles() {
  const res = await getFileListApi(props.kbId);
  files.value = res.items.filter((f) => f.has_graph);
  if (files.value.length > 0 && !selectedFileId.value) {
    selectedFileId.value = files.value[0]!.id;
  }
}

function handleSend(question: string) {
  if (!selectedFileId.value) {
    ElMessage.warning('请先选择一个已构建图谱的文件');
    return;
  }
  sendQuestion(props.kbId, selectedFileId.value, question, `tab_${Date.now()}`);
}

onMounted(() => {
  loadFiles();
});
</script>

<template>
  <div class="qa-tab">
    <div class="qa-toolbar">
      <div class="file-selector">
        <span class="label">选择文件：</span>
        <ElSelect
          v-model="selectedFileId"
          placeholder="选择已构建图谱的文件"
          style="width: 300px"
        >
          <ElOption
            v-for="f in files"
            :key="f.id"
            :label="f.filename"
            :value="f.id"
          />
        </ElSelect>
        <span v-if="files.length === 0" class="no-data-hint">
          暂无已构建图谱的文件，请先在「文件管理」中构建图谱
        </span>
      </div>
      <ElButton
        v-if="messages.length > 0"
        size="small"
        text
        @click="clearMessages"
      >
        清空对话
      </ElButton>
    </div>
    <div class="chat-wrapper">
      <ChatArea
        :messages="messages"
        :streaming="isStreaming"
        :ircot-enabled="ircotEnabled"
        @send="handleSend"
        @ircot-toggle="handleIrcotToggle"
      />
    </div>
  </div>
</template>

<style scoped>
.qa-tab {
  display: flex;
  flex-direction: column;
  height: 650px;
  padding: 16px 4px;
}

.qa-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.file-selector {
  display: flex;
  gap: 8px;
  align-items: center;
}

.file-selector .label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.no-data-hint {
  margin-left: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.chat-wrapper {
  flex: 1;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
</style>
