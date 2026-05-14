<script lang="ts" setup>
import type { ChatMessageItem } from '#/composables/useChat';

import { nextTick, ref, watch } from 'vue';

import { ElButton, ElInput, ElSwitch, ElTag } from 'element-plus';

const props = defineProps<{
  ircotEnabled?: boolean;
  loading?: boolean;
  messages: ChatMessageItem[];
  placeholder?: string;
  streaming?: boolean;
}>();

const emit = defineEmits<{
  ircotToggle: [enabled: boolean];
  send: [question: string];
}>();

const inputText = ref('');
const messagesContainer = ref<HTMLElement | null>(null);
const collapsedSteps = ref<Set<number>>(new Set());
const triplesExpanded = ref<Set<string>>(new Set());
const chunksExpanded = ref<Set<string>>(new Set());
const CHUNK_PREVIEW_LENGTH = 80;

function toggleCollapseStep(idx: number) {
  if (collapsedSteps.value.has(idx)) {
    collapsedSteps.value.delete(idx);
  } else {
    collapsedSteps.value.add(idx);
  }
}

function toggleTriples(key: string) {
  if (triplesExpanded.value.has(key)) {
    triplesExpanded.value.delete(key);
  } else {
    triplesExpanded.value.add(key);
  }
}

function toggleChunks(key: string) {
  if (chunksExpanded.value.has(key)) {
    chunksExpanded.value.delete(key);
  } else {
    chunksExpanded.value.add(key);
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

function handleSend() {
  const text = inputText.value.trim();
  if (!text || props.streaming) return;
  inputText.value = '';
  emit('send', text);
}

function onKeydown(e: Event) {
  const ke = e as KeyboardEvent;
  if (ke.ctrlKey && ke.key === 'Enter') {
    handleSend();
  }
}

function formatTime(timestamp: number): string {
  const d = new Date(timestamp);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

watch(() => props.messages.length, scrollToBottom);

watch(
  () => {
    if (props.messages.length === 0) return '';
    return props.messages[props.messages.length - 1]?.content ?? '';
  },
  scrollToBottom,
);
</script>

<template>
  <div class="chat-area">
    <div ref="messagesContainer" class="messages-container">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
            />
          </svg>
        </div>
        <p>输入问题开始对话</p>
        <div class="quick-questions">
          <el-button
            size="small"
            @click="emit('send', '这个文件的主要内容是什么？')"
          >
            文件内容概述
          </el-button>
          <el-button
            size="small"
            @click="emit('send', '提取文件中的关键实体和关系')"
          >
            提取实体关系
          </el-button>
          <el-button size="small" @click="emit('send', '总结文件的核心观点')">
            核心观点总结
          </el-button>
        </div>
      </div>
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
        <div class="avatar">
          <svg
            v-if="msg.role === 'user'"
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <svg
            v-else
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div class="message-content">
          <div class="bubble">
            <div
              v-if="
                msg.role === 'assistant' &&
                msg.subQuestions &&
                msg.subQuestions.length > 0
              "
              class="metadata-summary"
            >
              <el-tag size="small" type="info">
                {{ msg.subQuestions.length }} 子问题
              </el-tag>
              <el-tag size="small" type="warning">
                {{ msg.retrievedTriples?.length || 0 }} 三元组
              </el-tag>
              <el-tag size="small" type="success">
                {{ msg.retrievedChunks?.length || 0 }} 文本块
              </el-tag>
            </div>

            <template v-if="msg.role === 'assistant' && msg.reasoningSteps">
              <div class="reasoning-section">
                <div
                  v-for="(step, si) in msg.reasoningSteps.reasoning_steps"
                  :key="`step-${msg.id}-${si}`"
                  class="step-card"
                >
                  <div class="step-header" @click="toggleCollapseStep(si)">
                    <span class="step-icon">
                      <svg
                        v-if="step.type === 'sub_question'"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.3-4.3" />
                      </svg>
                      <svg
                        v-else
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                        <path d="M21 3v5h-5" />
                      </svg>
                    </span>
                    <span class="step-title">
                      {{ step.question || step.type }}
                    </span>
                    <span class="step-toggle">
                      <svg
                        :class="{ rotated: !collapsedSteps.has(si) }"
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path d="m9 18 6-6-6-6" />
                      </svg>
                    </span>
                  </div>
                  <div v-if="!collapsedSteps.has(si)" class="step-body">
                    <div
                      v-if="step.triples && step.triples.length > 0"
                      class="step-section"
                    >
                      <div class="step-section-title">三元组</div>
                      <div
                        v-for="(t, ti) in (triplesExpanded.has(`${msg.id}-${si}`) ? step.triples : step.triples.slice(0, 3))"
                        :key="ti"
                        class="triple-item"
                      >
                        {{ t }}
                      </div>
                      <el-button
                        v-if="step.triples.length > 3"
                        size="small"
                        link
                        @click="toggleTriples(`${msg.id}-${si}`)"
                      >
                        {{ triplesExpanded.has(`${msg.id}-${si}`) ? '收起' : `展开全部 ${step.triples.length} 条三元组` }}
                      </el-button>
                    </div>
                    <div
                      v-if="step.chunk_contents && step.chunk_contents.length > 0"
                      class="step-section"
                    >
                      <div class="step-section-title">文本块</div>
                      <template v-if="chunksExpanded.has(`${msg.id}-${si}`)">
                        <div
                          v-for="(ch, ci) in step.chunk_contents"
                          :key="ci"
                          class="chunk-item"
                        >
                          {{ ch }}
                        </div>
                      </template>
                      <template v-else>
                        <div class="chunk-item-preview">
                          {{ step.chunk_contents[0].slice(0, CHUNK_PREVIEW_LENGTH) }}{{ step.chunk_contents[0].length > CHUNK_PREVIEW_LENGTH ? '...' : '' }}
                        </div>
                      </template>
                      <el-button
                        v-if="step.chunk_contents.length > 1 || (step.chunk_contents[0] && step.chunk_contents[0].length > CHUNK_PREVIEW_LENGTH)"
                        size="small"
                        link
                        @click="toggleChunks(`${msg.id}-${si}`)"
                      >
                        {{ chunksExpanded.has(`${msg.id}-${si}`) ? '收起' : `展开全部 ${step.chunk_contents.length} 条文本块` }}
                      </el-button>
                    </div>
                    <div v-if="step.thought" class="step-section">
                      <div class="step-section-title">推理</div>
                      <div class="thought-text">{{ step.thought }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <div class="text">{{ msg.content }}</div>
          </div>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>
      <div v-if="streaming" class="streaming-indicator">
        <span class="dot-pulse"></span>
        <span>AI 正在思考...</span>
      </div>
    </div>

    <div class="input-area">
      <div class="input-controls">
        <el-switch
          v-if="ircotEnabled !== undefined"
          :model-value="ircotEnabled"
          size="small"
          active-text="IRCoT"
          @update:model-value="(v: string | number | boolean) => emit('ircotToggle', !!v)"
        />
      </div>
      <div class="input-row">
        <el-input
          v-model="inputText"
          :placeholder="placeholder || '输入您的问题 (Ctrl+Enter 发送)'"
          :disabled="streaming"
          type="textarea"
          :rows="2"
          resize="none"
          @keydown="onKeydown"
        />
        <el-button
          type="primary"
          :loading="streaming"
          :disabled="!inputText.trim()"
          @click="handleSend"
        >
          {{ streaming ? '生成中' : '发送' }}
        </el-button>
      </div>
    </div>
    <div class="disclaimer">AI 生成内容仅供参考，可能不准确。</div>
  </div>
</template>

<style scoped>
.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--el-bg-color);
}

.messages-container {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}

.empty-icon {
  margin-bottom: 12px;
  font-size: 48px;
}

.message-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
  font-size: 28px;
}

.bubble {
  max-width: 75%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--el-fill-color-light);
  border-radius: 12px;
}

.user .bubble {
  background: var(--el-color-primary-light-8);
  border-bottom-right-radius: 4px;
}

.assistant .bubble {
  border-bottom-left-radius: 4px;
}

.text {
  overflow-wrap: break-word;
  white-space: pre-wrap;
}

.message-time {
  margin-top: 4px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.user .message-time {
  text-align: right;
}

.metadata-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.reasoning-section {
  margin-bottom: 8px;
}

.step-card {
  margin-bottom: 6px;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.step-header {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 8px 10px;
  font-size: 13px;
  cursor: pointer;
  background: var(--el-fill-color-lighter);
}

.step-header:hover {
  background: var(--el-fill-color);
}

.step-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-toggle {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s;
}

.step-toggle .rotated {
  transform: rotate(90deg);
}

.step-body {
  padding: 8px 10px;
  font-size: 12px;
}

.step-section {
  margin-bottom: 8px;
}

.step-section-title {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
}

.triple-item {
  padding: 2px 6px;
  margin-bottom: 2px;
  font-family: monospace;
  font-size: 11px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.chunk-item {
  padding: 4px 6px;
  margin-bottom: 2px;
  overflow: hidden;
  font-size: 11px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.chunk-item-preview {
  padding: 4px 6px;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.thought-text {
  padding: 4px 6px;
  font-size: 11px;
  font-style: italic;
  background: var(--el-color-warning-light-9);
  border-radius: 4px;
}

.streaming-indicator {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.dot-pulse {
  width: 8px;
  height: 8px;
  background: var(--el-color-primary);
  border-radius: 50%;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.4;
  }

  50% {
    opacity: 1;
  }
}

.disclaimer {
  padding: 4px 16px 8px;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  text-align: center;
}

.input-area {
  padding: 12px 16px 4px;
  background: var(--el-bg-color-overlay);
  border-top: 1px solid var(--el-border-color-lighter);
}

.input-controls {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.input-row {
  display: flex;
  gap: 8px;
}

.input-row .el-input {
  flex: 1;
}
</style>
