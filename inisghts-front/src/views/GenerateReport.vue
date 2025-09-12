<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted, provide } from 'vue'
import apiClient from '@/services/axiosInstance'
import {
  CalendarIcon,
  UserGroupIcon,
  DocumentChartBarIcon,
  ChartBarIcon,
  LightBulbIcon,
  BoltIcon,
  MegaphoneIcon,
  ShoppingCartIcon,
  TruckIcon,
  HeartIcon,
  CurrencyDollarIcon,
  PuzzlePieceIcon,
  BuildingStorefrontIcon,
  GlobeAmericasIcon,
  BeakerIcon,
  ChatBubbleLeftRightIcon,
  DocumentMagnifyingGlassIcon,
  PresentationChartLineIcon,
  RocketLaunchIcon,
  SparklesIcon,
  StarIcon,
  MapIcon,
  QuestionMarkCircleIcon,
  XMarkIcon,
  GlobeEuropeAfricaIcon,
  ArrowPathIcon,
  CloudArrowDownIcon,
  EyeIcon,
  ServerIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'
import { useRouter } from 'vue-router'
import { useReportStore } from '@/store/reportStore'
import LowReviewsWarningModal from '@/components/LowReviewsWarningModal.vue'

const router = useRouter()
const reportStore = useReportStore()

// Data sources with review counts - will be populated dynamically
const sources = ref([])
const isLoadingSources = ref(true)
const sourcesError = ref(null)

// Countries
const countries = ref([
  { id: 'us', name: 'United States', flag: 'fi fi-us', selected: false },
  { id: 'uk', name: 'United Kingdom', flag: 'fi fi-gb', selected: false },
  { id: 'fr', name: 'France', flag: 'fi fi-fr', selected: false },
  { id: 'de', name: 'Germany', flag: 'fi fi-de', selected: false },
  { id: 'es', name: 'Spain', flag: 'fi fi-es', selected: false }
])

const steps = [
  { id: 'welcome', title: 'Bienvenida' },
  { id: 'dates', title: 'Fechas' },
  { id: 'sources', title: 'Fuentes' },
  { id: 'countries', title: 'Países' },
  { id: 'archetype', title: 'Arquetipo' },
  { id: 'report-type', title: 'Tipo de reporte' },
  { id: 'products', title: 'Productos', conditional: true },
  { id: 'summary', title: 'Resumen' }
]
const isLastStep = computed(() => {
  return currentStep.value === visibleSteps.value.length - 1;
})

// Actualiza canProceedToNext para usar el paso visible actual
const canProceedToNext = computed(() => {
  const currentVisibleStep = visibleSteps.value[currentStep.value];
  
  if (!currentVisibleStep) return false;
  
  switch (currentVisibleStep.id) {
    case 'welcome': 
      return true;
    case 'dates': 
      return true;
    case 'sources': 
      return selectedSources.value.length > 0;
    case 'countries': 
      return selectedCountries.value.length > 0;
    case 'archetype': 
      return selectedArchetype.value !== null;
    case 'report-type': 
      return selectedReport.value !== null;
    case 'products': 
      if (selectedReport.value === 'top-flop-products') {
        return productInputString.value.trim().length > 0;
      }
      return true;
    case 'summary': 
      return true;
    default:
      return true;
  }
})

const visibleSteps = computed(() => {
  const showProducts = selectedReport.value === 'top-flop-products'
  return steps.filter(s => s.id !== 'products' || showProducts)
})

// Selected date range
const dateRange = ref({
  start: '',
  end: ''
})

// ++ NEW ++: Ref for active quick date filter
const activeQuickDateFilter = ref<string | null>('all-time');

// Archetypes data
const archetypes = [
  {
    id: 'all',
    name: 'All Archetypes',
    avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=all&backgroundColor=cbd5e1',
    description: 'Analyze data across all customer archetypes'
  },
  {
    id: 'explorer',
    name: 'The Curious Explorer',
    avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=explorer&backgroundColor=b7c7ff',
    description: 'Adventurous diners who actively seek new culinary experiences'
  },
  {
    id: 'vegan',
    name: 'The Mindful Vegan',
    avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=vegan&backgroundColor=96ffd4',
    description: 'Health-conscious customers who prioritize plant-based options'
  },
  {
    id: 'foodie',
    name: 'The Passionate Foodie',
    avatar: 'https://api.dicebear.com/7.x/personas/svg?seed=foodie&backgroundColor=fecdd3',
    description: 'Culinary enthusiasts who appreciate quality ingredients'
  }
]

// Products data
// const products = ref([...])
// const selectedProducts = computed(() => { ... })
// const isProductDropdownOpen = ref(false)

// NUEVO ESTADO para input de productos
const productInputString = ref('');

// Selected values
const selectedArchetype = ref('all')
const selectedReport = ref<string | null>(null)


const currentStep = ref(0)




// Report categories with their reports
const reportCategories = [
  {
    name: 'Behavioral Analysis',
    icon: BoltIcon,
    reports: [
      { id: 'sentiment-analysis', name: 'Sentiment Analysis', icon: ChatBubbleLeftRightIcon, description: 'Evaluation of predominant emotions in user feedback.' },
      { id: 'cognitive-biases', name: 'Cognitive Biases', icon: BoltIcon, description: 'Identification of patterns of bias in user behavior.' },
      { id: 'awareness-levels', name: 'Awareness Levels', icon: LightBulbIcon, description: 'Measurement of user awareness about certain topics or products.' },
      { id: 'inference-analysis', name: 'Inference Analysis', icon: DocumentMagnifyingGlassIcon, description: 'Drawing conclusions based on user behavior and feedback.' }
    ]
  },
  {
    name: 'Marketing',
    icon: MegaphoneIcon,
    reports: [
      { id: 'swot', name: 'SWOT Analysis', icon: PresentationChartLineIcon, description: 'Evaluation of strengths, weaknesses, opportunities and threats.' },
      { id: 'problem-solution', name: 'Problem-Solution Matrix', icon: PuzzlePieceIcon, description: 'Identification of key problems and proposed solutions.' },
      { id: 'content-calendar', name: 'Content Calendar', icon: CalendarIcon, description: 'Strategic planning of content over time.' },
      { id: 'social-trends', name: 'Social Trends (Reddit)', icon: ChartBarIcon, description: 'Analysis of trending topics and discussions on Reddit.', disabled: true },
      { id: 'purchase-factors', name: 'Purchase Driving Factors', icon: CurrencyDollarIcon, description: 'Identification of key factors influencing purchase decisions.' }
    ]
  },
  {
    name: 'Product',
    icon: ShoppingCartIcon,
    reports: [
      { id: 'top-flop-products', name: 'Top and Flop Products', icon: StarIcon, description: 'Identification of most and least successful products.', disabled: false },
      { id: 'trend-identification', name: 'Trend Identification', icon: ChartBarIcon, description: 'Detection of emerging trends in the market.' },
      { id: 'single-product', name: 'Tops and Flops (Single Product)', icon: SparklesIcon, description: 'Detailed analysis of a single product\'s performance.', disabled: true },
      { id: 'delivery-packaging', name: 'Delivery & Packaging', icon: TruckIcon, description: 'Evaluation of delivery process and packaging quality.' }
    ]
  },
  {
    name: 'Industry',
    icon: BuildingStorefrontIcon,
    reports: [
      { id: 'pest', name: 'PEST Analysis', icon: GlobeAmericasIcon, description: 'Analysis of Political, Economic, Social, and Technological factors.', new: true, disabled: true },
      { id: 'trends-preferences', name: 'Trends and Preferences', icon: RocketLaunchIcon, description: 'Identification of industry trends and customer preferences.', new: true }
    ]
  },
  {
    name: 'Offsite',
    icon: MapIcon,
    reports: [
      { id: 'key-attributes', name: 'Key Attributes Analysis (In Store)', icon: BeakerIcon, description: 'Analysis of key product attributes in physical stores.', disabled: true },
      { id: 'customer-experience', name: 'Customer Experience (In Store)', icon: UserGroupIcon, description: 'Evaluation of customer experience in physical stores.', disabled: true },
      { id: 'regional-comparison', name: 'Regional Comparison', icon: GlobeAmericasIcon, description: 'Comparative analysis across different regions.', disabled: true },
      { id: 'city-benchmark', name: 'City / Region Benchmark', icon: MapIcon, description: 'Benchmarking performance in specific cities or regions.', disabled: true }
    ]
  }
]

// Computed total reviews selected
const totalSelectedReviews = computed(() => {
  return sources.value
    .filter(source => source.selected)
    .reduce((sum, source) => sum + source.count, 0)
})

// Maximum possible reviews
const maxReviews = computed(() => {
  return sources.value.reduce((sum, source) => sum + source.count, 0)
})

// Computed percentage of selected reviews
const selectedReviewsPercentage = computed(() => {
  if (maxReviews.value === 0) return 0; // Avoid division by zero
  return (dynamicSelectedCount.value / maxReviews.value) * 100;
})

// Function to format numbers with commas
const formatNumber = (num: number) => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

// --- Estado para Generación, Visualización y Guardado ---
const isGeneratingReport = computed(() => reportStore.isGenerating)
const generatedHtmlContent = computed(() => reportStore.generatedHtmlContent)
const generatedBrandName = computed(() => reportStore.generatedBrandName)
const generatedReportType = computed(() => reportStore.generatedReportType)
const reportGenerationError = computed(() => reportStore.reportGenerationError)

const isSavingReport = ref(false)
const savedReportUrl = ref<string | null>(null)
const reportSaveError = ref<string | null>(null)

// ++ NEW ++: State for dynamic selected review count
const dynamicSelectedCount = ref(0)
const isLoadingDynamicCount = ref(false)

// State for confirmation popup visibility
const showLowReviewsWarning = ref(false)

// --- Computed Properties --- 
const selectedSources = computed(() => sources.value.filter(s => s.selected).map(s => s.id))
const selectedCountries = computed(() => {
  const countriesSelected = countries.value.filter(c => c.selected).map(c => c.id.toUpperCase());
  //  // DEBUG
  return countriesSelected;
})

const canGenerate = computed(() => {
  const bothDatesSet = dateRange.value.start && dateRange.value.end;
  const bothDatesEmpty = dateRange.value.start === '' && dateRange.value.end === '';
  const validDateRange = bothDatesSet || bothDatesEmpty;

  return validDateRange &&
         selectedSources.value.length > 0 &&
         selectedCountries.value.length > 0 &&
         selectedReport.value && // Report IDs are non-empty strings, so this check is fine
         !isGeneratingReport.value;
})

const canSave = computed(() => {
    return generatedHtmlContent.value && !isSavingReport.value;
})

const nextStep = () => {
  const maxSteps = visibleSteps.value.length - 1;
  if (currentStep.value < maxSteps) {
    currentStep.value++;
  }
}

const previousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

// --- Estado para Arquetipos Cargados Dinámicamente ---
const availableArchetypes = ref<any[]>([])
const isLoadingArchetypes = ref(true);
const fetchArchetypesError = ref<string | null>(null);

// --- NUEVO: Definición para el objeto de actividad reciente ---
interface RecentActivityData {
  id: number;
  type: 'report';
  description: string;
  dateObject: string; // ISO string
  iconKey: string; // Key to map to icon component
  iconColor: string;
}

// --- Methods --- 

// Add this new method to fetch source data
async function fetchSourceData() {
  isLoadingSources.value = true
  sourcesError.value = null
  
  
  try {
    // Fetch sources data from API
    const response = await apiClient.get('/sources/review-counts')
    if (Array.isArray(response.data)) {
      sources.value = response.data.map((source: any) => ({
        ...source,
        selected: false
      }))
    } else {
      console.error("Error fetching source data: response.data is not an array. Received:", response.data);
      // This will make the function throw and be caught by the existing catch block
      throw new Error("Invalid data format received from server for sources.");
    }
    
  } catch (error) {
    console.error("Error fetching source data:", error)
    sourcesError.value = "Could not load review sources data."
    // Fall back to default values if API fails
    sources.value = [
      { id: 'amazon', name: 'Amazon', count: 0, selected: false },
      { id: 'tripadvisor', name: 'TripAdvisor', count: 0, selected: false },
      { id: 'trustpilot', name: 'Trustpilot', count: 0, selected: false },
      { id: 'mybusiness', name: 'Google', count: 0, selected: false },
      { id: 'druni', name: 'Druni', count: 0, selected: false }
    ]
  } finally {
    isLoadingSources.value = false
  }
}

// Función para generar el informe (devuelve HTML)
async function generateReportFromStore() {
  
  if (!canGenerate.value) {
     
     return;
  }

  if (dynamicSelectedCount.value < 100) {
    showLowReviewsWarning.value = true; // Show the modal
    return; 
  }

  await proceedWithReportGeneration();
}

// Function to actually proceed with generation
async function proceedWithReportGeneration() {
  showLowReviewsWarning.value = false; // Ensure modal is hidden

  const payload: any = {
    sources: selectedSources.value,
    countries: selectedCountries.value,
    report_type: selectedReport.value,
    archetype_id: selectedArchetype.value !== 'all' ? selectedArchetype.value : undefined
  };

  if (dateRange.value.start && dateRange.value.end) {
    payload.start_date = dateRange.value.start;
    payload.end_date = dateRange.value.end;
  }

  if (selectedReport.value === 'top-flop-products') {
    const productsList = productInputString.value
      .split(',').map(p => p.trim()).filter(p => p !== '');
    payload.products = productsList;
  }
  
  await reportStore.initiateReportGeneration(payload);
}

// Handlers for modal events
function handleModalConfirm() {
  proceedWithReportGeneration();
}

function handleModalCancel() {
  showLowReviewsWarning.value = false;
}

// Función para guardar el informe en S3
async function saveReport() {
    if (!canSave.value) return;

    isSavingReport.value = true;
    savedReportUrl.value = null;
    reportSaveError.value = null;

    const payload = {
        html_content: generatedHtmlContent.value,
        brand_name: generatedBrandName.value,
        report_type: generatedReportType.value
    };

  

    try {
        const response = await apiClient.post('/reports/save', payload);
        

        if (response.data && response.data.report_url) {
            savedReportUrl.value = response.data.report_url;
            alert("Report saved successfully!");
        } else {
            reportSaveError.value = response.data.message || "Save successful, but no URL returned.";
            alert(reportSaveError.value);
        }
    } catch (error: any) {
        console.error("Error during report save API call:", error);
        if (error.response && error.response.data && error.response.data.detail) {
            reportSaveError.value = `Save Error: ${error.response.data.detail}`;
        } else {
            reportSaveError.value = "An unexpected error occurred while saving the report.";
        }
        alert(reportSaveError.value);
    } finally {
        isSavingReport.value = false;
    }
}

// Función para cargar arquetipos
async function loadArchetypes() {
  isLoadingArchetypes.value = true;
  fetchArchetypesError.value = null;
  try {
    const response = await apiClient.get('/archetypes');
    availableArchetypes.value = response.data; // Guardar los arquetipos parseados
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
       fetchArchetypesError.value = error.response.data.detail || "No generated archetypes found. You may need to generate them first.";
    } else {
      fetchArchetypesError.value = "An error occurred while fetching archetypes.";
    }
    availableArchetypes.value = [] // Limpiar si hay error
  } finally {
    isLoadingArchetypes.value = false;
  }
}

// Navigate to view report detail page
const viewReport = (reportId: string | undefined) => {
  if (reportId) {
    router.push(`/reports/view/${reportId}`)
  } else {
    alert("Sorry, the ID for this report is missing.")
  }
}

// --- NUEVAS FUNCIONES PARA SELECCIÓN RÁPIDA DE FECHA ---
const formatDate = (date: Date): string => {
  return date.toISOString().split('T')[0];
}

const selectLastYear = () => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 1);
  
  dateRange.value.start = formatDate(startDate);
  dateRange.value.end = formatDate(endDate);
  activeQuickDateFilter.value = 'last-year'; // ++ SET ACTIVE FILTER
}

const selectAllTime = () => {
  dateRange.value.start = ''; 
  dateRange.value.end = '';   
  activeQuickDateFilter.value = 'all-time'; // ++ SET ACTIVE FILTER
}

const selectLastQuarter = () => {
  const today = new Date();
  const currentQuarter = Math.floor(today.getMonth() / 3);
  const currentYear = today.getFullYear();

  let startMonth, endMonth, year;

  if (currentQuarter === 0) { // Si estamos en Q1, el último trimestre fue Q4 del año pasado
    year = currentYear - 1;
    startMonth = 9; // Octubre (índice 9)
    endMonth = 11; // Diciembre (índice 11)
  } else { // Si estamos en Q2, Q3, Q4, el último trimestre fue el anterior del mismo año
    year = currentYear;
    startMonth = (currentQuarter - 1) * 3;
    endMonth = startMonth + 2;
  }

  const startDate = new Date(year, startMonth, 1);
  const endDate = new Date(year, endMonth + 1, 0); // El día 0 del mes siguiente da el último día del mes actual

  dateRange.value.start = formatDate(startDate);
  dateRange.value.end = formatDate(endDate);
  activeQuickDateFilter.value = 'last-quarter'; // ++ SET ACTIVE FILTER
}

// ++ NEW ++: Function to handle manual date input changes
const onManualDateChange = () => {
  activeQuickDateFilter.value = null;
}

// ++ NEW ++: Watch for changes in filters to update dynamic count
watch(
  [
    () => dateRange.value.start,
    () => dateRange.value.end,
    selectedSources,
    selectedCountries,
  ],
  async (newValues, oldValues) => {
    
    // Always call fetchDynamicSelectedCount; it will determine if an API call is warranted.
    await fetchDynamicSelectedCount();
  },
  { deep: true, immediate: true }
);

// Add this new method:
async function fetchDynamicSelectedCount() {
  

  // Determine sources for payload: user-selected or all available
  let sourcesForPayload = selectedSources.value;
  if (sourcesForPayload.length === 0) {
    // If no specific sources are selected by the user, use all available source IDs
    sourcesForPayload = sources.value.map((s: any) => s.id);
    //  // DEBUG
  }

  // If no sources are available AT ALL (neither selected by user nor from the global list,
  // e.g., initial load before sources.value is populated from API), then we cannot make a meaningful API call.
  if (sourcesForPayload.length === 0 && sources.value.length > 0) {
    // This case might happen if sources.value is populated but somehow selectedSources results in nothing,
    // and the map to all IDs also yields nothing (highly unlikely if sources.value has items).
    // More likely, if sources.value itself is empty (not yet loaded), sourcesForPayload would be empty.
     
     dynamicSelectedCount.value = 0;
     return;
  }
  // If sources.value is empty (initial load), the above map would make sourcesForPayload empty.
  // If sourcesForPayload is empty because sources.value is not yet loaded, we should not proceed.
  // This primarily protects against calls during the initial fraction of a second before onMounted finishes all fetches.
   if (sources.value.length === 0 && sourcesForPayload.length === 0) {
    
    dynamicSelectedCount.value = 0;
    return;
   }


  isLoadingDynamicCount.value = true;
  const payload: any = {
    sources: sourcesForPayload,
    countries: selectedCountries.value, // Empty array from computed property means all countries
  };

  const startDate = dateRange.value.start;
  const endDate = dateRange.value.end;

  if (startDate && endDate) { // Both dates are present (not empty strings)
    try {
      // Ensure dates are valid before creating Date objects
      // Basic check for YYYY-MM-DD format might be useful if direct input is allowed
      // For type="date", browser should enforce format, but value can still be invalid string initially
      if (isNaN(new Date(startDate).getTime()) || isNaN(new Date(endDate).getTime())) {
          throw new Error("Invalid date string provided");
      }
      payload.start_date = new Date(startDate + "T00:00:00.000Z").toISOString();
      payload.end_date = new Date(endDate + "T23:59:59.999Z").toISOString();
    } catch (dateError) {
      console.error("DEBUG: Error creating ISO dates or invalid date format:", dateError, "Raw dates:", startDate, endDate);
      dynamicSelectedCount.value = 0; // Invalid date format
      isLoadingDynamicCount.value = false;
      return;
    }
  } else if (startDate || endDate) { // Only one of the dates is present, or one is an empty string while other has value
    
    dynamicSelectedCount.value = 0;
    isLoadingDynamicCount.value = false;
    return;
  }
  // If both startDate and endDate are empty strings (e.g. from "All Time"),
  // they are correctly omitted from the payload.

   // DEBUG

  try {
    const response = await apiClient.post("/reviews/count", payload);
     // DEBUG
    dynamicSelectedCount.value = response.data.total_count || 0;
  } catch (error: any) {
    console.error(
      "DEBUG: Error fetching dynamic selected review count:", // DEBUG
      error.response ? JSON.parse(JSON.stringify(error.response.data)) : error.message
    );
    dynamicSelectedCount.value = 0;
  } finally {
    isLoadingDynamicCount.value = false;
  }
}
const currentSlideIndex = computed(() => {
  const currentVisibleStep = visibleSteps.value[currentStep.value];
  if (!currentVisibleStep) return 0;
  
  // Mapear el ID del paso al índice físico de la slide
  const stepToSlideMap = {
    'welcome': 0,
    'dates': 1,
    'sources': 2,
    'countries': 3,
    'archetype': 4,
    'report-type': 5,
    'products': 6,
    'summary': 7
  };
  
  return stepToSlideMap[currentVisibleStep.id] || 0;
});



// --- Lifecycle Hooks --- 
onMounted(async () => {
  const token = sessionStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;

  await fetchSourceData()

  // Obtener países disponibles
  try {
    const response = await apiClient.get('/countries/')
     // LOG 1: Raw response
    countries.value = response.data.map((c: { country: string; name: string; flag?: string /* Flag is optional */ }) => ({
      id: c.country,
      name: c.name,
      flag: c.flag || '', // Provide a fallback for flag if not present in JSON
      selected: false
    }))
     // LOG 2: Mapped data
  } catch (error) {
    // reportStore.reportGenerationError = "Could not load available countries."; // Update store for errors
    // Or handle locally if it's specific to this page's setup
    console.error("Could not load available countries.");
  }
  // Aquí podríamos añadir lógica para obtener fuentes disponibles si fuera necesario

  await loadArchetypes(); // Cargar arquetipos

  // ++ NEW ++: Initial call to fetch dynamic count if conditions are met
  // The watcher below with `immediate: true` will also handle this.
})

const toggleSource = (source) => {
  source.selected = !source.selected
}

// toggleCountry: Función para seleccionar/deseleccionar países
const toggleCountry = (country) => {
  country.selected = !country.selected
}

// getDateRangeText: Función para mostrar el texto del rango de fechas en el resumen
const getDateRangeText = () => {
  if (dateRange.value.start && dateRange.value.end) {
    return `${dateRange.value.start} - ${dateRange.value.end}`
  }
  return 'Todo el tiempo'
}

// getSelectedReportName: Función para obtener el nombre del reporte seleccionado
const getSelectedReportName = () => {
  if (!selectedReport.value) return 'Ninguno'
  
  for (const category of reportCategories) {
    const report = category.reports.find(r => r.id === selectedReport.value)
    if (report) return report.name
  }
  return 'Reporte desconocido'
}

// closeReportPreview: Función para cerrar la vista previa del reporte
const closeReportPreview = () => {
  // Limpiar el contenido HTML generado para cerrar la vista previa
  reportStore.clearGeneratedContent() // Asumiendo que tienes esta función en el store
  // O si no existe, puedes usar directamente:
  // generatedHtmlContent.value = null
}

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
    return 'Invalid date'
  }
}

// Watch for report generation progress messages from the store
watch(() => reportStore.progressMessage, (newMessage) => {
  if (newMessage && reportStore.isGenerating && reportStore.reportTaskId) {
    // Update UI with this message if needed, or rely on toasts for major updates
    
  }
});

onUnmounted(() => {
  // If this component initiated a report, and the user navigates away,
  // decide if the SSE subscription for this specific reportTaskId should be removed.
  if (reportStore.reportTaskId) {
    // reportStore.unsubscribeFrom(reportStore.reportTaskId, 'task');
     
  }
});
</script>

<template>
  <div class="h-screen bg-gradient-to-br p-4 overflow-hidden"> <!-- overflow-hidden añadido -->
    <div class="max-w-4xl mx-auto h-full flex flex-col"> <!-- h-full y flex flex-col añadidos -->
      
      <!-- Header con progreso - altura fija -->
      <div class="text-center mb-6 flex-shrink-0"> <!-- flex-shrink-0 añadido -->
        <h1 class="text-3xl font-bold text-gray-800 mb-4">Generador de Reportes</h1>
        
        <!-- Barra de progreso -->
        <div class="relative mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-600">
              Paso {{ currentStep + 1 }} de {{ visibleSteps.length }} 
              
              <br>
            </span>
            <span class="text-sm text-gray-600">
              {{ Math.round(((currentStep + 1) / visibleSteps.length) * 100) }}% completado
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div 
              class="bg-gradient-to-r from-amber-500 to-orange-600 h-2 rounded-full transition-all duration-500 ease-out"
              :style="{ width: `${((currentStep + 1) / visibleSteps.length) * 100}%` }"
            ></div>
          </div>
        </div>

        <!-- Indicadores de pasos -->
        <div class="flex justify-center space-x-2">
          <div 
            v-for="(step, index) in steps" 
            :key="step.id"
            class="w-3 h-3 rounded-full transition-all duration-300"
            :class="index <= currentStep ? 'bg-orange-500' : 'bg-gray-300'"
          ></div>
        </div>
      </div>

      <!-- Carrusel - ocupa el espacio restante -->
      <div class="relative overflow-hidden flex-1"> <!-- flex-1 añadido -->
        <div 
          class="flex transition-transform duration-500 ease-in-out h-full"
          :style="{ transform: `translateX(-${currentSlideIndex * 100}%)` }"
        >
          <!-- Paso 1: Bienvenida -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2"> <!-- overflow-y-auto y px-2 añadidos -->
            <div class="bg-white rounded-2xl shadow-xl p-8 text-center">
              <div class="mb-6">
                <ChartBarIcon class="h-16 w-16 text-blue-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">¡Bienvenido a Analytics!</h2>
                <p class="text-gray-600 text-lg">Te guiaremos paso a paso para crear tu reporte personalizado</p>
              </div>
              
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div class="text-center p-4">
                  <CalendarIcon class="h-8 w-8 text-blue-500 mx-auto mb-2" />
                  <h3 class="font-semibold text-gray-700">Fechas</h3>
                  <p class="text-sm text-gray-500">Selecciona el período</p>
                </div>
                <div class="text-center p-4">
                  <GlobeEuropeAfricaIcon class="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <h3 class="font-semibold text-gray-700">Fuentes</h3>
                  <p class="text-sm text-gray-500">Elige tus datos</p>
                </div>
                <div class="text-center p-4">
                  <DocumentChartBarIcon class="h-8 w-8 text-purple-500 mx-auto mb-2" />
                  <h3 class="font-semibold text-gray-700">Reporte</h3>
                  <p class="text-sm text-gray-500">Genera insights</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 2: Selección de fechas -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <CalendarIcon class="h-12 w-12 text-blue-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Selecciona el período de tiempo</h2>
                <p class="text-gray-600">¿Qué rango de fechas quieres analizar?</p>
              </div>

              <!-- Opciones rápidas -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <button 
                  @click="selectAllTime"
                  class="p-4 border-2 rounded-xl transition-all duration-300 hover:shadow-md"
                  :class="activeQuickDateFilter === 'all-time' 
                    ? 'border-blue-500 bg-blue-50 text-blue-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="text-center">
                    <h3 class="font-semibold mb-1">Todo el tiempo</h3>
                    <p class="text-sm opacity-75">Todos los datos disponibles</p>
                  </div>
                </button>
                
                <button 
                  @click="selectLastYear"
                  class="p-4 border-2 rounded-xl transition-all duration-300 hover:shadow-md"
                  :class="activeQuickDateFilter === 'last-year' 
                    ? 'border-blue-500 bg-blue-50 text-blue-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="text-center">
                    <h3 class="font-semibold mb-1">Último año</h3>
                    <p class="text-sm opacity-75">365 días hacia atrás</p>
                  </div>
                </button>
                
                <button 
                  @click="selectLastQuarter"
                  class="p-4 border-2 rounded-xl transition-all duration-300 hover:shadow-md"
                  :class="activeQuickDateFilter === 'last-quarter' 
                    ? 'border-blue-500 bg-blue-50 text-blue-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="text-center">
                    <h3 class="font-semibold mb-1">Último trimestre</h3>
                    <p class="text-sm opacity-75">Últimos 3 meses</p>
                  </div>
                </button>
              </div>

              <!-- Selección manual -->
              <div class="border-t pt-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-4 text-center">O selecciona fechas específicas</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-md mx-auto">
                  <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Fecha inicio</label>
                    <input
                      type="date"
                      v-model="dateRange.start"
                      @change="onManualDateChange"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Fecha fin</label>
                    <input
                      type="date"
                      v-model="dateRange.end"
                      @change="onManualDateChange"
                      :min="dateRange.start"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 3: Fuentes de datos -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <ServerIcon class="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Selecciona las fuentes de datos</h2>
                <p class="text-gray-600">¿De qué plataformas quieres obtener datos?</p>
              </div>

              <div v-if="isLoadingSources" class="text-center py-8">
                <ArrowPathIcon class="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
                <p class="text-gray-600">Cargando fuentes disponibles...</p>
              </div>

              <div v-else-if="sourcesError" class="text-center py-8 text-red-600">
                <p>{{ sourcesError }}</p>
              </div>

              <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div 
                  v-for="source in sources" 
                  :key="source.id"
                  @click="toggleSource(source)"
                  class="p-4 border-2 rounded-xl cursor-pointer transition-all duration-300 hover:shadow-md"
                  :class="source.selected 
                    ? 'border-green-500 bg-green-50 text-green-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="text-center">
                    <div class="flex items-center justify-center mb-2">
                      <CheckCircleIcon v-if="source.selected" class="h-6 w-6 text-green-500" />
                      <div v-else class="h-6 w-6 border-2 border-gray-300 rounded-full"></div>
                    </div>
                    <h3 class="font-semibold mb-1">{{ source.name }}</h3>
                    <p class="text-sm opacity-75">{{ formatNumber(source.count) }} reseñas</p>
                  </div>
                </div>
              </div>

              <!-- Contador de reseñas seleccionadas -->
              <div class="mt-6 text-center">
                <div class="inline-flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-lg">
                  <EyeIcon class="h-5 w-5 text-blue-500" />
                  <span class="text-blue-700 font-medium">
                    Reseñas seleccionadas: 
                    <template v-if="isLoadingDynamicCount">
                      <ArrowPathIcon class="h-4 w-4 inline animate-spin" />
                    </template>
                    <template v-else>
                      {{ formatNumber(dynamicSelectedCount) }}
                    </template>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 4: Países -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <GlobeEuropeAfricaIcon class="h-12 w-12 text-purple-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Selecciona los países</h2>
                <p class="text-gray-600">¿De qué mercados quieres obtener datos?</p>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div 
                  v-for="country in countries" 
                  :key="country.id"
                  @click="toggleCountry(country)"
                  class="p-4 border-2 rounded-xl cursor-pointer transition-all duration-300 hover:shadow-md"
                  :class="country.selected 
                    ? 'border-purple-500 bg-purple-50 text-purple-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="text-center">
                    <div class="flex items-center justify-center mb-2">
                      <CheckCircleIcon v-if="country.selected" class="h-6 w-6 text-purple-500" />
                      <div v-else class="h-6 w-6 border-2 border-gray-300 rounded-full"></div>
                    </div>
                    <div class="text-2xl mb-2">
                      <span :class="country.flag"></span>
                    </div>
                    <h3 class="font-semibold">{{ country.name }}</h3>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 5: Arquetipo -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <UserGroupIcon class="h-12 w-12 text-indigo-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Selecciona el arquetipo</h2>
                <p class="text-gray-600">¿Para qué tipo de cliente quieres generar el reporte?</p>
              </div>

              <div v-if="isLoadingArchetypes" class="text-center py-8">
                <ArrowPathIcon class="h-8 w-8 animate-spin text-indigo-500 mx-auto mb-4" />
                <p class="text-gray-600">Cargando arquetipos...</p>
              </div>

              <div v-else-if="fetchArchetypesError" class="text-center py-8 text-red-600">
                <p>{{ fetchArchetypesError }}</p>
              </div>

              <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Todos los arquetipos -->
                <div 
                  @click="selectedArchetype = 'all'"
                  class="p-6 border-2 rounded-xl cursor-pointer transition-all duration-300 hover:shadow-md"
                  :class="selectedArchetype === 'all' 
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="flex items-center space-x-4">
                    <img src="https://api.dicebear.com/7.x/personas/svg?seed=all&backgroundColor=cbd5e1" class="w-12 h-12 rounded-lg" />
                    <div>
                      <h3 class="font-semibold text-lg">Todos los arquetipos</h3>
                      <p class="text-sm opacity-75">Análisis completo de todos los tipos de cliente</p>
                    </div>
                  </div>
                </div>

                <!-- Arquetipos específicos -->
                <div 
                  v-for="archetype in availableArchetypes" 
                  :key="archetype.id || archetype.name"
                  @click="selectedArchetype = archetype.id || archetype.name"
                  class="p-6 border-2 rounded-xl cursor-pointer transition-all duration-300 hover:shadow-md"
                  :class="selectedArchetype === (archetype.id || archetype.name) 
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700' 
                    : 'border-gray-200 hover:border-gray-300'"
                >
                  <div class="flex items-center space-x-4">
                    <img :src="archetype.avatar" :alt="archetype.name" class="w-12 h-12 rounded-lg" />
                    <div>
                      <h3 class="font-semibold text-lg">{{ archetype.name }}</h3>
                      <p class="text-sm opacity-75 line-clamp-2">{{ archetype.description || 'Arquetipo personalizado' }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 6: Tipo de reporte -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <DocumentChartBarIcon class="h-12 w-12 text-orange-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">Selecciona el tipo de reporte</h2>
                <p class="text-gray-600">¿Qué tipo de análisis necesitas?</p>
              </div>

              <div class="space-y-6">
                <div v-for="category in reportCategories" :key="category.name">
                  <h3 class="text-lg font-semibold text-gray-700 mb-3 flex items-center">
                    <component :is="category.icon" class="h-5 w-5 mr-2 text-orange-500" />
                    {{ category.name }}
                  </h3>
                  
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                      v-for="report in category.reports"
                      :key="report.id"
                      @click="!report.disabled && (selectedReport = report.id)"
                      class="p-4 border-2 rounded-xl cursor-pointer transition-all duration-300"
                      :class="{ 
                        'border-orange-500 bg-orange-50 text-orange-700': selectedReport === report.id && !report.disabled, 
                        'border-gray-200 hover:border-gray-300': selectedReport !== report.id && !report.disabled,
                        'opacity-50 cursor-not-allowed border-gray-200 bg-gray-50': report.disabled
                      }"
                    >
                      <div class="flex items-start space-x-3">
                        <component :is="report.icon" class="h-6 w-6 mt-1 flex-shrink-0" 
                          :class="selectedReport === report.id && !report.disabled ? 'text-orange-500' : 'text-gray-400'" />
                        <div class="flex-1">
                          <div class="flex items-center space-x-2 mb-1">
                            <h4 class="font-semibold">{{ report.name }}</h4>
                            <span v-if="report.new && !report.disabled" class="px-2 py-0.5 text-xs font-medium text-white bg-green-500 rounded-full">NUEVO</span>
                            <span v-if="report.disabled" class="px-2 py-0.5 text-xs font-medium text-gray-500 bg-gray-200 rounded-full">Próximamente</span>
                          </div>
                          <p class="text-sm opacity-75">{{ report.description }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Paso 7: Productos (condicional) -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div v-if="selectedReport === 'top-flop-products'">
                <div class="text-center mb-6">
                  <ShoppingCartIcon class="h-12 w-12 text-pink-500 mx-auto mb-4" />
                  <h2 class="text-2xl font-bold text-gray-800 mb-2">Especifica los productos</h2>
                  <p class="text-gray-600">¿Qué productos quieres analizar en detalle?</p>
                </div>

                <div class="max-w-2xl mx-auto">
                  <label class="block text-sm font-medium text-gray-700 mb-3">
                    Nombres o IDs de productos (separados por comas)
                  </label>
                  <textarea
                    v-model="productInputString"
                    placeholder="Ej: Producto A, ID123, Otro Producto, SKU456"
                    rows="4"
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 resize-none"
                  ></textarea>
                  <p class="mt-2 text-sm text-gray-500">
                    Ingresa los identificadores exactos de los productos que quieres analizar
                  </p>
                </div>
              </div>
              <div v-else class="text-center py-16">
                <QuestionMarkCircleIcon class="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <p class="text-gray-500">Este paso se omite para el tipo de reporte seleccionado</p>
              </div>
            </div>
          </div>

          <!-- Paso 8: Resumen y generación -->
          <div class="w-full flex-shrink-0 h-full overflow-y-auto px-2">
            <div class="bg-white rounded-2xl shadow-xl p-8">
              <div class="text-center mb-6">
                <RocketLaunchIcon class="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h2 class="text-2xl font-bold text-gray-800 mb-2">¡Listo para generar!</h2>
                <p class="text-gray-600">Revisa tu configuración antes de generar el reporte</p>
              </div>

              <!-- Resumen de configuración -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="bg-gray-50 p-4 rounded-lg">
                  <h3 class="font-semibold text-gray-700 mb-2">Período</h3>
                  <p class="text-sm text-gray-600">
                    {{ getDateRangeText() }}
                  </p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                  <h3 class="font-semibold text-gray-700 mb-2">Fuentes</h3>
                  <p class="text-sm text-gray-600">
                    {{ selectedSources.length }} fuente(s) seleccionada(s)
                  </p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                  <h3 class="font-semibold text-gray-700 mb-2">Países</h3>
                  <p class="text-sm text-gray-600">
                    {{ selectedCountries.length }} país(es) seleccionado(s)
                  </p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                  <h3 class="font-semibold text-gray-700 mb-2">Tipo de reporte</h3>
                  <p class="text-sm text-gray-600">
                    {{ getSelectedReportName() }}
                  </p>
                </div>
              </div>

              <!-- Contador de reseñas -->
              <div class="text-center mb-6">
                <div class="inline-flex items-center space-x-2 bg-blue-50 px-6 py-3 rounded-lg">
                  <EyeIcon class="h-6 w-6 text-blue-500" />
                  <span class="text-blue-700 font-medium text-lg">
                    Total de reseñas: 
                    <template v-if="isLoadingDynamicCount">
                      <ArrowPathIcon class="h-5 w-5 inline animate-spin" />
                    </template>
                    <template v-else>
                      {{ formatNumber(dynamicSelectedCount) }}
                    </template>
                  </span>
                </div>
              </div>

              <!-- Botón de generación -->
              <div class="text-center">
                <button
                  @click="generateReportFromStore"
                  :disabled="!canGenerate || isGeneratingReport"
                  class="px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white text-lg font-semibold rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl disabled:shadow-none disabled:cursor-not-allowed"
                >
                  <div class="flex items-center space-x-3">
                    <ArrowPathIcon v-if="isGeneratingReport" class="h-6 w-6 animate-spin" />
                    <DocumentChartBarIcon v-else class="h-6 w-6" />
                    <span>{{ isGeneratingReport ? (reportStore.progressMessage || 'Generando reporte...') : 'Generar Reporte' }}</span>
                  </div>
                </button>
              </div>

              <!-- Estado de generación -->
              <div v-if="isGeneratingReport && reportStore.progressMessage" class="text-center mt-4 text-gray-600">
                {{ reportStore.progressMessage }}
              </div>
              <div v-else-if="reportGenerationError" class="text-center mt-4 text-red-600 bg-red-100 border border-red-300 p-3 rounded-lg">
                {{ reportGenerationError }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Controles de navegación - altura fija -->
      <div class="flex justify-between items-center mt-6 flex-shrink-0"> <!-- flex-shrink-0 añadido -->
        <button
          @click="previousStep"
          :disabled="currentStep === 0"
          class="flex items-center space-x-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed text-gray-700 disabled:text-gray-400 rounded-lg transition-all duration-300"
        >
          <ChevronLeftIcon class="h-5 w-5" />
          <span>Anterior</span>
        </button>

        <button
          @click="nextStep"
          :disabled="!canProceedToNext || isLastStep"
          class="flex items-center space-x-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white disabled:text-gray-500 rounded-lg transition-all duration-300"
        >
          <span>{{ isLastStep ? 'Finalizar' : 'Siguiente' }}</span>
          <ChevronRightIcon class="h-5 w-5" />
        </button>
      </div>
    </div>

    <!-- Modal de advertencia de pocas reseñas -->
    <LowReviewsWarningModal
      :visible="showLowReviewsWarning"
      :review-count="dynamicSelectedCount"
      @confirm="handleModalConfirm"
      @cancel="handleModalCancel"
    />

    <!-- Preview del reporte generado -->
    <div v-if="generatedHtmlContent" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div class="p-6 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-xl font-bold text-gray-800">Vista previa del reporte</h3>
          <button @click="closeReportPreview" class="text-gray-400 hover:text-gray-600">
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>
        <div class="h-96 overflow-y-auto">
          <iframe 
            :srcdoc="generatedHtmlContent" 
            class="w-full h-full" 
            sandbox="allow-scripts allow-same-origin" 
            title="Report Preview">
          </iframe>
        </div>
      </div>
    </div>
  </div>
</template>