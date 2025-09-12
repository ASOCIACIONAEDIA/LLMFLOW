<script setup lang="ts">
import { ref, defineProps, defineEmits } from 'vue';
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { PlusIcon } from '@heroicons/vue/24/outline';

const props = defineProps<{
  isOpen: boolean;
  existingCompetitors: string[];
}>();

const emit = defineEmits(['close', 'competitor-added']);

const newCompetitorName = ref('');
const error = ref<string | null>(null);

const addCompetitor = () => {
  const name = newCompetitorName.value.trim();
  if (!name) {
    error.value = "Competitor name cannot be empty.";
    return;
  }
  if (props.existingCompetitors.map(c => c.toLowerCase()).includes(name.toLowerCase())) {
    error.value = `"${name}" is already in your competitor list.`;
    return;
  }
  emit('competitor-added', name);
  closeModal();
};

const closeModal = () => {
  newCompetitorName.value = '';
  error.value = null;
  emit('close');
};
</script>

<template>
  <TransitionRoot appear :show="isOpen" as="template">
    <Dialog as="div" @close="closeModal" class="relative z-50">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/30" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <TransitionChild
            as="template"
            enter="duration-300 ease-out"
            enter-from="opacity-0 scale-95"
            enter-to="opacity-100 scale-100"
            leave="duration-200 ease-in"
            leave-from="opacity-100 scale-100"
            leave-to="opacity-0 scale-95"
          >
            <DialogPanel class="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
              <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                Add a New Competitor
              </DialogTitle>
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  Enter the name of the competitor you want to start tracking.
                </p>
              </div>

              <div class="mt-4">
                <input 
                  v-model="newCompetitorName"
                  @keyup.enter="addCompetitor"
                  type="text"
                  placeholder="e.g., Competitor Inc."
                  class="w-full rounded-lg border-gray-300 focus:border-primary-light focus:ring focus:ring-primary/20"
                />
                <p v-if="error" class="text-sm text-red-600 mt-2">{{ error }}</p>
              </div>

              <div class="mt-6 flex justify-end space-x-2">
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                  @click="closeModal"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                  @click="addCompetitor"
                  :disabled="!newCompetitorName.trim()"
                >
                  Add Competitor
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template> 