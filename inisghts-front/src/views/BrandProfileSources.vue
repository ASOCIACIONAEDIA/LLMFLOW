<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import { 
  ArrowLeftIcon,
  CircleStackIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  PlayIcon,
  EyeIcon
} from '@heroicons/vue/24/outline';
import apiClient from '@/services/axiosInstance';
import SourceConfigCard from '@/components/SourceConfigCard.vue';
import ConfirmationModal from '@/components/ConfirmationModal.vue';
import JobStatusModal from '@/components/JobStatusModal.vue';

interface SourceConfig {
  source_type: string;
  brand_name: string;
  countries: string[];
  number_of_reviews: number;
  google_config?: any;
}

interface BrandProfile {
  id: string;
  name: string;
  sources: SourceConfig[];
}

const route = useRoute();
const router = useRouter();
const toast = useToast();

const profile = ref<BrandProfile | null>(null);
const isLoading = ref(true);
const isScraping = ref(false);
const profileId = computed(() => route.params.profileId as string);

const isDeleteModalOpen = ref(false);
const sourceToDelete = ref<SourceConfig | null>(null);

const jobStatusModalOpen = ref(false);
const currentJobId = ref<string | null>(null);
const jobStatusTitle = ref('');

const availableSources = ref([
    { id: 'google', name: 'Google My Business', type: 'location' },
    { id: 'trustpilot', name: 'Trustpilot', type: 'domain' },
    { id: 'tripadvisor', name: 'TripAdvisor', type: 'location' },
    { id: 'amazon', name: 'Amazon Products', type: 'product' },
    { id: 'druni', name: 'Druni Products', type: 'product' },
]);

const fetchProfileDetails = async () => {
  isLoading.value = true;
  try {
    const response = await apiClient.get(`/brand-profiles/${profileId.value}`);
    profile.value = response.data;
  } catch (error) {
    toast.error('Failed to fetch brand profile details.');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const onSaveSource = async (config: SourceConfig) => {
  try {
    const response = await apiClient.put(`/brand-profiles/${profileId.value}/sources/${config.source_type}`, config);
    
    const index = profile.value?.sources.findIndex(s => s.source_type === config.source_type) ?? -1;
    if (index !== -1) {
      profile.value!.sources[index] = response.data;
    } else {
      profile.value?.sources.push(response.data);
    }
    toast.success(`Source '${config.source_type}' saved successfully.`);
  } catch (error: any) {
    toast.error(`Failed to save source. ${error.response?.data?.detail || ''}`);
  }
};

const onAddSource = (sourceType: string) => {
    if (profile.value?.sources.some(s => s.source_type === sourceType)) {
        toast.info(`Source '${sourceType}' is already configured.`);
        return;
    }
    const newSource: SourceConfig = {
        source_type: sourceType,
        brand_name: profile.value?.name || '',
        countries: [],
        number_of_reviews: 1000,
    };
    if (!profile.value) profile.value = { id: profileId.value, name: 'New Profile', sources: [] };
    profile.value.sources.push(newSource);
};


const openDeleteModal = (source: SourceConfig) => {
  sourceToDelete.value = source;
  isDeleteModalOpen.value = true;
};

const confirmDeleteSource = async () => {
  if (!sourceToDelete.value || !profile.value) return;
  try {
    await apiClient.delete(`/brand-profiles/${profile.value.id}/sources/${sourceToDelete.value!.source_type}`);
    profile.value.sources = profile.value.sources.filter(s => s.source_type !== sourceToDelete.value!.source_type);
    toast.success(`Source '${sourceToDelete.value.source_type}' removed.`);
  } catch (error) {
    toast.error('Failed to remove source.');
  } finally {
    isDeleteModalOpen.value = false;
    sourceToDelete.value = null;
  }
};

const handleScrape = async () => {
  if (!profile.value) return;
  isScraping.value = true;
  jobStatusTitle.value = `Scraping for ${profile.value.name}`;
  try {
    const response = await apiClient.post(`/brand-profiles/${profile.value.id}/scrape`);
    currentJobId.value = response.data.job_id;
    jobStatusModalOpen.value = true;
    toast.info(`Scraping job started for profile: ${profile.value.name}`);
  } catch (error) {
    toast.error('Failed to start scraping job.');
  } finally {
    isScraping.value = false;
  }
};

const goBack = () => {
  router.push({ name: 'my-sources' });
};

onMounted(fetchProfileDetails);
</script>

<template>
  <div class="space-y-8 p-4 md:p-6 lg:p-8">
    <div v-if="isLoading" class="text-center py-10">Loading profile...</div>
    <div v-else-if="!profile" class="text-center py-10">
      <h2 class="text-2xl font-bold">Profile not found</h2>
      <button @click="goBack" class="mt-4 flex items-center mx-auto text-primary hover:underline">
        <ArrowLeftIcon class="h-5 w-5 mr-2" />
        Back to My Sources
      </button>
    </div>
    <div v-else>
      <!-- Header -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <button @click="goBack" class="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeftIcon class="h-4 w-4 mr-1" />
            Back to Brand Profiles
          </button>
          <h1 class="text-2xl md:text-3xl font-display font-bold text-text-primary">
            Manage Sources for <span class="text-primary">{{ profile.name }}</span>
          </h1>
          <p class="text-text-secondary mt-1">Configure the data sources you want to scrape for this profile.</p>
        </div>
        <button @click="handleScrape"
                :disabled="isScraping || profile.sources.length === 0"
                class="flex items-center justify-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-sm text-base font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed">
          <PlayIcon class="h-6 w-6 mr-2" />
          {{ isScraping ? 'Starting...' : 'Run Scraping' }}
        </button>
      </div>

      <!-- Configured Sources -->
      <div class="mt-8">
        <h2 class="text-xl font-semibold mb-4 text-text-primary">Configured Sources</h2>
        <div v-if="profile.sources.length > 0" class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <SourceConfigCard
            v-for="source in profile.sources"
            :key="source.source_type"
            :source-config="source"
            @save="onSaveSource"
            @delete="openDeleteModal(source)"
          />
        </div>
        <div v-else class="text-center py-10 bg-gray-50/50 rounded-xl border border-dashed">
            <CircleStackIcon class="mx-auto h-12 w-12 text-gray-400" />
            <h3 class="mt-2 text-lg font-medium text-text-primary">No Sources Added</h3>
            <p class="text-text-secondary mt-1">Add sources from the list below to get started.</p>
        </div>
      </div>

      <!-- Available Sources to Add -->
      <div class="mt-12">
        <h2 class="text-xl font-semibold mb-4 text-text-primary">Add a New Source</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          <button
            v-for="source in availableSources"
            :key="source.id"
            @click="onAddSource(source.id)"
            :disabled="profile.sources.some(s => s.source_type === source.id)"
            class="p-4 bg-white border rounded-lg flex flex-col items-center justify-center text-center hover:bg-gray-50 hover:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100"
          >
            <CircleStackIcon class="h-8 w-8 text-primary mb-2" />
            <span class="font-semibold text-sm">{{ source.name }}</span>
          </button>
        </div>
      </div>
    </div>
    
    <ConfirmationModal
      v-if="sourceToDelete"
      :is-open="isDeleteModalOpen"
      title="Remove Source"
      :message="`Are you sure you want to remove the '${sourceToDelete.source_type}' source from this profile? All its configurations will be lost.`"
      confirm-button-text="Remove"
      @confirm="confirmDeleteSource"
      @close="isDeleteModalOpen = false"
    />

    <JobStatusModal
      :is-open="jobStatusModalOpen"
      :job-id="currentJobId"
      :title="jobStatusTitle"
      @close="jobStatusModalOpen = false"
    />
  </div>
</template> 