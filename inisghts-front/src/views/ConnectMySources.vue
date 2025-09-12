<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '@/services/axiosInstance';
import ConnectSources from './ConnectSources.vue'; // The main component
import { ArrowLeftIcon } from '@heroicons/vue/24/solid';

const route = useRoute();
const isLoading = ref(true);
const containerName = ref('');
const initialSources = ref([]);
const error = ref<string | null>(null);

const containerId = computed(() => route.params.id as string);

onMounted(async () => {
  if (!containerId.value) {
    error.value = "No source container ID provided.";
    isLoading.value = false;
    return;
  }

  try {
    const response = await apiClient.get(`/source-containers/${containerId.value}`);
    containerName.value = response.data.name;
    initialSources.value = response.data.sources || [];
  } catch (err: any) {
    console.error("Failed to load source container details:", err);
    error.value = err.response?.data?.detail || "Could not load source container information.";
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div>
    <div v-if="isLoading" class="p-8 text-center">
      <p>Loading configuration...</p>
    </div>
    <div v-else-if="error" class="p-8 text-center text-red-600 bg-red-50 rounded-lg m-4">
      <p><strong>Error:</strong> {{ error }}</p>
      <router-link :to="{ name: 'MySources' }" class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark">
        <ArrowLeftIcon class="h-5 w-5 mr-2" />
        Back to My Sources
      </router-link>
    </div>
    <ConnectSources
      v-else
      :sourceContainerId="containerId"
      :sourceContainerName="containerName"
      :initialSources="initialSources"
    />
  </div>
</template>