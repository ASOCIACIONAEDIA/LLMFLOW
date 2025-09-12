<script setup lang="ts">
import { ref } from 'vue'
import { 
  PaperAirplaneIcon,
  QuestionMarkCircleIcon,
  ChartBarIcon,
  SparklesIcon,
  LightBulbIcon,
  DocumentChartBarIcon,
  ChatBubbleLeftRightIcon,
  BoltIcon,
  ArrowTrendingUpIcon,
  CommandLineIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import apiClient from '@/services/axiosInstance'

const messageInput = ref('')
const isAnalyzing = ref(false)
const showSidebar = ref(window.innerWidth >= 1024)

const toggleSidebar = () => {
  showSidebar.value = !showSidebar.value
}

const features = [
  {
    icon: BoltIcon,
    title: 'Real-time Analysis',
    description: 'Get instant insights from your Brands UGC'
  },
  {
    icon: ChatBubbleLeftRightIcon,
    title: 'Natural Language',
    description: 'Ask questions in your language'
  },
  {
    icon: ChartBarIcon,
    title: 'Quick Insights',
    description: 'Automatic data analysis'
  },
  {
    icon: ArrowTrendingUpIcon,
    title: 'Trend Detection',
    description: 'Identify patterns and trends'
  }
]

const messages = ref([
  {
    id: 1,
    type: 'system',
    content: "Welcome to Chat2Data! I can help you analyze your review data and provide insights. Try asking questions like:",
    suggestions: [
      {
        text: "Compare sentiment trends between different countries",
        icon: ChartBarIcon
      },
      {
        text: "What are the top complaints in negative reviews?",
        icon: ChartBarIcon
      },
      {
        text: "Show me the busiest review periods",
        icon: ChartBarIcon
      },
      {
        text: "Analyze product feedback patterns",
        icon: ChartBarIcon
      }
    ]
  }
])

const sendMessage = async () => {
  if (!messageInput.value.trim()) return

  // Add user message
  messages.value.push({
    id: Date.now(),
    type: 'user',
    content: messageInput.value
  })

  // Clear input
  messageInput.value = ''
  isAnalyzing.value = true

  // Simulate AI response
  setTimeout(() => {
    isAnalyzing.value = false
    messages.value.push({
      id: Date.now() + 1,
      type: 'assistant',
      content: "Based on the analysis of your review data, I found that sentiment has been consistently positive across most regions, with a notable 15% increase in positive reviews over the last quarter. The most frequently mentioned positive aspects are product quality (45%) and customer service (32%).",
      charts: [
        {
          type: 'trend',
          title: 'Sentiment Trend'
        }
      ]
    })
  }, 2000)

  try {
    // Example:
    // const response = await apiClient.post('/chat/send-message', { message: newMessage.value }); // USE apiClient
    // ... handle response ...
  } catch (error) {
    // ... error handling ...
  } finally {
    // ... existing code ...
  }
}

const useSuggestion = (suggestion: { text: string }) => {
  messageInput.value = suggestion.text
  sendMessage()
}
</script>

<template>
  <div class="space-y-8">
    <!-- Title with tooltip -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-display font-bold text-text-primary">Chat2Data</h1>
        <div class="group relative">
          <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
          <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <p class="text-sm text-text-secondary">
              Ask questions about your data in natural language and get instant insights, visualizations, and analysis.
            </p>
          </div>
        </div>
      </div>
      <!-- Mobile Toggle -->
      <button 
        @click="toggleSidebar"
        class="lg:hidden p-2 text-text-secondary hover:text-primary rounded-lg hover:bg-background-lighter">
        <span class="sr-only">Toggle sidebar</span>
        <XMarkIcon v-if="showSidebar" class="h-6 w-6" />
        <CommandLineIcon v-else class="h-6 w-6" />
      </button>
    </div>

    <div class="relative lg:grid lg:grid-cols-4 lg:gap-8">
      <!-- Introduction Card -->
      <div class="lg:block"
           :class="[
             showSidebar ? 'block' : 'hidden',
             'lg:relative fixed inset-0 z-40 lg:z-auto bg-background lg:bg-transparent'
           ]">
        <div class="h-full overflow-y-auto lg:h-auto p-4 lg:p-0">
          <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
            <div class="space-y-6">
              <!-- Header -->
              <div class="flex items-center space-x-3">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 flex items-center justify-center">
                  <CommandLineIcon class="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 class="text-lg font-display font-semibold text-text-primary">Meet Tama</h2>
                  <p class="text-sm text-text-secondary">Your AI Data Assistant</p>
                </div>
              </div>

              <!-- Description -->
              <p class="text-text-secondary">
                Tama is your intelligent assistant that can analyze and interpret your review data in real-time. Ask questions in natural language and get immediate, data-driven insights.
              </p>

              <!-- Features -->
              <div class="space-y-4">
                <div v-for="feature in features" 
                     :key="feature.title"
                     class="flex items-start space-x-3">
                  <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <component :is="feature.icon" class="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <h3 class="text-sm font-medium text-text-primary">{{ feature.title }}</h3>
                    <p class="text-xs text-text-secondary">{{ feature.description }}</p>
                  </div>
                </div>
              </div>

              <!-- Tips -->
              <div class="bg-surface rounded-xl p-4 border border-border">
                <div class="flex items-center space-x-2 mb-3">
                  <LightBulbIcon class="h-5 w-5 text-amber-500" />
                  <h3 class="font-medium text-text-primary">Pro Tips</h3>
                </div>
                <ul class="text-sm text-gray-400 space-y-2">
                  <li>• Be specific with your questions</li>
                  <li>• Ask about trends and patterns</li>
                  <li>• Compare different time periods</li>
                  <li>• Ask for Country or source details</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Backdrop -->
      <div v-if="showSidebar" 
           class="fixed inset-0 bg-black/50 z-30 lg:hidden"
           @click="toggleSidebar"></div>

      <!-- Chat Interface -->
      <div class="lg:col-span-3 bg-white rounded-2xl shadow-sm border border-border flex flex-col h-[calc(100vh-12rem)]">
        <!-- Chat Header -->
        <div class="p-4 border-b border-border">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 flex items-center justify-center">
              <SparklesIcon class="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 class="font-medium text-text-primary">AI Data Assistant</h3>
              <p class="text-sm text-text-secondary">Ask anything about your review data</p>
            </div>
          </div>
        </div>

        <!-- Chat Messages -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
          <div v-for="message in messages" 
               :key="message.id"
               class="flex"
               :class="message.type === 'user' ? 'justify-end' : 'justify-start'">
            <div class="max-w-2xl w-full lg:w-auto" :class="message.type === 'user' ? 'flex flex-col items-end' : ''">
              <!-- System Message -->
              <div v-if="message.type === 'system'"
                   class="bg-surface border border-border rounded-2xl p-6 space-y-4 w-full">
                <p class="text-text-primary">{{ message.content }}</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button v-for="suggestion in message.suggestions"
                          :key="suggestion.text"
                          @click="useSuggestion(suggestion)"
                          class="flex items-center space-x-3 px-4 py-3 rounded-xl bg-primary/5 text-gray-600 border border-primary/10 hover:bg-primary/10 transition-colors duration-200">
                    <component :is="suggestion.icon" class="h-5 w-5 flex-shrink-0 text-amber-600" />
                    <span class="text-sm truncate">{{ suggestion.text }}</span>
                  </button>
                </div>
              </div>

              <!-- User Message -->
              <div v-else-if="message.type === 'user'"
                   class="bg-gradient-to-r from-amber-400 to-orange-500 text-white rounded-2xl px-6 py-3 max-w-full break-words">
                <p>{{ message.content }}</p>
              </div>

              <!-- Assistant Message -->
              <div v-else
                   class="bg-surface border border-border rounded-2xl p-6 space-y-4 w-full lg:w-auto">
                <p class="text-text-primary">{{ message.content }}</p>
                <!-- Placeholder for charts/visualizations -->
                <div v-if="message.charts"
                     class="bg-background rounded-xl p-4 flex items-center justify-center h-64">
                  <p class="text-text-secondary">
                    [Visualization would be rendered here]
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Analysis Indicator -->
          <div v-if="isAnalyzing" class="flex items-center space-x-2 text-text-secondary">
            <DocumentChartBarIcon class="h-5 w-5 animate-pulse" />
            <span>Analyzing data...</span>
          </div>
        </div>

        <!-- Message Input -->
        <div class="p-4 border-t border-border">
          <form @submit.prevent="sendMessage" class="flex items-center space-x-4">
            <input
              v-model="messageInput"
              type="text"
              placeholder="Ask anything about your review data..."
              class="flex-1 rounded-xl border-border focus:border-primary-light focus:ring focus:ring-primary/20 py-3 px-4"
            />
            <button
              type="submit"
              class="px-6 py-3 bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-xl transition-all duration-300 flex items-center space-x-2 whitespace-nowrap"
            >
              <span class="hidden sm:inline">Ask</span>
              <PaperAirplaneIcon class="h-5 w-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>