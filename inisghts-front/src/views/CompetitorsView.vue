<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '@/services/axiosInstance';
import { useToast } from 'vue-toastification';
import { PlusIcon, TrashIcon, CogIcon } from '@heroicons/vue/24/outline';

const competitors = ref<any[]>([]);
const newCompetitorName = ref('');
const isLoading = ref(true);
const router = useRouter();
const toast = useToast();

const fetchCompetitors = async () => {
  isLoading.value = true;
  try {
    const response = await apiClient.get('/competitors');
    competitors.value = response.data;
  } catch (error) {
    toast.error('Failed to load competitors.');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const addCompetitor = async () => {
  if (!newCompetitorName.value.trim()) {
    toast.warning('Please enter a competitor name.');
    return;
  }
  try {
    await apiClient.post('/competitors', { name: newCompetitorName.value });
    toast.success(`Competitor "${newCompetitorName.value}" added.`);
    newCompetitorName.value = '';
    await fetchCompetitors(); // Refresh list
  } catch (error: any) {
    toast.error(error.response?.data?.detail || 'Failed to add competitor.');
    console.error(error);
  }
};

const deleteCompetitor = async (competitorId: string, competitorName: string) => {
  if (!confirm(`Are you sure you want to delete "${competitorName}"?`)) {
    return;
  }
  try {
    await apiClient.delete(`/competitors/${competitorId}`);
    toast.success(`Competitor "${competitorName}" deleted.`);
    await fetchCompetitors(); // Refresh list
  } catch (error) {
    toast.error('Failed to delete competitor.');
    console.error(error);
  }
};

const goToConfiguration = (competitorId: string) => {
  router.push({ name: 'CompetitorSources', params: { id: competitorId } });
};

onMounted(fetchCompetitors);
</script>

<template>
  <div class="p-8">
    <h1 class="text-3xl font-bold mb-6">Manage Competitors</h1>

    <!-- Add Competitor Form -->
    <div class="mb-8 p-6 bg-white rounded-lg shadow-sm">
      <h2 class="text-xl font-semibold mb-4">Add New Competitor</h2>
      <div class="flex gap-4">
        <input
          v-model="newCompetitorName"
          @keyup.enter="addCompetitor"
          type="text"
          placeholder="Enter competitor name"
          class="flex-grow rounded-md border-gray-300 shadow-sm"
        />
        <button
          @click="addCompetitor"
          class="bg-primary text-white px-4 py-2 rounded-md hover:bg-primary-dark flex items-center"
        >
          <PlusIcon class="h-5 w-5 mr-2" />
          Add
        </button>
      </div>
    </div>

    <!-- Competitors List -->
    <div>
      <h2 class="text-xl font-semibold mb-4">Your Competitors</h2>
      <div v-if="isLoading" class="text-center">Loading...</div>
      <div v-else-if="competitors.length === 0" class="text-center text-gray-500 py-4">
        You haven't added any competitors yet.
      </div>
      <div v-else class="space-y-4">
        <div
          v-for="competitor in competitors"
          :key="competitor.id"
          class="bg-white rounded-lg shadow-sm p-4 flex justify-between items-center"
        >
          <span class="font-medium">{{ competitor.name }}</span>
          <div class="flex gap-2">
            <button @click="goToConfiguration(competitor.id)" class="p-2 text-gray-600 hover:text-primary">
              <CogIcon class="h-5 w-5" />
            </button>
            <button @click="deleteCompetitor(competitor.id, competitor.name)" class="p-2 text-gray-600 hover:text-red-600">
              <TrashIcon class="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
