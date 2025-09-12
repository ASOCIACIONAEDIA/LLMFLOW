<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
// import axios from 'axios'
import apiClient from '@/services/axiosInstance'
import { 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon,
  QuestionMarkCircleIcon,
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  DocumentTextIcon,
  CalendarIcon,
  StarIcon,
  GlobeEuropeAfricaIcon,
  ArrowPathIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'
import { Line, Bar, Doughnut } from 'vue-chartjs'
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
  ArcElement
} from 'chart.js'
import 'flag-icons/css/flag-icons.min.css'
import qs from 'qs'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

// Date Range
const dateRange = ref({
  start: '',
  end: ''
})
const activeQuickDateFilter = ref<string | null>('all-time')

const countries = ref<any[]>([])
const isLoadingCountries = ref(true)
const countriesError = ref<string | null>(null)
const isMarketDropdownOpen = ref(false)

// KPI Data - will be fetched
const kpiData = ref<any>({ // Changed to any to allow flexible structure from API initially
  totalReviews: { value: '0', change: '+0%', trend: 'neutral' },
  newReviews7d: { value: '0', change: '+0%', trend: 'neutral' }, // Renamed from newReviews24h
  averageSentiment: { value: '0', change: '+0', trend: 'neutral' },
  lastUpdated: { value: 'N/A', change: 'Real-time data', trend: 'neutral' }
})
const isLoadingKpis = ref(false)
const kpisError = ref<string | null>(null)
const newReviewsLabelSuffix = ref('(7d)'); // Step 1: Reactive variable for label suffix

const isLoadingReviewTrend = ref(false);
const reviewTrendError = ref<string | null>(null);

const isLoadingSourceDistribution = ref(false);
const sourceDistributionError = ref<string | null>(null);

// Add these for Source Statistics table
const sourceStats = ref<any[]>([]); // To store data for the table
const isLoadingSourceStats = ref(false);
const sourceStatsError = ref<string | null>(null);

// Add these for Latest Comments table
const latestComments = ref<any[]>([]); // Changed from static to reactive
const isLoadingLatestComments = ref(false);
const latestCommentsError = ref<string | null>(null);

// Helper function to format date to YYYY-MM-DD
const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0];
}

// Step 1: Adjust getFormattedPeriodSuffix for "all-time"
function getFormattedPeriodSuffix(startDateStr: string, endDateStr: string, activeFilter: string | null): string {
  if (activeFilter === 'all-time') {
    return ""; // Return empty string for "All Time"
  }
  if (activeFilter === 'last-year') return "(1Y)";
  if (activeFilter === 'last-quarter') return "(3M)";

  if (!startDateStr || !endDateStr) {
    return "(Range)";
  }
  const start = new Date(startDateStr);
  const end = new Date(endDateStr);
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || end < start) {
    return "(Invalid)";
  }
  const diffTime = end.getTime() - start.getTime();
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24)) + 1;
  if (diffDays <= 0) return "(Range)";
  if (diffDays === 1) return "(1d)";
  if (diffDays <= 10) return `(${diffDays}d)`;
  const diffWeeks = Math.round(diffDays / 7);
  if (diffWeeks === 1 && diffDays > 7 && diffDays < 11) return `(${diffDays}d)`;
  if (diffWeeks <= 8) return `(${diffWeeks}W)`;
  const diffMonths = Math.round(diffDays / 30.4375);
  if (diffMonths === 1 && diffDays > 31 && diffDays < (30.4375 * 1.5)) return `(${diffWeeks}W)`
  if (diffMonths <= 23) return `(${diffMonths}M)`;
  const diffYears = Math.round(diffDays / 365.25);
  return `(${diffYears}Y)`;
}

// --- Quick Date Selection Functions ---
const selectLastYear = () => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setFullYear(endDate.getFullYear() - 1);
  
  dateRange.value.start = formatDateForAPI(startDate);
  dateRange.value.end = formatDateForAPI(endDate);
  activeQuickDateFilter.value = 'last-year';
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value); // Step 3
  fetchAnalyticsOverviewData();
  fetchReviewVolumeTrendData();
  fetchSentimentDistributionData();
  fetchSourceDistributionData();
  fetchSourceStatsData(); // Add this call
  fetchLatestCommentsData(); // Add this call
}

// Step 3: selectAllTime ensures label suffix is empty
const selectAllTime = () => {
  const today = new Date();
  dateRange.value.start = ''; 
  dateRange.value.end = formatDateForAPI(today);
  activeQuickDateFilter.value = 'all-time';
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value); // Will set it to ""
  fetchAnalyticsOverviewData();
  fetchReviewVolumeTrendData();
  fetchSentimentDistributionData();
  fetchSourceDistributionData();
  fetchSourceStatsData(); // Add this call
  fetchLatestCommentsData(); // Add this call
}

const selectLastQuarter = () => {
  const today = new Date();
  const currentQuarter = Math.floor(today.getMonth() / 3);
  const currentYear = today.getFullYear();

  let startMonth, endMonth, year;

  if (currentQuarter === 0) {
    year = currentYear - 1;
    startMonth = 9; 
    endMonth = 11;
  } else {
    year = currentYear;
    startMonth = (currentQuarter - 1) * 3;
    endMonth = startMonth + 2;
  }

  const startDate = new Date(year, startMonth, 1);
  const endDate = new Date(year, endMonth + 1, 0); 

  dateRange.value.start = formatDateForAPI(startDate);
  dateRange.value.end = formatDateForAPI(endDate);
  activeQuickDateFilter.value = 'last-quarter';
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value); // Step 3
  fetchAnalyticsOverviewData();
  fetchReviewVolumeTrendData();
  fetchSentimentDistributionData();
  fetchSourceDistributionData();
  fetchSourceStatsData(); // Add this call
  fetchLatestCommentsData(); // Add this call
}

const onManualDateChange = () => {
  activeQuickDateFilter.value = null; 
  if (dateRange.value.start && dateRange.value.end) {
    newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value);
    fetchAnalyticsOverviewData(); 
    fetchReviewVolumeTrendData();
    fetchSentimentDistributionData();
    fetchSourceDistributionData();
    fetchSourceStatsData(); // Add this call
  }
}

// --- Computed Properties ---
const selectedCountryObjects = computed(() => {
  return countries.value.filter(c => c.selected);
})

const selectedCountries = computed(() => {
  return selectedCountryObjects.value.map(c => c.id.toUpperCase());
})

const selectedCountriesDisplay = computed(() => {
  const sel = selectedCountryObjects.value;
  if (sel.length === 0) return 'All Markets';
  if (sel.length === countries.value.length) return 'All Markets'; // If all are selected
  if (sel.length > 2) return `${sel.slice(0, 2).map(c=>c.name).join(', ')} +${sel.length - 2} more`;
  return sel.map(c => c.name).join(', ');
});

// --- Methods ---
const toggleMarketDropdown = () => {
  isMarketDropdownOpen.value = !isMarketDropdownOpen.value;
};

// --- Data Fetching Functions ---
async function fetchCountries() {
  isLoadingCountries.value = true
  countriesError.value = null
  try {
    const response = await apiClient.get('/countries/') // Assuming API endpoint
    countries.value = response.data.map((c: { country: string; name: string; flag?: string }) => ({ 
      id: c.country,
      name: c.name,
      flag: c.flag || `fi fi-${c.country.toLowerCase()}`, // Fallback flag
      selected: false // Default to not selected
    }))
    // Optionally, select "All Markets" or a default set of countries initially
  } catch (error) {
    console.error("Error fetching countries:", error)
    countriesError.value = "Could not load countries."
    countries.value = [] // Fallback to empty array
  } finally {
    isLoadingCountries.value = false
  }
}

async function fetchAnalyticsOverviewData() {
  isLoadingKpis.value = true
  kpisError.value = null
  
  const params: any = {};
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start;
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end;
  }

  // Send countries if:
  // 1. At least one country is selected.
  // 2. Not ALL countries are selected (because if all are selected, it's "All Markets", which means omitting the param or sending empty)
  //    However, the backend currently interprets "countries=None" as all markets.
  //    So, if some are selected, send them. If none are selected, don't send `params.countries`.
  
  if (selectedCountries.value.length > 0) {
    // If "All Markets" is selected by having ALL countries ticked, 
    // selectedCountries.value.length will be equal to countries.value.length.
    // In this case, we want to behave as if "All Markets" was chosen, meaning no specific country filter.
    // The backend interprets `countries=None` as "all markets".
    if (selectedCountries.value.length < countries.value.length) {
      params.countries = selectedCountries.value;
    }
    // If selectedCountries.value.length === countries.value.length, we intentionally do NOT set params.countries,
    // so the backend receives it as None, implying "All Markets".
  }
  // If selectedCountries.value.length is 0, params.countries is also not set.

  if (activeQuickDateFilter.value) {
    params.quickFilterType = activeQuickDateFilter.value;
  }
  
  

  try {
    const response = await apiClient.get('/analytics/overview', { 
      params,
      paramsSerializer: p => {
        // qs.stringify will format countries=['US', 'DE'] as countries=US&countries=DE
        // if arrayFormat: 'repeat' is used (or sometimes default with just qs.stringify)
        // FastAPI usually prefers repeated keys for lists.
        return qs.stringify(p, { arrayFormat: 'repeat' });
      }
    });
    kpiData.value = response.data; 
    

  } catch (error: any) {
    console.error("Error fetching analytics overview data:", error)
    kpisError.value = error.response?.data?.detail || "Could not load analytics overview."
    // Reset to default error state
    kpiData.value = {
      totalReviews: { value: 'N/A', change: '-', trend: 'neutral' },
      newReviews7d: { value: 'N/A', change: '-', trend: 'neutral' },
      averageSentiment: { value: 'N/A', change: '-', trend: 'neutral' },
      lastUpdated: { value: 'Error', change: 'Failed to load', trend: 'neutral' }
    }
  } finally {
    isLoadingKpis.value = false
  }
}

async function fetchReviewVolumeTrendData() {
  isLoadingReviewTrend.value = true;
  reviewTrendError.value = null;

  const params: any = {};
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start;
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end;
  }
  // Send countries only if some are selected AND not all are selected
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value;
  }
  // Backend defaults to 6 months if start_date is not sent, which is fine if dateRange.value.start is empty.

  
  try {
    const response = await apiClient.get('/analytics/review-volume-trend', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    });
    if (response.data && response.data.labels && response.data.datasets) {
      reviewTrendData.value = { 
        labels: response.data.labels,
        datasets: response.data.datasets.map((ds: any) => ({
          label: ds.label || 'Total Reviews', // Default label if missing
          data: ds.data || [],
          borderColor: ds.borderColor || '#6366F1',
          backgroundColor: ds.backgroundColor || 'rgba(99, 102, 241, 0.1)',
          fill: typeof ds.fill === 'boolean' ? ds.fill : true,
          tension: typeof ds.tension === 'number' ? ds.tension : 0.4,
        }))
      };
    } else {
      // Set to empty state if data is not as expected or empty
      reviewTrendData.value = { labels: [], datasets: [{ label: 'Total Reviews', data: [], borderColor: '#6366F1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: true, tension: 0.4 }] };
      console.warn("Invalid or empty data structure from API for review trend:", response.data);
      // Optionally set an error if empty data is considered an error for this chart
      // reviewTrendError.value = "No trend data available for the selected filters.";
    }
  } catch (error: any) {
    console.error("Error fetching review volume trend data:", error);
    reviewTrendError.value = error.response?.data?.detail || "Could not load review volume trend.";
    // Reset to empty state on error
    reviewTrendData.value = { labels: [], datasets: [{ label: 'Total Reviews', data: [], borderColor: '#6366F1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: true, tension: 0.4 }] };
  } finally {
    isLoadingReviewTrend.value = false;
  }
}

async function fetchSentimentDistributionData() {
  const params = {};
  if (dateRange.value.start) params.start_date = dateRange.value.start;
  if (dateRange.value.end) params.end_date = dateRange.value.end;
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value;
  }
  try {
    const response = await apiClient.get('/analytics/sentiment-distribution', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    });
    if (response.data && response.data.labels && response.data.datasets) {
      sentimentData.value = response.data;
    }
  } catch (error) {
    console.error("Error fetching sentiment distribution:", error);
    sentimentData.value = {
      labels: [],
      datasets: [
        { label: 'Positive', data: [], backgroundColor: '#10B981' },
        { label: 'Neutral', data: [], backgroundColor: '#6B7280' },
        { label: 'Negative', data: [], backgroundColor: '#EF4444' }
      ]
    };
  }
}

// Initial KPI structure (used for v-for in template)
const kpisMeta = ref([
  { id: 'totalReviews', name: 'Total Reviews', icon: ChartBarIcon, dataKey: 'totalReviews' },
  { id: 'newReviews7d', name: 'New Reviews', icon: DocumentTextIcon, dataKey: 'newReviews7d' }, // Base name, suffix added dynamically
  { id: 'averageSentiment', name: 'Average Sentiment', icon: ChatBubbleLeftRightIcon, dataKey: 'averageSentiment' },
  { id: 'lastUpdated', name: 'Last Updated', icon: ClockIcon, dataKey: 'lastUpdated' }
])

// Step 2: Adjust dynamicKpisMeta
const dynamicKpisMeta = computed(() => {
  return kpisMeta.value.map(kpi => {
    if (kpi.id === 'newReviews7d') {
      const name = `New Reviews ${newReviewsLabelSuffix.value}`.trim(); // Use trim to remove trailing space if suffix is empty
      return { ...kpi, name: name };
    }
    return kpi;
  });
});

// --- Watchers ---
watch([() => dateRange.value.start, () => dateRange.value.end], () => {
    // This watcher is now less critical for date changes if explicit calls handle it.
    // However, it can act as a fallback or for changes not covered by explicit calls.
    // Update label suffix here too if dates change by other means.
    if (activeQuickDateFilter.value === null && dateRange.value.start && dateRange.value.end) { // Manual change completed
        newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value);
    }
    // No fetch call here to prevent double fetch; rely on explicit calls or selectedCountries watcher
}, { deep: true });

watch(selectedCountries, () => {
    
    newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value);
    if (dateRange.value.end || activeQuickDateFilter.value === 'all-time') { // Ensure a valid state for fetching
        fetchAnalyticsOverviewData();
        fetchReviewVolumeTrendData();
        fetchSentimentDistributionData();
        fetchSourceDistributionData(); 
        fetchSourceStatsData(); 
        fetchLatestCommentsData(); // Add this call, as it depends on countries
    }
}, { deep: true });

// --- Lifecycle Hooks ---
onMounted(async () => {
  const token = sessionStorage.getItem('token')
  if (!token) {
    console.warn("User not authenticated. Redirect to login.");
    return;
  }
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  
  await fetchCountries(); 
  selectAllTime(); // This will now also call fetchLatestCommentsData
});

// Static KPIs, data will be dynamically inserted
// const kpis = [
//   {
//     name: 'Total Reviews',
//     value: '15,897', // This will become dynamic
//     change: '+12.5%', // This will become dynamic
//     trend: 'up', // This will become dynamic
//     icon: ChartBarIcon,
//     gradient: 'from-blue-400 to-indigo-500'
//   },
//   {
//     name: 'New Reviews (24h)',
//     value: '234', // Dynamic
//     change: '+8.1%', // Dynamic
//     trend: 'up', // Dynamic
//     icon: DocumentTextIcon,
//     gradient: 'from-emerald-400 to-teal-500'
//   },
//   {
//     name: 'Average Sentiment',
//     value: '4.2', // Dynamic
//     change: '+0.3', // Dynamic
//     trend: 'up', // Dynamic
//     icon: ChatBubbleLeftRightIcon,
//     gradient: 'from-rose-400 to-pink-500'
//   },
//   {
//     name: 'Last Updated',
//     value: '2 min ago', // Dynamic
//     change: 'Real-time data',
//     trend: 'neutral', // Dynamic
//     icon: ClockIcon,
//     gradient: 'from-violet-400 to-purple-500'
//   }
// ]

// Chart Data
const reviewTrendData = ref({
  labels: [] as string[],
  datasets: [
    {
      label: 'Total Reviews',
      data: [] as number[],
      borderColor: '#6366F1',
      backgroundColor: 'rgba(99, 102, 241, 0.1)',
      fill: true,
      tension: 0.4
    }
  ]
});

const sentimentData = ref({
  labels: [],
  datasets: [
    { label: 'Positive', data: [], backgroundColor: '#10B981' },
    { label: 'Neutral', data: [], backgroundColor: '#6B7280' },
    { label: 'Negative', data: [], backgroundColor: '#EF4444' }
  ]
});

const sourceDistributionData = ref({
  labels: [] as string[],
  datasets: [
    {
      data: [] as number[],
      backgroundColor: [] as string[]
    }
  ]
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const
    }
  }
}

const stackedBarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      stacked: true
    },
    y: {
      stacked: true,
      max: 100
    }
  },
  plugins: {
    legend: {
      position: 'bottom' as const
    }
  }
}

const formatNumber = (num: number) => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive':
      return 'bg-emerald-100 text-emerald-700'
    case 'neutral':
      return 'bg-gray-100 text-gray-700'
    case 'negative':
      return 'bg-red-100 text-red-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

async function fetchSourceDistributionData() {
  isLoadingSourceDistribution.value = true;
  sourceDistributionError.value = null;

  const params: any = {};
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start;
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end;
  }

  // Add selected countries to params if any are selected
  // And if not ALL countries are selected (as "All Markets" means no country filter)
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value;
  }
  // If selectedCountries.value.length is 0 (All Markets by default) or 
  // selectedCountries.value.length === countries.value.length (All Markets by selecting all),
  // params.countries will not be set, and backend should interpret as no country filter.

  try {
    // Use qs to serialize params, especially for arrays like 'countries'
    const response = await apiClient.get('/sources/review-counts', { 
      params,
      paramsSerializer: p => {
        return qs.stringify(p, { arrayFormat: 'repeat' });
      }
    }); 
    if (response.data && Array.isArray(response.data)) {
      const sourcesWithReviews = response.data.filter(source => source.count > 0);

      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
      };
      
      const displayNameToColorMap: Record<string, string> = {
        'Google Reviews': '#6366F1', 
        'Amazon': '#6B7280',         
        'Trustpilot': '#10B981',     
        'TripAdvisor': '#F59E0B',    
        'Druni': '#EC4899'           
      };

      const displayLabels: string[] = [];
      const displayData: number[] = [];
      const displayColors: string[] = [];

      sourcesWithReviews.forEach(source => {
        const displayName = apiIdToDisplayNameMap[source.id.toLowerCase()] || source.name; 
        const color = displayNameToColorMap[displayName] || '#CCCCCC';

        displayLabels.push(displayName);
        displayData.push(source.count);
        displayColors.push(color);
      });
      
      sourceDistributionData.value = {
        labels: displayLabels,
        datasets: [{
          data: displayData,
          backgroundColor: displayColors
        }]
      };
    } else {
      sourceDistributionData.value = { labels: [], datasets: [{ data: [], backgroundColor: [] }] };
    }
  } catch (error) {
    console.error('Error fetching source distribution:', error);
    sourceDistributionError.value = 'Failed to load source distribution data';
    sourceDistributionData.value = { labels: [], datasets: [{ data: [], backgroundColor: [] }] };
  } finally {
    isLoadingSourceDistribution.value = false;
  }
}

// New function to fetch data for the Source Statistics table
async function fetchSourceStatsData() {
  isLoadingSourceStats.value = true;
  sourceStatsError.value = null;

  const params: any = {};
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start;
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end;
  }
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value;
  }

  try {
    const response = await apiClient.get('/analytics/source-statistics', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    });

    if (response.data && Array.isArray(response.data)) {
      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
      };
      // Map API data to include the display name
      sourceStats.value = response.data.map((stat: any) => ({
        ...stat,
        sourceDisplayName: apiIdToDisplayNameMap[stat.id.toLowerCase()] || stat.name
      })).filter(stat => stat.reviewCount > 0); // Optionally filter out sources with 0 reviews for the table
    } else {
      sourceStats.value = [];
    }
  } catch (error: any) {
    console.error('Error fetching source statistics:', error);
    sourceStatsError.value = error.response?.data?.detail || 'Failed to load source statistics';
    sourceStats.value = [];
  } finally {
    isLoadingSourceStats.value = false;
  }
}

// New function to fetch data for the Latest Comments table
async function fetchLatestCommentsData() {
  isLoadingLatestComments.value = true;
  latestCommentsError.value = null;

  const params: any = {};
  // Only pass countries if some are selected and not "All Markets"
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value;
  }

  try {
    const response = await apiClient.get('/analytics/latest-comments', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    });

    if (response.data && Array.isArray(response.data)) {
      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
        // Add other mappings if your backend `sourceId` might differ
      };
      latestComments.value = response.data.map((comment: any) => ({
        ...comment,
        // Use sourceDisplayName from API if available, otherwise map sourceId
        source: apiIdToDisplayNameMap[comment.sourceId.toLowerCase()] || comment.sourceDisplayName || comment.sourceId,
        countryCode: comment.countryCode || 'xx' // Provide a fallback for flag
      }));
      
    } else {
      latestComments.value = [];
    }
  } catch (error: any) {
    console.error('Error fetching latest comments:', error);
    latestCommentsError.value = error.response?.data?.detail || 'Failed to load latest comments';
    latestComments.value = [];
  } finally {
    isLoadingLatestComments.value = false;
  }
}

async function fetchInitialData() {
  isLoading.value = true;
  errorFetching.value = null;
  try {
    const token = sessionStorage.getItem('token')
    if (!token) {
      throw new Error('Authentication token not found. Please log in again.');
    }
    // ... existing code ...
  } catch (error) {
    console.error("Error fetching initial data:", error);
    errorFetching.value = error instanceof Error ? error.message : "An unknown error occurred";
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Title with tooltip -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-display font-bold text-text-primary">Analytics Overview</h1>
        <div class="group relative">
          <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
          <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <p class="text-sm text-text-secondary">
              Comprehensive analytics dashboard showing key performance indicators, trends, and insights from customer reviews.
            </p>
          </div>
        </div>
      </div>
      
      <!-- Date and Country Filters Row -->
      <div class="flex items-start space-x-6">
        <!-- Date Filter Column -->
        <div class="flex flex-col space-y-2">
        <div class="flex items-center space-x-2">
          <CalendarIcon class="h-5 w-5 text-text-secondary" />
            <span class="text-sm font-medium text-text-secondary">Date Range:</span>
          </div>
          <div class="flex items-center space-x-2">
          <input
            type="date"
            v-model="dateRange.start"
              @change="onManualDateChange"
              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 text-sm p-2"
          />
            <span class="text-text-secondary text-sm">to</span>
        <input
          type="date"
          v-model="dateRange.end"
              @change="onManualDateChange"
              :min="dateRange.start"
              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 text-sm p-2"
            />
          </div>
          <!-- Quick Select Buttons -->
          <div class="flex space-x-2">
            <button 
              @click="selectLastYear" 
              class="px-3 py-1 text-xs rounded transition-colors duration-150 ease-in-out"
              :class="activeQuickDateFilter === 'last-year' 
                ? 'bg-primary text-white hover:bg-primary-dark' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">
              Last Year
            </button>
            <button 
              @click="selectAllTime" 
              class="px-3 py-1 text-xs rounded transition-colors duration-150 ease-in-out"
              :class="activeQuickDateFilter === 'all-time' 
                ? 'bg-primary text-white hover:bg-primary-dark' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">
              All Time
            </button>
            <button 
              @click="selectLastQuarter" 
              class="px-3 py-1 text-xs rounded transition-colors duration-150 ease-in-out"
              :class="activeQuickDateFilter === 'last-quarter' 
                ? 'bg-primary text-white hover:bg-primary-dark' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">
              Last Quarter
            </button>
          </div>
        </div>

        <!-- Country Filter Column with Dropdown -->
        <div class="flex flex-col space-y-2 relative w-80"> 
          <div class="flex items-center space-x-2">
            <GlobeEuropeAfricaIcon class="h-5 w-5 text-text-secondary" />
            <span class="text-sm font-medium text-text-secondary">Markets:</span>
          </div>
          
          <div v-if="isLoadingCountries" class="flex items-center text-sm text-text-secondary py-2 h-10"> 
            <ArrowPathIcon class="h-4 w-4 animate-spin mr-1" /> Loading markets...
          </div>
          <div v-else-if="countriesError" class="text-sm text-red-500 py-2 h-10"> 
            {{ countriesError }}
          </div>
          <template v-else>
            <!-- Dropdown Button -->
            <button 
              @click="toggleMarketDropdown" 
              class="flex items-center justify-between w-full p-2 border border-border rounded-lg text-left text-sm text-text-primary bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-primary-light h-10"
            >
              <span class="truncate">{{ selectedCountriesDisplay }}</span>
              <ChevronDownIcon class="h-5 w-5 text-gray-400 transition-transform duration-200" :class="{'rotate-180': isMarketDropdownOpen}" />
            </button>

            <!-- Dropdown Panel -->
            <div 
              v-if="isMarketDropdownOpen" 
              class="absolute top-full mt-1 w-full bg-white border border-border rounded-lg shadow-lg z-20 max-h-48 overflow-y-auto p-2 space-y-1"
              @click.stop 
            >
              <!-- Optional: "Select All/None" Checkbox -->
              <!-- 
              <label class="flex items-center space-x-2 cursor-pointer p-1 hover:bg-gray-100 rounded border-b border-border mb-1">
                <input
                  type="checkbox"
                  @change="toggleSelectAllCountries"
                  :checked="areAllCountriesSelected"
                  class="rounded border-border text-primary focus:ring-primary/20"
                />
                <span class="text-sm font-medium text-text-primary">Select All / None</span>
              </label>
              -->
              <label 
                v-for="country in countries" 
                :key="country.id" 
                class="flex items-center space-x-2 cursor-pointer p-1 hover:bg-gray-100 rounded">
                <input
                  type="checkbox"
                  v-model="country.selected"
                  class="rounded border-border text-primary focus:ring-primary/20"
                />
                <span :class="country.flag" class="mr-1 text-lg"></span>
                <span class="text-sm text-text-primary">{{ country.name }}</span>
              </label>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- KPI Cards -->
    <div v-if="isLoadingKpis" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="i in 4" :key="i" class="bg-white p-6 rounded-2xl shadow-sm border border-border animate-pulse">
            <div class="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div class="h-8 bg-gray-300 rounded w-1/2 mb-3"></div>
            <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
    </div>
     <div v-else-if="kpisError" class="text-red-500 bg-red-50 p-4 rounded-lg text-center">
      Error loading KPI data: {{ kpisError }}
    </div>
    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="kpiItem in dynamicKpisMeta" 
           :key="kpiItem.id"
           class="bg-white p-6 rounded-2xl shadow-sm border border-border">
        <div class="flex justify-between items-start">
          <dt class="text-sm font-medium text-text-secondary">
            {{ kpiItem.name }}
          </dt>
          <component :is="kpiItem.icon" 
                    class="h-5 w-5 text-primary-dark" />
        </div>
        <dd class="mt-2 text-3xl font-display font-bold text-text-primary">{{ kpiData[kpiItem.dataKey]?.value || 'N/A' }}</dd>
        <div class="mt-2 flex items-center">
          <component :is="kpiData[kpiItem.dataKey]?.trend === 'up' ? ArrowTrendingUpIcon : ArrowTrendingDownIcon"
                    v-if="kpiData[kpiItem.dataKey]?.trend && kpiData[kpiItem.dataKey]?.trend !== 'neutral'"
                    class="h-4 w-4 mr-1"
                    :class="kpiData[kpiItem.dataKey]?.trend === 'up' ? 'text-emerald-500' : 'text-red-500'" />
          <span :class="[
            'text-sm font-medium',
            kpiData[kpiItem.dataKey]?.trend === 'up' ? 'text-emerald-600' : 
            kpiData[kpiItem.dataKey]?.trend === 'down' ? 'text-red-600' : 
            'text-text-secondary'
          ]">
            {{ kpiData[kpiItem.dataKey]?.change || '-' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Review Trend -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-border">
        <h3 class="text-lg font-display font-semibold text-text-primary mb-6">Review Volume Trend</h3>
        <div v-if="isLoadingReviewTrend" class="h-80 flex items-center justify-center">
          <ArrowPathIcon class="h-8 w-8 text-primary animate-spin" />
          <span class="ml-2 text-text-secondary">Loading trend data...</span>
        </div>
        <div v-else-if="reviewTrendError" class="h-80 flex flex-col items-center justify-center text-red-500">
          <p>Error: {{ reviewTrendError }}</p>
          <button @click="fetchReviewVolumeTrendData" class="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm">
            Try Again
          </button>
        </div>
        <div v-else class="h-80">
          <Line :data="reviewTrendData" :options="chartOptions" v-if="reviewTrendData.labels && reviewTrendData.labels.length > 0"/>
          <p v-else class="text-center text-text-secondary h-full flex items-center justify-center">No data available for the selected period.</p>
        </div>
      </div>

      <!-- Sentiment Analysis -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-border">
        <h3 class="text-lg font-display font-semibold text-text-primary mb-6">Sentiment Distribution</h3>
        <div class="h-80">
          <Bar :data="sentimentData" :options="stackedBarOptions" />
        </div>
      </div>

      <!-- Source Distribution -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-border">
        <h3 class="text-lg font-display font-semibold text-text-primary mb-6">Reviews by Source</h3>
        <div class="h-80">
          <div v-if="isLoadingSourceDistribution" class="h-full flex items-center justify-center">
            <ArrowPathIcon class="h-8 w-8 text-primary animate-spin" />
            <span class="ml-2 text-text-secondary">Loading source distribution...</span>
          </div>
          <div v-else-if="sourceDistributionError" class="h-full flex flex-col items-center justify-center text-red-500">
            <p>{{ sourceDistributionError }}</p>
            <button @click="fetchSourceDistributionData" class="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm">
              Try Again
            </button>
          </div>
          <div v-else-if="!sourceDistributionData.labels || sourceDistributionData.labels.length === 0" class="h-full flex items-center justify-center">
            <p class="text-text-secondary">No review data available for sources</p>
          </div>
          <Doughnut 
            v-else 
            :data="sourceDistributionData" 
            :options="chartOptions" 
          />
        </div>
      </div>

      <!-- Source Statistics Table -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-border">
        <h3 class="text-lg font-display font-semibold text-text-primary mb-6">Source Statistics</h3>
        <div v-if="isLoadingSourceStats" class="flex items-center justify-center py-8">
          <ArrowPathIcon class="h-8 w-8 text-primary animate-spin mr-2" />
          <span class="text-text-secondary">Loading statistics...</span>
        </div>
        <div v-else-if="sourceStatsError" class="text-red-500 bg-red-50 p-4 rounded-lg text-center">
          Error: {{ sourceStatsError }}
          <button @click="fetchSourceStatsData" class="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm">
            Try Again
          </button>
        </div>
        <div v-else-if="sourceStats.length === 0" class="text-center text-text-secondary py-8">
          No source statistics available for the selected filters.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full">
            <thead>
              <tr class="border-b border-border">
                <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Source</th>
                <th class="text-right py-3 px-4 text-sm font-medium text-text-secondary">Reviews</th>
                <th class="text-right py-3 px-4 text-sm font-medium text-text-secondary">Avg. Sentiment</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stat in sourceStats" 
                  :key="stat.id"
                  class="border-b border-border last:border-b-0">
                <td class="py-3 px-4 text-text-primary">{{ stat.sourceDisplayName }}</td>
                <td class="py-3 px-4 text-right text-text-primary">{{ formatNumber(stat.reviewCount) }}</td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end space-x-1" v-if="stat.reviewCount > 0">
                    <StarIcon class="h-4 w-4 text-amber-400" />
                    <span class="font-medium">{{ stat.avgSentiment.toFixed(1) }}</span>
                  </div>
                  <span v-else class="text-text-secondary">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Latest Comments -->
    <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
      <h3 class="text-lg font-display font-semibold text-text-primary mb-6">Latest Comments</h3>
      <div v-if="isLoadingLatestComments" class="flex items-center justify-center py-8">
        <ArrowPathIcon class="h-8 w-8 text-primary animate-spin mr-2" />
        <span class="text-text-secondary">Loading comments...</span>
      </div>
      <div v-else-if="latestCommentsError" class="text-red-500 bg-red-50 p-4 rounded-lg text-center">
        Error: {{ latestCommentsError }}
        <button @click="fetchLatestCommentsData" class="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm">
          Try Again
        </button>
      </div>
      <div v-else-if="latestComments.length === 0" class="text-center text-text-secondary py-8">
        No recent comments available for the selected filters.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full">
          <thead>
            <tr class="border-b border-border">
              <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Country</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Source</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Date Added</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Comment</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Sentiment</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(comment, index) in latestComments" 
                :key="index"
                class="border-b border-border last:border-b-0">
              <td class="py-3 px-4">
                <span :class="`fi fi-${comment.countryCode || 'xx'} text-2xl`"></span> <!-- Fallback for flag -->
              </td>
              <td class="py-3 px-4 text-text-primary">{{ comment.source }}</td>
              <td class="py-3 px-4 text-text-secondary">{{ formatDate(comment.date) }}</td>
              <td class="py-3 px-4 text-text-primary max-w-md">
                <p class="line-clamp-2">{{ comment.comment }}</p>
              </td>
              <td class="py-3 px-4">
                <span v-if="comment.sentiment" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="getSentimentColor(comment.sentiment)">
                  {{ comment.sentiment.charAt(0).toUpperCase() + comment.sentiment.slice(1) }}
                </span>
                <span v-else class="text-text-secondary">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>