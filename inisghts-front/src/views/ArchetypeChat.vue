<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { 
  PaperAirplaneIcon, 
  QuestionMarkCircleIcon,
  UserGroupIcon,
  InformationCircleIcon,
  ShieldCheckIcon,
  ChartBarIcon
} from '@heroicons/vue/24/outline'
import apiClient from '@/services/axiosInstance'
import { marked } from 'marked'

// Define an interface for the archetype structure we expect from the API
interface Archetype {
  id: string;
  name: string;
  avatar: string;
  description: string; // Or general_description, ensure consistency with backend
  // Add other fields if your API returns them and you need them for display
  pain_points?: string[];
  fears_and_concerns?: string[]; // Note: your backend uses fears_concerns, might need to align
  objections?: string[];
  goals_and_objectives?: string[];
  expected_benefits?: string[];
  values?: string[];
  social_behavior?: string;
  influence_factors?: string[];
  internal_narrative?: string;
}

const fetchedArchetypes = ref<Archetype[]>([])
const selectedArchetypeId = ref<string | null>(null) // Store only the ID
const messageInput = ref('')
const isLoadingArchetypes = ref(true)
const chatError = ref<string | null>(null)

const messages = ref<Array<{
  id: number | string;
  archetype?: string | null; // Archetype ID
  content: string;
  type: 'sent' | 'received' | 'error' | 'info';
  timestamp: string;
}>>([])

const selectedArchetypeDetails = computed<Archetype | undefined>(() => {
  return fetchedArchetypes.value.find(a => a.id === selectedArchetypeId.value)
})

const initializeChatWithArchetype = (archetype: Archetype | undefined) => {
  if (archetype) {
    messages.value = [
      {
        id: Date.now(),
        archetype: archetype.id,
        content: `Hi! I'm ${archetype.name}. ${archetype.description || 'I can help you understand my perspective.'} How can I assist you today?`,
        type: 'received',
        timestamp: new Date().toISOString()
      }
    ]
  } else {
    messages.value = [{
      id: Date.now(),
      type: 'info',
      content: 'Please select an archetype to start chatting.',
      timestamp: new Date().toISOString()
    }]
  }
}

onMounted(async () => {
  isLoadingArchetypes.value = true
  chatError.value = null
  try {
    const response = await apiClient.get<Archetype[]>('/archetypes')
    fetchedArchetypes.value = response.data
    if (fetchedArchetypes.value.length > 0) {
      // Automatically select the first archetype
      selectedArchetypeId.value = fetchedArchetypes.value[0].id
      initializeChatWithArchetype(selectedArchetypeDetails.value)
    } else {
      chatError.value = "No archetypes found for your brand. Please generate them first."
       messages.value = [{
        id: Date.now(),
        type: 'info',
        content: chatError.value,
        timestamp: new Date().toISOString()
      }]
    }
  } catch (error) {
    console.error('Failed to fetch archetypes:', error)
    chatError.value = 'Failed to load archetypes. Please try again later.'
     messages.value = [{
        id: Date.now(),
        type: 'error',
        content: chatError.value,
        timestamp: new Date().toISOString()
      }]
  } finally {
    isLoadingArchetypes.value = false
  }
})

const updateSelectedArchetype = (archetypeId: string) => {
  selectedArchetypeId.value = archetypeId
  initializeChatWithArchetype(selectedArchetypeDetails.value)
}

const sendMessage = async () => {
  if (!messageInput.value.trim() || !selectedArchetypeId.value) return

  const userMessageContent = messageInput.value
  messages.value.push({
    id: Date.now(),
    content: userMessageContent,
    type: 'sent',
    timestamp: new Date().toISOString()
  })

  const currentMessageId = Date.now()
  messageInput.value = ''
  
  // Optional: Add a temporary loading message
  const loadingMessageId = `${currentMessageId}_loading`;
  messages.value.push({ 
    id: loadingMessageId, 
    archetype: selectedArchetypeId.value, 
    type: 'received', 
    content: 'Thinking...', 
    timestamp: new Date().toISOString() 
  });
  await nextTick(); // Ensure loading message is rendered

  try {
    const historyForAPI = messages.value
      .filter(m => (m.type === 'sent' || m.type === 'received') && m.id !== loadingMessageId)
      .slice(0, -1) // Exclude the message just added by the user and the loading message
      .map(m => ({
        role: m.type === 'sent' ? 'user' : 'assistant',
        content: m.content
      }))

    const response = await apiClient.post(
      `/archetype-chat/${selectedArchetypeId.value}/message`, 
      {
        message: userMessageContent,
        history: historyForAPI
      }
    )
    
    // Remove loading message
    const loadingMsgIndex = messages.value.findIndex(m => m.id === loadingMessageId);
    if (loadingMsgIndex !== -1) messages.value.splice(loadingMsgIndex, 1);

    if (response.data && response.data.response) {
      messages.value.push({
        id: currentMessageId + 1,
        archetype: selectedArchetypeId.value,
        content: response.data.response,
        type: 'received',
        timestamp: new Date().toISOString()
      })
    } else {
      messages.value.push({
        id: currentMessageId + 1,
        archetype: selectedArchetypeId.value,
        content: 'Sorry, I encountered an issue processing your request. The response was not as expected.',
        type: 'error',
        timestamp: new Date().toISOString()
      })
    }
  } catch (error: any) {
    console.error('Error sending message to archetype chat API:', error)
    
    const loadingMsgIndex = messages.value.findIndex(m => m.id === loadingMessageId);
    if (loadingMsgIndex !== -1) messages.value.splice(loadingMsgIndex, 1);
    
    let errorMessage = 'There was an error connecting. Please check your connection or try again later.'
    if (error.response && error.response.data && error.response.data.detail) {
      errorMessage = error.response.data.detail;
    }
    messages.value.push({
      id: currentMessageId + 1,
      archetype: selectedArchetypeId.value,
      content: errorMessage,
      type: 'error',
      timestamp: new Date().toISOString()
    })
  }
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const parsedMessageContent = (content: string) => {
  return marked(content);
};
</script>

<template>
  <div class="space-y-8">
    <!-- Title with tooltip -->
    <div class="flex items-center space-x-2">
      <h1 class="text-2xl font-display font-bold text-text-primary">Archetype Chat</h1>
      <div class="group relative">
        <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
        <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
          <p class="text-sm text-text-secondary">
            Have a conversation with different customer archetypes to better understand their perspectives, preferences, and decision-making processes.
          </p>
        </div>
      </div>
    </div>

    <div v-if="isLoadingArchetypes" class="text-center py-10">
      <p class="text-text-secondary">Loading archetypes...</p>
      <!-- You can add a spinner here -->
    </div>
    <div v-else-if="chatError && !fetchedArchetypes.length" class="bg-red-50 border-l-4 border-red-400 p-4 rounded-md">
      <div class="flex">
        <div class="flex-shrink-0">
          <InformationCircleIcon class="h-5 w-5 text-red-400" aria-hidden="true" />
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{{ chatError }}</p>
        </div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-4 gap-8">
      <!-- Archetype Selection -->
      <div class="space-y-6">
        <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
          <h2 class="text-lg font-display font-semibold text-text-primary mb-4 flex items-center">
            <UserGroupIcon class="h-5 w-5 mr-2 text-primary" />
            Select Archetype
          </h2>
          <div v-if="fetchedArchetypes.length === 0" class="text-sm text-text-secondary">
            No archetypes available for this brand. You might need to generate them first.
          </div>
          <div v-else class="space-y-3">
            <button
              v-for="archetype in fetchedArchetypes"
              :key="archetype.id"
              @click="updateSelectedArchetype(archetype.id)"
              class="w-full p-3 rounded-xl border transition-all duration-300 flex items-center space-x-3"
              :class="[
                selectedArchetypeId === archetype.id
                  ? 'border-primary shadow-sm ring-1 ring-primary/20 bg-gradient-to-r from-blue-50 to-indigo-50'
                  : 'border-border hover:border-primary/50 hover:shadow-sm'
              ]"
            >
              <img :src="archetype.avatar" :alt="archetype.name" class="w-10 h-10 rounded-lg" />
              <span class="font-medium text-text-primary">{{ archetype.name }}</span>
            </button>
          </div>
        </div>

        <!-- Disclaimer Card -->
        <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
          <div class="flex items-center space-x-2 mb-4">
            <InformationCircleIcon class="h-6 w-6 text-primary" />
            <h3 class="font-display font-semibold text-text-primary">Important Notice</h3>
          </div>
          <div class="space-y-4">
            <div class="flex items-start space-x-4 pb-4 border-b border-border">
              <ShieldCheckIcon class="h-8 w-8 flex-shrink-0 text-emerald-500" />
              <p class="text-sm text-text-secondary">
                This feature provides simulated conversations based on our data-driven customer archetypes. 
              </p>
            </div>
            <div class="flex items-start space-x-4">
              <ChartBarIcon class="h-8 w-8 flex-shrink-0 text-blue-500" />
              <p class="text-sm text-text-secondary">
                Use these conversations to explore customer perspectives and spark ideas, but always validate them before acting.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Chat Interface -->
      <div class="lg:col-span-3 bg-white rounded-2xl shadow-sm border border-border flex flex-col h-[600px]">
        <!-- Chat Header -->
        <div v-if="selectedArchetypeDetails" class="p-4 border-b border-border flex items-center space-x-3">
          <img 
            :src="selectedArchetypeDetails.avatar" 
            :alt="selectedArchetypeDetails.name"
            class="w-10 h-10 rounded-lg" 
          />
          <div>
            <h3 class="font-medium text-text-primary">{{ selectedArchetypeDetails.name }}</h3>
            <p class="text-sm text-text-secondary">Online</p>
          </div>
        </div>
         <div v-else class="p-4 border-b border-border flex items-center space-x-3">
            <UserGroupIcon class="w-10 h-10 rounded-lg text-gray-400 p-1 border border-gray-300" />
             <div>
                <h3 class="font-medium text-text-secondary">No Archetype Selected</h3>
                 <p class="text-sm text-text-secondary">Select an archetype to begin</p>
            </div>
        </div>


        <!-- Chat Messages -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div v-for="message in messages" 
               :key="message.id"
               class="flex"
               :class="message.type === 'sent' ? 'justify-end' : 'justify-start'">
            <div class="flex items-end space-x-2" 
                 :class="message.type === 'sent' ? 'flex-row-reverse space-x-reverse' : ''">
              <img v-if="message.type === 'received' && message.archetype && fetchedArchetypes.find(a => a.id === message.archetype)"
                   :src="fetchedArchetypes.find(a => a.id === message.archetype)?.avatar"
                   class="w-8 h-8 rounded-lg" />
              <div>
                <div class="max-w-md rounded-2xl px-4 py-2 shadow-sm"
                     :class="[
                       message.type === 'sent' 
                         ? 'bg-gradient-to-r from-blue-400 to-indigo-500 text-white' 
                         : 'bg-surface border border-border',
                       message.type === 'error' ? 'bg-red-100 border-red-300' : '',
                       message.type === 'info' ? 'bg-blue-50 border-blue-300' : ''
                     ]">
                  <div
                    v-html="parsedMessageContent(message.content)"
                    :class="[
                      'prose prose-sm max-w-none',
                      message.type === 'sent' ? 'text-white prose-strong:text-white prose-a:text-white' : 'text-text-primary',
                      message.type === 'error' ? 'text-red-700' : '',
                      message.type === 'info' ? 'text-blue-700' : ''
                    ]"
                  ></div>
                </div>
                <p class="text-xs text-text-secondary mt-1" 
                   :class="message.type === 'sent' ? 'text-right' : ''">
                  {{ formatTime(message.timestamp) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Message Input -->
        <div class="p-4 border-t border-border">
          <form @submit.prevent="sendMessage" class="flex items-center space-x-4">
            <input
              v-model="messageInput"
              type="text"
              placeholder="Type your message..."
              class="flex-1 rounded-xl border-border focus:border-primary-light focus:ring focus:ring-primary/20 py-2 px-4"
              :disabled="!selectedArchetypeId || isLoadingArchetypes || (chatError && !fetchedArchetypes.length)"
            />
            <button
              type="submit"
              class="px-4 py-2 bg-gradient-to-r from-blue-400 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 text-white rounded-xl transition-all duration-300 flex items-center space-x-2 disabled:opacity-50"
              :disabled="!selectedArchetypeId || isLoadingArchetypes || !messageInput.trim() || (chatError && !fetchedArchetypes.length)"
            >
              <span>Send</span>
              <PaperAirplaneIcon class="h-5 w-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>