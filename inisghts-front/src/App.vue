<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue' // Added watch
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import TopBar from './components/TopBar.vue'

// Import Pinia store and vue-toastification
import { useReportStore } from './store/reportStore'; // Make sure this path is correct
import { useToast } from 'vue-toastification';

const route = useRoute()
const reportStore = useReportStore(); // Initialize the store
const toast = useToast(); // Initialize toast

const isSidebarOpen = ref(window.innerWidth >= 1024)
const isMobile = ref(window.innerWidth < 1024)

// Determinar si la ruta actual es una página de autenticación
const isAuthPage = computed(() => {
  return route.path === '/login' || route.path === '/admin/login' || route.path === '/admin/dashboard'
})

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 1024
  if (!isMobile.value) {
    isSidebarOpen.value = true
  } else {
    isSidebarOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // Call handleResize once on mount to set initial state correctly
  handleResize();
  
  // Rehydrate SSE subscriptions on page load
  reportStore.rehydrateStateAndReconnect();
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// Watch for notifications from the Pinia store
watch(() => reportStore.notification, (newNotification) => {
  if (newNotification) {
    const { type, message } = newNotification;
    // Map store notification types to toast functions
    if (type === 'success') {
      toast.success(message);
    } else if (type === 'error') {
      toast.error(message);
    } else if (type === 'info') {
      toast.info(message);
    } else if (type === 'warning') {
      toast.warning(message);
    }
    reportStore.clearNotification(); // Clear notification from store after showing
  }
}, { deep: true });

</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Layout for non-authentication pages -->
    <template v-if="!isAuthPage">
      <!-- Mobile Sidebar Backdrop -->
      <div v-if="isMobile && isSidebarOpen"
          class="fixed inset-0 bg-black/50 z-20"
          @click="toggleSidebar"></div>

      <!-- Sidebar -->
      <Sidebar
        :class="[
          'fixed inset-y-0 left-0 z-30 transform transition-transform duration-300',
          isMobile ? (isSidebarOpen ? 'translate-x-0' : '-translate-x-full') : 'translate-x-0',
          isMobile ? 'w-[280px]' : 'w-64'
        ]" />

      <!-- Main Content -->
      <div :class="[
        'transition-all duration-300',
        isMobile ? 'pl-0' : 'pl-64' // Kept your original padding logic for desktop
      ]">
        <TopBar @toggle-sidebar="toggleSidebar" :is-mobile="isMobile" :is-sidebar-open="isSidebarOpen" />
        <main class="p-4 md:p-8">
          <router-view></router-view>
        </main>
      </div>
    </template>

    <!-- Content for authentication pages (no main layout) -->
    <template v-else>
      <router-view></router-view>
    </template>
  </div>
</template>