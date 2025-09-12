<template>
    <div>
      <div v-if="isLoading" class="p-8 text-center">
        <p>Loading competitor configuration...</p>
      </div>
      <div v-else-if="!competitor" class="p-8 text-center text-red-500">
        <p>Could not load data for this competitor. Please go back and try again.</p>
      </div>
      <ConnectSources
        v-else
        :competitor-name="competitor.name"
        :competitor-id="competitor.id"
        :initial-sources="competitor.sources"
      />
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, onMounted, computed } from 'vue';
  import { useRoute } from 'vue-router';
  import apiClient from '@/services/axiosInstance';
  import ConnectSources from './ConnectSources.vue';
  import { useToast } from 'vue-toastification';
  
  const route = useRoute();
  const toast = useToast();
  
  const competitor = ref<any>(null);
  const isLoading = ref(true);
  
  const competitorId = computed(() => route.params.id as string);
  
  onMounted(async () => {
    if (!competitorId.value) {
      toast.error("No competitor ID provided in URL.");
      isLoading.value = false;
      return;
    }
    try {
      const response = await apiClient.get(`/competitors/${competitorId.value}`);
      competitor.value = response.data;
    } catch (error) {
      console.error("Failed to load competitor data:", error);
      toast.error("Could not load competitor details.");
    } finally {
      isLoading.value = false;
    }
  });
  </script>
  