<script setup lang="ts">
import { QuestionMarkCircleIcon } from '@heroicons/vue/24/outline'

interface Props {
  visible: boolean
  reviewCount: number
}

const props = defineProps<Props>()

const emit = defineEmits(['confirm', 'cancel'])

const formatNumber = (num: number) => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

const confirmAction = () => {
  emit('confirm')
}

const cancelAction = () => {
  emit('cancel')
}
</script>

<template>
  <div v-if="props.visible" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center z-50">
    <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-xl bg-white">
      <div class="mt-3 text-center">
        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100">
          <QuestionMarkCircleIcon class="h-6 w-6 text-yellow-600" />
        </div>
        <h3 class="text-lg leading-6 font-medium text-gray-900 mt-2">Low Review Count</h3>
        <div class="mt-2 px-7 py-3">
          <p class="text-sm text-gray-500">
            You have selected fewer than 100 reviews ({{ formatNumber(props.reviewCount) }} selected).
            Reports generated with a low number of reviews might not be statistically significant or provide comprehensive insights.
          </p>
          <p class="text-sm text-gray-500 mt-2">
            Are you sure you want to proceed?
          </p>
        </div>
        <div class="items-center px-4 py-3 space-x-4">
          <button
            @click="confirmAction"
            class="px-4 py-2 bg-primary text-white text-base font-medium rounded-md w-auto shadow-sm hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
          >
            Proceed Anyway
          </button>
          <button
            @click="cancelAction"
            class="px-4 py-2 bg-gray-200 text-gray-800 text-base font-medium rounded-md w-auto shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>