<script lang="ts" setup>
import { ref, onMounted, watch } from 'vue';
import { Page } from '@vben/common-ui';
import { ElSelect, ElOption, ElButton, ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Trash2 } from '@vben/icons';
import type { KnowledgeBase, KnowledgeBaseFile, ChatConversation } from '#/api/core/rag';
import {
  getKnowledgeBaseListApi,
  getFileListApi,
  createConversationApi,
  getUserConversationsApi,
  getChatHistoryApi,
  deleteConversationApi,
  chatCompletionStream,
  getIRCoTStatusApi,
  setIRCoTEnabledApi,
} from '#/api/core/rag';
import ChatArea from '#/components/rag/ChatArea.vue';
import type { ChatMessageItem } from '#/composables/useChat';

defineOptions({ name: 'QAPage' });

const USER_ID = 'current'; // will be replaced with actual user ID

const kbs = ref<KnowledgeBase[]>([]);
const selectedKbId = ref('');
const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const conversations = ref<ChatConversation[]>([]);
const selectedConvId = ref<string | null>(null);

const messages = ref<ChatMessageItem[]>([]);
const isStreaming = ref(false);
const loadingConv = ref(false);
const ircotEnabled = ref(false);

let msgCounter = 0;

async function loadKbs() {
  const res = await getKnowledgeBaseListApi({ page: 1, pageSize: 200 });
  kbs.value = res.items;
}

async function loadFiles(kbId: string) {
  if (!kbId) { files.value = []; return; }
  const res = await getFileListApi(kbId);
  files.value = res.items.filter((f) => f.has_graph);
}

async function loadConversations() {
  try {
    const res = await getUserConversationsApi(USER_ID, 1, 50);
    conversations.value = res;
  } catch {
    conversations.value = [];
  }
}

async function loadHistory(convId: string) {
  loadingConv.value = true;
  try {
    const history = await getChatHistoryApi(convId);
    messages.value = history.map((m: any, i: number) => ({
      id: `hist_${i}`,
      role: m.role,
      content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content),
      timestamp: new Date(m.sys_create_datetime).getTime(),
    }));
    msgCounter = messages.value.length;
  } catch {
    messages.value = [];
  } finally {
    loadingConv.value = false;
  }
}

async function handleNewConversation() {
  try {
    const conv = await createConversationApi({ user_id: USER_ID, title: '新对话' });
    conversations.value.unshift(conv);
    selectedConvId.value = conv.id;
    messages.value = [];
    msgCounter = 0;
  } catch (err: any) {
    ElMessage.error(err.message || '创建对话失败');
  }
}

async function handleSelectConversation(convId: string) {
  selectedConvId.value = convId;
  await loadHistory(convId);
}

async function handleDeleteConversation(convId: string) {
  try {
    await ElMessageBox.confirm('确定删除此对话？', '删除确认', { type: 'warning' });
    await deleteConversationApi(convId);
    conversations.value = conversations.value.filter((c) => c.id !== convId);
    if (selectedConvId.value === convId) {
      selectedConvId.value = null;
      messages.value = [];
    }
  } catch {
    // cancelled
  }
}

function addUserMessage(text: string) {
  messages.value.push({
    id: `msg_${++msgCounter}`,
    role: 'user',
    content: text,
    timestamp: Date.now(),
  });
}

function addAssistantMessage() {
  const msg: ChatMessageItem = {
    id: `msg_${++msgCounter}`,
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
  };
  messages.value.push(msg);
  return msg;
}

function formatTime(dt: string): string {
  const d = new Date(dt);
  const now = Date.now();
  const diff = now - d.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

function truncateTitle(title: string): string {
  return title.length > 20 ? title.slice(0, 20) + '...' : title;
}

async function handleSend(question: string) {
  if (!selectedFileId.value) {
    ElMessage.warning('请先选择知识库和文件');
    return;
  }

  isStreaming.value = true;
  addUserMessage(question);
  const assistantMsg = addAssistantMessage();
  const answerParts: string[] = [];

  try {
    await chatCompletionStream(
      {
        user_id: USER_ID,
        conversation_id: selectedConvId.value || undefined,
        question,
        model_name: 'qwen',
        file_id: selectedFileId.value,
      },
      {
        onToken: (token) => {
          answerParts.push(token);
          assistantMsg.content += token;
        },
        onMetadata: (data) => {
          assistantMsg.subQuestions = data.sub_questions;
          assistantMsg.retrievedTriples = data.triples;
          assistantMsg.retrievedChunks = data.chunks;
        },
        onReasoningSteps: (data) => {
          assistantMsg.reasoningSteps = data;
        },
        onVisualization: (data) => {
          assistantMsg.visualizationData = data;
        },
        onStatus: (_progress, _message) => {
          // progress updates
        },
        onDone: (data) => {
          isStreaming.value = false;
          selectedConvId.value = data.conversation_id || selectedConvId.value;
          loadConversations();
        },
        onError: (err) => {
          ElMessage.error(err.message || '请求失败');
          isStreaming.value = false;
        },
        onComplete: () => {
          isStreaming.value = false;
        },
      },
    );
  } catch (err: any) {
    ElMessage.error(err.message || '请求失败');
    isStreaming.value = false;
  }
}

function handleIrcotToggle(v: boolean) {
  ircotEnabled.value = v;
  setIRCoTEnabledApi(v).catch(() => {});
}

watch(selectedKbId, (kbId) => {
  selectedFileId.value = '';
  loadFiles(kbId);
});

onMounted(() => {
  loadKbs();
  loadConversations();
  getIRCoTStatusApi().then((cfg) => { ircotEnabled.value = cfg.enable_ircot; }).catch(() => {});
});
</script>

<template>
  <Page>
    <div class="qa-page">
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>对话历史</h3>
          <ElButton :icon="Plus" circle size="small" @click="handleNewConversation" />
        </div>
        <div class="conv-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conv-item"
            :class="{ active: conv.id === selectedConvId }"
            @click="handleSelectConversation(conv.id)"
          >
            <div class="conv-title">{{ truncateTitle(conv.title) }}</div>
            <div class="conv-time">{{ formatTime(conv.sys_create_datetime) }}</div>
            <ElButton
              link
              type="danger"
              size="small"
              class="conv-delete"
              :icon="Trash2"
              @click.stop="handleDeleteConversation(conv.id)"
            />
          </div>
          <div v-if="conversations.length === 0" class="conv-empty">
            暂无对话记录
          </div>
        </div>
      </div>

      <div class="main-area">
        <div class="qa-selector">
          <div class="selector-item">
            <span class="label">知识库：</span>
            <ElSelect
              v-model="selectedKbId"
              placeholder="选择知识库"
              style="width: 200px"
              clearable
            >
              <ElOption
                v-for="kb in kbs"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </ElSelect>
          </div>
          <div class="selector-item">
            <span class="label">文件：</span>
            <ElSelect
              v-model="selectedFileId"
              placeholder="选择已构建图谱的文件"
              style="width: 260px"
              :disabled="!selectedKbId"
            >
              <ElOption
                v-for="f in files"
                :key="f.id"
                :label="f.filename"
                :value="f.id"
              />
            </ElSelect>
          </div>
        </div>

        <div class="qa-chat">
          <ChatArea
            :messages="messages"
            :streaming="isStreaming"
            :ircot-enabled="ircotEnabled"
            placeholder="输入您的问题..."
            @send="handleSend"
            @ircot-toggle="handleIrcotToggle"
          />
        </div>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.qa-page {
  display: flex;
  gap: 12px;
  height: calc(100vh - 140px);
}

.sidebar {
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  width: 240px;
  overflow: hidden;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 15px;
}

.conv-list {
  flex: 1;
  padding: 4px 0;
  overflow-y: auto;
}

.conv-item {
  position: relative;
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 8px 14px;
  cursor: pointer;
  border-left: 3px solid transparent;
}

.conv-item:hover {
  background: var(--el-fill-color-lighter);
}

.conv-item.active {
  background: var(--el-color-primary-light-9);
  border-left-color: var(--el-color-primary);
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  white-space: nowrap;
}

.conv-time {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.conv-delete {
  flex-shrink: 0;
  opacity: 0;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-empty {
  padding: 24px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.main-area {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.qa-selector {
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  padding: 12px 16px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}

.selector-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.selector-item .label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.qa-chat {
  flex: 1;
  min-height: 400px;
  overflow: hidden;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
}
</style>
