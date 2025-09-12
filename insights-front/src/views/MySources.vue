<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import apiClient from '@/services/axiosInstance';
import { 
  PlusIcon, 
  PencilIcon, 
  TrashIcon, 
  Cog8ToothIcon, 
  ExclamationTriangleIcon, 
  ChevronDownIcon,
  BuildingStorefrontIcon,
  GlobeAltIcon,
  StarIcon,
  ShoppingBagIcon,
  TagIcon
} from '@heroicons/vue/24/outline';
import { 
  Dialog, 
  DialogPanel, 
  DialogTitle, 
  TransitionChild, 
  TransitionRoot,
  Disclosure,
  DisclosureButton,
  DisclosurePanel
} from '@headlessui/vue';

interface SourceConfig {
  source_type: string;
  brand_name?: string;
  number_of_reviews?: number;
}

interface SourceContainer {
  id: string;
  name: string;
  sources: SourceConfig[];
}

const router = useRouter();
const toast = useToast();

const sourceContainers = ref<SourceContainer[]>([]);
const isLoading = ref(true);
const isModalOpen = ref(false);
const isEditMode = ref(false);
const containerToEdit = ref<SourceContainer | null>(null);
const newContainerName = ref('');
const isDeleteModalOpen = ref(false);
const containerToDelete = ref<SourceContainer | null>(null);

const connectorDetailsMap = {
  mybusiness: { name: 'Google My Business', icon: BuildingStorefrontIcon },
  tripadvisor: { name: 'TripAdvisor', icon: GlobeAltIcon },
  trustpilot: { name: 'Trustpilot', icon: StarIcon },
  druni: { name: 'Druni', icon: ShoppingBagIcon },
  amazon: { name: 'Amazon', icon: ShoppingBagIcon },
  products: { name: 'Products', icon: ShoppingBagIcon },
};


const fetchSourceContainers = async () => {
  isLoading.value = true;
  try {
    const response = await apiClient.get('/source-containers');
    sourceContainers.value = response.data;
  } catch (error) {
    console.error("Error fetching source containers:", error);
    toast.error("Failed to load your source containers.");
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchSourceContainers);

const openCreateModal = () => {
  isEditMode.value = false;
  containerToEdit.value = null;
  newContainerName.value = '';
  isModalOpen.value = true;
};

const openEditModal = (container: SourceContainer) => {
  isEditMode.value = true;
  containerToEdit.value = { ...container };
  newContainerName.value = container.name;
  isModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
};

const saveContainer = async () => {
  if (!newContainerName.value.trim()) {
    toast.warning("Container name cannot be empty.");
    return;
  }

  const payload = {
    name: newContainerName.value,
  };

  try {
    if (isEditMode.value && containerToEdit.value) {
      await apiClient.put(`/source-containers/${containerToEdit.value.id}`, payload);
      toast.success(`Container "${newContainerName.value}" updated successfully.`);
    } else {
      await apiClient.post('/source-containers', payload);
      toast.success(`Container "${newContainerName.value}" created successfully.`);
    }
    await fetchSourceContainers();
    closeModal();
  } catch (error: any) {
    console.error("Error saving container:", error);
    toast.error(error.response?.data?.detail || "Failed to save the container.");
  }
};

const openDeleteModal = (container: SourceContainer) => {
  containerToDelete.value = container;
  isDeleteModalOpen.value = true;
};

const closeDeleteModal = () => {
  isDeleteModalOpen.value = false;
  containerToDelete.value = null;
};

const confirmDelete = async () => {
  if (!containerToDelete.value) return;
  try {
    await apiClient.delete(`/source-containers/${containerToDelete.value.id}`);
    toast.success(`Container "${containerToDelete.value.name}" has been deleted.`);
    await fetchSourceContainers();
  } catch (error: any) {
    console.error("Error deleting container:", error);
    toast.error(error.response?.data?.detail || "Failed to delete the container.");
  } finally {
    closeDeleteModal();
  }
};


const configureContainer = (containerId: string) => {
  router.push({ name: 'ConnectMySources', params: { id: containerId } });
};
</script>

<template>
  <div class="p-4 md:p-6 lg:p-8 space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between">
      <h1 class="text-2xl md:text-3xl font-display font-bold text-text-primary">My Sources</h1>
      <button @click="openCreateModal" class="mt-4 sm:mt-0 px-4 py-2 bg-amber-400 text-white font-semibold rounded-lg shadow-md hover:bg-orange-400 transition-colors flex items-center space-x-2">
        <PlusIcon class="h-5 w-5" />
        <span>Create New Source Container</span>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-10">
      <p class="text-text-secondary">Loading your source containers...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="sourceContainers.length === 0" class="text-center py-20 bg-gray-50 rounded-xl border border-dashed">
      <h3 class="text-xl font-semibold text-text-primary">No Source Containers Found</h3>
      <p class="mt-2 text-text-secondary">Get started by creating your first source container.</p>
      <button @click="openCreateModal" class="mt-6 px-5 py-2.5 bg-primary text-white font-semibold rounded-lg shadow-md hover:bg-primary-dark transition-colors flex items-center space-x-2 mx-auto">
        <PlusIcon class="h-5 w-5" />
        <span>Create Container</span>
      </button>
    </div>

    <!-- Containers List -->
    <div v-else class="space-y-4 border-red-200">
      <Disclosure v-for="container in sourceContainers" :key="container.id" v-slot="{ open }">
        <div class="bg-white rounded-xl shadow-lg  border-gray-200 transition-all duration-300 ease-in-out">
          <DisclosureButton class="w-full flex items-center justify-between p-4 md:p-5 text-left">
            <div class="flex items-center space-x-4 flex-grow">
              <h3 class="text-lg font-semibold text-text-primary">{{ container.name }}</h3>
              <span class="text-xs font-medium text-white px-2 py-0.5 rounded-full" :class="container.sources.length > 0 ? 'bg-orange-500' : 'bg-gray-400'">
                {{ container.sources.length }} Source(s)
              </span>
            </div>
            <div class="flex items-center ml-4 space-x-2">
              <button @click.stop="configureContainer(container.id)" class="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors" title="Manage Sources">
                <Cog8ToothIcon class="h-5 w-5" />
              </button>
              <button @click.stop="openEditModal(container)" class="p-2 text-gray-500 hover:bg-orange-100 rounded-full transition-colors" title="Edit Name">
                  <PencilIcon class="h-5 w-5 text-orange-600"/>
              </button>
              <button @click.stop="openDeleteModal(container)" class="p-2 text-red-500 hover:bg-red-100 rounded-full transition-colors" title="Delete Container">
                  <TrashIcon class="h-5 w-5" />
              </button>
              <ChevronDownIcon :class="open ? 'transform rotate-180' : ''" class="h-6 w-6 text-text-secondary transition-transform" />
            </div>
          </DisclosureButton>
          
          <transition enter-active-class="transition duration-100 ease-out" enter-from-class="transform scale-95 opacity-0" enter-to-class="transform scale-100 opacity-100" leave-active-class="transition duration-75 ease-out" leave-from-class="transform scale-100 opacity-100" leave-to-class="transform scale-95 opacity-0">
            <DisclosurePanel class="p-4 md:p-5 border-gray-200">
              <div v-if="container.sources.length > 0" class="space-y-3">
                <div v-for="source in container.sources" :key="source.source_type" class="p-3 bg-white border border-gray-200 rounded-lg flex items-center justify-between">
                  <div class="flex items-center space-x-3">
                    <component :is="connectorDetailsMap[source.source_type as keyof typeof connectorDetailsMap]?.icon || TagIcon" class="h-5 w-5 text-orange-600" />
                    <div>
                      <p class="font-medium text-sm text-text-primary">{{ connectorDetailsMap[source.source_type as keyof typeof connectorDetailsMap]?.name }}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-center p-4">
                <p class="text-sm text-text-secondary">No sources have been configured for this container yet.</p>
              </div>
              <div class="mt-4 flex justify-start">
                <button @click="configureContainer(container.id)" class="flex items-center text-sm font-medium text-amber-600 hover:text-orange-600">
                  <PlusIcon class="h-4 w-4 mr-1 text-amber" />
                  Add or Manage Sources
                </button>
              </div>
            </DisclosurePanel>
          </transition>
        </div>
      </Disclosure>
    </div>

    <!-- Create/Edit Modal -->
    <TransitionRoot appear :show="isModalOpen" as="template">
      <Dialog as="div" @close="closeModal" class="relative z-10">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-black bg-opacity-25" />
        </TransitionChild>
        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 scale-95" enter-to="opacity-100 scale-100" leave="duration-200 ease-in" leave-from="opacity-100 scale-100" leave-to="opacity-0 scale-95">
              <DialogPanel class="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                  {{ isEditMode ? 'Edit Source Container' : 'Create New Source Container' }}
                </DialogTitle>
                <div class="mt-4">
                  <label for="containerName" class="block text-sm font-medium text-gray-700">Container Name</label>
                  <input type="text" id="containerName" v-model="newContainerName" @keyup.enter="saveContainer" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-amber-500 focus:ring-amber-500 sm:text-sm" placeholder="e.g., Primary Brand Analysis">
                </div>
                <div class="mt-6 flex justify-end space-x-3">
                  <button type="button" @click="closeModal" class="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2">
                    Cancel
                  </button>
                  <button type="button" @click="saveContainer" class="inline-flex justify-center rounded-md border border-transparent bg-orange-400 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-primary-dark focus:ring-offset-2">
                    {{ isEditMode ? 'Save Changes' : 'Create Container' }}
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
                        Delete Source Container
                      </DialogTitle>
                      <div class="mt-2">
                        <p class="text-sm text-gray-500">
                          Are you sure you want to delete '<strong>{{ containerToDelete?.name }}</strong>'? This action cannot be undone.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                  <button type="button" class="inline-flex w-full justify-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-base font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm" @click="confirmDelete">
                    Delete
                  </button>
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-base font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 sm:mt-0 sm:w-auto sm:text-sm" @click="closeDeleteModal">
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