<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import {
  PencilIcon,
  TrashIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline';

const props = defineProps<{
  sourceConfig: any;
}>();

const emit = defineEmits(['save', 'delete']);

const isEditing = ref(false);
const editableConfig = ref<any>({});

watch(() => props.sourceConfig, (newConfig) => {
  editableConfig.value = JSON.parse(JSON.stringify(newConfig));
}, { immediate: true, deep: true });

const sourceDetails = computed(() => {
    const sources: { [key: string]: { name: string, type: 'location' | 'domain' | 'product' } } = {
        google: { name: 'Google My Business', type: 'location' },
        trustpilot: { name: 'Trustpilot', type: 'domain' },
        tripadvisor: { name: 'TripAdvisor', type: 'location' },
        amazon: { name: 'Amazon Products', type: 'product' },
        druni: { name: 'Druni Products', type: 'product' },
    };
    return sources[props.sourceConfig.source_type] || { name: props.sourceConfig.source_type, type: 'domain' };
});

const handleSave = () => {
  emit('save', editableConfig.value);
  isEditing.value = false;
};

const cancelEdit = () => {
  editableConfig.value = JSON.parse(JSON.stringify(props.sourceConfig));
  isEditing.value = false;
};

const handleDelete = () => {
  emit('delete', props.sourceConfig);
};

const countriesInput = ref('');
watch(isEditing, (editing) => {
  if (editing) {
    countriesInput.value = editableConfig.value.countries.join(', ');
  }
});
watch(countriesInput, (newVal) => {
  if (editableConfig.value.countries !== undefined) {
    editableConfig.value.countries = newVal.split(',').map(c => c.trim()).filter(Boolean);
  }
});

</script>

<template>
  <div class="bg-white rounded-xl border shadow-sm p-5 space-y-4 transition-all hover:shadow-md">
    <div class="flex justify-between items-start">
      <div>
        <h3 class="text-lg font-bold text-text-primary">{{ sourceDetails.name }}</h3>
        <span class="text-xs bg-primary-light text-primary font-medium px-2 py-0.5 rounded-full">{{ sourceConfig.source_type }}</span>
      </div>
      <div class="flex items-center gap-2">
        <template v-if="!isEditing">
          <button @click="isEditing = true" class="p-2 text-gray-500 hover:text-primary rounded-full hover:bg-gray-100">
            <PencilIcon class="h-5 w-5" />
          </button>
          <button @click="handleDelete" class="p-2 text-gray-500 hover:text-red-500 rounded-full hover:bg-gray-100">
            <TrashIcon class="h-5 w-5" />
          </button>
        </template>
        <template v-else>
          <button @click="handleSave" class="p-2 text-green-600 hover:bg-green-100 rounded-full">
            <CheckIcon class="h-5 w-5" />
          </button>
          <button @click="cancelEdit" class="p-2 text-red-600 hover:bg-red-100 rounded-full">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </template>
      </div>
    </div>

    <!-- Configuration Form -->
    <div class="space-y-4 pt-2">
        <div>
            <label class="block text-sm font-medium text-gray-700">Brand Name</label>
            <input v-if="isEditing" type="text" v-model="editableConfig.brand_name" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm">
            <p v-else class="text-gray-900 mt-1">{{ editableConfig.brand_name }}</p>
        </div>
        
        <div>
            <label class="block text-sm font-medium text-gray-700">Countries (comma-separated)</label>
            <input v-if="isEditing" type="text" v-model="countriesInput" placeholder="e.g. us, es, fr" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm">
            <p v-else class="text-gray-900 mt-1">{{ editableConfig.countries.join(', ') || 'Not specified' }}</p>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-700">Number of Reviews</label>
            <input v-if="isEditing" type="number" v-model.number="editableConfig.number_of_reviews" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm">
            <p v-else class="text-gray-900 mt-1">{{ editableConfig.number_of_reviews }}</p>
        </div>

        <div v-if="sourceConfig.source_type === 'google' && editableConfig.google_config">
             <label class="block text-sm font-medium text-gray-700">Google Search Query</label>
             <input v-if="isEditing" type="text" v-model="editableConfig.google_config.query" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm">
             <p v-else class="text-gray-900 mt-1">{{ editableConfig.google_config.query }}</p>
        </div>
    </div>
  </div>
</template> 