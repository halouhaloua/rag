import { reactive, ref } from 'vue';
import type { QuestionResult } from '#/api/core/rag';
import { askQuestionStream, chatCompletionStream } from '#/api/core/rag';

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  reasoningSteps?: any;
  visualizationData?: any;
  subQuestions?: any[];
  retrievedTriples?: string[];
  retrievedChunks?: string[];
  timestamp: number;
}

export function useChat() {
  const messages = ref<ChatMessageItem[]>([]);
  const isStreaming = ref(false);
  const streamError = ref<string | null>(null);

  let msgCounter = 0;

  function addUserMessage(text: string) {
    messages.value.push(reactive({
      id: `msg_${++msgCounter}`,
      role: 'user' as const,
      content: text,
      timestamp: Date.now(),
    }));
  }

  function addAssistantMessage() {
    const msg = reactive({
      id: `msg_${++msgCounter}`,
      role: 'assistant' as const,
      content: '',
      timestamp: Date.now(),
    }) as ChatMessageItem;
    messages.value.push(msg);
    return msg;
  }

  async function sendQuestion(
    kbId: string,
    fileId: string,
    question: string,
    clientId: string,
  ) {
    streamError.value = null;
    isStreaming.value = true;

    addUserMessage(question);
    const assistantMsg = addAssistantMessage();
    const answerParts: string[] = [];

    try {
      await askQuestionStream(kbId, fileId, question, clientId, {
        onToken: (token) => {
          answerParts.push(token);
          assistantMsg.content += token;
        },
        onReasoningToken: (token) => {
          // stored in reasoning steps
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
        onDone: (data: any) => {
          if (data?.answer && !assistantMsg.content) {
            assistantMsg.content = data.answer;
          }
          isStreaming.value = false;
        },
        onStatus: () => {
          // progress updates
        },
        onError: (err) => {
          streamError.value = err.message;
          isStreaming.value = false;
        },
        onComplete: () => {
          isStreaming.value = false;
        },
      });
    } catch (err: any) {
      streamError.value = err.message || '请求失败';
      isStreaming.value = false;
    }
  }

  function clearMessages() {
    messages.value = [];
    msgCounter = 0;
  }

  return {
    messages,
    isStreaming,
    streamError,
    sendQuestion,
    addUserMessage,
    addAssistantMessage,
    clearMessages,
  };
}

export function useChatCompletion() {
  const messages = ref<ChatMessageItem[]>([]);
  const isStreaming = ref(false);
  const streamError = ref<string | null>(null);
  const currentConversationId = ref<string | null>(null);

  let msgCounter = 0;

  function setConversationId(id: string) {
    currentConversationId.value = id;
  }

  function addUserMessage(text: string) {
    messages.value.push(reactive({
      id: `msg_${++msgCounter}`,
      role: 'user' as const,
      content: text,
      timestamp: Date.now(),
    }));
  }

  function addAssistantMessage() {
    const msg = reactive({
      id: `msg_${++msgCounter}`,
      role: 'assistant' as const,
      content: '',
      timestamp: Date.now(),
    }) as ChatMessageItem;
    messages.value.push(msg);
    return msg;
  }

  function loadHistory(historyMessages: any[]) {
    messages.value = historyMessages.map((m: any) => {
      const msg: ChatMessageItem = {
        id: m.id,
        role: m.role,
        content: '',
        timestamp: new Date(m.sys_create_datetime).getTime(),
      };

      if (m.role === 'assistant') {
        try {
          const parsed =
            typeof m.content === 'string'
              ? JSON.parse(m.content)
              : m.content;
          msg.content = parsed.answer || '';
          msg.subQuestions = parsed.sub_questions;
          msg.retrievedTriples = parsed.retrieved_triples;
          msg.retrievedChunks = parsed.retrieved_chunks;
          if (parsed.reasoning_steps) {
            msg.reasoningSteps = { reasoning_steps: parsed.reasoning_steps };
          }
          msg.visualizationData = parsed.visualization_data;
        } catch {
          msg.content =
            typeof m.content === 'string'
              ? m.content
              : JSON.stringify(m.content);
        }
      } else {
        msg.content =
          typeof m.content === 'string' ? m.content : JSON.stringify(m.content);
      }

      return msg;
    });
    msgCounter = messages.value.length;
  }

  function clearMessages() {
    messages.value = [];
    msgCounter = 0;
  }

  return {
    messages,
    isStreaming,
    streamError,
    currentConversationId,
    setConversationId,
    async sendQuestion(
      _kbId: string,
      fileId: string,
      question: string,
      userId: string,
    ) {
      streamError.value = null;
      isStreaming.value = true;

      addUserMessage(question);
      const assistantMsg = addAssistantMessage();
      const answerParts: string[] = [];

      try {
        await chatCompletionStream(
          {
            user_id: userId,
            conversation_id: currentConversationId.value || undefined,
            question,
            file_id: fileId,
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
            onDone: (data: any) => {
              if (data?.answer && !assistantMsg.content) {
                assistantMsg.content = data.answer;
              }
              isStreaming.value = false;
              currentConversationId.value = data.conversation_id || currentConversationId.value;
            },
            onError: (err) => {
              streamError.value = err.message;
              isStreaming.value = false;
            },
            onComplete: () => {
              isStreaming.value = false;
            },
          },
        );
      } catch (err: any) {
        streamError.value = typeof err === 'string' ? err : (err.message || '请求失败');
        isStreaming.value = false;
      }
    },
    loadHistory,
    addUserMessage,
    addAssistantMessage,
    clearMessages,
  };
}
