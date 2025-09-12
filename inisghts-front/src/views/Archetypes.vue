<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { 
  QuestionMarkCircleIcon,
  CpuChipIcon,
  XMarkIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  CursorArrowRaysIcon
} from '@heroicons/vue/24/outline'
import apiClient from '@/services/axiosInstance'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Import Pinia store
import { useReportStore } from '@/store/reportStore'

const reportStore = useReportStore()

// --- User Info from sessionStorage ---
const getUserInfo = () => {
  const userString = sessionStorage.getItem('user')
  if (userString) {
    try {
      const parsedUser = JSON.parse(userString)
      return parsedUser
    } catch (e) {
      console.error('Error parsing user from sessionStorage:', e)
      return null
    }
  }
  return null
}

const userInfo = computed(() => getUserInfo())

// --- Admin Check Logic ---
const isAdmin = computed(() => {
  return !!sessionStorage.getItem('adminToken')
})

const isUserAdmin = computed(() => {
  if (!userInfo.value) return false
  return userInfo.value.is_admin === 1 || userInfo.value.is_admin === true
})

const canManageArchetypes = computed(() => {
  return isAdmin.value || isUserAdmin.value
})

// --- Estado para Generación ---
const isGenerating = computed(() => reportStore.isGeneratingFocusedArchetype)
const generationError = computed(() => reportStore.focusedArchetypeGenerationError)

// --- Estado del Modal de Generación ---
const isGenerationModalOpen = ref(false)
const selectedBinSize = ref<'1m' | '3m' | '6m'>('1m')
const selectedTimeInterval = ref<{ start: string; end: string; label: string } | null>(null)
const isLoadingChartData = ref(false)
const chartData = ref<any>(null)
const rawHistoricalData = ref<any>(null)

const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index' as const
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
    },
    title: {
      display: true,
      text: 'Historical Review Volume - Click on a bar to select time period'
    },
    tooltip: {
      callbacks: {
        afterLabel: function(context: any) {
          return 'Click to select this period for analysis'
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        stepSize: 1
      }
    },
    x: {
      ticks: {
        maxRotation: 45,
        minRotation: 0
      }
    }
  },
  onHover: (event: any, elements: any) => {
    if (event?.native?.target) {
      event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default'
    }
  },
  onClick: (event: any, elements: any) => {
    if (elements.length > 0) {
      selectTimeInterval(elements[0].index)
    }
  }
})

// --- Computed property for current user's brand name from sessionStorage ---
const currentUserBrandName = computed(() => {
  const user = getUserInfo()
  return user?.brandName || 'DefaultBrand'
})

// --- Bin size options ---
const binSizeOptions = [
  { value: '1m', label: '1 Month', description: 'Group reviews by monthly periods' },
  { value: '3m', label: '3 Months', description: 'Group reviews by quarterly periods' },
  { value: '6m', label: '6 Months', description: 'Group reviews by semi-annual periods' }
]

// --- Función para cargar datos históricos completos ---
async function loadAllHistoricalData() {
  isLoadingChartData.value = true
  
  try {
    // Get all historical data by setting a very early start date
    const veryEarlyDate = new Date('2020-01-01')
    const currentDate = new Date()

    const params = {
      start_date: veryEarlyDate.toISOString(),
      end_date: currentDate.toISOString()
    }

    const response = await apiClient.get('/analytics/review-volume-trend', { params })
    rawHistoricalData.value = response.data
    
    // Process data according to selected bin size
    processDataByBinSize(selectedBinSize.value)
    
  } catch (error: any) {
    console.error('Error loading historical data:', error)
    // Set empty chart data on error
    chartData.value = {
      labels: [],
      datasets: [{
        label: 'Review Count',
        data: [],
        backgroundColor: [],
        borderColor: '#6366F1',
        borderWidth: 1
      }]
    }
  } finally {
    isLoadingChartData.value = false
  }
}

// --- Función para procesar datos según el bin size ---
function processDataByBinSize(binSize: '1m' | '3m' | '6m') {
  if (!rawHistoricalData.value) return

  const labels = rawHistoricalData.value.labels || []
  const cumulativeData = rawHistoricalData.value.datasets?.[0]?.data || []
  
  // Convert cumulative data to discrete period counts
  const discreteData: number[] = []
  for (let i = 0; i < cumulativeData.length; i++) {
    if (i === 0) {
      discreteData.push(cumulativeData[i] || 0)
    } else {
      discreteData.push((cumulativeData[i] || 0) - (cumulativeData[i - 1] || 0))
    }
  }
  
  let processedLabels: string[] = []
  let processedData: number[] = []

  // Aggregate based on bin size
  if (binSize === '1m') {
    // Use monthly data as-is (discrete counts per month)
    processedLabels = [...labels]
    processedData = [...discreteData]
  } else if (binSize === '3m') {
    // Group by 3-month periods
    for (let i = 0; i < labels.length; i += 3) {
      const startLabel = labels[i]
      const endLabel = labels[i + 2] || labels[i + 1] || labels[i]
      const label = labels[i + 2] ? `${startLabel} - ${endLabel}` : 
                   labels[i + 1] ? `${startLabel} - ${labels[i + 1]}` : startLabel
      const value = (discreteData[i] || 0) + (discreteData[i + 1] || 0) + (discreteData[i + 2] || 0)
      processedLabels.push(label)
      processedData.push(value)
    }
  } else if (binSize === '6m') {
    // Group by 6-month periods
    for (let i = 0; i < labels.length; i += 6) {
      const startLabel = labels[i]
      const endLabel = labels[i + 5] || labels[i + 4] || labels[i + 3] || labels[i + 2] || labels[i + 1] || labels[i]
      const label = labels[i + 5] ? `${startLabel} - ${endLabel}` : 
                   labels[i + 4] ? `${startLabel} - ${labels[i + 4]}` :
                   labels[i + 3] ? `${startLabel} - ${labels[i + 3]}` :
                   labels[i + 2] ? `${startLabel} - ${labels[i + 2]}` :
                   labels[i + 1] ? `${startLabel} - ${labels[i + 1]}` : startLabel
      const value = (discreteData[i] || 0) + (discreteData[i + 1] || 0) + (discreteData[i + 2] || 0) + 
                   (discreteData[i + 3] || 0) + (discreteData[i + 4] || 0) + (discreteData[i + 5] || 0)
      processedLabels.push(label)
      processedData.push(value)
    }
  }

  // Create background colors (highlight selected bar)
  const backgroundColors = processedData.map((_, index) => {
    if (selectedTimeInterval.value && index === getSelectedBarIndex()) {
      return 'rgba(250, 187, 0, 0.8)' // Purple for selected
    }
    return 'rgba(252, 116, 13, 0.92)' // Default oranfe
  })

  chartData.value = {
    labels: processedLabels,
    datasets: [{
      label: 'Reviews in Period',
      data: processedData,
      backgroundColor: backgroundColors,
      borderColor: 'rgba(250, 187, 0, 0.8)',
      borderWidth: 1,
      hoverBackgroundColor: 'rgba(250, 187, 0, 0.8)'
    }]
  }
}

// --- Función para manejar cambio de bin size ---
async function handleBinSizeChange(binSize: '1m' | '3m' | '6m') {
  selectedBinSize.value = binSize
  selectedTimeInterval.value = null // Reset selection
  processDataByBinSize(binSize)
}

// --- Función para seleccionar intervalo de tiempo ---
function selectTimeInterval(barIndex: number) {
  if (!chartData.value?.labels) return

  const label = chartData.value.labels[barIndex]
  
  // Calculate actual date range based on bar index and bin size
  const currentDate = new Date()
  let startDate: Date
  let endDate: Date

  if (selectedBinSize.value === '1m') {
    // Calculate monthly periods going backwards from current date
    const monthsBack = (chartData.value.labels.length - 1) - barIndex
    endDate = new Date()
    endDate.setMonth(currentDate.getMonth() - monthsBack)
    endDate.setDate(0) // Last day of the month
    startDate = new Date(endDate)
    startDate.setDate(1) // First day of the month
  } else if (selectedBinSize.value === '3m') {
    // Calculate quarterly periods going backwards from current date
    const quartersBack = (chartData.value.labels.length - 1) - barIndex
    endDate = new Date()
    endDate.setMonth(currentDate.getMonth() - quartersBack * 3)
    endDate.setDate(0) // Last day of the quarter
    startDate = new Date(endDate)
    startDate.setMonth(endDate.getMonth() - 2)
    startDate.setDate(1) // First day of the quarter
  } else { // 6m
    // Calculate semi-annual periods going backwards from current date
    const semiAnnualPeriodsBack = (chartData.value.labels.length - 1) - barIndex
    endDate = new Date()
    endDate.setMonth(currentDate.getMonth() - semiAnnualPeriodsBack * 6)
    endDate.setDate(0) // Last day of the period
    startDate = new Date(endDate)
    startDate.setMonth(endDate.getMonth() - 5)
    startDate.setDate(1) // First day of the period
  }

  selectedTimeInterval.value = {
    start: startDate.toISOString(),
    end: endDate.toISOString(),
    label: label
  }

  // Update chart colors
  processDataByBinSize(selectedBinSize.value)
}

// --- Función helper para obtener el índice de la barra seleccionada ---
function getSelectedBarIndex(): number {
  if (!selectedTimeInterval.value || !chartData.value?.labels) return -1
  return chartData.value.labels.findIndex((label: string) => label === selectedTimeInterval.value?.label)
}

// --- Función para abrir modal de generación ---
async function openGenerationModal() {
  isGenerationModalOpen.value = true
  await loadAllHistoricalData()
}

// --- Función para generar Arquetipos ---
async function generateArchetypes() {
  if (!selectedTimeInterval.value) {
    alert('Please select a time period from the chart before generating archetypes.')
    return
  }

  isGenerationModalOpen.value = false // Close modal

  // Use the existing store method
  await reportStore.initiateArchetypeGeneration()
  
  console.log('Generating archetypes for period:', selectedTimeInterval.value)
}

// --- Hook de Ciclo de Vida --- 
onMounted(async () => {
  if (userInfo.value?.marca_name && !reportStore.currentUserBrandName) {
    reportStore.setCurrentUserBrandName(userInfo.value.marca_name)
  }

  if (reportStore.activeArchetypeTaskId || reportStore.currentUserBrandName) {
    reportStore.connectOrUpdateSse()
  }
})
</script>

<template>
  <div class="space-y-8">
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-display font-bold text-text-primary">Behavioral Archetypes</h1>
        <div class="group relative">
          <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
          <div class="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
            <p class="text-sm text-text-secondary">
              Behavioral archetypes are data-driven customer personas that represent distinct patterns in customer behavior, preferences, and motivations. They help businesses better understand and serve their diverse customer base.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Generate Archetypes Card -->
    <div v-if="canManageArchetypes" class="bg-white rounded-2xl shadow-sm border border-border p-6">
      <div class="flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="space-y-2 flex-1">
          <h2 class="text-xl font-display font-bold text-text-primary flex items-center">
            <CpuChipIcon class="h-6 w-6 mr-2  text-orange-600" />
            Generate Your Archetypes Automatically
          </h2>
          <p class="text-text-secondary max-w-2xl">
            Let ReviewInsight analyze all relevant brand information (reviews, product data, etc.) to automatically generate behavioral archetypes based on observed patterns and the Forrester/Adele Revella methodology. This process may take a few minutes.
          </p>
        </div>
        <div class="flex flex-col items-center space-y-2">
          <button 
            @click="openGenerationModal"
            :disabled="isGenerating"
            class="flex items-center justify-center px-6 py-3 rounded-xl text-white transition-all duration-300 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-orange-600 hover:to-amber-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed w-full md:w-auto shadow-md hover:shadow-lg"
          >
            <ArrowPathIcon v-if="isGenerating" class="h-5 w-5 mr-2 animate-spin" />
            <CpuChipIcon v-else class="h-5 w-5 mr-2" />
            <span class="font-medium">{{ isGenerating ? 'Generating...' : 'Generate Archetypes' }}</span>
          </button>
          <p v-if="isGenerating" class="text-sm text-text-secondary animate-pulse">{{ reportStore.focusedArchetypeProgressMessage || 'Processing data, please wait...' }}</p>
          <p v-if="generationError && !isGenerating" class="text-sm text-red-600">{{ generationError }}</p>
        </div>
      </div>
    </div>

    <!-- MODAL PARA GENERACIÓN DE ARQUETIPOS -->
    <div v-if="isGenerationModalOpen" 
         class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4">
      
      <!-- Contenedor del Modal -->
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
        
        <!-- Cabecera del Modal -->
        <div class="flex items-center justify-between p-6 border-b border-border">
          <div class="flex items-center space-x-4">
            <ChartBarIcon class="h-8 w-8 text-orange-600" />
            <div>
              <h2 class="text-2xl font-display font-bold text-text-primary">Generate Archetypes</h2>
              <p class="text-sm text-text-secondary">Review your complete historical data and select a time period for analysis</p>
            </div>
          </div>
          <button @click="isGenerationModalOpen = false" class="text-text-secondary hover:text-text-primary">
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>
        
        <!-- Contenido del Modal -->
        <div class="p-6 space-y-6 overflow-y-auto flex-1">
          <!-- Selección de Bin Size -->
          <div class="space-y-4">
            <h3 class="text-lg font-semibold text-text-primary flex items-center">
              <CalendarDaysIcon class="h-5 w-5 mr-2 text-orange-600" />
              Select Time Period Grouping
            </h3>
            <div class="grid grid-cols-3 gap-4">
              <button
                v-for="option in binSizeOptions"
                :key="option.value"
                @click="handleBinSizeChange(option.value as '1m' | '3m' | '6m')"
                :class="[
                  'p-4 rounded-lg border-2 transition-all duration-200 text-left',
                  selectedBinSize === option.value
                    ? 'border-orange-500 bg-orange-50 text-gray-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-orange-300 hover:bg-orange-50'
                ]"
              >
                <div class="font-medium">{{ option.label }}</div>
                <div class="text-sm opacity-75">{{ option.description }}</div>
              </button>
            </div>
          </div>

          <!-- Gráfico de Volumen Histórico -->
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-semibold text-text-primary">Historical Review Volume (Discrete Counts)</h3>
              <div v-if="selectedTimeInterval" class="flex items-center space-x-2 text-sm text-orange-700 bg-orange-100 px-3 py-1 rounded-full">
                <CursorArrowRaysIcon class="h-4 w-4" />
                <span>Selected: {{ selectedTimeInterval.label }}</span>
              </div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <div v-if="isLoadingChartData" class="flex items-center justify-center h-80 col">
                <div class="flex items-center space-x-2">
                  <ArrowPathIcon class="h-5 w-5 animate-spin text-orange-600" />
                  <span class="text-text-secondary">Loading historical data...</span>
                </div>
              </div>
              <div v-else-if="chartData" class="h-80 overflow-x-auto" >
                <div :style="{ width: Math.max(800, (chartData.labels?.length || 0) * 80) + 'px', height: '100%' }">
                  <Bar :data="chartData" :options="chartOptions" />
                </div>
              </div>
              <div v-else class="flex items-center justify-center h-80">
                <p class="text-text-secondary">No historical data available</p>
              </div>
            </div>
            <div class="text-sm text-gray-600 bg-orange-50 p-3 rounded-lg">
              <div class="flex items-start space-x-2">
                <CursorArrowRaysIcon class="h-4 w-4 text-orange-600 mt-0.5" />
                <div>
                  <strong>How to use:</strong> Each bar shows the number of reviews collected during that specific time period (not cumulative). 
                  Click on any bar to select that period for archetype analysis. The chart shows discrete review counts grouped by {{ binSizeOptions.find(opt => opt.value === selectedBinSize)?.description.toLowerCase() }}.
                </div>
              </div>
            </div>
          </div>

          <!-- Información adicional -->
          <div class="bg-orange-50 rounded-lg p-4">
            <div class="flex items-start space-x-3">
              <CpuChipIcon class="h-6 w-6 text-orange-600 mt-0.5" />
              <div>
                <h4 class="font-semibold text-gray-900">About Archetype Generation</h4>
                <p class="text-sm text-gray-700 mt-1">
                  The analysis will process only the reviews collected during your selected time period to identify behavioral patterns and create data-driven customer archetypes. 
                  Select a period with sufficient review volume for the best results. This process typically takes 3-5 minutes.
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Pie del Modal -->
        <div class="p-6 border-t border-border bg-gray-50 rounded-b-2xl flex justify-between">
          <button 
            @click="isGenerationModalOpen = false" 
            class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors duration-200"
          >
            Cancel
          </button>
          <button 
            @click="generateArchetypes"
            :disabled="isLoadingChartData || !selectedTimeInterval"
            class="flex items-center px-6 py-2 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-lg hover:from-amber-600 hover:to-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            <CpuChipIcon class="h-5 w-5 mr-2" />
            <span v-if="!selectedTimeInterval">Select Time Period</span>
            <span v-else>Start Generation</span>
          </button>
        </div>
      </div>
    </div>
    <!-- FIN MODAL GENERACIÓN -->

  </div>
</template>