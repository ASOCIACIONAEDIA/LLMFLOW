<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { 
  CalendarIcon, 
  UserGroupIcon,
  FunnelIcon,
  QuestionMarkCircleIcon,
  ChartBarIcon,
  MegaphoneIcon,
  ShoppingCartIcon,
  MapIcon,
  BuildingStorefrontIcon,
  PlusIcon,
  DocumentPlusIcon,
  GlobeEuropeAfricaIcon,
  DocumentTextIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  TrashIcon,
  ChevronUpIcon, 
  ChevronDownIcon,
  InformationCircleIcon,
  ArrowDownTrayIcon,
  ShareIcon,
  DocumentDuplicateIcon
} from '@heroicons/vue/24/outline'
import apiClient from '@/services/axiosInstance'
import { useRouter } from 'vue-router'
import ConfirmationModal from '@/components/ConfirmationModal.vue'

const router = useRouter()

// --- State Variables ---
const fetchedReports = ref<any[]>([])
const isLoadingReports = ref(true)
const reportsError = ref<string | null>(null)

// Modal State
const isConfirmDeleteModalOpen = ref(false)
const reportToDelete = ref<any | null>(null)
const modalTitle = ref('')
const modalMessage = ref('')

// Filter states
const selectedCategory = ref('all')
const selectedArchetype = ref('all')
const dateRange = ref({
  start: '',
  end: ''
})

// --- Static Data (Report Categories and Placeholder Archetypes) ---
const categories = [
  { id: 'all', name: 'All Categories' },
  { id: 'sentiment-analysis', name: 'Sentiment Analysis', icon: ChartBarIcon },
  { id: 'cognitive-biases', name: 'Cognitive Biases', icon: ChartBarIcon },
  { id: 'awareness-levels', name: 'Awareness Levels', icon: ChartBarIcon },
  { id: 'inference-analysis', name: 'Inference Analysis', icon: ChartBarIcon },
  { id: 'problem-solution', name: 'Problem-Solution', icon: MegaphoneIcon },
  { id: 'delivery-packaging', name: 'Delivery & Packaging', icon: ShoppingCartIcon },
  { id: 'purchase-factors', name: 'Purchase Factors', icon: MegaphoneIcon },
  { id: 'other', name: 'Other', icon: DocumentTextIcon }
]

const archetypes = [
  { id: 'all', name: 'All Archetypes', avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=all&backgroundColor=cbd5e1' },
  { id: 'General', name: 'General Analysis', avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=general&backgroundColor=e5e7eb' },
  { id: 'The Curious Explorer', name: 'The Curious Explorer', avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=explorer&backgroundColor=b7c7ff' },
  { id: 'The Mindful Vegan', name: 'The Mindful Vegan', avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=vegan&backgroundColor=96ffd4' },
  { id: 'The Passionate Foodie', name: 'The Passionate Foodie', avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=foodie&backgroundColor=fecdd3' }
]

const sortedReports = computed(() => {
  if (!filteredReports.value || !sortBy.value) return filteredReports.value

  return [...filteredReports.value].sort((a, b) => {
    let aValue = a[sortBy.value]
    let bValue = b[sortBy.value]

    // Manejo especial para fechas
    if (sortBy.value === 'generated_at') {
      aValue = new Date(aValue)
      bValue = new Date(bValue)
    }

    // Manejo especial para strings
    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = bValue.toLowerCase()
    }

    let comparison = 0
    if (aValue > bValue) comparison = 1
    if (aValue < bValue) comparison = -1

    return sortDirection.value === 'desc' ? comparison * -1 : comparison
  })
})

// ===== FUNCIONES FALTANTES =====
// Añade estas funciones después de formatNumber

// **toggleRowExpansion**: Alterna la expansión de una fila específica
// @param {string} reportId - ID del reporte para expandir/contraer
const toggleRowExpansion = (reportId) => {
  const newSet = new Set(expandedRows.value)
  if (newSet.has(reportId)) {
    newSet.delete(reportId)
  } else {
    newSet.add(reportId)
  }
  expandedRows.value = newSet
}

// **expandAllRows**: Expande o contrae todas las filas según el estado actual
// Si todas están expandidas, las contrae. Si no, las expande todas.
const expandAllRows = () => {
  if (allRowsExpanded.value) {
    expandedRows.value = new Set()
  } else {
    const newSet = new Set()
    filteredReports.value.forEach(report => {
      newSet.add(report._id)
    })
    expandedRows.value = newSet
  }
}

// **applySorting**: Aplica el ordenamiento cuando cambia el campo de ordenamiento
// Se ejecuta cuando el usuario selecciona un campo diferente para ordenar
const applySorting = () => {
  // El ordenamiento se maneja automáticamente por el computed sortedReports
  // Esta función está disponible para lógica adicional si es necesaria
  console.log('Sorting applied:', sortBy.value, sortDirection.value)
}

// **toggleSortDirection**: Cambia entre ordenamiento ascendente y descendente
const toggleSortDirection = () => {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

// **applyFilters**: Método que aplica los filtros seleccionados
// Como ya tienes filteredReports computed, esta función puede estar vacía
// o puedes usarla para lógica adicional de filtrado
const applyFilters = () => {
  // Los filtros se aplican automáticamente por el computed filteredReports
  // Puedes añadir lógica adicional aquí si es necesaria
}

// **formatReportType**: Formatea el tipo de reporte para mostrar
// @param {string} reportType - Tipo de reporte a formatear
// @returns {string} - Tipo de reporte formateado
const formatReportType = (reportType) => {
  if (!reportType) return 'N/A'
  return reportType.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// **formatDate**: Formatea una fecha para mostrar de forma legible
// @param {string} dateString - Fecha en formato ISO
// @returns {string} - Fecha formateada
const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// **formatDateTime**: Formatea fecha y hora completa
// @param {string} dateString - Fecha en formato ISO
// @returns {string} - Fecha y hora formateadas
const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// **formatStatus**: Formatea el estado del reporte
// @param {string} status - Estado del reporte
// @returns {string} - Estado formateado
const formatStatus = (status) => {
  const statusMap = {
    'completed': 'Completed',
    'processing': 'Processing',
    'failed': 'Failed',
    'pending': 'Pending'
  }
  return statusMap[status] || status
}

// **getStatusBadgeClass**: Obtiene las clases CSS para el badge de estado
// @param {string} status - Estado del reporte
// @returns {string} - Clases CSS para el badge
const getStatusBadgeClass = (status) => {
  const classMap = {
    'completed': 'bg-green-100 text-green-800',
    'processing': 'bg-yellow-100 text-yellow-800',
    'failed': 'bg-red-100 text-red-800',
    'pending': 'bg-gray-100 text-gray-800'
  }
  return classMap[status] || 'bg-gray-100 text-gray-800'
}

// **downloadReport**: Descarga un reporte específico
// @param {string} reportId - ID del reporte a descargar
const downloadReport = (reportId) => {
  console.log('Downloading report:', reportId)
  // Aquí implementarías la lógica para descargar el reporte
  // Por ejemplo, hacer una petición a tu API para obtener el archivo PDF
}

// **shareReport**: Comparte un reporte específico
// @param {string} reportId - ID del reporte a compartir
const shareReport = (reportId) => {
  console.log('Sharing report:', reportId)
  // Aquí implementarías la lógica para compartir el reporte
  // Por ejemplo, generar un enlace compartible o abrir modal de compartir
}

// **duplicateReport**: Duplica un reporte específico
// @param {string} reportId - ID del reporte a duplicar
const duplicateReport = (reportId) => {
  console.log('Duplicating report:', reportId)
  // Aquí implementarías la lógica para duplicar el reporte
  // Por ejemplo, navegar a la página de creación con los mismos parámetros
}

const allRowsExpanded = computed(() => {
  return filteredReports.value.length > 0 && expandedRows.value.size === filteredReports.value.length
})

const expandedRows = ref(new Set())

// **sortBy**: Campo por el cual ordenar (generated_at, report_type, archetype_identifier)
const sortBy = ref('generated_at')

// **sortDirection**: Dirección del ordenamiento ('asc' para ascendente, 'desc' para descendente)
const sortDirection = ref('desc')

// --- Computed Property: Filtered Reports ---
const filteredReports = computed(() => {
  return fetchedReports.value.filter(report => {
    const reportType = report.report_type || 'other'
    const matchesCategory = selectedCategory.value === 'all' || reportType === selectedCategory.value

    const archetypeIdentifier = report.archetype_identifier || 'General'
    const matchesArchetype = selectedArchetype.value === 'all' || archetypeIdentifier.toLowerCase() === selectedArchetype.value.toLowerCase()

    let matchesDate = true
    if (dateRange.value.start && dateRange.value.end && report.generated_at) {
      try {
        const reportDate = new Date(report.generated_at)
        const startDate = new Date(dateRange.value.start)
        const endDate = new Date(dateRange.value.end)
        endDate.setHours(23, 59, 59, 999)
        matchesDate = reportDate >= startDate && reportDate <= endDate
      } catch (e) {
        console.error("Error parsing date for filtering:", e)
        matchesDate = false
      }
    } else if ((dateRange.value.start || dateRange.value.end) && !report.generated_at) {
      matchesDate = false
    }

    return matchesCategory && matchesArchetype && matchesDate
  })
})

// --- Helper Functions ---

// Format relative time
const formatRelativeTime = (timestamp: string | null | undefined) => {
  if (!timestamp) return 'Date unavailable'
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    const months = Math.floor(days / 30)
    const years = Math.floor(days / 365)

    if (years > 0) return `${years} year${years > 1 ? 's' : ''} ago`
    if (months > 0) return `${months} month${months > 1 ? 's' : ''} ago`
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
    return 'Just now'
  } catch (e) {
    console.error("Error formatting relative time:", e)
    return 'Invalid date'
  }
}

// Get category details
const getCategoryDetails = (reportType: string | undefined | null) => {
  const type = reportType || 'other'
  const found = categories.find(c => c.id === type)
  return found || { id: type, name: type.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), icon: DocumentTextIcon }
}

// Get archetype details
const getArchetypeDetails = (archetypeIdentifier: string | null | undefined) => {
  const identifier = archetypeIdentifier || 'General'
  const found = archetypes.find(a => a.id.toLowerCase() === identifier.toLowerCase())
  if (found) return found

  const nameSeed = identifier.toLowerCase().replace(/[^a-z0-9]/g, '-') || 'unknown'
  return {
    id: identifier,
    name: identifier,
    avatar: `https://api.dicebear.com/7.x/personas/svg?seed=${nameSeed}&backgroundColor=e0e0e0`
  }
}

const navigateToNewReport = () => {
  router.push('/reports/new')
}

// Navigate to view report detail page
const viewReport = (reportId: string | undefined) => {
  if (reportId) {
    router.push(`/reports/view/${reportId}`)
  } else {
    console.error("Cannot view report: Missing report ID.")
    alert("Sorry, the ID for this report is missing.")
  }
}

// --- Delete Report Logic ---
const openConfirmDeleteModal = (report: any) => {
  if (!report || !report._id) {
    console.error("Cannot delete report: Invalid report object or missing ID.")
    alert("Could not prepare deletion: Invalid report data.")
    return
  }
  reportToDelete.value = report
  const reportDisplayName = report.report_type?.replace(/[-_]/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'N/A'
  const archetypeDisplayName = report.archetype_identifier && report.archetype_identifier !== 'General' ? ` (${report.archetype_identifier})` : ''
  
  modalTitle.value = `Delete Report: "${reportDisplayName}${archetypeDisplayName}"?`
  modalMessage.value = `Are you sure you want to delete this report? This action cannot be undone.`
  isConfirmDeleteModalOpen.value = true
}

const handleConfirmDelete = async () => {
  if (!reportToDelete.value || !reportToDelete.value._id) {
    isConfirmDeleteModalOpen.value = false
    reportToDelete.value = null
    console.error("Deletion failed: Report data became unavailable.")
    return
  }

  const reportIdToDelete = reportToDelete.value._id
  // const reportDisplayName = reportToDelete.value.report_type?.replace(/[-_]/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'N/A'
  // const archetypeDisplayName = reportToDelete.value.archetype_identifier && reportToDelete.value.archetype_identifier !== 'General' ? ` (${reportToDelete.value.archetype_identifier})` : ''


  try {
    const token = sessionStorage.getItem('token')
    if (!token) {
      // alert("Authentication error. Please log in again.") // REMOVED
      console.error("Authentication error. Token not found.") // Log instead
      router.push('/login')
      isConfirmDeleteModalOpen.value = false
      reportToDelete.value = null
      return
    }

    await apiClient.delete(`/reports/generated/${reportIdToDelete}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    // Remove the report from the local list for immediate UI update
    fetchedReports.value = fetchedReports.value.filter(r => r._id !== reportIdToDelete)
    // alert(`Report "${reportDisplayName}${archetypeDisplayName}" deleted successfully.`) // REMOVED
     // Log instead

  } catch (error: any) {
    console.error(`Failed to delete report ${reportIdToDelete}:`, error)
    // Consider a more user-friendly, non-alert notification system here for errors.
    // For example, setting an error message in a ref and displaying it on the page.
    if (error.response && error.response.data && error.response.data.detail) {
      // alert(`Failed to delete report: ${error.response.data.detail}`) // REMOVED
      console.error(`Failed to delete report: ${error.response.data.detail}`)
    } else if (error.message) {
      // alert(`Failed to delete report: ${error.message}`) // REMOVED
      console.error(`Failed to delete report: ${error.message}`)
    } else {
      // alert('An unexpected error occurred while deleting the report.') // REMOVED
      console.error('An unexpected error occurred while deleting the report.')
    }
    if (error.response && error.response.status === 401) {
      router.push('/login');
    }
  } finally {
    isConfirmDeleteModalOpen.value = false
    reportToDelete.value = null
  }
}

const handleCancelDelete = () => {
  isConfirmDeleteModalOpen.value = false
  reportToDelete.value = null
}

// Format number with commas
const formatNumber = (num: number | undefined | null) => {
  if (num === undefined || num === null) return 'N/A'
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

// --- Data Fetching Logic ---
async function loadReports() {
  isLoadingReports.value = true
  reportsError.value = null
  fetchedReports.value = []

  try {
    const token = sessionStorage.getItem('token')
    if (!token) {
      throw new Error("Authentication token not found. Please log in.")
    }

    const response = await apiClient.get('/reports/generated', {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (Array.isArray(response.data)) {
      fetchedReports.value = response.data
    } else {
      throw new Error("Received invalid data format from the server.")
    }

  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      reportsError.value = `Failed to load reports: ${error.response.data.detail}`
    } else if (error.message) {
      reportsError.value = error.message
    } else {
      reportsError.value = 'An unexpected error occurred while loading reports.'
    }
    if (error.response && error.response.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoadingReports.value = false
  }
}

// --- Lifecycle Hook ---
onMounted(() => {
  loadReports()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Title with tooltip - mantiene la estructura original -->
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-display font-bold text-text-primary">Generated Reports</h1>
        <div class="group relative">
          <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
          <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <p class="text-sm text-text-secondary">
              View and manage all your generated reports. Click on rows to expand and see detailed information.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters - reutiliza la estructura existente -->
    <div class="bg-white rounded-2xl shadow-sm border border-border p-4 sm:p-6">
      <div class="flex items-center space-x-2 mb-6">
        <FunnelIcon class="h-5 w-5 text-primary" />
        <h2 class="text-lg font-display font-semibold text-text-primary">Filters</h2>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <!-- Category Filter -->
        <div class="space-y-2">
          <label class="block text-sm font-medium text-text-secondary">Category (Report Type)</label>
          <select
            v-model="selectedCategory"
            @change="applyFilters"
            class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20"
          >
            
            <option v-for="category in categories" :key="category.id" :value="category.id">
              {{ category.name }}
            </option>
          </select>
        </div>

        <!-- Archetype Filter -->
        <div class="space-y-2">
          <label class="block text-sm font-medium text-text-secondary">Archetype</label>
          <select
            v-model="selectedArchetype"
            @change="applyFilters"
            class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20"
          >
            
            <option v-for="archetype in archetypes" :key="archetype.id" :value="archetype.id">
              {{ archetype.name }}
            </option>
          </select>
        </div>

        <!-- Date Range -->
        <div class="space-y-2">
          <label class="block text-sm font-medium text-text-secondary">Generation Date Range</label>
          <div class="grid grid-cols-2 gap-2 sm:gap-4">
            <input
              type="date"
              v-model="dateRange.start"
              @change="applyFilters"
              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20"
            />
            <input
              type="date"
              v-model="dateRange.end"
              :min="dateRange.start || undefined"
              @change="applyFilters"
              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoadingReports" class="text-center py-10">
      <ArrowPathIcon class="h-8 w-8 text-primary animate-spin mx-auto mb-4" />
      <p class="text-text-secondary">Loading reports...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="reportsError" class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
      <ExclamationCircleIcon class="h-6 w-6 text-red-500 mx-auto mb-2" />
      <p class="text-red-700 font-medium">Error Loading Reports</p>
      <p class="text-sm text-red-600 mt-1">{{ reportsError }}</p>
    </div>

    <!-- No Reports Found State -->
    <div v-else-if="!filteredReports.length && !isLoadingReports" class="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
      <DocumentTextIcon class="h-10 w-10 text-amber-400 mx-auto mb-3" />
      <p class="text-amber-700 font-medium">No Reports Found</p>
      <p class="text-sm text-amber-600 mt-1">Try adjusting your filters or generate a new report.</p>
    </div>

    <!-- Botón Generar Nuevo Reporte -->
    <div v-else class="flex justify-end mb-4">
      <button 
        @click="navigateToNewReport"
        class="px-6 py-3 bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-medium rounded-xl transition-all duration-300 flex items-center"
      >
        <PlusIcon class="h-5 w-5 mr-2" />
        Generate New Report
      </button>
    </div>

    <!-- Reports Table -->
    <div v-else class="bg-white rounded-2xl shadow-sm border border-border overflow-hidden">
      <!-- Table Controls -->
      <div class="p-4 border-b border-border bg-surface">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <span class="text-sm text-text-secondary">
              {{ filteredReports.length }} report{{ filteredReports.length !== 1 ? 's' : '' }} found
            </span>
            <button 
              @click="expandAllRows"
              class="text-sm text-primary hover:text-primary-light font-medium"
            >
              {{ allRowsExpanded ? 'Collapse All' : 'Expand All' }}
            </button>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-sm text-text-secondary">Sort by:</span>
            <select v-model="sortBy" @change="applySorting" class="text-sm border-border rounded-lg px-2 py-1">
              <option value="generated_at">Date Generated</option>
              <option value="report_type">Report Type</option>
              <option value="archetype_identifier">Archetype</option>
            </select>
            <button 
              @click="toggleSortDirection"
              class="p-1 text-text-secondary hover:text-primary rounded"
            >
              <ChevronUpIcon v-if="sortDirection === 'asc'" class="h-4 w-4" />
              <ChevronDownIcon v-else class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-surface">
            <tr class="text-left">
              <th class="p-4 text-sm font-semibold text-text-primary">Report</th>
              <th class="p-4 text-sm font-semibold text-text-primary">Category</th>
              <th class="p-4 text-sm font-semibold text-text-primary">Archetype</th>
              <th class="p-4 text-sm font-semibold text-text-primary">Generated</th>
              <th class="p-4 text-sm font-semibold text-text-primary">Status</th>
              <th class="p-4 text-sm font-semibold text-text-primary text-center">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <template v-for="report in sortedReports" :key="report._id">
              <!-- Main Row -->
              <tr 
                class="hover:bg-gray-50 cursor-pointer transition-colors"
                @click="toggleRowExpansion(report._id)"
              >
                <td class="p-4">
                  <div class="flex items-center space-x-3">
                    <div class="flex-shrink-0">
                      <img 
                        :src="getArchetypeDetails(report.archetype_identifier).avatar"
                        :alt="getArchetypeDetails(report.archetype_identifier).name"
                        class="w-10 h-10 rounded-lg shadow-sm"
                      />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-text-primary">
                        {{ formatReportType(report.report_type) }}
                      </div>
                      <div class="text-xs text-text-secondary">ID: {{ report._id }}</div>
                    </div>
                    <div class="ml-auto">
                      <ChevronDownIcon 
                        :class="[
                          'h-4 w-4 text-text-secondary transform transition-transform',
                          expandedRows.has(report._id) ? 'rotate-180' : ''
                        ]"
                      />
                    </div>
                  </div>
                </td>
                <td class="p-4">
                  <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                    <component :is="getCategoryDetails(report.report_type).icon" class="h-3 w-3 mr-1.5" />
                    {{ getCategoryDetails(report.report_type).name }}
                  </span>
                </td>
                <td class="p-4">
                  <div class="flex items-center space-x-2">
                    <img 
                      :src="getArchetypeDetails(report.archetype_identifier).avatar"
                      :alt="getArchetypeDetails(report.archetype_identifier).name"
                      class="w-8 h-8 rounded-lg flex-shrink-0 shadow-sm"
                    />
                    <span class="text-sm text-text-primary">{{ report.archetype_identifier }}</span>
                  </div>
                </td>
                <td class="p-4">
                  <div class="text-sm text-text-primary">{{ formatDate(report.generated_at) }}</div>
                  <div class="text-xs text-text-secondary">{{ formatRelativeTime(report.generated_at) }}</div>
                </td>
                <td class="p-4">
                  <span 
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      getStatusBadgeClass(report.status || 'completed')
                    ]"
                  >
                    {{ formatStatus(report.status || 'completed') }}
                  </span>
                </td>
                <td class="p-4" @click.stop>
                  <div class="flex items-center justify-center space-x-2">
                    <button 
                      @click="viewReport(report._id)"
                      class="px-3 py-1.5 bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white text-xs font-medium rounded-lg transition-all duration-300"
                    >
                      View Report
                    </button>
                    <button 
                      @click="openConfirmDeleteModal(report)"
                      title="Delete Report"
                      class="p-1.5 text-gray-400 hover:text-red-500 rounded-md hover:bg-red-100/50 transition-colors"
                    >
                      <TrashIcon class="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Expanded Row -->
              <tr 
                v-if="expandedRows.has(report._id)"
                class="bg-gray-50"
              >
                <td colspan="6" class="p-0">
                  <div class="p-6 space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      <!-- Filtros Aplicados -->
                      <div class="space-y-3">
                        <h4 class="text-sm font-semibold text-text-primary flex items-center">
                          <FunnelIcon class="h-4 w-4 mr-2 text-primary" />
                          Applied Filters
                        </h4>
                        <div class="space-y-2">
                          <div v-if="report.filters?.sources?.length">
                            <span class="text-xs font-medium text-text-secondary">Sources:</span>
                            <div class="flex flex-wrap gap-1 mt-1">
                              <span 
                                v-for="source in report.filters.sources" 
                                :key="source"
                                class="inline-flex items-center px-2 py-1 rounded-md bg-blue-100 text-blue-800 text-xs"
                              >
                                {{ source }}
                              </span>
                            </div>
                          </div>
                          <div v-if="report.filters?.countries?.length">
                            <span class="text-xs font-medium text-text-secondary">Countries:</span>
                            <div class="flex gap-1 mt-1">
                              <span 
                                v-for="country in report.filters.countries" 
                                :key="country"
                                :class="`fi fi-${country.toLowerCase()} text-sm`" 
                                :title="country"
                              >
                              </span>
                            </div>
                          </div>
                          <div v-if="!report.filters?.sources?.length && !report.filters?.countries?.length">
                            <span class="text-xs text-text-secondary italic">
                              No specific filters applied for this report.
                            </span>
                          </div>
                        </div>
                      </div>

                      <!-- Estadísticas -->
                      <div class="space-y-3">
                        <h4 class="text-sm font-semibold text-text-primary flex items-center">
                          <ChartBarIcon class="h-4 w-4 mr-2 text-primary" />
                          Report Statistics
                        </h4>
                        <div class="grid grid-cols-2 gap-3">
                          <div class="text-center p-3 bg-white rounded-lg border">
                            <div class="text-lg font-bold text-primary">{{ report.insights_count || 'N/A' }}</div>
                            <div class="text-xs text-text-secondary">Insights</div>
                          </div>
                          <div class="text-center p-3 bg-white rounded-lg border">
                            <div class="text-lg font-bold text-primary">{{ report.recommendations_count || 'N/A' }}</div>
                            <div class="text-xs text-text-secondary">Recommendations</div>
                          </div>
                        </div>
                      </div>

                      <!-- Información Técnica -->
                      <div class="space-y-3">
                        <h4 class="text-sm font-semibold text-text-primary flex items-center">
                          <InformationCircleIcon class="h-4 w-4 mr-2 text-primary" />
                          Technical Info
                        </h4>
                        <div class="space-y-2 text-sm">
                          <div class="flex justify-between">
                            <span class="text-text-secondary">File Size:</span>
                            <span class="text-text-primary">{{ report.file_size || 'N/A' }}</span>
                          </div>
                          <div class="flex justify-between">
                            <span class="text-text-secondary">Generated:</span>
                            <span class="text-text-primary">{{ formatDateTime(report.generated_at) }}</span>
                          </div>
                          <div class="flex justify-between">
                            <span class="text-text-secondary">Format:</span>
                            <span class="text-text-primary">PDF</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Acciones Adicionales -->
                    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                      <button 
                        @click="downloadReport(report._id)"
                        class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition-colors flex items-center"
                      >
                        <ArrowDownTrayIcon class="h-4 w-4 mr-2" />
                        Download
                      </button>
                      <button 
                        @click="shareReport(report._id)"
                        class="px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 text-sm font-medium rounded-lg transition-colors flex items-center"
                      >
                        <ShareIcon class="h-4 w-4 mr-2" />
                        Share
                      </button>
                      <button 
                        @click="duplicateReport(report._id)"
                        class="px-4 py-2 bg-green-100 hover:bg-green-200 text-green-700 text-sm font-medium rounded-lg transition-colors flex items-center"
                      >
                        <DocumentDuplicateIcon class="h-4 w-4 mr-2" />
                        Duplicate
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirmation Modal - reutiliza el componente existente -->
    <ConfirmationModal
      :open="isConfirmDeleteModalOpen"
      :title="modalTitle"
      :message="modalMessage"
      confirm-button-text="Delete"
      cancel-button-text="Cancel"
      @confirm="handleConfirmDelete"
      @cancel="handleCancelDelete"
    />
  </div>
</template>