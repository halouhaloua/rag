import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import type { QuestionResult } from '#/api/core/rag';

export const useRagStore = defineStore('rag', () => {
  const questionHistory = ref<QuestionResult[]>([]);
  const selectedKbId = ref<string>('');
  const selectedFileId = ref<string>('');
  const currentConversationId = ref<string | null>(null);

  const lastQuestionResult = computed<QuestionResult | null>(() => {
    if (questionHistory.value.length === 0) return null;
    return questionHistory.value[questionHistory.value.length - 1];
  });

  function pushQuestionResult(result: QuestionResult) {
    questionHistory.value.push(result);
  }

  function setSelectedKb(id: string) {
    selectedKbId.value = id;
  }

  function setSelectedFile(id: string) {
    selectedFileId.value = id;
  }

  function setConversationId(id: string | null) {
    currentConversationId.value = id;
  }

  function clearHistory() {
    questionHistory.value = [];
  }

  return {
    questionHistory,
    selectedKbId,
    selectedFileId,
    currentConversationId,
    lastQuestionResult,
    pushQuestionResult,
    setSelectedKb,
    setSelectedFile,
    setConversationId,
    clearHistory,
  };
});
