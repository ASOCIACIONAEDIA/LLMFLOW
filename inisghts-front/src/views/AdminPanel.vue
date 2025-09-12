<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-4">Panel de Administración</h1>
    <p>Bienvenido, administrador.</p>
    
    <nav class="mt-6">
      <ul class="space-y-2">
        <li>
          <router-link to="/admin/users" class="text-blue-600 hover:underline">Gestionar Usuarios</router-link>
        </li>
        <li>
          <router-link to="/admin/brands" class="text-blue-600 hover:underline">Gestionar Marcas (Subsecciones)</router-link>
        </li>
        <!-- Añadir más enlaces según sea necesario -->
      </ul>
    </nav>

    <div class="mt-8">
      <router-view></router-view> <!-- Aquí se mostrarán las sub-rutas como Gestionar Usuarios -->
    </div>

     <button @click="logout" class="mt-8 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-700">
      Cerrar Sesión
    </button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
// import { useAuthStore } from '@/stores/auth'; // Se creará más adelante
import apiClient from '@/services/axiosInstance'; // ADD THIS LINE

const router = useRouter();
// const authStore = useAuthStore();

const logout = () => {
  
  // authStore.logout();
  router.push('/login');
};
</script> 