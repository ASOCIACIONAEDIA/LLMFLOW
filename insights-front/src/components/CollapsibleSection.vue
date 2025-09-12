<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  content: {
    type: String,
    required: true
  },
  maxHeightCollapsed: {
    type: String, // e.g., '200px' or '12rem'
    default: '20rem' // Default to 20rem height (adjust as needed)
  }
})

const isExpanded = ref(false)
const isOverflowing = ref(false)
const contentRef = ref<HTMLElement | null>(null)

const checkOverflow = async () => {
  await nextTick() // Ensure DOM is updated
  if (contentRef.value) {
    // Check if the actual scroll height is greater than the container's offset height
    // We compare against a slightly smaller value than maxHeightCollapsed to be sure
    const contentHeight = contentRef.value.scrollHeight;
    // Simple check if content height exceeds a threshold (e.g., slightly more than collapsed height)
    // A more precise check would involve parsing maxHeightCollapsed, but this is simpler
    const threshold = parseInt(props.maxHeightCollapsed) * 16; // Convert rem to approx pixels (assuming 1rem = 16px)
    isOverflowing.value = contentHeight > threshold + 30; // Check if significantly taller
    // 

    // Fallback if it was overflowing but content changed and isn't anymore
    if (!isOverflowing.value) {
        isExpanded.value = true; // Ensure it's expanded if not overflowing
    }
  } else {
      isOverflowing.value = false;
  }
}

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// Watch for content changes to re-evaluate overflow
watch(() => props.content, () => {
    // Reset state before checking
    isExpanded.value = false; 
    isOverflowing.value = false;
    checkOverflow();
}, { immediate: true })

// Also check on mount
onMounted(() => {
    // Initial check might need slight delay for styles to apply
     setTimeout(checkOverflow, 100);
});

</script>

<template>
  <div>
    <div 
      ref="contentRef"
      :class="[
        'prose prose-sm max-w-none transition-all duration-300 ease-in-out',
        { 
          'overflow-hidden': !isExpanded,
          '[mask-image:linear-gradient(to_bottom,black_70%,transparent_100%)]': isOverflowing && !isExpanded,
          'max-h-full': isExpanded,
        }
      ]"
      :style="!isExpanded ? { maxHeight: maxHeightCollapsed } : {}"
    >
      <div v-html="props.content"></div>
    </div>
    
    <div v-if="isOverflowing" class="mt-2 flex justify-center">
        <button
          @click="toggleExpand"
          class="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/20 hover:text-primary-dark"
        >
          <ChevronUpIcon v-if="isExpanded" class="mr-1 h-4 w-4" />
          <ChevronDownIcon v-else class="mr-1 h-4 w-4" />
          <span>{{ isExpanded ? 'View Less' : 'View More' }}</span>
        </button>
    </div>
  </div>
</template>

<style scoped>
/* Ensure prose styles don't conflict too much with max-height */
.prose {
  max-width: none; /* Override default prose max-width if needed */
  color: inherit; /* Inherit text color from parent */
}

/* Additional styling for elements within v-html if needed */
:deep(p) {
  color: inherit;
}
:deep(ul),
:deep(ol) {
  color: inherit;
}
</style> 