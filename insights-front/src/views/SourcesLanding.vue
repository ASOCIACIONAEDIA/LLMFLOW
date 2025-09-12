<script setup lang="ts">
import { useRouter } from 'vue-router';
import { BuildingStorefrontIcon, UserGroupIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';

const router = useRouter();

const navigateTo = (path: string) => {
  router.push(path);
};
</script>

<template>
  <div class="space-y-8 p-4 md:p-6 lg:p-8">
    <div class="mb-6">
      <h1 class="text-2xl md:text-3xl font-display font-bold ">Connect Sources</h1>
      <p class="text-text-secondary mt-1">Manage your own data sources or track your competitors.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- My Sources Card -->
      <div @click="navigateTo('/settings/sources/my-sources')"
           class="bg-white rounded-2xl shadow-lg border border-border overflow-hidden cursor-pointer group hover:shadow-xl hover:border-primary/50 transition-all duration-300">
        <div class="p-6">
          <div class="flex items-center space-x-4">
            <div class="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600">
              <BuildingStorefrontIcon class="h-7 w-7 text-amber-600" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-text-primary">My Sources</h2>
              <p class="text-sm text-text-secondary">Connect and manage your business's review platforms.</p>
            </div>
          </div>
        </div>
        <div class="bg-gray-50/50 px-6 py-3 flex items-center justify-end text-sm font-medium text-amber-600 group-hover:text-primary-dark transition-colors">
          <span text-amber-600>Go to My Sources</span>
          <ChevronRightIcon class="h-5 w-5 ml-1 transform group-hover:translate-x-1 transition-transform text-amber-600" />
        </div>
      </div>

      <!-- Competitor Sources Card -->
      <div @click="navigateTo('/settings/sources/competitors')"
           class="bg-white rounded-2xl shadow-lg border border-border overflow-hidden cursor-pointer group hover:shadow-xl hover:border-primary/50 transition-all duration-300">
        <div class="p-6">
          <div class="flex items-center space-x-4">
            <div class="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
              <UserGroupIcon class="h-7 w-7 text-amber-600" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-text-primary">Competitor Sources</h2>
              <p class="text-sm text-text-secondary">Track competitor reviews to gain market insights.</p>
            </div>
          </div>
        </div>
        <div class="bg-gray-50/50 px-6 py-3 flex items-center justify-end text-sm font-medium text-amber-600 group-hover:text-amber-800 transition-colors">
          <span>Go to Competitor Sources</span>
          <ChevronRightIcon class="h-5 w-5 ml-1 transform group-hover:translate-x-1 transition-transform" />
        </div>
      </div>
    </div>
  </div>
</template> 