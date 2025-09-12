<template>
  <div class="space-y-8 p-4 md:p-6 lg:p-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl md:text-3xl font-display font-bold text-text-primary">Competitors</h1>
        <p class="text-text-secondary mt-1">Manage your competitors and their connected sources.</p>
      </div>
      <button @click="openAddModal"
              class="flex items-center justify-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors shadow-sm text-sm font-medium">
        <PlusIcon class="h-5 w-5 mr-2" />
        Add Competitor
      </button>
    </div>

    <!-- Loading and Empty States -->
    <div v-if="isLoading" class="text-center py-10">
      <p>Loading competitors...</p>
    </div>
    <div v-else-if="error" class="p-8 text-center text-red-500 bg-red-50 rounded-lg">
      <p>{{ error }}</p>
    </div>
    <div v-else-if="competitors.length === 0" class="text-center py-10 bg-gray-50 rounded-xl border border-dashed">
      <h3 class="text-lg font-medium text-text-primary">No Competitors Added Yet</h3>
      <p class="text-text-secondary mt-1 mb-4">Click 'Add Competitor' to get started.</p>
      <button @click="openAddModal" class="flex items-center justify-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark shadow-sm text-sm font-medium mx-auto">
        <PlusIcon class="h-5 w-5 mr-2" />Add Competitor
      </button>
    </div>

    <!-- Competitors List -->
    <div v-else class="space-y-4">
      <Disclosure v-for="competitor in competitors" :key="competitor.id" v-slot="{ open }">
        <div class="bg-white rounded-xl shadow-lg border border-border transition-all duration-300 ease-in-out"
             :class="{ 'ring-2 ring-primary/50': open }">
          <DisclosureButton class="w-full flex items-center justify-between p-4 md:p-5 text-left">
            <div class="flex items-center space-x-4 flex-grow">
              <h3 class="text-lg font-semibold text-text-primary">{{ competitor.name }}</h3>
              <span class="text-xs font-medium text-white px-2 py-0.5 rounded-full" :class="competitor.sources.length > 0 ? 'bg-blue-500' : 'bg-gray-400'">
                {{ competitor.sources.length }} Source(s)
              </span>
            </div>
            <div class="flex items-center ml-4 space-x-2">
               <button @click.stop="goToSources(competitor.id)" class="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors" title="Manage Sources">
                <Cog8ToothIcon class="h-5 w-5" />
              </button>
              <button @click.stop="handleDeleteCompetitor(competitor.id, competitor.name)" class="p-2 text-red-500 hover:bg-red-100 rounded-full transition-colors" title="Delete Competitor">
                <TrashIcon class="h-5 w-5" />
              </button>
              <ChevronDownIcon :class="open ? 'transform rotate-180' : ''" class="h-6 w-6 text-text-secondary transition-transform" />
            </div>
          </DisclosureButton>
          
          <transition enter-active-class="transition duration-100 ease-out" enter-from-class="transform scale-95 opacity-0" enter-to-class="transform scale-100 opacity-100" leave-active-class="transition duration-75 ease-out" leave-from-class="transform scale-100 opacity-100" leave-to-class="transform scale-95 opacity-0">
            <DisclosurePanel class="p-4 md:p-5 border-t border-border bg-surface">
                <div v-if="competitor.sources.length > 0" class="space-y-3">
                    <div v-for="source in competitor.sources" :key="source.source_type" class="p-3 bg-white border border-gray-200 rounded-lg flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <component :is="connectorDetailsMap[source.source_type as keyof typeof connectorDetailsMap]?.icon || TagIcon" class="h-5 w-5 text-primary" />
                            <div>
                                <p class="font-medium text-sm text-text-primary">{{ connectorDetailsMap[source.source_type as keyof typeof connectorDetailsMap]?.name }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                 <div v-else class="text-center p-4">
                    <p class="text-sm text-text-secondary">No sources have been configured for this competitor yet.</p>
                </div>
                <div class="mt-4 flex justify-start">
                    <button @click="goToSources(competitor.id)" class="flex items-center text-sm font-medium text-primary hover:text-primary-dark">
                        <PlusIcon class="h-4 w-4 mr-1" />
                        Add or Manage Sources
                    </button>
                </div>
            </DisclosurePanel>
          </transition>
        </div>
      </Disclosure>
    </div>
    
    <!-- Add Competitor Modal -->
    <TransitionRoot as="template" :show="isAddModalOpen">
      <Dialog as="div" class="relative z-20" @close="closeAddModal">
        <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0" enter-to="opacity-100" leave="ease-in duration-200" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>
        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
            <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="ease-in duration-200" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                <div class="bg-white px-4 pt-5 pb-4 sm:p-6">
                  <div class="sm:flex sm:items-start">
                    <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 sm:mx-0 sm:h-10 sm:w-10">
                      <PlusIcon class="h-6 w-6 text-primary" aria-hidden="true" />
                    </div>
                    <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                      <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                        Add New Competitor
                      </DialogTitle>
                      <div class="mt-4">
                        <p class="text-sm text-gray-500 mb-2">
                          Enter the name of the competitor you want to track.
                        </p>
                        <input v-model="newCompetitorName" type="text" placeholder="Competitor Name" class="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary" @keyup.enter="handleAddCompetitor">
                      </div>
                    </div>
                  </div>
                </div>
                <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                  <button type="button" class="inline-flex w-full justify-center rounded-md border border-transparent bg-primary px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50" @click="handleAddCompetitor" :disabled="isSaving">
                    {{ isSaving ? 'Saving...' : 'Save' }}
                  </button>
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:mt-0 sm:w-auto sm:text-sm" @click="closeAddModal">
                    Cancel
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Delete Confirmation Modal -->
    <TransitionRoot as="template" :show="isDeleteModalOpen">
      <Dialog as="div" class="relative z-30" @close="closeDeleteModal">
        <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0" enter-to="opacity-100" leave="ease-in duration-200" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>
        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
            <TransitionChild as="template" enter="ease-out duration-300" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="ease-in duration-200" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <div class="sm:flex sm:items-start">
                    <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                      <ExclamationTriangleIcon class="h-6 w-6 text-red-600" aria-hidden="true" />
                    </div>
                    <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                      <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                        Delete Competitor
                      </DialogTitle>
                      <div class="mt-2">
                        <p class="text-sm text-gray-500">
                          Are you sure you want to delete '<strong>{{ competitorToDelete?.name }}</strong>'? This action will also delete all associated data and cannot be undone.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                  <button type="button" class="inline-flex w-full justify-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm" @click="confirmDelete">
                    Delete
                  </button>
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:mt-0 sm:w-auto sm:text-sm" @click="closeDeleteModal">
                    Cancel
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '@/services/axiosInstance';
import { useToast } from 'vue-toastification';
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot, Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { 
  ExclamationTriangleIcon,
  PlusIcon,
  ChevronDownIcon,
  BuildingStorefrontIcon,
  GlobeAltIcon,
  StarIcon,
  ShoppingBagIcon,
  TagIcon,
  Cog8ToothIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const router = useRouter();
const toast = useToast();

const competitors = ref<any[]>([]);
const isLoading = ref(true);
const isSaving = ref(false);
const error = ref<string | null>(null);

const isAddModalOpen = ref(false);
const newCompetitorName = ref('');

const isDeleteModalOpen = ref(false);
const competitorToDelete = ref<{ id: string, name: string } | null>(null);

const connectorDetailsMap = {
  mybusiness: { name: 'Google My Business', icon: BuildingStorefrontIcon },
  tripadvisor: { name: 'TripAdvisor', icon: GlobeAltIcon },
  trustpilot: { name: 'Trustpilot', icon: StarIcon },
  druni: { name: 'Druni', icon: ShoppingBagIcon },
  amazon: { name: 'Amazon', icon: ShoppingBagIcon },
  products: { name: 'Products', icon: ShoppingBagIcon },
};

async function fetchCompetitors() {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await apiClient.get('/competitors');
    competitors.value = response.data;
  } catch (err) {
    console.error("Failed to load competitors:", err);
    error.value = "Could not load competitor data. Please try again later.";
    toast.error(error.value);
  } finally {
    isLoading.value = false;
  }
}

onMounted(fetchCompetitors);

function openAddModal() {
  newCompetitorName.value = '';
  isAddModalOpen.value = true;
}

function closeAddModal() {
  isAddModalOpen.value = false;
}

async function handleAddCompetitor() {
  if (!newCompetitorName.value.trim()) {
    toast.error("Competitor name cannot be empty.");
    return;
  }
  isSaving.value = true;
  try {
    await apiClient.post('/competitors', { name: newCompetitorName.value });
    toast.success(`Competitor '${newCompetitorName.value}' added successfully.`);
    closeAddModal();
    await fetchCompetitors(); // Refresh list
  } catch (err: any) {
    console.error("Failed to add competitor:", err);
    const errorMessage = err.response?.data?.detail || "An error occurred while adding the competitor.";
    toast.error(errorMessage);
  } finally {
    isSaving.value = false;
  }
}

function handleDeleteCompetitor(id: string, name: string) {
  competitorToDelete.value = { id, name };
  isDeleteModalOpen.value = true;
}

function closeDeleteModal() {
  isDeleteModalOpen.value = false;
  competitorToDelete.value = null;
}

async function confirmDelete() {
  if (!competitorToDelete.value) return;

  try {
    await apiClient.delete(`/competitors/${competitorToDelete.value.id}`);
    toast.success(`Competitor '${competitorToDelete.value.name}' deleted successfully.`);
    await fetchCompetitors(); // Refresh list
  } catch (err) {
    console.error("Failed to delete competitor:", err);
    toast.error("An error occurred while deleting the competitor.");
  } finally {
    closeDeleteModal();
  }
}

function goToSources(id: string) {
  router.push({ name: 'CompetitorSources-details', params: { id: id } });
}
</script> 