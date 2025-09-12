<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navbar superior -->
    <nav class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex">
            <div class="flex-shrink-0 flex items-center">
              <img class="h-8 w-auto" src="@/assets/logo.svg" alt="Logo">
              <span class="ml-2 font-semibold text-indigo-600">Admin Panel</span>
            </div>
          </div>
          <div class="flex items-center">
            <span class="text-sm text-gray-700 mr-4">{{ adminName }}</span>
            <button 
              @click="logout"
              class="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>

    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Tabs de navegación -->
        <div class="border-b border-gray-200">
          <nav class="-mb-px flex space-x-8">
            <button
              @click="activeTab = 'marcas'"
              class="px-1 py-4 text-center text-sm font-medium"
              :class="activeTab === 'marcas' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              Brand Management
            </button>
            <button
              @click="activeTab = 'usuarios'"
              class="px-1 py-4 text-center text-sm font-medium"
              :class="activeTab === 'usuarios' ? 'border-b-2 border-indigo-500 text-indigo-600' : 'border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              User Management
            </button>
          </nav>
        </div>

        <!-- Contenido de las tabs -->
        <div class="mt-6">
          <!-- Gestión de Marcas -->
          <div v-if="activeTab === 'marcas'">
            <div class="sm:flex sm:items-center sm:justify-between">
              <div>
                <h3 class="text-lg leading-6 font-medium text-gray-900">Brands</h3>
                <p class="mt-1 text-sm text-gray-500">Manage registered brands</p>
              </div>
              <button
                @click="openAddMarcaModal"
                class="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                New Brand
              </button>
            </div>

            <!-- Lista de marcas -->
            <div class="mt-6 bg-white shadow overflow-hidden sm:rounded-md">
              <ul class="divide-y divide-gray-200">
                <li v-for="marca in marcas" :key="marca.id">
                  <div class="px-4 py-4 sm:px-6">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center">
                        <p class="text-sm font-medium text-indigo-600 truncate">{{ marca.name }}</p>
                        <span class="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          {{ marca.user_count }} users
                        </span>
                      </div>
                      <div class="flex space-x-2">
                        <button
                          @click="editMarca(marca)"
                          class="inline-flex items-center px-2.5 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                          Edit
                        </button>
                        <button
                          @click="confirmDeleteMarca(marca)"
                          class="inline-flex items-center px-2.5 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <div class="mt-2 sm:flex sm:justify-between">
                      <div class="sm:flex">
                        <p class="flex items-center text-sm text-gray-500">
                          {{ marca.description }}
                        </p>
                      </div>
                      <div class="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                        <p>
                          Created: {{ formatDate(marca.created_at) }}
                        </p>
                      </div>
                    </div>
                  </div>
                </li>
                <li v-if="marcas.length === 0" class="px-4 py-4 sm:px-6 text-center text-sm text-gray-500">
                  No brands registered. Add your first brand!
                </li>
              </ul>
            </div>
          </div>

          <!-- Gestión de Usuarios -->
          <div v-if="activeTab === 'usuarios'">
            <div class="sm:flex sm:items-center sm:justify-between">
              <div>
                <h3 class="text-lg leading-6 font-medium text-gray-900">Users</h3>
                <p class="mt-1 text-sm text-gray-500">Manage users by brand</p>
              </div>
              <button
                @click="openAddUserModal"
                class="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                New User
              </button>
            </div>

            <!-- Filtro por marca -->
            <div class="mt-4">
              <label for="marca-filter" class="block text-sm font-medium text-gray-700">Filter by brand</label>
              <select
                id="marca-filter"
                v-model="selectedMarcaFilter"
                class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
              >
                <option value="">All brands</option>
                <option v-for="marca in marcas" :key="marca.id" :value="marca.id">{{ marca.name }}</option>
              </select>
            </div>

            <!-- Lista de usuarios -->
            <div class="mt-6 bg-white shadow overflow-hidden sm:rounded-md">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Name</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Email</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Active</th>
                    <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Admin</th>
                    <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                      <span class="sr-only">Edit</span>
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="usuario in filteredUsuarios" :key="usuario.id">
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{{ usuario.username }}</td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{{ usuario.email }}</td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                      <span v-if="usuario.is_active" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Active</span>
                      <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Inactive</span>
                    </td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                      <span v-if="usuario.is_admin" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Admin</span>
                      <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">User</span>
                    </td>
                    <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                      <button
                        @click="editUsuario(usuario)"
                        class="text-indigo-600 hover:text-indigo-900"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal para añadir/editar marca -->
    <div v-if="showAddMarcaModal" class="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title-marca" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" @click="closeAddMarcaModal"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div>
              <div class="mt-3 text-center sm:mt-0 sm:text-left">
                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title-marca">
                  {{ editingMarca ? 'Edit Brand' : 'Add New Brand' }}
                </h3>
                <div class="mt-4 space-y-4">
                  <div>
                    <label for="marca-name" class="block text-sm font-medium text-gray-700">Name</label>
                    <div class="mt-1">
                      <input type="text" name="marca-name" id="marca-name" 
                        v-model="marcaForm.name"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
                    </div>
                  </div>
                  <div>
                    <label for="marca-description" class="block text-sm font-medium text-gray-700">Description</label>
                    <div class="mt-1">
                      <textarea id="marca-description" name="marca-description" rows="3" 
                        v-model="marcaForm.description"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"></textarea>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button type="button" 
              :disabled="!marcaForm.name"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm disabled:bg-indigo-300 disabled:cursor-not-allowed"
              @click="saveMarca"
            >
              {{ editingMarca ? 'Save Changes' : 'Add Brand' }}
            </button>
            <button type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              @click="closeAddMarcaModal"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal para añadir/editar usuario -->
    <div v-if="showAddUserModal" class="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title-user" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" @click="closeAddUserModal"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div>
              <div class="mt-3 text-center sm:mt-0 sm:text-left">
                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title-user">
                  {{ editingUsuario ? 'Edit User' : 'Add New User' }}
                </h3>
                <div class="mt-4 space-y-4">
                  <div>
                    <label for="usuario-marca" class="block text-sm font-medium text-gray-700">Brand</label>
                    <div class="mt-1">
                      <select id="usuario-marca" name="usuario-marca" 
                        v-model="usuarioForm.marca_id"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        required>
                        <option value="" disabled>Select a brand</option>
                        <option v-for="marca in marcas" :key="marca.id" :value="marca.id">{{ marca.name }}</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label for="usuario-username" class="block text-sm font-medium text-gray-700">Username</label>
                    <div class="mt-1">
                      <input type="text" name="usuario-username" id="usuario-username" 
                        v-model="usuarioForm.username"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
                    </div>
                  </div>
                  <div>
                    <label for="usuario-email" class="block text-sm font-medium text-gray-700">Email</label>
                    <div class="mt-1">
                      <input type="email" name="usuario-email" id="usuario-email" 
                        v-model="usuarioForm.email"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
                    </div>
                  </div>
                  <div>
                    <label for="usuario-password" class="block text-sm font-medium text-gray-700">Password</label>
                    <div class="mt-1">
                      <input type="password" name="usuario-password" id="usuario-password" 
                        v-model="usuarioForm.password"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
                    </div>
                    <p v-if="editingUsuario" class="mt-1 text-xs text-gray-500">Leave blank to keep current password</p>
                  </div>
                  <div class="mt-4">
                    <div class="relative flex items-start">
                      <div class="flex items-center h-5">
                        <input
                          id="is_active"
                          name="is_active"
                          type="checkbox"
                          v-model="usuarioForm.is_active"
                          class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                        />
                      </div>
                      <div class="ml-3 text-sm">
                        <label for="is_active" class="font-medium text-gray-700">Active User</label>
                      </div>
                    </div>
                  </div>
                  
                  <div class="mt-4">
                    <div class="relative flex items-start">
                      <div class="flex items-center h-5">
                        <input
                          id="is_admin"
                          name="is_admin"
                          type="checkbox"
                          v-model="usuarioForm.is_admin"
                          class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
                        />
                      </div>
                      <div class="ml-3 text-sm">
                        <label for="is_admin" class="font-medium text-gray-700">Brand Admin</label>
                        <p class="text-gray-500">Assign admin privileges to this user</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button type="button" 
              :disabled="!usuarioForm.username || !usuarioForm.email || (!editingUsuario && !usuarioForm.password) || !usuarioForm.marca_id"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm disabled:bg-indigo-300 disabled:cursor-not-allowed"
              @click="saveUsuario"
            >
              {{ editingUsuario ? 'Save Changes' : 'Add User' }}
            </button>
            <button type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              @click="closeAddUserModal"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de confirmación de eliminación -->
    <div v-if="showDeleteConfirmModal" class="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title-delete" role="dialog" aria-modal="true">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" @click="showDeleteConfirmModal = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                <svg class="h-6 w-6 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title-delete">
                  Confirm Deletion
                </h3>
                <div class="mt-2">
                  <p class="text-sm text-gray-500">
                    Are you sure you want to delete this brand? This action cannot be undone and will delete all associated users.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button type="button" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm"
              @click="deleteMarcaAction"
            >
              Delete
            </button>
            <button type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              @click="showDeleteConfirmModal = false"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '@/services/axiosInstance';

const router = useRouter();
const activeTab = ref('marcas');

// Estado del administrador
const adminName = ref('');

// Estado de marcas
const marcas = ref<any[]>([]);
const showAddMarcaModal = ref(false);
const editingMarca = ref(false);
const marcaToDeleteId = ref<number | null>(null);
const showDeleteConfirmModal = ref(false);

const marcaForm = reactive({
  id: null as number | null,
  name: '',
  description: ''
});

// Estado de usuarios
const usuarios = ref<any[]>([]);
const showAddUserModal = ref(false);
const editingUsuario = ref(false);
const selectedMarcaFilter = ref('');

const usuarioForm = reactive({
  id: null as number | null,
  marca_id: null as number | null,
  username: '',
  email: '',
  password: '',
  is_active: true,
  is_admin: false
});

// Computed
const filteredUsuarios = computed(() => {
  if (!selectedMarcaFilter.value) {
    return usuarios.value;
  }
  return usuarios.value.filter(u => u.marca_id === parseInt(selectedMarcaFilter.value));
});

// Métodos de ciclo de vida
onMounted(async () => {
  // Comprobar si hay un token de administrador
  const adminToken = sessionStorage.getItem('corporateAdminToken'); // <-- Cambiado a corporateAdminToken
  if (!adminToken) {
    router.push('/admin/login'); // Redirige a la ruta correcta de login de admin
    return;
  }

  try {
    const adminData = JSON.parse(sessionStorage.getItem('corporateAdmin') || '{}'); // <-- Cambiado a corporateAdmin
    adminName.value = adminData.name || 'Corporate Administrator'; // Ajustar nombre por defecto si es necesario

    // Configurar Axios para incluir el token en las solicitudes
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${adminToken}`; // <-- Cambiado a adminToken (que ahora contiene corporateAdminToken)
    
    // Cargar datos iniciales
    await loadMarcas();
    await loadUsuarios();
  } catch (error) {
    sessionStorage.removeItem('corporateAdmin'); // Limpiar storage en caso de error
    sessionStorage.removeItem('corporateAdminToken');
    router.push('/admin/login');
  }
});

// Métodos para marcas
async function loadMarcas() {
  try {
    const response = await apiClient.get('/admin/marcas');
    marcas.value = response.data;
  } catch (error) {
  }
}

function openAddMarcaModal() {
  resetMarcaForm();
  showAddMarcaModal.value = true;
}

function closeAddMarcaModal() {
  showAddMarcaModal.value = false;
}

function editMarca(marca: any) {
  marcaForm.id = marca.id;
  marcaForm.name = marca.name;
  marcaForm.description = marca.description || '';
  editingMarca.value = true;
  showAddMarcaModal.value = true;
}

function confirmDeleteMarca(marca: any) {
  marcaToDeleteId.value = marca.id;
  showDeleteConfirmModal.value = true;
}

async function saveMarca() {
  try {
    if (editingMarca.value) {
      await apiClient.put(`/admin/marcas/${marcaForm.id}`, marcaForm);
    } else {
      await apiClient.post('/admin/marcas', marcaForm);
    }
    
    await loadMarcas();
    resetMarcaForm();
    showAddMarcaModal.value = false;
  } catch (error) {
    alert('Hubo un error al guardar la marca. Por favor, inténtalo de nuevo.');
  }
}

async function deleteMarcaAction() {
  try {
    if (marcaToDeleteId.value === null) return;
    await apiClient.delete(`/admin/marcas/${marcaToDeleteId.value}`);
    await loadMarcas();
    await loadUsuarios(); // Recargar usuarios también, ya que pueden haberse eliminado usuarios asociados
    showDeleteConfirmModal.value = false;
    marcaToDeleteId.value = null;
  } catch (error) {
    alert('Hubo un error al eliminar la marca. Por favor, inténtalo de nuevo.');
  }
}

function resetMarcaForm() {
  marcaForm.id = null;
  marcaForm.name = '';
  marcaForm.description = '';
  editingMarca.value = false;
}

// Métodos para usuarios
async function loadUsuarios() {
  try {
    const response = await apiClient.get('/admin/usuarios');
    usuarios.value = response.data;
  } catch (error) {
  }
}

function openAddUserModal() {
  resetUsuarioForm();
  showAddUserModal.value = true;
}

function closeAddUserModal() {
  showAddUserModal.value = false;
}

function editUsuario(usuario: any) {
  usuarioForm.id = usuario.id;
  usuarioForm.marca_id = usuario.marca_id;
  usuarioForm.username = usuario.username;
  usuarioForm.email = usuario.email;
  usuarioForm.password = ''; // No enviamos la contraseña actual
  usuarioForm.is_active = usuario.is_active;
  usuarioForm.is_admin = usuario.is_admin;
  editingUsuario.value = true;
  showAddUserModal.value = true;
}

async function saveUsuario() {
  if (!usuarioForm.marca_id) {
    alert('Please select a brand for the new user.');
    return;
  }

  try {
    const payload = { ...usuarioForm };
    
    // If editing and no password, remove it
    if (editingUsuario.value && !payload.password) {
      delete payload.password;
    }
    
    // Ensure is_admin is boolean (or handle 0/1 if needed by backend)
    payload.is_admin = Boolean(payload.is_admin);

     // Debug log

    if (editingUsuario.value) {
      await apiClient.put(`/admin/usuarios/${usuarioForm.id}`, payload);
    } else {
      await apiClient.post('/admin/usuarios', payload);
    }
    
    await loadUsuarios();
    resetUsuarioForm();
    showAddUserModal.value = false;
  } catch (error: any) {
    console.error("Error saving user:", error.response?.data || error.message); // Log detailed error
    const errorMessage = error.response?.data?.detail || 'Hubo un error al guardar el usuario. Por favor, inténtalo de nuevo.';
    // Check for specific validation errors if backend provides them
    if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
         // Handle Pydantic validation errors (example)
         const validationErrors = error.response.data.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('\n');
         alert(`Validation Errors:\n${validationErrors}`);
    } else {
        alert(errorMessage);
    }
  }
}

async function toggleUsuarioStatus(usuario: any) {
  try {
    await apiClient.patch(`/admin/usuarios/${usuario.id}/toggle-status`);
    await loadUsuarios();
  } catch (error) {
    alert('Hubo un error al cambiar el estado del usuario. Por favor, inténtalo de nuevo.');
  }
}

function resetUsuarioForm() {
  usuarioForm.id = null;
  usuarioForm.marca_id = marcas.value.length > 0 ? marcas.value[0].id : null;
  usuarioForm.username = '';
  usuarioForm.email = '';
  usuarioForm.password = '';
  usuarioForm.is_active = true;
  usuarioForm.is_admin = false;
  editingUsuario.value = false;
}

function getMarcaName(marcaId: number | null): string {
  if (marcaId === null) return 'Desconocida';
  const marca = marcas.value.find(m => m.id === marcaId);
  return marca ? marca.name : 'Desconocida';
}

// Métodos generales
function formatDate(dateString: string | null): string {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString(); // Formato local
  } catch (e) {
    return dateString; // Devolver el original si hay error
  }
}

function logout() {
  sessionStorage.removeItem('corporateAdmin'); // Cambiado
  sessionStorage.removeItem('corporateAdminToken'); // Cambiado
  router.push('/admin/login');
}
</script> 