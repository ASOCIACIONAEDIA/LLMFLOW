<script setup lang="ts">
import { BellIcon, Bars3Icon, XMarkIcon, ArrowRightOnRectangleIcon } from '@heroicons/vue/24/outline'
import { useRouter } from 'vue-router'

defineProps<{
  isMobile: boolean
  isSidebarOpen: boolean
}>()

const router = useRouter()
const emit = defineEmits(['toggle-sidebar'])

// Función para cerrar sesión
const logout = () => {
  // Remove user data from local storage
  sessionStorage.removeItem('token')
  sessionStorage.removeItem('adminToken')
  sessionStorage.removeItem('user')
  sessionStorage.removeItem('admin')
  
  // Redirect to login page or home page
  router.push('/login')
}
</script>

<template>
  <header class="bg-surface border-b border-border">
    <div class="flex h-16 items-center justify-between px-4 md:px-8">
      <div class="flex items-center">
        <!-- Mobile Menu Button -->
        <button v-if="isMobile"
                @click="$emit('toggle-sidebar')"
                class="p-2 text-text-secondary hover:text-primary-light rounded-lg hover:bg-background-lighter transition-all duration-200 mr-4">
          <Bars3Icon v-if="!isSidebarOpen" class="h-6 w-6" />
          <XMarkIcon v-else class="h-6 w-6" />
        </button>
        <div class="text-2xl font-semibold text-text-primary"></div>
      </div>
      <div class="flex items-center space-x-6">
        <button class="relative p-2 text-text-secondary hover:text-primary-light rounded-lg hover:bg-background-lighter transition-all duration-200">
          <BellIcon class="h-6 w-6" />
          <span class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent"></span>
        </button>
        
        <!-- Botón Cerrar Sesión -->
        <button 
          @click="logout"
          class="flex items-center space-x-2 px-3 py-2 bg-gradient-to-r from-orange-400 to-amber-500 text-white rounded-lg hover:opacity-90 transition-all duration-200"
        >
          <span class="hidden sm:inline">Sign out</span>
          <ArrowRightOnRectangleIcon class="h-5 w-5" />
        </button>
      </div>
    </div>
  </header>
</template>