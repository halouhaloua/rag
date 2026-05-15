<script lang="ts" setup>
import type { ChatMessageItem } from '#/composables/useChat';

import { ref, watch } from 'vue';

import { ElButton, ElInput, ElTag } from 'element-plus';
import { marked } from 'marked';

const props = defineProps<{
  kbFileLabel?: string;
  ircotEnabled?: boolean;
  loading?: boolean;
  messages: ChatMessageItem[];
  placeholder?: string;
  streaming?: boolean;
}>();

const emit = defineEmits<{
  ircotToggle: [enabled: boolean];
  openSelector: [];
  send: [question: string];
}>();

const inputText = ref('');
const messagesContainer = ref<HTMLElement | null>(null);
const collapsedSteps = ref<Set<string>>(new Set());
const triplesExpanded = ref<Set<string>>(new Set());
const chunksExpanded = ref<Set<string>>(new Set());
const CHUNK_PREVIEW_LENGTH = 80;

function toggleCollapseStep(id: string, idx: number) {
  const key = `${id}-${idx}`;
  if (collapsedSteps.value.has(key)) {
    collapsedSteps.value.delete(key);
  } else {
    collapsedSteps.value.add(key);
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
  const el = messagesContainer.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

function handleSend() {
  const text = inputText.value.trim();
  if (!text || props.streaming) return;
  inputText.value = '';
  emit('send', text);
}

function renderMarkdown(content: string): string {
  if (!content) return '';
  return marked.parse(content, { breaks: true }) as string;
}

function onKeydown(e: Event) {
  const ke = e as KeyboardEvent;
  if (ke.ctrlKey && ke.key === 'Enter') {
    handleSend();
  }
}

watch(
  () => props.messages[props.messages.length - 1],
  scrollToBottom,
  { flush: 'post', deep: true },
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
        <template v-if="msg.role === 'user'">
          <div class="message-content">
            <div class="bubble user-bubble">
              <div class="text">{{ msg.content }}</div>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="message-content">
            <div
              v-if="msg.subQuestions && msg.subQuestions.length > 0"
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

            <template v-if="msg.reasoningSteps">
              <div class="reasoning-section">
                <div
                  v-for="(step, si) in msg.reasoningSteps.reasoning_steps"
                  :key="`step-${msg.id}-${si}`"
                  class="step-card"
                >
                  <div class="step-header" @click="toggleCollapseStep(msg.id, si)">
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
                        :class="{ rotated: !collapsedSteps.has(`${msg.id}-${si}`) }"
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
                  <div v-if="!collapsedSteps.has(`${msg.id}-${si}`)" class="step-body">
                    <div
                      v-if="step.triples && step.triples.length > 0"
                      class="step-section"
                    >
                      <div class="step-section-title">三元组</div>
                      <div
                        v-for="(t, ti) in (triplesExpanded.has(`${msg.id}-${si}`) ? step.triples : step.triples.slice(0, 2))"
                        :key="ti"
                        class="triple-item"
                      >
                        {{ t }}
                      </div>
                      <el-button
                        v-if="step.triples.length > 2"
                        class="toggle-inline-button"
                        :class="{ expanded: triplesExpanded.has(`${msg.id}-${si}`) }"
                        size="small"
                        @click="toggleTriples(`${msg.id}-${si}`)"
                      >
                        {{ triplesExpanded.has(`${msg.id}-${si}`) ? '收起' : '展开三元组' }}
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
                        class="toggle-inline-button"
                        :class="{ expanded: chunksExpanded.has(`${msg.id}-${si}`) }"
                        size="small"
                        @click="toggleChunks(`${msg.id}-${si}`)"
                      >
                        {{ chunksExpanded.has(`${msg.id}-${si}`) ? '收起' : '展开文本块' }}
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

            <div class="md-content" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </template>
      </div>
      <div v-if="streaming" class="streaming-indicator">
        <span class="dot-pulse"></span>
        <span>AI 正在思考...</span>
      </div>
    </div>

    <div class="input-area">
      <div class="input-shell">
        <el-input
          v-model="inputText"
          :placeholder="placeholder || '输入您的问题，Ctrl+Enter 发送'"
          :disabled="streaming"
          type="textarea"
          :rows="2"
          resize="none"
          @keydown="onKeydown"
        />
        <div class="input-footer">
          <div class="footer-actions">
            <el-button class="selector-button" @click="emit('openSelector')">
              <span class="selector-button-label">{{ kbFileLabel || '选择知识库 / 文件' }}</span>
            </el-button>
            <el-button
              v-if="ircotEnabled !== undefined"
              class="mode-button"
              :class="{ active: ircotEnabled }"
              @click="emit('ircotToggle', !ircotEnabled)"
            >
              IRCoT
            </el-button>
          </div>
          <el-button
            type="primary"
            circle
            class="send-button"
            :disabled="!inputText.trim()"
            @click="handleSend"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M22 2 11 13" />
              <path d="M22 2 15 22 11 13 2 9 22 2z" />
            </svg>
          </el-button>
        </div>
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
  padding: 16px 10%;
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
  margin-bottom: 16px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-content {
  min-width: 0;
}

.user .message-content {
  display: flex;
  width: 100%;
  justify-content: flex-end;
  margin-left: auto;
}

.bubble {
  width: fit-content;
  max-width: 100%;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--el-fill-color-light);
  border-radius: 12px;
}

.user-bubble {
  background: var(--el-color-primary-light-8);
  border-bottom-right-radius: 4px;
  margin-left: auto;
  max-width: min(80%, 100%);
}

.assistant .message-content {
  padding: 4px 0;
}

.text {
  max-width: 100%;
  overflow-wrap: break-word;
  word-break: normal;
  white-space: pre-wrap;
}

.md-content {
  width: fit-content;
  max-width: 100%;
  padding: 0 4px;
  font-size: 14px;
  line-height: 1.75;
  overflow-wrap: break-word;
}

.md-content :deep(p) {
  margin: 0.5em 0;
}

.md-content :deep(pre) {
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}

.md-content :deep(code) {
  padding: 2px 6px;
  font-family: monospace;
  font-size: 13px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.md-content :deep(pre code) {
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.md-content :deep(ul),
.md-content :deep(ol) {
  padding-left: 20px;
  margin: 0.5em 0;
}

.md-content :deep(li) {
  margin: 0.25em 0;
}

.md-content :deep(blockquote) {
  margin: 0.5em 0;
  padding: 4px 12px;
  color: var(--el-text-color-secondary);
  border-left: 3px solid var(--el-border-color);
}

.md-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.md-content :deep(th),
.md-content :deep(td) {
  padding: 6px 12px;
  text-align: left;
  border: 1px solid var(--el-border-color-lighter);
}

.md-content :deep(th) {
  font-weight: 600;
  background: var(--el-fill-color-lighter);
}

.md-content :deep(a) {
  color: var(--el-color-primary);
}

.md-content :deep(strong) {
  font-weight: 600;
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3) {
  margin: 1em 0 0.5em;
  font-weight: 600;
}

.md-content :deep(h1) { font-size: 1.3em; }
.md-content :deep(h2) { font-size: 1.15em; }
.md-content :deep(h3) { font-size: 1.05em; }

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
  margin-bottom: 8px;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.step-header {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 44px;
  padding: 10px 14px;
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
  line-height: 1.4;
  white-space: nowrap;
}

.step-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 10px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s;
}

.step-toggle .rotated {
  transform: rotate(90deg);
}

.step-body {
  padding: 12px 14px 10px;
  font-size: 12px;
}

.step-section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
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
  padding: 6px 10px;
  margin-bottom: 4px;
  font-family: monospace;
  font-size: 12px;
  background: var(--el-fill-color-lighter);
  border-left: 3px solid var(--el-color-primary-light-5);
  border-radius: 4px;
}

.chunk-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.5;
  background: var(--el-fill-color-lighter);
  border-left: 3px solid var(--el-color-success-light-5);
  border-radius: 4px;
}

.chunk-item-preview {
  padding: 8px 10px;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  background: var(--el-fill-color-lighter);
  border-left: 3px solid var(--el-color-success-light-5);
  border-radius: 4px;
}

.thought-text {
  padding: 4px 6px;
  font-size: 11px;
  font-style: italic;
  background: var(--el-color-warning-light-9);
  border-radius: 4px;
}

button.toggle-inline-button {
  min-width: 104px;
  flex-shrink: 0;
  padding: 0 10px;
  margin-top: 4px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 999px;
}

button.toggle-inline-button.expanded {
  max-width: 80%;
}

button.toggle-inline-button:hover {
  background: var(--el-color-primary-light-8);
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
  width: 80%;
  margin: 0 auto;
  padding: 4px 0 8px;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  text-align: center;
}

.input-area {
  display: flex;
  justify-content: center;
  padding: 8px 0;
  background: var(--el-bg-color-overlay);
}

.input-shell {
  width: 80%;
  max-width: 80%;
  padding: 8px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 16px;
  box-shadow: 0 10px 24px rgb(15 23 42 / 6%);
}

.input-shell :deep(.el-textarea__inner) {
  min-height: 48px !important;
  max-height: 120px;
  padding: 2px 4px;
  background: transparent;
  border: none;
  box-shadow: none;
}

.input-shell :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.footer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.selector-button,
.mode-button {
  height: 36px;
  padding: 0 14px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border-color: transparent;
  border-radius: 999px;
}

.selector-button {
  max-width: 320px;
}

.selector-button-label {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mode-button.active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}

.send-button {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
}

.selector-button,
.mode-button {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border-color: transparent;
  border-radius: 999px;
}

@media (max-width: 768px) {
  .input-footer {
    align-items: stretch;
  }

  .footer-actions {
    flex: 1;
  }

  .selector-button {
    max-width: none;
    flex: 1;
  }
}
</style>
