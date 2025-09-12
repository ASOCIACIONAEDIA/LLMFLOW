<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import apiClient from '@/services/axiosInstance'
import { 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon,
  UserGroupIcon, 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon, 
  ClockIcon, 
  ArrowRightIcon,
  DocumentChartBarIcon,
  ChartBarIcon,
  DocumentMagnifyingGlassIcon,
  ArrowPathIcon,
  CircleStackIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CpuChipIcon,
  QuestionMarkCircleIcon,
  CalendarIcon,
  StarIcon,
  GlobeEuropeAfricaIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'
import qs from 'qs'
import { useReportStore } from '@/store/reportStore'
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

const toast = useToast()
const reportAndScrapeStore = useReportStore()

// --- Quick Actions Data ---


// --- Recent Activity Types ---
interface RecentActivity {
  id: string;
  type: 'reviews' | 'report' | 'analysis' | 'scraping_job' | 'archetype_generation';
  description: string;
  timestamp: string;
  icon: any;
  iconColor: string;
  dateObject: string;
  status: string;
  progress?: number;
}

interface RawActivityData {
  id: string;
  type: 'reviews' | 'report' | 'analysis' | 'scraping_job' | 'archetype_generation';
  description: string;
  iconKey: string; 
  iconColor: string; 
  dateObject: string;
  status: string;
  progress?: number;
}

// --- KPI Stats Type ---
interface KpiStat {
  id: string;
  name: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  icon: any;
  iconColorClass: string;
  trendType?: 'positive' | 'negative' | 'neutral';
}

// --- Icon Mapping ---
const iconMap: Record<string, any> = {
  DocumentTextIcon,
  DocumentChartBarIcon,
  ChartBarIcon,
  DocumentMagnifyingGlassIcon,
  UserGroupIcon,
  ArrowTrendingUpIcon,
  CircleStackIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CpuChipIcon,
};

// --- Reactive Data ---
const stats = ref<KpiStat[]>([
  { 
    id: 'totalReviews',
    name: 'Total Reviews', 
    value: '...', 
    change: 'N/A', 
    trend: 'neutral',
    icon: ChartBarIcon,
    iconColorClass: 'text-blue-500',
    trendType: 'neutral'
  },
  { 
    id: 'newReviews7d',
    name: 'New Reviews (7d)', 
    value: '...', 
    change: '...', 
    trend: 'neutral',
    icon: DocumentTextIcon,
    iconColorClass: 'text-emerald-500',
    trendType: 'neutral'
  },
  { 
    id: 'averageSentiment',
    name: 'Average Sentiment', 
    value: '...', 
    change: '...', 
    trend: 'neutral',
    icon: ChatBubbleLeftRightIcon,
    iconColorClass: 'text-rose-500',
    trendType: 'neutral'
  },
  { 
    id: 'lastUpdated',
    name: 'Last Updated', 
    value: 'Loading...', 
    change: 'Real-time data', 
    trend: 'neutral',
    icon: ClockIcon,
    iconColorClass: 'text-violet-500',
    trendType: 'neutral'
  },
])

const isLoadingKpis = ref(true)
const kpisError = ref<string | null>(null)
const recentActivities = ref<RecentActivity[]>([])
const MAX_RECENT_ACTIVITIES = 7

// --- Analytics Data ---
const dateRange = ref({
  start: '',
  end: ''
})
const activeQuickDateFilter = ref<string | null>('all-time')
const countries = ref<any[]>([])
const isLoadingCountries = ref(true)
const countriesError = ref<string | null>(null)
const isMarketDropdownOpen = ref(false)
const newReviewsLabelSuffix = ref('(7d)')

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
})

const sentimentData = ref({
  labels: [],
  datasets: [
    { label: 'Positive', data: [], backgroundColor: '#10B981' },
    { label: 'Neutral', data: [], backgroundColor: '#6B7280' },
    { label: 'Negative', data: [], backgroundColor: '#EF4444' }
  ]
})

const sourceDistributionData = ref({
  labels: [] as string[],
  datasets: [
    {
      data: [] as number[],
      backgroundColor: [] as string[]
    }
  ]
})

const sourceStats = ref<any[]>([])
const latestComments = ref<any[]>([])
const isLoadingLatestComments = ref(false)
const latestCommentsError = ref<string | null>(null)
const isLoadingReviewTrend = ref(false)
const reviewTrendError = ref<string | null>(null)
const isLoadingSourceDistribution = ref(false)
const sourceDistributionError = ref<string | null>(null)
const isLoadingSourceStats = ref(false)
const sourceStatsError = ref<string | null>(null)

// --- Chart Options ---
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

// --- Computed Properties ---
const selectedCountryObjects = computed(() => {
  return countries.value.filter(c => c.selected)
})

const selectedCountries = computed(() => {
  return selectedCountryObjects.value.map(c => c.id.toUpperCase())
})

const selectedCountriesDisplay = computed(() => {
  const sel = selectedCountryObjects.value
  if (sel.length === 0) return 'All Markets'
  if (sel.length === countries.value.length) return 'All Markets'
  if (sel.length > 2) return `${sel.slice(0, 2).map(c=>c.name).join(', ')} +${sel.length - 2} more`
  return sel.map(c => c.name).join(', ')
})

const dynamicKpisMeta = computed(() => {
  const kpisMeta = [
    { id: 'totalReviews', name: 'Total Reviews', icon: ChartBarIcon, dataKey: 'totalReviews' },
    { id: 'newReviews7d', name: 'New Reviews', icon: DocumentTextIcon, dataKey: 'newReviews7d' },
    { id: 'averageSentiment', name: 'Average Sentiment', icon: ChatBubbleLeftRightIcon, dataKey: 'averageSentiment' },
    { id: 'lastUpdated', name: 'Last Updated', icon: ClockIcon, dataKey: 'lastUpdated' }
  ]
  
  return kpisMeta.map(kpi => {
    if (kpi.id === 'newReviews7d') {
      const name = `New Reviews ${newReviewsLabelSuffix.value}`.trim()
      return { ...kpi, name: name }
    }
    return kpi
  })
})

// --- Helper Functions ---
const formatRelativeTime = (isoDateString?: string): string => {
  if (!isoDateString) return 'just now'
  try {
    const date = new Date(isoDateString)
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (typeof Intl.RelativeTimeFormat !== 'undefined') {
        const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
        if (diffInSeconds < 60) return rtf.format(-diffInSeconds, 'second')
        const diffInMinutes = Math.floor(diffInSeconds / 60)
        if (diffInMinutes < 60) return rtf.format(-diffInMinutes, 'minute')
        const diffInHours = Math.floor(diffInMinutes / 60)
        if (diffInHours < 24) return rtf.format(-diffInHours, 'hour')
        const diffInDays = Math.floor(diffInHours / 24)
        if (diffInDays < 7) return rtf.format(-diffInDays, 'day')
        return date.toLocaleDateString()
    } else {
        const minutes = Math.floor(diffInSeconds / 60)
        const hours = Math.floor(minutes / 60)
        const days = Math.floor(hours / 24)
        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
        return 'just now'
    }
  } catch (e) {
    return 'Invalid date'
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

const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0]
}

const getFormattedPeriodSuffix = (startDateStr: string, endDateStr: string, activeFilter: string | null): string => {
  if (activeFilter === 'all-time') {
    return ""
  }
  if (activeFilter === 'last-year') return "(1Y)"
  if (activeFilter === 'last-quarter') return "(3M)"

  if (!startDateStr || !endDateStr) {
    return "(Range)"
  }
  const start = new Date(startDateStr)
  const end = new Date(endDateStr)
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || end < start) {
    return "(Invalid)"
  }
  const diffTime = end.getTime() - start.getTime()
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24)) + 1
  if (diffDays <= 0) return "(Range)"
  if (diffDays === 1) return "(1d)"
  if (diffDays <= 10) return `(${diffDays}d)`
  const diffWeeks = Math.round(diffDays / 7)
  if (diffWeeks === 1 && diffDays > 7 && diffDays < 11) return `(${diffDays}d)`
  if (diffWeeks <= 8) return `(${diffWeeks}W)`
  const diffMonths = Math.round(diffDays / 30.4375)
  if (diffMonths === 1 && diffDays > 31 && diffDays < (30.4375 * 1.5)) return `(${diffWeeks}W)`
  if (diffMonths <= 23) return `(${diffMonths}M)`
  const diffYears = Math.round(diffDays / 365.25)
  return `(${diffYears}Y)`
}

// --- Methods ---
const handleQuickAction = (action: typeof quickActions[0]) => {
  toast.info(`Navigating to ${action.name}...`)
  setTimeout(() => {
    window.location.href = action.href
  }, 300)
}

const toggleMarketDropdown = () => {
  isMarketDropdownOpen.value = !isMarketDropdownOpen.value
}

// --- Date Selection Functions ---
const selectLastYear = () => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setFullYear(endDate.getFullYear() - 1)
  
  dateRange.value.start = formatDateForAPI(startDate)
  dateRange.value.end = formatDateForAPI(endDate)
  activeQuickDateFilter.value = 'last-year'
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value)
  fetchAllAnalyticsData()
}

const selectAllTime = () => {
  const today = new Date()
  dateRange.value.start = ''
  dateRange.value.end = formatDateForAPI(today)
  activeQuickDateFilter.value = 'all-time'
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value)
  fetchAllAnalyticsData()
}

const selectLastQuarter = () => {
  const today = new Date()
  const currentQuarter = Math.floor(today.getMonth() / 3)
  const currentYear = today.getFullYear()

  let startMonth, endMonth, year

  if (currentQuarter === 0) {
    year = currentYear - 1
    startMonth = 9
    endMonth = 11
  } else {
    year = currentYear
    startMonth = (currentQuarter - 1) * 3
    endMonth = startMonth + 2
  }

  const startDate = new Date(year, startMonth, 1)
  const endDate = new Date(year, endMonth + 1, 0)

  dateRange.value.start = formatDateForAPI(startDate)
  dateRange.value.end = formatDateForAPI(endDate)
  activeQuickDateFilter.value = 'last-quarter'
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value)
  fetchAllAnalyticsData()
}

const onManualDateChange = () => {
  activeQuickDateFilter.value = null
  if (dateRange.value.start && dateRange.value.end) {
    newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value)
    fetchAllAnalyticsData()
  }
}

// --- Activity Management ---
const loadRecentActivities = () => {
  console.log("%cDashboard: loadRecentActivities CALLED", "color: green; font-weight: bold;")
  let processedActivities: RecentActivity[] = []
  try {
    const storedRawActivitiesString = sessionStorage.getItem('recentActivities')
    let rawActivitiesToProcess: RawActivityData[] = []

    if (storedRawActivitiesString) {
      const parsedRawActivities = JSON.parse(storedRawActivitiesString)
      if (Array.isArray(parsedRawActivities) && parsedRawActivities.length > 0) {
        rawActivitiesToProcess = parsedRawActivities.filter(
          (act): act is RawActivityData =>
            act && typeof act.id === 'string' &&
            typeof act.iconKey === 'string' &&
            typeof act.dateObject === 'string' &&
            typeof act.description === 'string' &&
            typeof act.iconColor === 'string' &&
            typeof act.status === 'string' &&
            ['reviews', 'report', 'analysis', 'scraping_job', 'archetype_generation'].includes(act.type)
        )
      }
    }
    
    processedActivities = rawActivitiesToProcess.map(activityRaw => ({
      ...activityRaw,
      timestamp: formatRelativeTime(activityRaw.dateObject),
      icon: iconMap[activityRaw.iconKey] || DocumentMagnifyingGlassIcon, 
    })).sort((a, b) => new Date(b.dateObject).getTime() - new Date(a.dateObject).getTime())

  } catch (e) {
    console.error("Error loading/parsing recent activities from sessionStorage:", e)
    recentActivities.value = []
  }
  recentActivities.value = processedActivities
}

const upsertActivity = (activityData: RawActivityData) => {
  console.log(`%cDashboard: upsertActivity CALLED for ID: ${activityData.id}, Status: ${activityData.status}`, "color: dodgerblue; font-weight: bold;")

  let currentProgress = activityData.progress
  if (activityData.status === 'completed' || activityData.status === 'failed' || activityData.status === 'timeout') {
    currentProgress = 100
  } else if (currentProgress === undefined) {
    currentProgress = activityData.status === 'initiated' ? 5 : 0
  }

  const displayActivity: RecentActivity = {
    ...activityData,
    timestamp: formatRelativeTime(activityData.dateObject),
    icon: iconMap[activityData.iconKey] || DocumentMagnifyingGlassIcon,
    progress: currentProgress,
  }

  const existingActivityIndex = recentActivities.value.findIndex(act => act.id === displayActivity.id)

  if (existingActivityIndex !== -1) {
    recentActivities.value.splice(existingActivityIndex, 1, displayActivity)
  } else {
    recentActivities.value.unshift(displayActivity)
  }

  recentActivities.value.sort((a, b) => new Date(b.dateObject).getTime() - new Date(a.dateObject).getTime())

  if (recentActivities.value.length > MAX_RECENT_ACTIVITIES) {
    recentActivities.value = recentActivities.value.slice(0, MAX_RECENT_ACTIVITIES)
  }
  
  try {
    const rawActivitiesToStore = recentActivities.value.map(actDisp => {
        const iconKeyVal = Object.keys(iconMap).find(key => iconMap[key] === actDisp.icon) || 'DocumentMagnifyingGlassIcon'
        return {
            id: actDisp.id,
            type: actDisp.type,
            description: actDisp.description,
            iconKey: iconKeyVal,
            iconColor: actDisp.iconColor,
            dateObject: actDisp.dateObject,
            status: actDisp.status,
            progress: actDisp.progress,
        } as RawActivityData
    })
    sessionStorage.setItem('recentActivities', JSON.stringify(rawActivitiesToStore))
  } catch (e) {
    console.error("Error in upsertActivity (sessionStorage part):", e)
  }
}

// --- Data Fetching Functions ---
async function fetchCountries() {
  isLoadingCountries.value = true
  countriesError.value = null
  try {
    const response = await apiClient.get('/countries/')
    countries.value = response.data.map((c: { country: string; name: string; flag?: string }) => ({ 
      id: c.country,
      name: c.name,
      flag: c.flag || `fi fi-${c.country.toLowerCase()}`,
      selected: false
    }))
  } catch (error) {
    console.error("Error fetching countries:", error)
    countriesError.value = "Could not load countries."
    countries.value = []
  } finally {
    isLoadingCountries.value = false
  }
}

async function fetchDashboardKpis() {
  isLoadingKpis.value = true
  kpisError.value = null

  const formatDateForAPI = (date: Date): string => date.toISOString().split('T')[0]
  const today = new Date()
  const sevenDaysAgo = new Date(today)
  sevenDaysAgo.setDate(today.getDate() - 7)

  const params7Days: any = {
    start_date: formatDateForAPI(sevenDaysAgo),
    end_date: formatDateForAPI(today),
  }

  const paramsAllTime: any = {
    quickFilterType: 'all-time',
  }

  try {
    const response7Days = await apiClient.get('/analytics/overview', {
      params: params7Days,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })
    const data7Days = response7Days.data

    const responseAllTime = await apiClient.get('/analytics/overview', {
      params: paramsAllTime,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })
    const dataAllTime = responseAllTime.data

    stats.value = stats.value.map(stat => {
      let kpiData
      switch (stat.id) {
        case 'totalReviews':
          kpiData = dataAllTime.totalReviews
          return {
            ...stat,
            value: kpiData?.value || 'N/A',
            change: kpiData?.change || 'N/A',
            trend: kpiData?.trend || 'neutral',
            trendType: kpiData?.trend === 'up' ? 'positive' : kpiData?.trend === 'down' ? 'negative' : 'neutral',
          }
        case 'newReviews7d':
          kpiData = data7Days.newReviews7d
          return {
            ...stat,
            value: kpiData?.value || 'N/A',
            change: kpiData?.change || 'N/A',
            trend: kpiData?.trend || 'neutral',
            trendType: kpiData?.trend === 'up' ? 'positive' : kpiData?.trend === 'down' ? 'negative' : 'neutral',
          }
        case 'averageSentiment':
          kpiData = dataAllTime.averageSentiment
          return {
            ...stat,
            value: kpiData?.value || 'N/A',
            change: kpiData?.change || 'N/A',
            trend: kpiData?.trend || 'neutral',
            trendType: kpiData?.trend === 'up' ? 'positive' : kpiData?.trend === 'down' ? 'negative' : 'neutral',
          }
        case 'lastUpdated':
          let lastUpdatedValue = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          let lastUpdatedChange = 'Live Data'

          if (recentActivities.value.length > 0 && recentActivities.value[0].dateObject) {
            try {
              const mostRecentActivityDate = new Date(recentActivities.value[0].dateObject)
              lastUpdatedValue = mostRecentActivityDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
              if (mostRecentActivityDate.toDateString() !== new Date().toDateString()) {
                lastUpdatedValue = `${mostRecentActivityDate.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${lastUpdatedValue}`
              }
              lastUpdatedChange = 'Latest Activity'
            } catch (e) {
              console.error("Error parsing date for last updated KPI:", e)
              kpiData = dataAllTime.lastUpdated
              lastUpdatedValue = kpiData?.value.startsWith('As of') ? kpiData.value.split('As of ')[1].split(' UTC')[0] : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              lastUpdatedChange = kpiData?.change || 'Real-time data'
            }
          } else {
            kpiData = dataAllTime.lastUpdated
            lastUpdatedValue = kpiData?.value.startsWith('As of') ? kpiData.value.split('As of ')[1].split(' UTC')[0] : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            lastUpdatedChange = kpiData?.change || 'Real-time data'
          }
          return {
            ...stat,
            value: lastUpdatedValue,
            change: lastUpdatedChange,
            trend: 'neutral', 
            trendType: 'neutral'
          }
        default:
          return stat
      }
    })

  } catch (error: any) {
    console.error("Error fetching dashboard KPIs:", error)
    kpisError.value = error.response?.data?.detail || "Could not load KPI data."
    stats.value = stats.value.map(s => ({ ...s, value: 'Error', change: '-', trend: 'neutral' }))
  } finally {
    isLoadingKpis.value = false
  }
}

async function fetchAnalyticsOverviewData() {
  const params: any = {}
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end
  }

  if (selectedCountries.value.length > 0) {
    if (selectedCountries.value.length < countries.value.length) {
      params.countries = selectedCountries.value
    }
  }

  if (activeQuickDateFilter.value) {
    params.quickFilterType = activeQuickDateFilter.value
  }
  
  try {
    const response = await apiClient.get('/analytics/overview', { 
      params,
      paramsSerializer: p => {
        return qs.stringify(p, { arrayFormat: 'repeat' })
      }
    })
    
    // Update stats with analytics data
    stats.value = stats.value.map(stat => {
      const kpiData = response.data[stat.id]
      if (kpiData) {
        return {
          ...stat,
          value: kpiData.value || 'N/A',
          change: kpiData.change || 'N/A',
          trend: kpiData.trend || 'neutral',
          trendType: kpiData.trend === 'up' ? 'positive' : kpiData.trend === 'down' ? 'negative' : 'neutral',
        }
      }
      return stat
    })

  } catch (error: any) {
    console.error("Error fetching analytics overview data:", error)
  }
}

async function fetchReviewVolumeTrendData() {
  isLoadingReviewTrend.value = true
  reviewTrendError.value = null

  const params: any = {}
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end
  }
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value
  }
  
  try {
    const response = await apiClient.get('/analytics/review-volume-trend', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })
    
    if (response.data && response.data.labels && response.data.datasets) {
      reviewTrendData.value = { 
        labels: response.data.labels,
        datasets: response.data.datasets.map((ds: any) => ({
          label: ds.label || 'Total Reviews',
          data: ds.data || [],
          borderColor: ds.borderColor || '#6366F1',
          backgroundColor: ds.backgroundColor || 'rgba(99, 102, 241, 0.1)',
          fill: typeof ds.fill === 'boolean' ? ds.fill : true,
          tension: typeof ds.tension === 'number' ? ds.tension : 0.4,
        }))
      }
    } else {
      reviewTrendData.value = { labels: [], datasets: [{ label: 'Total Reviews', data: [], borderColor: '#6366F1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: true, tension: 0.4 }] }
    }
  } catch (error: any) {
    console.error("Error fetching review volume trend data:", error)
    reviewTrendError.value = error.response?.data?.detail || "Could not load review volume trend."
    reviewTrendData.value = { labels: [], datasets: [{ label: 'Total Reviews', data: [], borderColor: '#6366F1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: true, tension: 0.4 }] }
  } finally {
    isLoadingReviewTrend.value = false
  }
}

async function fetchSentimentDistributionData() {
  const params: any = {}
  if (dateRange.value.start) params.start_date = dateRange.value.start
  if (dateRange.value.end) params.end_date = dateRange.value.end
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value
  }
  try {
    const response = await apiClient.get('/analytics/sentiment-distribution', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })
    if (response.data && response.data.labels && response.data.datasets) {
      sentimentData.value = response.data
    }
  } catch (error) {
    console.error("Error fetching sentiment distribution:", error)
    sentimentData.value = {
      labels: [],
      datasets: [
        { label: 'Positive', data: [], backgroundColor: '#10B981' },
        { label: 'Neutral', data: [], backgroundColor: '#6B7280' },
        { label: 'Negative', data: [], backgroundColor: '#EF4444' }
      ]
    }
  }
}

async function fetchSourceDistributionData() {
  isLoadingSourceDistribution.value = true
  sourceDistributionError.value = null

  const params: any = {}
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end
  }

  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value
  }

  try {
    const response = await apiClient.get('/sources/review-counts', { 
      params,
      paramsSerializer: p => {
        return qs.stringify(p, { arrayFormat: 'repeat' })
      }
    }) 
    if (response.data && Array.isArray(response.data)) {
      const sourcesWithReviews = response.data.filter(source => source.count > 0)

      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
      }
      
      const displayNameToColorMap: Record<string, string> = {
        'Google Reviews': '#6366F1', 
        'Amazon': '#6B7280',         
        'Trustpilot': '#10B981',     
        'TripAdvisor': '#F59E0B',    
        'Druni': '#EC4899'           
      }

      const displayLabels: string[] = []
      const displayData: number[] = []
      const displayColors: string[] = []

      sourcesWithReviews.forEach(source => {
        const displayName = apiIdToDisplayNameMap[source.id.toLowerCase()] || source.name 
        const color = displayNameToColorMap[displayName] || '#CCCCCC'

        displayLabels.push(displayName)
        displayData.push(source.count)
        displayColors.push(color)
      })
      
      sourceDistributionData.value = {
        labels: displayLabels,
        datasets: [{
          data: displayData,
          backgroundColor: displayColors
        }]
      }
    } else {
      sourceDistributionData.value = { labels: [], datasets: [{ data: [], backgroundColor: [] }] }
    }
  } catch (error) {
    console.error('Error fetching source distribution:', error)
    sourceDistributionError.value = 'Failed to load source distribution data'
    sourceDistributionData.value = { labels: [], datasets: [{ data: [], backgroundColor: [] }] }
  } finally {
    isLoadingSourceDistribution.value = false
  }
}

async function fetchSourceStatsData() {
  isLoadingSourceStats.value = true
  sourceStatsError.value = null

  const params: any = {}
  if (dateRange.value.start) {
    params.start_date = dateRange.value.start
  }
  if (dateRange.value.end) {
    params.end_date = dateRange.value.end
  }
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value
  }

  try {
    const response = await apiClient.get('/analytics/source-statistics', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })

    if (response.data && Array.isArray(response.data)) {
      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
      }
      sourceStats.value = response.data.map((stat: any) => ({
        ...stat,
        sourceDisplayName: apiIdToDisplayNameMap[stat.id.toLowerCase()] || stat.name
      })).filter(stat => stat.reviewCount > 0)
    } else {
      sourceStats.value = []
    }
  } catch (error: any) {
    console.error('Error fetching source statistics:', error)
    sourceStatsError.value = error.response?.data?.detail || 'Failed to load source statistics'
    sourceStats.value = []
  } finally {
    isLoadingSourceStats.value = false
  }
}

async function fetchLatestCommentsData() {
  isLoadingLatestComments.value = true
  latestCommentsError.value = null

  const params: any = {}
  if (selectedCountries.value.length > 0 && selectedCountries.value.length < countries.value.length) {
    params.countries = selectedCountries.value
  }

  try {
    const response = await apiClient.get('/analytics/latest-comments', {
      params,
      paramsSerializer: p => qs.stringify(p, { arrayFormat: 'repeat' })
    })

    if (response.data && Array.isArray(response.data)) {
      const apiIdToDisplayNameMap: Record<string, string> = {
        'google': 'Google Reviews',
        'amazon': 'Amazon',
        'trustpilot': 'Trustpilot',
        'tripadvisor': 'TripAdvisor',
        'druni': 'Druni'
      }
      latestComments.value = response.data.map((comment: any) => ({
        ...comment,
        source: apiIdToDisplayNameMap[comment.sourceId.toLowerCase()] || comment.sourceDisplayName || comment.sourceId,
        countryCode: comment.countryCode || 'xx'
      }))
      
    } else {
      latestComments.value = []
    }
  } catch (error: any) {
    console.error('Error fetching latest comments:', error)
    latestCommentsError.value = error.response?.data?.detail || 'Failed to load latest comments'
    latestComments.value = []
  } finally {
    isLoadingLatestComments.value = false
  }
}

async function syncBackendReportsToLocal() {
  try {
    const reportResponse = await apiClient.get('/reports/generated')
    const backendReports: any[] = reportResponse.data || []

    backendReports.forEach(report => {
      const reportActivity: RawActivityData = {
        id: `report_${String(report._id || report.id)}`,
        type: 'report',
        description: `Generated "${report.report_type || 'Unknown Report'}" for ${report.brand_name || 'brand'}`,
        dateObject: report.generated_at || new Date().toISOString(),
        iconKey: 'DocumentChartBarIcon',
        iconColor: 'text-emerald-500',
        status: 'completed', 
        progress: 100,
      }
      upsertActivity(reportActivity)
    })
    
  } catch (error) {
    console.error('Error in syncBackendReportsToLocal:', error)
  }
}

// Fetch all analytics data
const fetchAllAnalyticsData = () => {
  fetchAnalyticsOverviewData()
  fetchReviewVolumeTrendData()
  fetchSentimentDistributionData()
  fetchSourceDistributionData()
  fetchSourceStatsData()
  fetchLatestCommentsData()
}

// --- Watchers ---
watch(() => reportAndScrapeStore.latestReportActivityUpdate, (newActivityInfo) => {
  if (newActivityInfo) {
    upsertActivity(newActivityInfo as RawActivityData)
  }
}, { deep: true })

watch(() => reportAndScrapeStore.latestScrapingActivityUpdate, (newActivityInfo) => {
  if (newActivityInfo) {
    upsertActivity(newActivityInfo as RawActivityData)
  }
}, { deep: true })

watch(() => reportAndScrapeStore.latestArchetypeActivityUpdate, (newActivityInfo) => {
  if (newActivityInfo) {
    upsertActivity(newActivityInfo as RawActivityData)
  }
}, { deep: true })

watch(selectedCountries, () => {
  newReviewsLabelSuffix.value = getFormattedPeriodSuffix(dateRange.value.start, dateRange.value.end, activeQuickDateFilter.value)
  if (dateRange.value.end || activeQuickDateFilter.value === 'all-time') {
    fetchAllAnalyticsData()
  }
}, { deep: true })

// --- Lifecycle ---
onMounted(async () => {
  const token = sessionStorage.getItem('token')
  if (!token) {
    return
  }

  loadRecentActivities()

  const activitiesFromStoreRaw: (RawActivityData | null)[] = [
    reportAndScrapeStore.latestReportActivityUpdate,
    reportAndScrapeStore.latestScrapingActivityUpdate,
    reportAndScrapeStore.latestArchetypeActivityUpdate
  ]

  const activitiesFromStore = activitiesFromStoreRaw.filter(act => act !== null) as RawActivityData[]

  if (activitiesFromStore.length > 0) {
    for (const activityInfo of activitiesFromStore) {
      upsertActivity(activityInfo)
    }
  }
  
  await syncBackendReportsToLocal()
  await fetchCountries()
  fetchDashboardKpis()
  selectAllTime()

  const handleStorageEvent = (event: StorageEvent) => {
    if (event.key === 'recentActivities') {
      loadRecentActivities()
      fetchDashboardKpis()
    }
  }
  window.addEventListener('storage', handleStorageEvent)

  const intervalId = setInterval(() => {
    recentActivities.value = recentActivities.value.map(act => ({
      ...act,
      timestamp: formatRelativeTime(act.dateObject) 
    }))
  }, 60000)

  onUnmounted(() => {
    clearInterval(intervalId)
    window.removeEventListener('storage', handleStorageEvent)
  })
})
</script>

<template>
  <div class="space-y-8">
    <!-- Title with Date and Country Filters -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <h1 class="text-2xl font-display font-bold text-text-primary">Dashboard & Analytics</h1>
        <div class="group relative">
          <QuestionMarkCircleIcon class="h-5 w-5 text-text-secondary cursor-help" />
          <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <p class="text-sm text-text-secondary">
              Comprehensive dashboard with analytics, showing key performance indicators, trends, and recent activities.
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

    <!-- KPI Stats -->
    <div v-if="isLoadingKpis" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="i in 4" :key="`loader-${i}`" class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 animate-pulse">
            <div class="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div class="h-8 bg-gray-300 rounded w-1/2 mb-3"></div>
            <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
    </div>
    <div v-else-if="kpisError" class="text-red-500 bg-red-50 p-4 rounded-lg text-center col-span-full">
      Error loading KPI data: {{ kpisError }}
    </div>
    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="stat in stats" 
           :key="stat.name"
           class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div class="flex justify-between items-start">
          <dt class="text-sm font-medium text-text-secondary">
            {{ stat.name }}
          </dt>
          <component :is="stat.icon" class="h-5 w-5" :class="stat.iconColorClass" />
        </div>
        <dd class="mt-2 text-2xl font-display font-bold text-text-primary">{{ stat.value }}</dd>
        <div class="mt-1 flex items-center text-xs">
          <component 
            :is="stat.trend === 'up' ? ArrowTrendingUpIcon : stat.trend === 'down' ? ArrowTrendingDownIcon : null"
            v-if="stat.trend !== 'neutral' && !( (stat.id === 'totalReviews' || stat.id === 'averageSentiment') && stat.change === 'N/A' )"
            class="h-4 w-4 mr-1"
            :class="{
              'text-emerald-500': stat.trend === 'up',
              'text-red-500': stat.trend === 'down'
            }" />
          
          <span v-if="(stat.id === 'totalReviews' || stat.id === 'averageSentiment') && stat.change === 'N/A'"
                class="text-xs font-medium text-text-secondary">
            All Time
          </span>
          <span v-else-if="stat.id === 'lastUpdated' || stat.change !== 'N/A'"
                :class="[
                  'inline-flex items-center px-1.5 py-0.5 rounded font-medium',
                  stat.trendType === 'positive' ? 'bg-emerald-100 text-emerald-700' :
                  stat.trendType === 'negative' ? 'bg-red-100 text-red-700' :
                  'text-text-secondary' 
                ]">
            {{ stat.change }}
          </span>
           <span v-else class="text-xs font-medium text-text-secondary">
             {{ stat.change }}
           </span>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div>
      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="action in quickActions"
           :key="action.name"
           @click="handleQuickAction(action)"
           class="group relative bg-surface rounded-2xl shadow-sm overflow-hidden cursor-pointer hover:shadow-md transition-all duration-300">
          <div class="absolute inset-0 opacity-100 transition-opacity duration-300" :class="action.color"></div>
          <div class="relative p-6">
            <div class="mb-4 flex justify-between items-center">
              <component :is="action.icon" class="h-8 w-8 text-white transition-colors duration-300" />
              <ArrowRightIcon class="h-5 w-5 text-white opacity-100 transform translate-x-0 group-hover:translate-x-1 transition-all duration-300" />
            </div>
            <h3 class="text-lg font-display font-bold text-white transition-colors duration-300">
              {{ action.name }}
            </h3>
            <p class="mt-2 text-sm text-white/90 transition-colors duration-300">
              {{ action.description }}
            </p>
          </div>
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

    <!-- Two Column Layout: Recent Activity + Latest Comments -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <!-- Recent Activity -->
      <div class="lg:col-span-2">
        <h2 class="text-xl font-display font-bold text-text-primary mb-6">Recent Activity</h2>
        <div class="bg-surface rounded-2xl shadow-sm p-6 relative overflow-hidden">
          <div class="absolute inset-0 bg-gradient-to-r from-blue-400 to-indigo-500 opacity-10"></div>
          
          <transition-group name="slide-fade" tag="div" class="relative space-y-4">
            <div v-if="recentActivities.length === 0" key="no-activity" class="text-center text-text-secondary py-4">
              No recent activity to display.
            </div>
            <div v-for="activity in recentActivities" 
                 :key="activity.id"
                 class="flex flex-col py-3 px-4 bg-white/80 backdrop-blur-sm rounded-xl border border-white/20 space-y-2">
              
              <div class="flex items-center space-x-4">
              <div :class="[
                  'flex items-center justify-center w-8 h-8 rounded-lg shrink-0', 
                   activity.type === 'report' && activity.status === 'completed' ? 'bg-emerald-100' : 
                   activity.type === 'report' ? 'bg-blue-100' : 
                   activity.type === 'scraping_job' && activity.status === 'completed' ? 'bg-green-100' :
                   activity.type === 'scraping_job' && (activity.status === 'failed' || activity.status === 'timeout') ? (activity.iconColor.includes('red') ? 'bg-red-100' : 'bg-orange-100') :
                   activity.type === 'scraping_job' ? 'bg-blue-100' : 
                   activity.type === 'archetype_generation' && activity.status === 'completed' ? 'bg-purple-100' :
                   activity.type === 'archetype_generation' ? 'bg-indigo-100' : 
                  'bg-violet-100' 
              ]">
                <component :is="activity.icon" 
                          class="h-5 w-5"
                          :class="activity.iconColor" />
              </div>
                <div class="flex-1 min-w-0"> 
                  <p class="text-sm font-medium text-text-primary truncate">{{ activity.description }}</p>
                <span class="text-xs text-text-secondary">{{ activity.timestamp }}</span>
                </div>
              </div>
              <div v-if="activity.progress !== undefined && activity.progress < 100 && activity.status !== 'failed' && activity.status !== 'timeout' && activity.status !== 'completed'"
                   class="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                <div class="h-full bg-primary rounded-full transition-all duration-5000 ease-out"
                     :style="{ width: activity.progress + '%' }">
                </div>
              </div>
            </div>
          </transition-group>
        </div>
      </div>

      <!-- Latest Comments -->
      <div class="lg:col-span-3">
        <h2 class="text-xl font-display font-bold text-text-primary mb-6">Latest Comments</h2>
        <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
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
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Date</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Comment</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-secondary">Sentiment</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(comment, index) in latestComments" 
                    :key="index"
                    class="border-b border-border last:border-b-0">
                  <td class="py-3 px-4">
                    <span :class="`fi fi-${comment.countryCode || 'xx'} text-2xl`"></span>
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
    </div>
  </div>
</template>

<style scoped>
/* Animations for Recent Activity List */
.slide-fade-enter-active {
  transition: all 0.5s cubic-bezier(0.55, 0, 0.1, 1);
}
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.55, 0, 0.1, 1);
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-30px) scale(0.95);
}

/* Ensure moving items animate smoothly */
.slide-fade-move {
  transition: transform 0.5s cubic-bezier(0.55, 0, 0.1, 1);
}
</style>