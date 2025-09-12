<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue';
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { CheckCircleIcon, XCircleIcon, ArrowPathIcon, InformationCircleIcon } from '@heroicons/vue/24/outline';
import { SSE } from 'sse.js';

const props = defineProps({
  isOpen: Boolean,
  jobId: String,
  title: String,
});

const emit = defineEmits(['close']);

const events = ref<any[]>([]);
const status = ref('pending'); // pending, running, source_complete, completed, failed
const sseInstance = ref<SSE | null>(null);
const finalS3Paths = ref<any>(null);
const processedSources = ref(0);
const totalSources = ref(0);

const statusInfo = computed(() => {
  switch (status.value) {
    case 'running':
      return { text: 'In Progress', icon: ArrowPathIcon, color: 'text-blue-500', iconClass: 'animate-spin' };
    case 'completed':
      return { text: 'Completed', icon: CheckCircleIcon, color: 'text-green-500' };
    case 'failed':
      return { text: 'Failed', icon: XCircleIcon, color: 'text-red-500' };
    default:
      return { text: 'Initializing...', icon: InformationCircleIcon, color: 'text-gray-500' };
  }
});

const progress = computed(() => {
    if (totalSources.value === 0) return 0;
    return (processedSources.value / totalSources.value) * 100;
});


const setupSSE = () => {
  if (!props.jobId || sseInstance.value) return;

  const url = `/api/sse/stream?subscribe_job_ids=${props.jobId}`;
  
  sseInstance.value = new SSE(url, {
    headers: { 'Authorization': `Bearer ${sessionStorage.getItem('token')}` },
    withCredentials: true,
  });

  sseInstance.value.addEventListener('message', (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      events.value.unshift(data.data); // Add new event to the top

      const eventData = data.data;
      status.value = eventData.status;

      if(eventData.total_sources_to_track) {
          totalSources.value = eventData.total_sources_to_track;
      }
      if(eventData.processed_sources) {
          processedSources.value = eventData.processed_sources;
      }

      if (eventData.status === 'completed') {
        finalS3Paths.value = eventData.s3_paths;
        closeSSE();
      }
      if (eventData.status === 'failed') {
        closeSSE();
      }

    } catch (e) {
      console.error('Failed to parse SSE event data:', e);
    }
  });

  sseInstance.value.addEventListener('error', (error: any) => {
    console.error('SSE connection error:', error);
    status.value = 'failed';
    events.value.unshift({ message: 'Connection to status updates failed.' });
    closeSSE();
  });

  sseInstance.value.stream();
  status.value = 'running';
};

const closeSSE = () => {
  if (sseInstance.value) {
    sseInstance.value.close();
    sseInstance.value = null;
  }
};

const closeModal = () => {
  emit('close');
};

watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    // Reset state when modal opens
    events.value = [];
    status.value = 'pending';
    finalS3Paths.value = null;
    processedSources.value = 0;
    totalSources.value = 0;
    setupSSE();
  } else {
    closeSSE();
  }
});

onUnmounted(() => {
  closeSSE();
});
</script>

<template>
  <TransitionRoot as="template" :show="isOpen">
    <Dialog as="div" class="relative z-20" @close="closeModal">
      <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0" enter-to="opacity-100" leave="ease-in duration-200" leave-from="opacity-100" leave-to="opacity-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
      </TransitionChild>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
          <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="ease-in duration-200" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
            <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-xl">
              <div class="bg-white px-4 pt-5 pb-4 sm:p-6">
                <div class="sm:flex sm:items-start">
                  <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 sm:mx-0 sm:h-10 sm:w-10">
                    <component :is="statusInfo.icon" :class="[statusInfo.color, statusInfo.iconClass]" class="h-6 w-6" aria-hidden="true" />
                  </div>
                  <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-grow">
                    <DialogTitle as="h3" class="text-lg font-semibold leading-6 text-gray-900">
                      {{ title || 'Job Status' }}
                    </DialogTitle>
                    <div class="mt-1">
                      <p class="text-sm text-gray-500">Job ID: {{ jobId }}</p>
                    </div>
                  </div>
                </div>

                <div class="mt-4">
                    <div class="flex justify-between mb-1">
                        <span class="text-base font-medium text-primary">{{ statusInfo.text }}</span>
                        <span class="text-sm font-medium text-primary">{{ processedSources }} / {{ totalSources }} Sources</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="bg-primary h-2.5 rounded-full" :style="{ width: progress + '%' }"></div>
                    </div>
                </div>

                <div class="mt-4 h-64 overflow-y-auto bg-gray-50 p-3 rounded-lg border">
                  <ul v-if="events.length > 0" class="space-y-2">
                    <li v-for="(event, index) in events" :key="index" class="text-xs text-gray-600">
                      <span class="font-semibold text-gray-800">[{{ new Date().toLocaleTimeString() }}]</span> {{ event.message }}
                    </li>
                  </ul>
                  <div v-else class="flex items-center justify-center h-full">
                      <p class="text-sm text-gray-500">Waiting for job to start...</p>
                  </div>
                </div>

              </div>
              <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                <button
                  type="button"
                  class="inline-flex w-full justify-center rounded-md border border-transparent bg-primary px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-primary-dark focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                  @click="closeModal"
                >
                  Close
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template> 