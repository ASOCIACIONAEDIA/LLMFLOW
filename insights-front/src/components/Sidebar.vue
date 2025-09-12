<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeIcon, UserGroupIcon, DocumentTextIcon, ChatBubbleLeftRightIcon, CogIcon, QuestionMarkCircleIcon, ChartBarIcon, DocumentPlusIcon, SparklesIcon, Cog8ToothIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'

const route = useRoute()
const router = useRouter()

const userString = sessionStorage.getItem('user');
let userName = ref('');
let userEmail = ref('');
let userImage = ref(''); // Add a ref for the user's image

const connectSourcesDropdownVisible = ref(false);
const connectSourcesContainer = ref<HTMLElement[]>([]);

function toggleConnectSourcesDropdown() {
  connectSourcesDropdownVisible.value = !connectSourcesDropdownVisible.value;
}

const handleClickOutside = (event: MouseEvent) => {
  if (connectSourcesContainer.value.length > 0 && !connectSourcesContainer.value[0].contains(event.target as Node)) {
    connectSourcesDropdownVisible.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside, true);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside, true);
});

watch(() => route.path, () => {
  connectSourcesDropdownVisible.value = false;
});

const isAdmin = computed(() => {
  return !!sessionStorage.getItem('adminToken');
});

// Check if the user is a corporate admin
// const isCorporateAdmin = computed(() => {
//   // Assuming 'corporateAdminToken' is stored in localStorage upon corporate admin login
//   return !!localStorage.getItem('corporateAdminToken');
// });

const userInfo = computed(() => {
  // Obtener información del usuario logueado
  if (!userString) return null;
  try {
    return JSON.parse(userString);
  } catch (e) {
    return null;
  }
});

const isUserAdmin = computed(() => {
  // Verificar si es administrador de marca
  if (!userInfo.value) return false;
  return userInfo.value.is_admin === 1 || userInfo.value.is_admin === true;
});

const canAccessConnectSources = computed(() => {
  // Puede acceder si es admin de sistema o admin de marca
  return isAdmin.value || isUserAdmin.value;
});

// Filtrar navegación según permisos
const filteredNavigation = computed(() => {
  return navigation.filter(item => {
    // Si es "Connect Sources", solo mostrar si tiene permisos
    if (item.name === 'Connect Sources') {
      return canAccessConnectSources.value;
    }
    return true; // Mostrar los demás elementos a todos
  });
});

const navigation = [
  { name: 'Dashboard', icon: HomeIcon, href: '/dashboard', gradient: 'from-amber-400 to-orange-500' },
  { name: 'Behavioral Archetypes', icon: UserGroupIcon, href: '/archetypes', gradient: 'from-amber-400 to-orange-500' },
  { name: 'Generate Report', icon: DocumentPlusIcon, href: '/reports/new', gradient: 'from-amber-400 to-orange-500' },
  { name: 'Generated Reports', icon: DocumentTextIcon, href: '/reports', gradient: 'from-amber-400 to-orange-500' },
  { name: 'Archetype Chat', icon: ChatBubbleLeftRightIcon, href: '/chat', gradient: 'from-amber-400 to-orange-500' },
  { name: 'Chat2Data', icon: SparklesIcon, href: '/chat2data', gradient: 'from-amber-400 to-orange-500', new: true },
  { name: 'Connect Sources', icon: Cog8ToothIcon, href: '/settings/sources', gradient: 'from-amber-400 to-orange-500' },
  // { name: 'Help', icon: QuestionMarkCircleIcon, href: '/help', gradient: 'from-amber-400 to-orange-500' }, // Eliminado/Comentado
]

const sources =
[
  {name: 'zara'}
]

const isCurrentRoute = (href: string) => {
  return route.path === href
}

const getUserName = computed(() => {
  if (isAdmin.value) {
    try {
      const adminDataString = sessionStorage.getItem('admin');
      const adminData = JSON.parse(adminDataString || '{}');
      return adminData.name || 'Admin';
    } catch (e) {
      return 'Admin';
    }
  }
  
  if (userInfo.value) {
    return userInfo.value.username || 'Usuario';
  }
  
  return 'Usuario';
});

const getUserEmail = computed(() => {
  if (isAdmin.value) {
    try {
      const adminDataString = sessionStorage.getItem('admin');
      const adminData = JSON.parse(adminDataString || '{}');
      return adminData.email || '';
    } catch (e) {
      return '';
    }
  }
  
  if (userInfo.value) {
    return userInfo.value.email || '';
  }
  
  return '';
});

const fetchAdminData = () => {
  // Assuming 'admin' data is stored in localStorage after admin login
  const adminDataString = sessionStorage.getItem('admin'); // Or 'corporateAdmin'
  if (adminDataString) {
    const adminData = JSON.parse(sessionStorage.getItem('admin') || '{}');
    userName.value = adminData.name || 'Admin User'; // Fallback name
    userEmail.value = adminData.email || 'admin@example.com'; // Fallback email
    // Add other admin-specific data if needed
  }
};

const fetchCorporateAdminData = () => {
  const adminDataString = sessionStorage.getItem('corporateAdmin');
  if (adminDataString) {
    const adminData = JSON.parse(sessionStorage.getItem('admin') || '{}');
    userName.value = adminData.name || 'Corporate Admin';
    userEmail.value = adminData.email || 'corp.admin@example.com';
    // Potentially set a default or specific image for corporate admins
    userImage.value = adminData.profileImageUrl || '/default-corporate-admin-image.png';
  }
};
</script>

<template>
  <div class="flex h-full flex-col bg-surface border-r border-border">
    <div class="flex h-16 items-center justify-center bg-gradient-to-r from-orange-400 to-orange-600">
      <div class="flex items-center space-x-2">
        <div class="w-8 h-8 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center">
          <ChartBarIcon class="h-5 w-5 text-white" />
        </div>
        <h1 class="text-xl font-semibold text-white">LLM Flow</h1>
      </div>
    </div>
    
    <nav class="flex-1 space-y-1 px-2 py-4">
      <div v-for="item in filteredNavigation" :key="item.name">
        <router-link
          :to="item.href"
          custom
          v-slot="{ navigate }">
          <a @click="navigate"
            class="group relative flex items-center px-3 py-2 text-sm font-medium rounded-xl text-text-primary hover:text-white transition-all duration-300 cursor-pointer"
            :class="{ 'text-white': isCurrentRoute(item.href) || (item.name === 'Connect Sources' && (route.path.startsWith('/settings/sources') || route.name === 'CompetitorSources-details')) }">
            <!-- Gradient background -->
            <div class="absolute inset-0 bg-gradient-to-r rounded-xl transition-all duration-300"
                :class="[item.gradient, (isCurrentRoute(item.href) || (item.name === 'Connect Sources' && (route.path.startsWith('/settings/sources') || route.name === 'CompetitorSources-details'))) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100']"></div>
            
            <!-- Icon with glow effect -->
            <div class="relative z-10 mr-3">
              <component :is="item.icon" 
                        class="h-5 w-5 transition-all duration-300 group-hover:transform group-hover:scale-110"
                        :class="[
                          (isCurrentRoute(item.href) || (item.name === 'Connect Sources' && (route.path.startsWith('/settings/sources') || route.name === 'CompetitorSources-details'))) ? 'text-white' : 'text-' + item.gradient.split('-')[2] + '-500 group-hover:text-white'
                        ]"
                        aria-hidden="true" />
              <div class="absolute inset-0 bg-current rounded-full blur-sm opacity-0 group-hover:opacity-25 transition-opacity duration-300"></div>
            </div>
            
            <!-- Menu item text -->
            <span class="relative z-10">{{ item.name }}</span>

            <!-- NEW badge -->
            <span v-if="item.new"
                  class="relative z-10 ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-accent text-white rounded-full">
              NEW
            </span>
            
            <!-- Right border indicator -->
            <div class="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-l-full transition-all duration-300"
                :class="[item.gradient, (isCurrentRoute(item.href) || (item.name === 'Connect Sources' && (route.path.startsWith('/settings/sources') || route.name === 'CompetitorSources-details'))) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100']"></div>
          </a>
        </router-link>
      </div>
    </nav>

    <div class="p-4 bg-gradient-to-r from-orange-400 to-orange-600">
      <div class="flex items-center space-x-3">
        <div class="relative">
          <div class="w-10 h-10 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center text-lg font-semibold text-white">
            {{ getUserName.charAt(0) }}
          </div>
          <div class="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-white"></div>
        </div>
        <div>
          <p class="text-sm font-medium text-white">{{ getUserName }}</p>
          <p class="text-xs text-white/80">{{ getUserEmail }}</p>
        </div>
      </div>
    </div>
  </div>
</template>