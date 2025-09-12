<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onUnmounted, watchEffect } from 'vue'
import { 
  QuestionMarkCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ShoppingBagIcon,
  BuildingStorefrontIcon,
  GlobeAltIcon,
  StarIcon,
  PlusIcon,
  EnvelopeIcon,
  ChatBubbleLeftRightIcon,
  ArrowPathIcon,
  ShoppingCartIcon,
  DevicePhoneMobileIcon,
  ComputerDesktopIcon,
  MapPinIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  TagIcon,
  CircleStackIcon,
  InformationCircleIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'
import { GoogleMap, Marker } from 'vue3-google-map'
import apiClient from '@/services/axiosInstance'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useReportStore } from '@/store/reportStore'
import { TabGroup, TabList, Tab, TabPanels, TabPanel, Switch, Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'

const props = defineProps<{
  competitorName?: string;
  competitorId?: string;
  sourceContainerId?: string; // <-- ADD THIS PROP
  sourceContainerName?: string; // <-- ADD THIS PROP
  initialSources?: any[];
}>();

// --- Store and Toast Instances ---
const reportAndScrapeStore = useReportStore();
const toast = useToast();
const router = useRouter();
const route = useRoute();

// --- Competitor Scraping State ---
const competitorToScrape = ref<string | null>(props.competitorName || null);

// --- Source Container State ---
const sourceContainerToConfigure = ref<string | null>(props.sourceContainerName || null);

// --- Google Maps API Key ---
const googleMapsApiKey = ref(import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '');

// --- Google Places Search State ---
const isSearchingGooglePlaces = computed(() => reportAndScrapeStore.isDiscoveringGooglePlaces);
const googlePlacesResults = ref<any[]>([]); // This remains local to merge different types of results
const showGoogleMapAndList = ref(false);
const googleSearchError = computed(() => reportAndScrapeStore.googlePlacesDiscoveryError);

// --- State for Adding New Places ---
const additionalPlaceQuery = ref('');
const isAddingNewPlace = ref(false); // This seems unused, can be reviewed later
const addNewPlaceError = ref<string | null>(null); // This seems unused, can be reviewed later

// --- State for Map Click & Add ---
const isFetchingPlaceFromMapClick = ref(false);
const mapClickError = ref<string | null>(null);

// --- State for "Add a specific place" ---
const specificPlaceSuggestions = ref<any[]>([]);
const selectedSpecificPlaces = ref<any[]>([]);
const isLoadingSpecificPlaceSuggestions = ref(false);
const specificPlaceSuggestionsError = ref<string | null>(null);
const isAddingSelectedSpecificPlaces = ref(false);
const addSelectedSpecificPlacesError = ref<string | null>(null);
const specificPlaceSearchContainer = ref<HTMLElement | null>(null);

// --- Trustpilot Discovery State (now mostly from store) ---
const trustpilotBrandNameForDiscovery = ref('');
const trustpilotCountryForDiscovery = ref('');
// Local state to hold the selected URL from the results
const selectedTrustpilotUrl = ref<string | null>(null);

// --- Computed properties to get reactive state from the store ---
const isDiscoveringTrustpilotUrls = computed(() => reportAndScrapeStore.isDiscoveringTrustpilot);
const trustpilotDiscoveryError = computed(() => reportAndScrapeStore.trustpilotDiscoveryError);
const discoveredTrustpilotUrls = computed(() => reportAndScrapeStore.trustpilotDiscoveredUrls);

// --- TripAdvisor Discovery State ---
const tripadvisorBrandNameForDiscovery = ref('');
const tripadvisorCountryForDiscovery = ref('');
const selectedTripadvisorUrl = ref<string | null>(null);

// --- Computed properties for TripAdvisor Discovery ---
const isDiscoveringTripadvisorUrls = computed(() => reportAndScrapeStore.isDiscoveringTripadvisor);
const tripadvisorDiscoveryError = computed(() => reportAndScrapeStore.tripadvisorDiscoveryError);
const discoveredTripadvisorUrls = computed(() => reportAndScrapeStore.tripadvisorDiscoveredUrls);

// --- Source definitions (moved up) ---
interface ProductScrapeItem {
  identifier: string;
  url?: string;
  title?: string;
  scrapeTargets: {
    amazon: boolean;
    druni: boolean;
  };
}

interface BackendSourceConfig {
  source_type: string;
  brand_name?: string;
  countries?: string[];
  number_of_reviews?: number;
  is_brand_query?: boolean;
  google_config?: { selected_provinces?: string[] };
}

const sources = ref([
  {
    id: 'mybusiness',
    name: 'Google My Business',
    icon: BuildingStorefrontIcon,
    logo: '/images/mybusiness-square-logo.png',
    enabled: false,
    config: {
      brandName: '',
      countries: [] as string[],
      selectedProvinces: [] as string[]
    }
  },
  {
    id: 'tripadvisor',
    name: 'TripAdvisor',
    icon: GlobeAltIcon,
    logo: '/images/tripadvisor-square-logo.png',
    enabled: false,
    config: {
      brandName: '',
      countries: ['es'] as string[] 
    }
  },
  {
    id: 'trustpilot',
    name: 'Trustpilot',
    icon: StarIcon,
    logo: '/images/trustpilot-square-logo.png',
    enabled: false,
    config: {
      brandName: '',
      countries: [] as string[] 
    }
  },
  {
    id: 'products', 
    name: 'Products',
    icon: ShoppingBagIcon, 
    logo: '/images/product-default-logo.png', 
    enabled: false,
    enabled_amazon: false,
    enabled_druni: false,
    config: {
      inputQuery: '', 
      productItems: [] as ProductScrapeItem[], 
      isBrandQuery: false, 
      countries: [] as string[] 
    },
    isFixedReviews: true 
  }
]);

// --- NEW state for right-hand selector: Refactored for Amazon/Retailers split ---
const sourceViews = computed(() => {
    return [
      { id: 'mybusiness', name: 'Google My Business', icon: BuildingStorefrontIcon },
      { id: 'tripadvisor', name: 'TripAdvisor', icon: GlobeAltIcon },
      { id: 'trustpilot', name: 'Trustpilot', icon: StarIcon },
      { id: 'products_amazon', name: 'Amazon', icon: ShoppingBagIcon },
      { id: 'products_druni', name: 'Retailers', icon: ShoppingCartIcon },
    ];
});

const selectedSourceView = ref(sourceViews.value[0].id);

// Computed properties to get specific source objects
const googleMyBusinessSource = computed(() => sources.value.find(s => s.id === 'mybusiness'));
const tripAdvisorSource = computed(() => sources.value.find(s => s.id === 'tripadvisor'));
const trustpilotSource = computed(() => sources.value.find(s => s.id === 'trustpilot'));
const productsSource = computed(() => sources.value.find(s => s.id === 'products'));

const hasAnyProducts = computed(() => {
    const productsSrc = sources.value.find(s => s.id === 'products');
    if (!productsSrc || !productsSrc.config.productItems) return false;
    return productsSrc.config.productItems.length > 0;
});

const isCurrentSourceViewEnabled = computed({
  get() {
    const source = currentSourceForDisplay.value;
    if (!source) return false;
    if (source.id === 'products') {
      if (selectedSourceView.value === 'products_amazon') {
        return source.enabled_amazon;
      }
      if (selectedSourceView.value === 'products_druni') {
        return source.enabled_druni;
      }
    }
    return source.enabled;
  },
  set(newValue: boolean) {
    const source = currentSourceForDisplay.value;
    if (!source) return;
    if (source.id === 'products') {
      if (selectedSourceView.value === 'products_amazon') {
        source.enabled_amazon = newValue;
      } else if (selectedSourceView.value === 'products_druni') {
        source.enabled_druni = newValue;
      }
    } else {
      source.enabled = newValue;
    }
  }
});

const currentSourceForDisplay = computed(() => {
  if (!selectedSourceView.value) {
    return null; 
  }
  // If the view is for Amazon or Retailers, find the underlying 'products' source
  if (selectedSourceView.value.startsWith('products_')) {
    return sources.value.find(s => s.id === 'products');
  }
  const source = sources.value.find(s => s.id === selectedSourceView.value);
  return source;
});

const numberOfReviewsSelectable = ref(1000);
const FIXED_REVIEWS = 500;

const userInfo = ref(null); // Seems unused, can be reviewed for removal
const userBrandName = ref<string | null>(null);
const isLoading = ref(true);

const allCountries = ref<{id: string, name: string, flag: string}[]>([]);
const currentSourceId = ref(null);

const spanishProvinces = [
  'Álava', 'Albacete', 'Alicante', 'Almería', 'Asturias', 'Ávila', 'Badajoz', 'Barcelona',
  'Burgos', 'Cáceres', 'Cádiz', 'Cantabria', 'Castellón', 'Ciudad Real', 'Córdoba', 'La Coruña',
  'Cuenca', 'Gerona', 'Granada', 'Guadalajara', 'Guipúzcoa', 'Huelva', 'Huesca', 'Islas Baleares',
  'Jaén', 'León', 'Lérida', 'Lugo', 'Madrid', 'Málaga', 'Murcia', 'Navarra', 'Orense', 'Palencia',
  'Las Palmas', 'Pontevedra', 'La Rioja', 'Salamanca', 'Santa Cruz de Tenerife', 'Segovia',
  'Sevilla', 'Soria', 'Tarragona', 'Teruel', 'Toledo', 'Valencia', 'Valladolid', 'Vizcaya',
  'Zamora', 'Zaragoza', 'Ceuta', 'Melilla'
];

const comingSoonSources = [
  { id: 'carrefour', name: 'Carrefour', icon: ShoppingCartIcon, logo: '/images/carrefour-square-logo.png', description: 'Retail customer reviews' },
  { id: 'appstore', name: 'Apple App Store', icon: DevicePhoneMobileIcon, logo: '/images/appstore-square-logo.png', description: 'iOS app reviews' },
  { id: 'playstore', name: 'Google Play Store', icon: ComputerDesktopIcon, logo: '/images/google-play-square-logo.png', description: 'Android app reviews' },
  { id: 'yelp', name: 'Yelp', icon: MapPinIcon, logo: '/images/yelp-square-logoo.png', description: 'Local business reviews' }
];

const faqItems = ref([
  { question: 'How often are reviews scraped?', answer: 'Reviews are scraped every 72 hours by default. ¿Do you want more frequent updates? Contact Tama Insights team.' },
  { question: 'What happens if a source is temporarily unavailable?', answer: 'Our system will automatically retry failed scraping attempts and notify you if there are persistent issues with any source.' },
  { question: 'Can I export the raw data?', answer: 'No, you cant not export the raw data. If you need it, we offer Data As a Service solutions and we can provide it to you for internal purposes.' },
  { question: 'Is historical data available?', answer: 'Yes, when you first connect a source, we retrieve up to 12 months of historical review data where available. ¿Do you need a bigger lookback window? We can also get it. Contact our team' }
]);

const openFaqItem = ref<number | null>(null);

const toggleFaq = (index: number) => {
  openFaqItem.value = openFaqItem.value === index ? null : index;
};

const isSourceConfigured = (source: any) => {
  if (!source.enabled) return true;
  switch (source.id) {
    case 'products':
      if (!source.config.productItems || source.config.productItems.length === 0) {
        return false;
      }
      // A product source is configured if at least one item has a scrape target enabled (Amazon or Druni).
      return source.config.productItems.some(
        (item: ProductScrapeItem) => item.scrapeTargets?.amazon || item.scrapeTargets?.druni
      );
    case 'mybusiness':
      const mainSearchConfigured = !!source.config.brandName?.trim() && source.config.countries.length > 0;
      const specificPlacesExistAndValid = googlePlacesResults.value.length > 0 && googlePlacesResults.value.every(p => p.google_id);
      return mainSearchConfigured || specificPlacesExistAndValid;
    case 'trustpilot':
      // A URL must be selected from the discovery results. This now checks the local selection.
      return !!selectedTrustpilotUrl.value;
    case 'tripadvisor':
      return !!selectedTripadvisorUrl.value;
    default: // Old default for other sources
      return !!source.config.brandName?.trim() && source.config.countries.length > 0;
  }
};

const canSearchGooglePlaces = computed(() => {
  const googleSource = sources.value.find(s => s.id === 'mybusiness');
  return googleSource && !!googleSource.config.brandName?.trim() && googleSource.config.countries.length > 0;
});

const canSaveAndGather = computed(() => {
  const enabledSources = sources.value.filter(source => source.enabled);
  return enabledSources.length > 0 && enabledSources.every(source => isSourceConfigured(source));
});

const mapCenter = computed(() => {
  if (googlePlacesResults.value.length > 0) {
    const firstPlace = googlePlacesResults.value[0];
    if (firstPlace && typeof firstPlace.latitude === 'number' && typeof firstPlace.longitude === 'number') {
      return { lat: firstPlace.latitude, lng: firstPlace.longitude };
    }
  }
  return { lat: 40.416775, lng: -3.703790 }; // Default to Madrid
});

const mapZoom = computed(() => {
  return googlePlacesResults.value.length === 1 ? 14 : (googlePlacesResults.value.length > 1 ? 11 : 9);
});

const mapMarkers = computed(() => {
  return googlePlacesResults.value
    .filter(place => place && typeof place.latitude === 'number' && typeof place.longitude === 'number')
    .map(place => ({
      position: { lat: place.latitude, lng: place.longitude },
      title: place.name,
      key: place.google_id
    }));
});

// NEW: Watch for results from the store and update the local component state
watch(() => reportAndScrapeStore.googlePlacesDiscoveredResults, (newResults) => {
  if (reportAndScrapeStore.googlePlacesDiscoveryCompleted && newResults) {
    // Preserve any locations that were added manually
    const manualPlaces = googlePlacesResults.value.filter(p => p.origin === 'manual');
    const searchResults = newResults.map(p => ({ ...p, origin: 'main_search' }));

    // Avoid duplicates if the search is re-run
    const manualPlaceIds = new Set(manualPlaces.map(p => p.google_id));
    const uniqueSearchResults = searchResults.filter(p => !manualPlaceIds.has(p.google_id));

    googlePlacesResults.value = [...manualPlaces, ...uniqueSearchResults];
    
    if (googlePlacesResults.value.length > 0) {
      showGoogleMapAndList.value = true;
    }
  }
}, { deep: true });

const fetchCountries = async () => {
  try {
    const response = await apiClient.get('/countries/');
    allCountries.value = response.data.map((country: any) => ({
      id: country.country, // Map 'country' to 'id'
      name: country.name,
      flag: country.flag
    }));
  } catch (error) {
    console.error("Error fetching countries:", error);
    toast.error("Could not load country list.");
    // Fallback to a minimal list if API fails
    allCountries.value = [{ id: 'es', name: 'Spain', flag: 'fi fi-es' }];
  }
};

onMounted(async () => {
  // If in competitor mode, the name comes directly from props
  if (isCompetitorMode.value) {
    competitorToScrape.value = props.competitorName || null;
  } else if (route.query.competitor) {
    competitorToScrape.value = route.query.competitor as string;
  }
  
  // Optional: pre-configure a source based on the competitor
  if (competitorToScrape.value) {
    const trustpilotSourceRef = sources.value.find(s => s.id === 'trustpilot');
    if (trustpilotSourceRef) {
      selectedSourceView.value = 'trustpilot';
      trustpilotSourceRef.enabled = true;
      // Pre-fill discovery input, not the config brandName which will hold the URL
      trustpilotBrandNameForDiscovery.value = competitorToScrape.value;
    }
  }

  await fetchCountries(); // Fetch countries on component mount

  const token = sessionStorage.getItem('token');
  if (!token) {
    router.push('/login');
    return;
  }
  try {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    // Fetch user brand name only if NOT in competitor mode
    if (!isCompetitorMode.value) {
      try {
        const userResponse = await apiClient.get('/user/me');
        if (userResponse.data && userResponse.data.marca_name) {
          userBrandName.value = userResponse.data.marca_name;
          // Pre-fill discovery fields for better UX
          amazonBrandNameForBrightData.value = userResponse.data.marca_name;
          trustpilotBrandNameForDiscovery.value = userResponse.data.marca_name;
          tripadvisorBrandNameForDiscovery.value = userResponse.data.marca_name;
        }
      } catch (userError) {
        console.error('Error al obtener información del usuario:', userError);
      }
    }
    
    // In competitor mode, sources are passed as props. Otherwise, load them.
    if (isCompetitorMode.value) {
        // Logic to populate the 'sources' ref from 'props.initialSources'
        // This will be similar to what loadSourceConfigs does
        loadSourcesFromProps(); 
        // Also load saved products, as they are part of the configuration
        await loadSavedProducts();
    } else if (isSourceContainerMode.value) {
        loadSourcesFromProps();
    } else {
        await loadSourceConfigs();
        await loadSavedProducts(); // Fetch full product data
    }
    
    const tsSource = sources.value.find(s => s.id === 'trustpilot');
    if (tsSource && tsSource.enabled && tsSource.config.brandName) {
      // If a URL is already configured, set it as the selected one.
      selectedTrustpilotUrl.value = tsSource.config.brandName;
      // Also pre-fill the discovery country if it's available
      if (tsSource.config.countries && tsSource.config.countries.length > 0) {
        trustpilotCountryForDiscovery.value = tsSource.config.countries[0];
      }
    }
    const taSourceOnLoad = sources.value.find(s => s.id === 'tripadvisor');
    if (taSourceOnLoad && taSourceOnLoad.enabled) {
      // If a URL is already configured, set it as the selected one.
      if (taSourceOnLoad.config.brandName) {
        selectedTripadvisorUrl.value = taSourceOnLoad.config.brandName;
      }
      // Also pre-fill the discovery country if it's available. TA is fixed to 'es' but we set it here for UI consistency.
      tripadvisorCountryForDiscovery.value = 'es';
    }
  } catch (error: any) {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('token');
      router.push('/login');
    }
  } finally {
    isLoading.value = false;
  }
  // Note: Original onUnmounted logic moved to a separate onUnmounted hook for clarity
});

watchEffect(() => {
  const productsSrc = sources.value.find(s => s.id === 'products');
  if (productsSrc) {
    productsSrc.enabled = productsSrc.enabled_amazon || productsSrc.enabled_druni;
  }
});

// New function to handle loading from props
function loadSourcesFromProps() {
    if (props.initialSources && props.initialSources.length > 0) {
        // Find the 'products' source configuration in the frontend state
        const productsSource = sources.value.find(s => s.id === 'products');
        if (productsSource) {
            // A map to hold product items and their scrape targets
            const productItemsMap = new Map<string, ProductScrapeItem>();

            // Iterate over the source configurations passed from the backend
            props.initialSources.forEach(config => {
                if ((config.source_type === 'amazon' || config.source_type === 'druni') && config.brand_name) {
                    const identifiers = config.brand_name.split('%%-%%');
                    
                    identifiers.forEach(identifier => {
                        const trimmedId = identifier.trim();
                        if (!trimmedId) return;

                        // Get or create the product item
                        if (!productItemsMap.has(trimmedId)) {
                            productItemsMap.set(trimmedId, {
                                identifier: trimmedId,
                                scrapeTargets: { amazon: false, druni: false }
                            });
                        }
                        const item = productItemsMap.get(trimmedId)!;

                        // Enable the correct scrape target
                        if (config.source_type === 'amazon') item.scrapeTargets.amazon = true;
                        if (config.source_type === 'druni') item.scrapeTargets.druni = true;
                    });
                }
            });

            // Update the products list in the component's state
            productsSource.config.productItems = Array.from(productItemsMap.values());
        }


        props.initialSources.forEach(config => {
            let originalSourceType = config.source_type;
            let sourceTypeId = originalSourceType;
            // Map amazon/druni from backend to 'products' source in frontend
            if (sourceTypeId === 'amazon' || sourceTypeId === 'druni') {
                sourceTypeId = 'products';
            }
            const source = sources.value.find(s => s.id === sourceTypeId);
            if (source) {
                if (source.id === 'products') {
                    if (originalSourceType === 'amazon') source.enabled_amazon = true;
                    if (originalSourceType === 'druni') source.enabled_druni = true;
                } else {
                    source.enabled = true;
                }

                if (source.id === 'products') {
                    // Combine countries from all product-related sources
                    const newCountries = config.countries || [];
                    if (!source.config.countries) {
                        source.config.countries = [];
                    }
                    const combined = [...source.config.countries, ...newCountries];
                    source.config.countries = [...new Set(combined)];
                } else if (source.id === 'mybusiness') {
                    source.config.brandName = config.brand_name || '';
                    source.config.countries = config.countries || [];
                    if (config.google_config) {
                        source.config.selectedProvinces = config.google_config.selected_provinces || [];
                        if (config.google_config.places) {
                            googlePlacesResults.value = config.google_config.places.map((p: any) => ({ ...p, origin: 'main_search' }));
                            if (googlePlacesResults.value.length > 0) {
                                showGoogleMapAndList.value = true;
                            }
                        }
                    }
                } else if (source.id === 'tripadvisor') {
                    source.config.brandName = config.brand_name || '';
                    selectedTripadvisorUrl.value = config.brand_name;
                    source.config.countries = ['es']; // Always 'es' for TripAdvisor
                } else { // Trustpilot
                    source.config.brandName = config.brand_name || '';
                    selectedTrustpilotUrl.value = config.brand_name;
                    source.config.countries = config.countries || [];
                }
                 if (config.number_of_reviews && (source.id === 'trustpilot' || source.id === 'mybusiness')) {
                    numberOfReviewsSelectable.value = config.number_of_reviews;
                }
            }
        });
    }
}

async function loadSourceConfigs() {
  isLoading.value = true; // Ensure loading state is true at start
  try {
    const response = await apiClient.get('/sources/config');
    const configs: BackendSourceConfig[] = response.data;
    if (configs && configs.length > 0) {
      const selectableConfig = configs.find(c => c.source_type === 'trustpilot' || c.source_type === 'mybusiness' || c.source_type === 'products');
      if (selectableConfig) {
        if ((selectableConfig.source_type === 'trustpilot' || selectableConfig.source_type === 'mybusiness') && selectableConfig.number_of_reviews) {
          numberOfReviewsSelectable.value = selectableConfig.number_of_reviews;
        }
      }
      configs.forEach(config => {
        let originalSourceType = config.source_type;
        let sourceTypeId = originalSourceType;
        if (sourceTypeId === 'amazon' || sourceTypeId === 'druni') {
            sourceTypeId = 'products';
        }
        const source = sources.value.find(s => s.id === sourceTypeId);

        if (source) {
            if (source.id === 'products') {
                if (originalSourceType === 'amazon') source.enabled_amazon = true;
                if (originalSourceType === 'druni') source.enabled_druni = true;
            } else {
                source.enabled = true;
            }
          
            if (source.id === 'products') {
            // This part is now handled by loadSavedProducts() to get full object data
            // We just enable it if a config exists. The actual items are loaded separately.
            source.config.countries = config.countries || [];
          } else if (source.id === 'mybusiness') {
            source.config.brandName = config.brand_name || '';
            source.config.countries = config.countries || [];
            if (config.google_config) {
              source.config.selectedProvinces = config.google_config.selected_provinces || [];
            }
          } else if (source.id === 'tripadvisor') {
            source.config.brandName = config.brand_name || '';
            source.config.countries = ['es']; // Always 'es' for TripAdvisor
          } else { // Trustpilot
            source.config.brandName = config.brand_name || '';
            source.config.countries = config.countries || [];
          }
        }
      });
      
      // After loading configs, check if we need to populate the GMB results list
      const gmbSource = sources.value.find(s => s.id === 'mybusiness');
      const gmbConfig = configs.find(c => c.source_type === 'mybusiness');
      if (gmbSource && gmbSource.enabled && gmbConfig && gmbConfig.google_config && gmbConfig.google_config.places) {
        googlePlacesResults.value = gmbConfig.google_config.places.map(p => ({ ...p, origin: 'main_search' }));
        if (googlePlacesResults.value.length > 0) {
          showGoogleMapAndList.value = true;
        }
      }
    }
  } catch (error) {
    console.error("Error loading source configs:", error);
    // Optionally, show a toast error to the user
    toast.error("Failed to load source configurations.");
  } finally {
  isLoading.value = false;
  }
}

const loadSavedProducts = async () => {
  try {
    const response = await apiClient.get('/products/discovered-items');
    if (response.data && Array.isArray(response.data)) {
      const productsSourceRef = sources.value.find(s => s.id === 'products');
      if (productsSourceRef) {
        // The items from DB are full product objects
        productsSourceRef.config.productItems = response.data;
      }
    }
  } catch (error) {
    console.error("Error loading saved products:", error);
    toast.error("Failed to load your saved product list.");
  }
};

const searchGooglePlaces = async () => {
  const googleSource = sources.value.find(s => s.id === 'mybusiness');
  if (!googleSource || !canSearchGooglePlaces.value || reportAndScrapeStore.isDiscoveringGooglePlaces) {
    return;
  }

  // Clear previous non-manual search results before starting a new one
  googlePlacesResults.value = googlePlacesResults.value.filter(p => p.origin === 'manual');
  reportAndScrapeStore.clearGooglePlacesDiscoveryState();

  try {
    if (!googleMapsApiKey.value) {
      reportAndScrapeStore.googlePlacesDiscoveryError = "Google Maps API key is not configured.";
      return;
    }
    const payload = {
      brand_name_or_query: googleSource.config.brandName!,
      countries: googleSource.config.countries,
      selected_provinces: googleSource.config.countries.includes('es') && googleSource.config.selectedProvinces
        ? (googleSource.config.selectedProvinces.includes('__ALL__') ? [] : googleSource.config.selectedProvinces)
        : []
    };
    
    // This will be a new action in the store
    await reportAndScrapeStore.initiateGooglePlacesDiscovery(payload);
    // The component will now react to store state changes (isDiscovering, error, results)
    
  } catch (error: any) {
    console.error('[DEBUG] Error calling initiateGooglePlacesDiscovery from component:', error);
    reportAndScrapeStore.googlePlacesDiscoveryError = error.message || 'An unexpected error occurred when starting the search.';
  }
};

const removeGooglePlace = (placeId: string) => {
  googlePlacesResults.value = googlePlacesResults.value.filter(p => p.google_id !== placeId);
  if (googlePlacesResults.value.length === 0) {
    showGoogleMapAndList.value = false;
  }
};

let debounceTimer: number;
const debounce = (func: Function, delay: number) => {
  return (...args: any[]) => {
    clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      func.apply(null, args);
    }, delay);
  };
};

const fetchSpecificPlaceSuggestions = async () => {
  if (!additionalPlaceQuery.value.trim()) {
    specificPlaceSuggestions.value = [];
    specificPlaceSuggestionsError.value = null;
    return;
  }
  const googleSource = sources.value.find(s => s.id === 'mybusiness');
  if (!googleSource || !googleSource.enabled) {
    specificPlaceSuggestionsError.value = "Google My Business source must be enabled to search specific places.";
    specificPlaceSuggestions.value = [];
    return;
  }
  isLoadingSpecificPlaceSuggestions.value = true;
  specificPlaceSuggestionsError.value = null;
  specificPlaceSuggestions.value = [];
  try {
    if (!googleMapsApiKey.value) {
      specificPlaceSuggestionsError.value = "Google Maps API key configuration might be needed for suggestions.";
      // Don't return, still attempt the call as backend might not need it for text search.
    }
    const payload = {
      brand_name_or_query: additionalPlaceQuery.value,
      countries: googleSource.config.countries.length > 0 ? googleSource.config.countries : [], // Pass GMB countries if set
      selected_provinces: (googleSource.config.countries.includes('es') && googleSource.config.selectedProvinces)
        ? (googleSource.config.selectedProvinces.includes('__ALL__') ? [] : googleSource.config.selectedProvinces)
        : []
    };
    
    // Call store action to get suggestions
    const suggestions = await reportAndScrapeStore.fetchGooglePlaceSuggestions(payload);

    if (suggestions) {
      specificPlaceSuggestions.value = suggestions.slice(0, 5); // Limit to 5 suggestions
      if (specificPlaceSuggestions.value.length === 0) {
        specificPlaceSuggestionsError.value = "No suggestions found for your query.";
      }
    } else {
      specificPlaceSuggestionsError.value = reportAndScrapeStore.googlePlacesDiscoveryError || "Received unexpected data format for suggestions.";
    }

  } catch (error: any) {
    console.error('Error fetching specific place suggestions:', error);
    specificPlaceSuggestionsError.value = error.response?.data?.detail || 'Error fetching suggestions.';
  } finally {
    isLoadingSpecificPlaceSuggestions.value = false;
  }
};

const debouncedFetchSpecificPlaceSuggestions = debounce(fetchSpecificPlaceSuggestions, 500);

watch(additionalPlaceQuery, (newQuery) => {
  if (newQuery.trim()) {
    debouncedFetchSpecificPlaceSuggestions();
  } else {
    specificPlaceSuggestions.value = [];
    selectedSpecificPlaces.value = []; // Clear selections if query is cleared
    specificPlaceSuggestionsError.value = null;
  }
});

const toggleSpecificPlaceSelection = (place: any) => {
  const index = selectedSpecificPlaces.value.findIndex(p => p.google_id === place.google_id);
  if (index > -1) {
    selectedSpecificPlaces.value.splice(index, 1);
  } else {
    selectedSpecificPlaces.value.push(place);
  }
};

const isSpecificPlaceSelected = (place: any) => {
  return selectedSpecificPlaces.value.some(p => p.google_id === place.google_id);
};

const addSelectedSpecificPlacesToMainList = () => {
  if (selectedSpecificPlaces.value.length === 0) {
    addSelectedSpecificPlacesError.value = "No places selected from the suggestions.";
    return;
  }
  isAddingSelectedSpecificPlaces.value = true;
  addSelectedSpecificPlacesError.value = null;
  let addedCount = 0;
  selectedSpecificPlaces.value.forEach(newPlace => {
    if (newPlace && newPlace.google_id && !googlePlacesResults.value.some(existing => existing.google_id === newPlace.google_id)) {
      newPlace.origin = 'manual'; // Mark as manually added
      googlePlacesResults.value.push(newPlace);
      addedCount++;
    }
  });

  if (addedCount > 0) {
    showGoogleMapAndList.value = true; // Ensure map/list is visible if new places added
    toast.success(`${addedCount} place(s) added to your list.`);
  } else if (selectedSpecificPlaces.value.length > 0 && addedCount === 0) {
    addSelectedSpecificPlacesError.value = "Selected places are already in your main list.";
    toast.info("Selected places are already in your list.");
  }
  
  // Clear the search and selection states
  additionalPlaceQuery.value = '';
  specificPlaceSuggestions.value = [];
  selectedSpecificPlaces.value = [];
  specificPlaceSuggestionsError.value = null;
  isAddingSelectedSpecificPlaces.value = false;
};


const handleClickOutsideSuggestions = (event: MouseEvent) => {
  if (specificPlaceSearchContainer.value && !specificPlaceSearchContainer.value.contains(event.target as Node)) {
    specificPlaceSuggestions.value = []; // Hide suggestions
  }
};

// Manage event listener for clicking outside suggestions
watch(specificPlaceSuggestions, (newValue) => {
  if (newValue.length > 0 || isLoadingSpecificPlaceSuggestions.value || specificPlaceSuggestionsError.value) {
    nextTick(() => { // Ensure container is rendered before adding listener
      document.addEventListener('click', handleClickOutsideSuggestions, true);
    });
  } else {
    document.removeEventListener('click', handleClickOutsideSuggestions, true);
  }
}, { deep: true });


const saveAndGather = async () => {
  if (!canSaveAndGather.value) return;

  const enabledSourcesData = sources.value
    .filter(source => source.enabled && isSourceConfigured(source))
    .flatMap(sourceElement => {
      const generatedSources: any[] = [];

      if (sourceElement.id === 'products') {
        const productConfig = sourceElement.config as { 
          productItems: ProductScrapeItem[]; 
          countries: string[];
        };

        const druniItems = productConfig.productItems.filter(item => item.scrapeTargets?.druni);
        if (druniItems.length > 0 && sourceElement.enabled_druni) {
          const druniIdentifiers = druniItems.map(item => item.title || item.identifier).filter(Boolean);
          generatedSources.push({
            source_type: 'druni',
            brand_name: [...new Set(druniIdentifiers)].join('%%-%%'),
            number_of_reviews: FIXED_REVIEWS,
            countries: productConfig.countries,
          });
        }
        
        const amazonItems = productConfig.productItems.filter(item => item.scrapeTargets?.amazon);
        if (amazonItems.length > 0 && sourceElement.enabled_amazon) {
          const amazonIdentifiers = amazonItems.map(item => item.url || item.identifier).filter(Boolean);
          generatedSources.push({
            source_type: 'amazon',
            brand_name: [...new Set(amazonIdentifiers)].join('%%-%%'),
            number_of_reviews: FIXED_REVIEWS,
            countries: productConfig.countries,
          });
        }

      } else {
        let brandNameToSend: string | undefined;
        let countriesToSend: string[] = sourceElement.config.countries;
        let googleConfigToSend: any = undefined;

        if (sourceElement.id === 'tripadvisor') {
          brandNameToSend = selectedTripadvisorUrl.value || sourceElement.config.brandName;
          countriesToSend = ['es'];
        } else if (sourceElement.id === 'mybusiness') {
          const validGooglePlaces = googlePlacesResults.value.filter(p => p.google_id);
          if (validGooglePlaces.length > 0) {
            brandNameToSend = validGooglePlaces.map(place => place.google_id).join(',');
            countriesToSend = [];
            googleConfigToSend = {
              places: validGooglePlaces.map(p => ({
                google_id: p.google_id, name: p.name, full_address: p.full_address,
                latitude: p.latitude, longitude: p.longitude, category: p.category,
              }))
            };
          } else {
            brandNameToSend = sourceElement.config.brandName!;
            if (sourceElement.config.countries.includes('es')) {
              googleConfigToSend = { 
                selected_provinces: sourceElement.config.selectedProvinces?.includes('__ALL__') 
                                      ? [] 
                                      : sourceElement.config.selectedProvinces || [] 
              };
            }
          }
        } else { // For Trustpilot
          brandNameToSend = selectedTrustpilotUrl.value || sourceElement.config.brandName;
        }
        
        const data: any = {
          source_type: sourceElement.id,
          brand_name: brandNameToSend,
          countries: countriesToSend,
          number_of_reviews: (sourceElement.id === 'tripadvisor' || sourceElement.id === 'products')
            ? FIXED_REVIEWS
            : numberOfReviewsSelectable.value,
        };

        if (sourceElement.id === 'mybusiness' && googleConfigToSend) {
          data.google_config = googleConfigToSend;
        }
        generatedSources.push(data);
      }
      
      return generatedSources;
    });

  // If we are in source container mode, save and scrape
  if (isSourceContainerMode.value && props.sourceContainerId) {
    reportAndScrapeStore.isScrapingFocusedJob = true;
    reportAndScrapeStore.focusedScrapingProgressMessage = 'Saving configuration...';

    const configSaved = await saveSourceContainerConfiguration(enabledSourcesData);

    if (configSaved) {
      reportAndScrapeStore.focusedScrapingProgressMessage = 'Configuration saved. Starting scrape...';
      let scrapeResponse;
      try {
        scrapeResponse = await apiClient.post(`/source-containers/${props.sourceContainerId}/scrape`);
      } catch (error: any) {
        toast.error(error.response?.data?.detail || "Failed to start container scraping.");
        reportAndScrapeStore.isScrapingFocusedJob = false;
        return;
      }

      toast.success(scrapeResponse.data.message || "Container scraping started.");

      if (scrapeResponse.data.job_id) {
        try {
          reportAndScrapeStore._addSubscription(scrapeResponse.data.job_id, 'job');
        } catch (storeError: any) {
          console.error("Error setting active scraping job in store:", storeError);
          toast.warning("Scraping started, but failed to connect to live updates.");
        }
      }
    } else {
      reportAndScrapeStore.isScrapingFocusedJob = false;
    }
    return;
  }

  // If we are in competitor mode, we save the configuration first, then scrape
  if (isCompetitorMode.value && props.competitorId) {
    reportAndScrapeStore.isScrapingFocusedJob = true; // Show loading state on button
    reportAndScrapeStore.focusedScrapingProgressMessage = 'Saving configuration...';
    
    const configSaved = await saveCompetitorConfiguration(enabledSourcesData);
    
    if (configSaved) {
        reportAndScrapeStore.focusedScrapingProgressMessage = 'Configuration saved. Starting scrape...';
        
        let scrapeResponse;
        try {
            scrapeResponse = await apiClient.post(`/competitors/${props.competitorId}/scrape`);
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to start competitor scraping.");
            reportAndScrapeStore.isScrapingFocusedJob = false;
            return; // Stop if the API call itself fails
        }

        // --- Handle successful API response ---
        toast.success(scrapeResponse.data.message || "Competitor scraping started.");

        if (scrapeResponse.data.job_id) {
            try {
                // This logic is now in its own try-catch block
                reportAndScrapeStore._addSubscription(scrapeResponse.data.job_id, 'job');
            } catch (storeError: any) {
                console.error("Error setting active scraping job in store:", storeError);
                toast.warning("Scraping started, but failed to connect to live updates. Check console for details.");
            }
        }
    } else {
        // saveCompetitorConfiguration shows its own error toast
        reportAndScrapeStore.isScrapingFocusedJob = false;
    }
    return;
  }
  
  // --- THIS IS THE ORIGINAL LOGIC for the user's own brand ---
  try {
    if (enabledSourcesData.length === 0) {
      toast.warning("No scrape jobs to run. Please enable a source or select a scrape target for a product.");
      return;
    }
    const jobId = await reportAndScrapeStore.initiateScrapingProcess(enabledSourcesData);
    if (jobId) {
      toast.success(`Scraping process started. Job ID: ${jobId.substring(0,8)}. You will receive notifications.`);
    }
  } catch (error) {
    console.error("Error in saveAndGather calling store action:", error);
    toast.error('A critical error occurred trying to start the scraping process.');
  }
};

const handleMapClick = async (event: any) => {
  if (!event.latLng) {
    console.warn("Map click event missing latLng.");
    return;
  }
  const lat = event.latLng.lat();
  const lng = event.latLng.lng();
  mapClickError.value = null;
  isFetchingPlaceFromMapClick.value = true;
  try {
    const response = await apiClient.post('/maps/reverse-geocode', { latitude: lat, longitude: lng });
    const placeFromMap = response.data;
    if (placeFromMap) placeFromMap.origin = 'manual';
    if (placeFromMap && placeFromMap.google_id) {
      const confirmAdd = confirm(`Add "${placeFromMap.name}" to the list?`);
      if (confirmAdd) {
        if (!googlePlacesResults.value.some(existing => existing.google_id === placeFromMap.google_id)) {
          googlePlacesResults.value.push(placeFromMap);
          showGoogleMapAndList.value = true;
        } else {
          mapClickError.value = `"${placeFromMap.name}" is already in the list.`;
        }
      }
    } else {
      mapClickError.value = "Could not identify a specific place for the clicked location.";
    }
  } catch (error: any) {
    console.error('Error fetching place details from map click:', error);
    mapClickError.value = error.response?.data?.detail || "Error identifying place from map click.";
  } finally {
    isFetchingPlaceFromMapClick.value = false;
  }
};


watch(() => reportAndScrapeStore.notification, (newNotification) => {
  if (newNotification) {
    toast[newNotification.type](newNotification.message);
    reportAndScrapeStore.clearNotification();
  }
}, { deep: true });

watch(() => reportAndScrapeStore.focusedScrapingProgressMessage, (newMessage) => {
  if (newMessage && reportAndScrapeStore.isScrapingFocusedJob && reportAndScrapeStore.activeScrapingJobId) {
    // console.log('[ConnectSources] Scraping Progress Update:', newMessage);
  }
});

watch(() => reportAndScrapeStore.focusedReportProgressMessage, (newMessage) => {
  if (newMessage && reportAndScrapeStore.isGeneratingFocusedReport) {
    // console.log('[ConnectSources] Report Progress Update:', newMessage);
  }
});

watch(() => reportAndScrapeStore.amazonDiscoveryCompletedTaskId, (completedId) => {
  if (completedId && completedId === activeAmazonDiscoveryTaskId.value) {
    discoveredAmazonProducts.value = reportAndScrapeStore.amazonDiscoveredProducts;
    brightDataDiscoveryStatusMessage.value = `Successfully fetched ${discoveredAmazonProducts.value.length} products.`;
    toast.success(`Found ${discoveredAmazonProducts.value.length} Amazon products.`);
    if (discoveredAmazonProducts.value.length === 0) {
      brightDataDiscoveryStatusMessage.value += " No products were found matching the criteria.";
    }
    // Do not clear state here, let the user see the results
  }
});

watch(() => reportAndScrapeStore.amazonDiscoveryErrorTaskId, (errorId) => {
  if (errorId && errorId === activeAmazonDiscoveryTaskId.value) {
    brightDataDiscoveryError.value = reportAndScrapeStore.amazonDiscoveryError || 'An unknown error occurred during Amazon product discovery.';
    toast.error(brightDataDiscoveryError.value);
  }
});

watch(() => reportAndScrapeStore.amazonDiscoveryStatusMessage, (newMessage) => {
  if (newMessage) {
    brightDataDiscoveryStatusMessage.value = newMessage;
  }
});

onUnmounted(() => {
  if (reportAndScrapeStore.activeScrapingJobId) {
    // reportAndScrapeStore.unsubscribeFromActivity(reportAndScrapeStore.activeScrapingJobId, 'job');
     reportAndScrapeStore._removeSubscription(reportAndScrapeStore.activeScrapingJobId, 'job'); // Use _removeSubscription
  }
  document.removeEventListener('click', handleClickOutsideSuggestions, true);
  if (activeAmazonDiscoveryTaskId.value) {
    // reportAndScrapeStore.unsubscribeFromActivity(brightDataSnapshotId.value, 'discovery');
    reportAndScrapeStore._removeSubscription(activeAmazonDiscoveryTaskId.value, 'discovery'); // Use _removeSubscription
  }
  if (reportAndScrapeStore.activeManualLookupSnapshotId) {
    reportAndScrapeStore._removeSubscription(reportAndScrapeStore.activeManualLookupSnapshotId, 'manual_lookup');
  }
  reportAndScrapeStore.clearManualLookupStates(); // Clean up on leaving the page
});

const toggleScrapeTarget = (product: any, target: 'amazon' | 'druni') => {
  if (!product.scrapeTargets) {
    // If scrapeTargets doesn't exist, create it.
    // In Vue 3, this is reactive if `product` is.
    product.scrapeTargets = { amazon: false, druni: false };
  }
  // Toggle the value
  product.scrapeTargets[target] = !product.scrapeTargets[target];
};

const checkIfBrandInternal = (textValue: string): boolean => {
  const query = textValue?.trim() || '';
  if (!query) return false;
  // Does it look like an ASIN? (B0 followed by 8 alphanumeric chars)
  if (/\bB0[A-Z0-9]{8}\b/i.test(query)) {
    return false; // ASINs are not brand queries
  }
  // Does it look like a URL?
  if (query.includes('/') || query.includes('www.') || query.match(/\.[a-z]{2,}(\/|$)/i)) {
    return false; // URLs are not brand queries
  }
  // Basic length check for a "brand name"
  if (query.length < 2 || query.length > 70) {
    return false;
  }
  // If none of the above, assume it might be a brand name.
  return true;
};

watch(
  () => currentSourceForDisplay.value?.id === 'products' ? currentSourceForDisplay.value?.config.productItems : null,
  (newItemsArray) => { // newItemsArray is ProductScrapeItem[] | null
    if (currentSourceForDisplay.value && currentSourceForDisplay.value.id === 'products') {
      const config = currentSourceForDisplay.value.config as any; // Cast to any for dynamic property access
      if (newItemsArray && newItemsArray.length === 1) {
        // Only check if it's a brand query if there's exactly one item.
        // If multiple items, it's treated as a list of specific products.
        config.isBrandQuery = checkIfBrandInternal(newItemsArray[0].identifier);
      } else {
        config.isBrandQuery = false; // Not a brand query if 0 or >1 items
      }
    }
  },
  { deep: true } // Deep watch to detect changes within the productItems array
);

const addProductIdentifiers = (productConfig: any) => { // productConfig is Source['config'] for products
  if (!productConfig || !productConfig.inputQuery?.trim()) return;
  const newEntries = productConfig.inputQuery
    .split(/[\n,]+/) // Split by newline or comma
    .map((entry: string) => entry.trim())
    .filter((entry: string) => entry.length > 0); // Remove empty entries

  if (!productConfig.productItems) {
    productConfig.productItems = [] as ProductScrapeItem[];
  }

  newEntries.forEach((entry: string) => {
    if (!productConfig.productItems.some((item: ProductScrapeItem) => item.identifier === entry)) {
      productConfig.productItems.push({
        identifier: entry,
        scrapeTargets: { amazon: true, druni: false } // Default: Amazon true, Druni false
      });
    }
  });
  productConfig.inputQuery = '';
};

const removeProductIdentifier = async (productConfig: any, index: number) => { // productConfig is Source['config'] for products
  if (productConfig && productConfig.productItems && productConfig.productItems.length > index) {
    const itemToRemove = productConfig.productItems[index];
    const identifier = itemToRemove.identifier;

    try {
      // Axios delete method signature: axios.delete(url, { data: { foo: 'bar' } })
      await apiClient.delete('/products/discovered-item', { data: { identifier: identifier } });
      
      // On success, remove from local list
      productConfig.productItems.splice(index, 1);
      toast.success(`Item removed from your list and the database.`);
    } catch(error: any) {
      console.error("Error removing product from database:", error);
      toast.error(error.response?.data?.detail || "Failed to remove product from the database.");
    }
  }
};

const amazonBrandNameForBrightData = ref('');
const amazonCountryForBrightData = ref(''); // Default to empty
const isDiscoveringAmazonProducts = computed(() => reportAndScrapeStore.isDiscoveringAmazonProducts);
const isLoadingDiscoveredAmazonProducts = computed(() => reportAndScrapeStore.isLoadingDiscoveredAmazonProducts);
const brightDataDiscoveryError = ref<string | null>(null);
const activeAmazonDiscoveryTaskId = ref<string | null>(null);
const discoveredAmazonProducts = ref<any[]>([]);
const brightDataDiscoveryStatusMessage = ref<string | null>(null);

// ++ NEW ++
const amazonDiscoverySearchQuery = ref('');
const isAddingAllProducts = ref(false);

const filteredDiscoveredAmazonProducts = computed(() => {
  if (!amazonDiscoverySearchQuery.value.trim()) {
    return discoveredAmazonProducts.value;
  }
  const query = amazonDiscoverySearchQuery.value.trim().toLowerCase();
  return discoveredAmazonProducts.value.filter(product => {
    const title = (product.title || '').toLowerCase();
    const asin = (product.asin || '').toLowerCase();
    const brand = (product.brand || '').toLowerCase();
    
    // Debug logging to see what we're filtering
    console.log('Filtering product:', { 
      title: product.title, 
      asin: product.asin, 
      brand: product.brand, 
      query,
      titleMatch: title.includes(query),
      asinMatch: asin.includes(query),
      brandMatch: brand.includes(query)
    });
    
    return title.includes(query) || asin.includes(query) || brand.includes(query);
  });
});

// Add a watcher to debug the search
watch(amazonDiscoverySearchQuery, (newQuery) => {
  console.log('Search query changed:', newQuery);
  console.log('Total products:', discoveredAmazonProducts.value.length);
  console.log('Filtered products:', filteredDiscoveredAmazonProducts.value.length);
}, { immediate: true });

const amazonDiscoveryCountries = computed(() => {
  const supportedCountryCodes = ['US', 'DE', 'ES', 'GB', 'FR', 'IT', 'CA', 'MX', 'AU', 'JP', 'IN', 'CN', 'BR', 'NL'];
  if (!allCountries.value || allCountries.value.length === 0) {
    // Fallback in case allCountries is not populated for some reason
    return supportedCountryCodes.map(code => ({ id: code.toLowerCase(), name: code, flag: `fi fi-${code.toLowerCase()}` }));
  }
  return allCountries.value.filter(c => supportedCountryCodes.includes(c.id.toUpperCase()));
});

const triggerAmazonProductDiscovery = async () => {
  if (!amazonBrandNameForBrightData.value.trim()) {
    brightDataDiscoveryError.value = "Please enter a brand name for Amazon discovery.";
    return;
  }
  if (!amazonCountryForBrightData.value) {
    brightDataDiscoveryError.value = "Please select a country for Amazon discovery.";
    return;
  }
  discoveredAmazonProducts.value = [];
  amazonDiscoverySearchQuery.value = ''; // Reset search query on new discovery
  activeAmazonDiscoveryTaskId.value = null;
  brightDataDiscoveryError.value = null;
  brightDataDiscoveryStatusMessage.value = `Initiating Amazon product discovery for "${amazonBrandNameForBrightData.value}"...`;

  try {
    const newTaskId = await reportAndScrapeStore.initiateAmazonProductDiscovery(amazonBrandNameForBrightData.value, amazonCountryForBrightData.value);
    if (newTaskId) {
      activeAmazonDiscoveryTaskId.value = newTaskId;
      toast.info(`Amazon product discovery initiated for '${amazonBrandNameForBrightData.value}' in ${amazonCountryForBrightData.value}. You'll be notified.`);
    } else {
      brightDataDiscoveryError.value = reportAndScrapeStore.amazonDiscoveryError || "Failed to start Amazon product discovery.";
      toast.error(brightDataDiscoveryError.value);
    }
  } catch(error: any) {
    console.error("Error triggering Amazon product discovery via component:", error);
    brightDataDiscoveryError.value = error.response?.data?.detail || "An error occurred in component trying to start Amazon product discovery.";
    toast.error(brightDataDiscoveryError.value);
    // Ensure loading state is reset in the store on catch
    reportAndScrapeStore.isDiscoveringAmazonProducts = false;
  }
};

const fetchDiscoveredAmazonProducts = async (snapshotId: string) => {
  if (!snapshotId) return;
  isLoadingDiscoveredAmazonProducts.value = true;
  brightDataDiscoveryError.value = null;
  try {
    brightDataDiscoveryStatusMessage.value = `Fetching results for snapshot ID: ${snapshotId.substring(0, 8)}...`;
    const response = await apiClient.get(`/amazon/brightdata/products/${snapshotId}`); // Ensure /api/ prefix
    if (response.data && response.data.products && Array.isArray(response.data.products)) {
      discoveredAmazonProducts.value = response.data.products.map((product: any) => ({
        ...product,
        title: product.name || product.title, // Use `name` field as primary, fallback to `title`
        scrapeTargets: { amazon: true, druni: false } // Default targets
      }));
      brightDataDiscoveryStatusMessage.value = `Successfully fetched ${response.data.products.length} products for snapshot ${snapshotId.substring(0, 8)}.`;
      toast.success(`Found ${response.data.products.length} Amazon products.`);
      if (response.data.products.length === 0) {
        brightDataDiscoveryStatusMessage.value += " No products were found matching the criteria.";
      }
    } else {
      discoveredAmazonProducts.value = []; 
      brightDataDiscoveryError.value = response.data?.message || "Failed to fetch discovered Amazon products or data is not an array.";
      toast.error(brightDataDiscoveryError.value);
    }
  } catch (error: any) {
    discoveredAmazonProducts.value = []; 
    console.error("Error fetching discovered Amazon products:", error);
    brightDataDiscoveryError.value = error.response?.data?.detail || "An error occurred while fetching discovered Amazon products.";
    toast.error(brightDataDiscoveryError.value);
  } finally {
    isLoadingDiscoveredAmazonProducts.value = false;
    if (reportAndScrapeStore.amazonDiscoveryResultsReadySnapshotId === snapshotId || reportAndScrapeStore.amazonDiscoveryErrorSnapshotId === snapshotId) {
      reportAndScrapeStore.clearAmazonDiscoveryStates(); // Clear store states after processing
    }
  }
};

const addAllVisibleDiscoveredProducts = async (target: 'amazon' | 'druni') => {
  const productsToAdd = filteredDiscoveredAmazonProducts.value;
  if (productsToAdd.length === 0 || isAddingAllProducts.value) {
    return;
  }
  
  const productConfig = currentSourceForDisplay.value?.config;
  if (!productConfig || !('productItems' in productConfig)) {
    toast.error("Cannot find product configuration.");
    return;
  }

  isAddingAllProducts.value = true;
  toast.info(`Adding ${productsToAdd.length} products for '${target}'. This may take a moment...`);

  // Auto-select the discovery country for scraping
  const discoveryCountry = amazonCountryForBrightData.value;
  if (discoveryCountry && productConfig.countries && !productConfig.countries.includes(discoveryCountry)) {
    productConfig.countries.push(discoveryCountry);
    toast.info(`Country '${discoveryCountry.toUpperCase()}' was automatically added to your scrape list.`);
  }

  let addedCount = 0;
  let updatedCount = 0;
  let errorCount = 0;

  for (const product of productsToAdd) {
    const primaryIdentifier = product.asin || product.url || product.title;
    if (!primaryIdentifier) continue;
    
    // When adding all for a specific target, only that target should be true.
    const scrapeTargetsForCall = {
        amazon: target === 'amazon',
        druni: target === 'druni'
    };

    const payloadForBackend = { 
        ...product, 
        identifier: primaryIdentifier,
        scrapeTargets: scrapeTargetsForCall
    };

    try {
      await apiClient.post('/products/discovered-item', payloadForBackend);
      
      const existingItemIndex = productConfig.productItems.findIndex((item: ProductScrapeItem) => item.identifier === primaryIdentifier);
      
      if (existingItemIndex !== -1) {
        // Item exists, update its target
        const existingItem = productConfig.productItems[existingItemIndex];
        let wasUpdatedInThisIteration = false;
        if (target === 'amazon' && !existingItem.scrapeTargets.amazon) {
            existingItem.scrapeTargets.amazon = true;
            wasUpdatedInThisIteration = true;
        }
        if (target === 'druni' && !existingItem.scrapeTargets.druni) {
            existingItem.scrapeTargets.druni = true;
            wasUpdatedInThisIteration = true;
        }
        if(wasUpdatedInThisIteration) updatedCount++;

      } else {
        // Item doesn't exist, add it
        productConfig.productItems.push({
          identifier: primaryIdentifier,
          url: product.url,
          title: product.title,
          scrapeTargets: scrapeTargetsForCall
        });
        addedCount++;
      }
    } catch (error) {
      console.error(`Failed to add product ${primaryIdentifier}:`, error);
      errorCount++;
    }
  }

  if (addedCount > 0) {
    toast.success(`${addedCount} new products were added to your list.`);
  }
  if (updatedCount > 0) {
    toast.info(`${updatedCount} existing products were updated with the '${target}' scrape target.`);
  }
  if (errorCount > 0) {
    toast.error(`${errorCount} products could not be added due to an error.`);
  }
  if (addedCount === 0 && updatedCount === 0 && errorCount === 0) {
      toast.info("All products were already in your list with the target enabled.");
  }
  isAddingAllProducts.value = false;
  
  // REMOVE THESE LINES to keep products visible after adding:
  // discoveredAmazonProducts.value = [];
  // amazonDiscoverySearchQuery.value = '';
};

// This is the SINGLE, CORRECT definition of addDiscoveredProductToItems
const addDiscoveredProductToItems = async (product: any, productConfig: any) => { 
  if (!productConfig) return;
  if (!productConfig.productItems) {
    productConfig.productItems = [] as ProductScrapeItem[];
  }

  const primaryIdentifier = product.asin || product.url || product.title;
  if (!primaryIdentifier) {
    toast.warning("Discovered product has no usable identifier (ASIN, URL, or title).");
    return;
  }
  
  const itemForLocalList: ProductScrapeItem = {
      identifier: primaryIdentifier,
      url: product.url,
      title: product.title,
      scrapeTargets: { 
          amazon: product.scrapeTargets.amazon,
          druni: product.scrapeTargets.druni
      }
  };
  
  const payloadForBackend = { ...product, identifier: primaryIdentifier };

  try {
    await apiClient.post('/products/discovered-item', payloadForBackend);

    // Auto-select the discovery country for scraping
    const discoveryCountry = amazonCountryForBrightData.value;
    if (discoveryCountry && productConfig.countries && !productConfig.countries.includes(discoveryCountry)) {
      productConfig.countries.push(discoveryCountry);
      toast.info(`Country '${discoveryCountry.toUpperCase()}' was automatically added to your scrape list.`);
    }

    const existingItemIndex = productConfig.productItems.findIndex((item: ProductScrapeItem) => item.identifier === primaryIdentifier);

    if (existingItemIndex !== -1) {
      const existingItem = productConfig.productItems[existingItemIndex];
      let updated = false;
      if (itemForLocalList.scrapeTargets.amazon && !existingItem.scrapeTargets.amazon) {
          existingItem.scrapeTargets.amazon = true;
          updated = true;
      }
      if (itemForLocalList.scrapeTargets.druni && !existingItem.scrapeTargets.druni) {
          existingItem.scrapeTargets.druni = true;
          updated = true;
      }
      if (updated) {
          toast.info(`Updated targets for "${primaryIdentifier.substring(0, 30)}${primaryIdentifier.length > 30 ? '...' : ''}" in your list.`);
      } else {
          toast.info(`"${primaryIdentifier.substring(0, 30)}${primaryIdentifier.length > 30 ? '...' : ''}" is already in your product list.`);
      }
    } else {
      if (itemForLocalList.scrapeTargets.amazon || itemForLocalList.scrapeTargets.druni) {
        productConfig.productItems.push(itemForLocalList);
        toast.success(`"${primaryIdentifier.substring(0, 30)}${primaryIdentifier.length > 30 ? '...' : ''}" added to your product list and saved to DB.`);
      } else {
        toast.warning("No scrape target selected. Product was saved to DB but not added to active scrape list.");
      }
    }
  } catch (error: any) {
    console.error("Error saving discovered product:", error);
    toast.error(error.response?.data?.detail || "Failed to save the product to the database.");
  }
};

// --- New state for Manual Product Lookup ---
const manualProductInputQuery = ref('');
const manuallyFetchedAmazonProducts = ref<any[]>([]);
const amazonCountryForManualLookup = ref('');

// Computed properties to reflect store state for manual lookup
const isFetchingManualProducts = computed(() => reportAndScrapeStore.isPerformingManualLookup);
const manualProductFetchError = computed(() => reportAndScrapeStore.manualLookupError);
const manualLookupStatusMessageDisplay = computed(() => reportAndScrapeStore.manualLookupStatusMessage);
const manualLookupResultsFromStore = computed(() => reportAndScrapeStore.manualLookupProducts);


watch(manualLookupResultsFromStore, (newProducts) => {
  if (newProducts && Array.isArray(newProducts)) {
    const newProductsWithDefaults = newProducts.map((product: any) => ({
      ...product,
      scrapeTargets: product.scrapeTargets || { amazon: true, druni: false } 
    }));
    
    const existingIdentifiers = new Set(manuallyFetchedAmazonProducts.value.map(p => p.asin || p.url).filter(Boolean));
    const uniqueNewProducts = newProductsWithDefaults.filter((p: any) => {
      const identifier = p.asin || p.url;
      return identifier && !existingIdentifiers.has(identifier);
    });

    if (uniqueNewProducts.length > 0) {
      manuallyFetchedAmazonProducts.value.push(...uniqueNewProducts);
    }
  }
}, { deep: true });

watch(() => reportAndScrapeStore.manualLookupErrorTaskId, (newTaskId) => {
  if (newTaskId && newTaskId === reportAndScrapeStore.activeManualLookupTaskId) {
    // We don't clear the list on error anymore, so a user can see what was previously found.
    // The main error message is already displayed via `manualLookupStatusMessageDisplay`.
    toast.error(reportAndScrapeStore.manualLookupLastErrorMessage || "An error occurred during manual lookup.");
  }
});

const fetchManuallyLookedUpProducts = async (snapshotId: string) => {
  if (!snapshotId) return;
  try {
    reportAndScrapeStore.manualLookupStatusMessage = `Fetching results for lookup ${snapshotId.substring(0,8)}...`;
    const response = await apiClient.get(`/products/manual-lookup/results/${snapshotId}`); // Corrected API Path
    if (response.data && Array.isArray(response.data.products)) {
      const newProducts = response.data.products.map((product: any) => ({
        ...product,
        scrapeTargets: product.scrapeTargets || { amazon: true, druni: false } 
      }));

      const existingIdentifiers = new Set(manuallyFetchedAmazonProducts.value.map(p => p.asin || p.url).filter(Boolean));
      const uniqueNewProducts = newProducts.filter((p: any) => {
        const identifier = p.asin || p.url;
        return identifier && !existingIdentifiers.has(identifier);
      });
      
      manuallyFetchedAmazonProducts.value.push(...uniqueNewProducts);

      if (response.data.products.length === 0 && response.data.status === 'completed_empty') {
         reportAndScrapeStore.manualLookupStatusMessage = `Lookup ${snapshotId.substring(0,8)} completed. No products found.`;
         toast.info(`No products found for your manual lookup.`);
      } else if (response.data.products.length > 0) {
        const addedCount = uniqueNewProducts.length;
        const totalFound = response.data.products.length;
        reportAndScrapeStore.manualLookupStatusMessage = `Successfully fetched ${totalFound} products. Added ${addedCount} new product(s) to the list.`;
        toast.success(`Found ${totalFound} product(s). Added ${addedCount} new one(s).`);
      }
    } else {
      const errorMsg = response.data?.detail || "Failed to fetch looked up products or data format is incorrect.";
      reportAndScrapeStore.manualLookupError = errorMsg; 
      reportAndScrapeStore.manualLookupLastErrorMessage = errorMsg;
      toast.error(errorMsg);
    }
  } catch (error: any) {
    console.error("Error fetching looked up Amazon products:", error);
    const errorMsg = error.response?.data?.detail || "An error occurred while fetching looked up products.";
    reportAndScrapeStore.manualLookupError = errorMsg; 
    reportAndScrapeStore.manualLookupLastErrorMessage = errorMsg;
    toast.error(errorMsg);
  } 
};

const getIdentifierType = (identifier: string): 'asin' | 'amazon_url' | 'druni_url' | 'search_term' => {
    const trimmedIdentifier = identifier.trim().toLowerCase();
    // Regex for ASIN: starts with B0, followed by 8 alphanumeric characters.
    if (/^b0[a-z0-9]{8}$/i.test(trimmedIdentifier)) return 'asin';
    if (trimmedIdentifier.includes('amazon.') || trimmedIdentifier.includes('amzn.to')) return 'amazon_url';
    if (trimmedIdentifier.includes('druni.')) return 'druni_url';
    return 'search_term';
};

const triggerManualProductLookup = () => {
  if (!manualProductInputQuery.value.trim()) {
    toast.warning("Please enter product names.");
    return;
  }
  if (!amazonCountryForManualLookup.value) {
    toast.warning("Please select a country for the look up.");
    return;
  }

  const identifiers = manualProductInputQuery.value
    .split(/\n+/) // Split only by newlines
    .map((entry: string) => entry.trim())
    .filter((entry: string) => entry.length > 0);

  if (identifiers.length === 0) {
    toast.warning("No valid product names provided.");
    return;
  }

  // Clear the input field for the next batch
  manualProductInputQuery.value = '';

  // Call the store action to trigger the backend lookup
  reportAndScrapeStore.initiateManualProductLookup(identifiers, amazonCountryForManualLookup.value);
};

const amazonDiscoveryInput = ref({ brand_name: '', country: '' });
const isDiscovering = ref(false);
const amazonDiscoveryError = ref(null);
const discoveredProducts = ref([]);
const sseListeners = new Map();

const availableCountries = (sourceId: string) => {
  if (sourceId === 'products') {
     return allCountries.value.filter(c => ['US', 'DE', 'ES', 'GB', 'FR', 'IT', 'CA', 'MX', 'AU', 'JP', 'IN', 'CN', 'BR', 'NL'].includes(c.id.toUpperCase()));
  }
  // Currently, the logic is the same for all sources using this function.
  // We can add source-specific logic here if needed in the future.
  return allCountries.value;
};

const triggerAmazonDiscovery = async () => {
  if (!amazonDiscoveryInput.value.brand_name || !amazonDiscoveryInput.value.country) {
    toast.error('Please enter a brand name and select a country for Amazon discovery.');
    return;
  }
  isDiscovering.value = true;
  amazonDiscoveryError.value = null;
  discoveredProducts.value = [];
  
  try {
    const response = await apiClient.post('/amazon/brightdata/discover-products', {
      brand_name: amazonDiscoveryInput.value.brand_name,
      country: amazonDiscoveryInput.value.country,
    });

    if (response.data && response.data.snapshot_id) {
      toast.info(`Amazon product discovery started for brand "${response.data.brand_name}". This may take a few minutes.`);
      // ... existing code ...
    }
  } catch (error: any) {
    console.error("Error triggering Amazon product discovery:", error);
    amazonDiscoveryError.value = error.response?.data?.detail || "An error occurred while triggering Amazon product discovery.";
    toast.error(amazonDiscoveryError.value);
    isDiscovering.value = false;
  }
};

const triggerTrustpilotUrlDiscovery = async () => {
  if (!trustpilotBrandNameForDiscovery.value.trim()) {
    reportAndScrapeStore.notification = { type: 'warning', message: 'Please enter a brand name for Trustpilot discovery.' };
    return;
  }
  if (!trustpilotCountryForDiscovery.value) {
    reportAndScrapeStore.notification = { type: 'warning', message: 'Please select a country for Trustpilot discovery.' };
    return;
  }
  
  // Reset previous results
  selectedTrustpilotUrl.value = null;

  // Call the store action
  await reportAndScrapeStore.initiateTrustpilotUrlDiscovery(
    trustpilotBrandNameForDiscovery.value,
    trustpilotCountryForDiscovery.value
  );
};

const trustpilotDiscoveryCountries = ref([
  { id: 'es', name: 'Spain', flag: 'fi fi-es' },
  { id: 'de', name: 'Germany', flag: 'fi fi-de' },
  { id: 'us', name: 'United States', flag: 'fi fi-us' },
  { id: 'gb', name: 'United Kingdom', flag: 'fi fi-gb' }
]);

const triggerTripadvisorUrlDiscovery = async () => {
  if (!tripadvisorBrandNameForDiscovery.value.trim()) {
    reportAndScrapeStore.notification = { type: 'warning', message: 'Please enter a brand name for TripAdvisor discovery.' };
    return;
  }
  if (!tripadvisorCountryForDiscovery.value) {
    reportAndScrapeStore.notification = { type: 'warning', message: 'Please select a country for TripAdvisor discovery.' };
    return;
  }
  
  // Reset previous results
  selectedTripadvisorUrl.value = null;

  // Call the store action
  await reportAndScrapeStore.initiateTripadvisorUrlDiscovery(
    tripadvisorBrandNameForDiscovery.value,
    tripadvisorCountryForDiscovery.value
  );
};

const tripadvisorDiscoveryCountries = ref([
  { id: 'es', name: 'Spain', flag: 'fi fi-es' },
  { id: 'de', name: 'Germany', flag: 'fi fi-de' },
  { id: 'us', name: 'United States', flag: 'fi fi-us' },
  { id: 'gb', name: 'United Kingdom', flag: 'fi fi-gb' }
]);

const googleMyBusinessCountry = computed({
  get() {
    const googleSource = sources.value.find(s => s.id === 'mybusiness');
    return googleSource?.config.countries[0] || '';
  },
  set(value) {
    const googleSource = sources.value.find(s => s.id === 'mybusiness');
    if (googleSource) {
      if (value) {
        googleSource.config.countries = [value];
        // if country changes, reset provinces if it's not spain
        if (value !== 'es') {
          googleSource.config.selectedProvinces = [];
        }
      } else {
        googleSource.config.countries = [];
        googleSource.config.selectedProvinces = [];
      }
    }
  }
});

const provinceToAdd = ref('');
watch(provinceToAdd, (newProvince) => {
    const gmbConfig = sources.value.find(s => s.id === 'mybusiness')?.config;
    if (newProvince && gmbConfig) {
        if (newProvince === '__ALL__') {
            gmbConfig.selectedProvinces = ['__ALL__'];
        } else {
            if (gmbConfig.selectedProvinces.includes(newProvince)) {
                // Province already selected, do nothing.
            } else {
                 // Remove '__ALL__' if a specific province is added
                const allIndex = gmbConfig.selectedProvinces.indexOf('__ALL__');
                if (allIndex > -1) {
                    gmbConfig.selectedProvinces.splice(allIndex, 1);
                }
                gmbConfig.selectedProvinces.push(newProvince);
            }
        }
         // Reset dropdown after selection
        nextTick(() => {
            provinceToAdd.value = '';
        });
    }
});

const removeProvince = (provinceToRemove: string) => {
    const gmbConfig = sources.value.find(s => s.id === 'mybusiness')?.config;
    if (gmbConfig) {
        const index = gmbConfig.selectedProvinces.indexOf(provinceToRemove);
        if (index > -1) {
            gmbConfig.selectedProvinces.splice(index, 1);
        }
    }
};

// --- Determine context ---
const isCompetitorMode = computed(() => !!props.competitorId);
const isSourceContainerMode = computed(() => !!props.sourceContainerId);

async function saveSourceContainerConfiguration(enabledSourcesData: BackendSourceConfig[]) {
  if (!isSourceContainerMode.value || !props.sourceContainerId) return false;

  const existingConfigs: BackendSourceConfig[] = props.initialSources || [];
  const existingSourceTypes = new Set(existingConfigs.map(c => c.source_type));
  const newSourceTypes = new Set(enabledSourcesData.map(c => c.source_type));

  const promises = [];

  // Add or update sources
  for (const config of enabledSourcesData) {
    if (existingSourceTypes.has(config.source_type)) {
      promises.push(apiClient.put(`/source-containers/${props.sourceContainerId}/sources/${config.source_type}`, config));
    } else {
      promises.push(apiClient.post(`/source-containers/${props.sourceContainerId}/sources`, config));
    }
  }

  // Delete sources that are no longer enabled
  for (const sourceType of existingSourceTypes) {
    if (!newSourceTypes.has(sourceType)) {
      promises.push(apiClient.delete(`/source-containers/${props.sourceContainerId}/sources/${sourceType}`));
    }
  }

  try {
    await Promise.all(promises);
    toast.success("Source container configuration saved successfully.");
    return true;
  } catch (error: any) {
    console.error("Failed to save source container configuration:", error);
    toast.error(error.response?.data?.detail || "An error occurred while saving the configuration.");
    return false;
  }
}

async function saveCompetitorConfiguration(enabledSourcesData: BackendSourceConfig[]) {
  if (!isCompetitorMode.value || !props.competitorId) return false;

  const existingConfigs: BackendSourceConfig[] = props.initialSources || [];
  const existingSourceTypes = new Set(existingConfigs.map(c => c.source_type));
  const newSourceTypes = new Set(enabledSourcesData.map(c => c.source_type));

  const promises = [];

  // Add or update sources
  for (const config of enabledSourcesData) {
    if (existingSourceTypes.has(config.source_type)) {
      // Update existing source
      promises.push(apiClient.put(`/competitors/${props.competitorId}/sources/${config.source_type}`, config));
    } else {
      // Add new source
      promises.push(apiClient.post(`/competitors/${props.competitorId}/sources`, config));
    }
  }

  // Delete sources that are no longer enabled
  for (const sourceType of existingSourceTypes) {
    if (!newSourceTypes.has(sourceType)) {
      promises.push(apiClient.delete(`/competitors/${props.competitorId}/sources/${sourceType}`));
    }
  }

  try {
    await Promise.all(promises);
    toast.success("Competitor configuration saved successfully.");
    return true;
  } catch (error: any) {
    console.error("Failed to save competitor configuration:", error);
    toast.error(error.response?.data?.detail || "An error occurred while saving competitor configuration.");
    return false;
  }
}

</script> // Ensure this closing script tag is present

<template>
  <div class="space-y-8 p-4 md:p-6 lg:p-8">

    <!-- Top Bar: Title and Global Actions -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
      <div class="flex items-center space-x-3">
        <h1 class="text-2xl md:text-3xl font-display font-bold text-text-primary">
          {{ isCompetitorMode ? 'Configure Competitor Sources' : (isSourceContainerMode ? 'Configure Source Container' : 'Connect My Sources') }}
        </h1>
        
        <!-- Competitor Box -->
        <div v-if="competitorToScrape" class="bg-amber-100 text-amber-800 text-sm font-medium px-3 py-1.5 rounded-full flex items-center shadow-sm border border-amber-200">
          <span>Competitor: <strong>{{ competitorToScrape }}</strong></span>
        </div>
        <!-- Source Container Box -->
        <div v-if="sourceContainerToConfigure" class="bg-teal-100 text-teal-800 text-sm font-medium px-3 py-1.5 rounded-full flex items-center shadow-sm border border-teal-200">
          <span>Container: <strong>{{ sourceContainerToConfigure }}</strong></span>
        </div>
      </div>
      <div class="group relative">
        <QuestionMarkCircleIcon class="h-6 w-6 text-text-secondary cursor-help" />
        <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-white rounded-xl shadow-lg border border-border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-20">
        <p class="text-sm text-text-secondary">
          Configure your review sources to automatically gather customer feedback from multiple platforms.
        </p>
        </div>
      </div>
    </div>

    <!-- Main Content: Selector on Right, Config on Left -->
    <div class="flex flex-col lg:flex-row gap-6 lg:gap-8">

      <!-- Configuration Area (Left Panel) -->
      <div class="flex-grow lg:order-1 lg:w-2/3 xl:w-3/4 space-y-6">
        
        <!-- Single Source Display (GMB, TripAdvisor, Trustpilot, Products) -->
        <template v-if="currentSourceForDisplay">
          <div class="bg-white rounded-2xl shadow-lg border border-border overflow-hidden transition-all duration-300 ease-in-out">
            <!-- SOURCE HEADER -->
            <div class="p-5 md:p-6 flex items-center justify-between bg-gray-50/50">
          <div class="flex items-center space-x-4">
                <div class="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-primary/10 flex items-center justify-center shadow-sm">
                  <img v-if="currentSourceForDisplay.id !== 'products' && currentSourceForDisplay.logo" :src="currentSourceForDisplay.logo" :alt="currentSourceForDisplay.name" class="p-1 w-full h-full object-contain" />
                  <component v-else :is="currentSourceForDisplay.icon" class="h-6 w-6 md:h-7 md:w-7 text-primary" />
            </div>
            <div>
                  <h3 class="text-lg md:text-xl font-semibold text-text-primary">{{ currentSourceForDisplay.name }}</h3>
                  <p class="text-xs md:text-sm text-text-secondary">Configure automatic review collection</p>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="isCurrentSourceViewEnabled" class="sr-only peer">
            <div class="w-11 h-6 bg-amber-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-400/40 
rounded-full peer 
peer-checked:after:translate-x-full peer-checked:after:border-white 
after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
after:bg-white after:border-amber-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all 
peer-checked:bg-gradient-to-r peer-checked:from-amber-500 peer-checked:to-orange-600
"></div>
          </label>
        </div>

            <!-- CONFIGURATION PANEL for currentSourceForDisplay -->
            <div v-if="isCurrentSourceViewEnabled" class="border-t border-border bg-surface relative transition-all duration-300 ease-in-out">
              <div v-if="currentSourceForDisplay.id === 'mybusiness' && isSearchingGooglePlaces" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-b-2xl">
             <ArrowPathIcon class="h-8 w-8 text-primary animate-spin" />
                 <span class="ml-3 text-text-secondary">{{ reportAndScrapeStore.googlePlacesDiscoveryMessage || 'Searching Locations...' }}</span>
          </div>
              <div class="p-5 md:p-6 space-y-6" :class="{ 'opacity-50 pointer-events-none': currentSourceForDisplay.id === 'mybusiness' && isSearchingGooglePlaces }">

            <!-- TripAdvisor Config -->
                <template v-if="currentSourceForDisplay.id === 'tripadvisor'">
                  <!-- TripAdvisor Discovery UI -->
                  <div class="p-4 my-4 border border-dashed border-amber-300 rounded-xl bg-amber-50/50 space-y-3">
                    <div class="flex items-center space-x-2">
                      <MagnifyingGlassIcon class="h-6 w-6 text-amber-600" />
                      <h4 class="text-md font-semibold text-amber-700">Discover TripAdvisor Page</h4>
                    </div>
                    <p class="text-xs text-amber-600">
                      Enter a brand name to find its official TripAdvisor page. Select the correct one from the results below.
                    </p>
                    <div>
                      <label for="tripadvisorBrandForDiscovery" class="block text-sm font-medium text-text-secondary mb-1">Brand Name</label>
                      <div class="flex items-stretch gap-2">
                        <input type="text" id="tripadvisorBrandForDiscovery" v-model="tripadvisorBrandNameForDiscovery"
                              placeholder="e.g., YourBrand, CompetitorRestaurante"
                              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 flex-grow"
                              :disabled="isDiscoveringTripadvisorUrls">
                        
                        <button @click="triggerTripadvisorUrlDiscovery"
                                type="button"
                                :disabled="!tripadvisorBrandNameForDiscovery.trim() || !tripadvisorCountryForDiscovery || isDiscoveringTripadvisorUrls"
                                class="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-sm flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed">
                          <MagnifyingGlassIcon class="h-5 w-5 sm:mr-2" />
                          <span class="hidden sm:inline">Discover</span>
                          <ArrowPathIcon v-if="isDiscoveringTripadvisorUrls" class="h-5 w-5 ml-2 animate-spin" />
                        </button>
                      </div>
                    </div>

                    <!-- Single-select Country selector for discovery -->
                    <div class="pt-2">
                      <label class="block text-sm font-medium text-text-secondary mb-2">Country for Discovery</label>
                      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        <div v-for="country in tripadvisorDiscoveryCountries" :key="country.id" 
                              @click="tripadvisorCountryForDiscovery = country.id"
                              class="flex items-center space-x-2 p-2 rounded-lg border hover:border-primary/50 cursor-pointer transition-colors"
                              :class="tripadvisorCountryForDiscovery === country.id ? 'bg-primary/10 border-primary shadow-sm' : 'border-border'">
                          <span :class="country.flag" class="text-lg"></span>
                          <span class="text-sm text-text-primary">{{ country.name }}</span>
                        </div>
                      </div>
                    </div>

                    <div v-if="tripadvisorDiscoveryError" class="mt-2 p-2.5 bg-red-100 border border-red-300 text-red-700 rounded-lg text-xs">
                      {{ tripadvisorDiscoveryError }}
                    </div>
                  </div>

                  <!-- Discovered TripAdvisor URLs Results -->
                  <div v-if="discoveredTripadvisorUrls.length > 0" class="mt-4 space-y-2">
                    <h5 class="text-sm font-medium text-text-secondary mb-2">Select the correct TripAdvisor Page:</h5>
                    <div v-for="(item, index) in discoveredTripadvisorUrls" :key="index"
                        class="p-2 rounded-lg border transition-colors"
                        :class="selectedTripadvisorUrl === item.url ? 'bg-primary/10 border-primary' : 'border-border'">
                      <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" v-model="selectedTripadvisorUrl" :value="item.url" name="tripadvisor-url-selection" class="h-4 w-4 text-primary focus:ring-primary/50 border-gray-300">
                        <GlobeAltIcon class="h-5 w-5 text-amber-500" />
                        <span class="text-sm text-text-primary hover:text-primary transition-colors">{{ item.url }}</span>
                      </label>
                    </div>
                  </div>

              <div class="opacity-50">
                <label :for="`numReviews_${currentSourceForDisplay.id}`" class="block text-sm font-medium text-text-secondary mb-1">Number of Reviews (per URL)</label>
                <input :id="`numReviews_${currentSourceForDisplay.id}`" type="text" :value="`${FIXED_REVIEWS} (Fixed for ${currentSourceForDisplay.name})`" readonly class="w-full rounded-lg border-border bg-gray-100 cursor-not-allowed">
              </div>
            </template>
            
            <!-- Products Config (NEW) -->
            <template v-else-if="currentSourceForDisplay.id === 'products'">
              <!-- AMAZON VIEW -->
              <div v-if="selectedSourceView === 'products_amazon'">
                <!-- NEW: Bright Data Amazon Product Discovery Section -->
                <div class="p-4 my-4 border border-dashed border-amber-300 rounded-xl bg-amber-50/50 space-y-3">
                  <div class="flex items-center space-x-2">
                    <CircleStackIcon class="h-6 w-6 text-amber-600" />
                    <h4 class="text-md font-semibold text-amber-700">Discover Products via Amazon Brand Search</h4>
                  </div>
                  <p class="text-xs text-amber-600">
                    Enter a brand name to discover related products on Amazon.
                    Results will appear below. Add them to your list for scraping.
                  </p>
                  <div>
                    <label for="amazonBrandForBrightData" class="block text-sm font-medium text-text-secondary mb-1">Brand Name</label>
                    <div class="flex items-stretch gap-2">
                      <input type="text" id="amazonBrandForBrightData" v-model="amazonBrandNameForBrightData"
                            placeholder="e.g., CeraVe, Anker"
                            class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 flex-grow"
                            :disabled="isDiscoveringAmazonProducts || isLoadingDiscoveredAmazonProducts">
                      
                      <button @click="triggerAmazonProductDiscovery"
                              type="button"
                              :disabled="!amazonBrandNameForBrightData.trim() || !amazonCountryForBrightData || isDiscoveringAmazonProducts || isLoadingDiscoveredAmazonProducts"
                              class="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-sm flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed">
                        <MagnifyingGlassIcon class="h-5 w-5 sm:mr-2" />
                        <span class="hidden sm:inline">Discover</span>
                        <ArrowPathIcon v-if="isDiscoveringAmazonProducts || isLoadingDiscoveredAmazonProducts" class="h-5 w-5 ml-2 animate-spin" />
                      </button>
                    </div>
                  </div>

                  <!-- NEW: Single-select Country selector for discovery -->
                  <div class="pt-2">
                    <label class="block text-sm font-medium text-text-secondary mb-2">Country for Discovery</label>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      <div v-for="country in amazonDiscoveryCountries" :key="country.id" 
                            @click="amazonCountryForBrightData = country.id"
                            class="flex items-center space-x-2 p-2 rounded-lg border hover:border-primary/50 cursor-pointer transition-colors"
                            :class="amazonCountryForBrightData === country.id ? 'bg-primary/10 border-primary shadow-sm' : 'border-border'">
                        <span :class="country.flag" class="text-lg"></span>
                        <span class="text-sm text-text-primary">{{ country.name }}</span>
                      </div>
                    </div>
                  </div>

                  <div v-if="brightDataDiscoveryError" class="mt-2 p-2.5 bg-red-100 border border-red-300 text-red-700 rounded-lg text-xs">
                    {{ brightDataDiscoveryError }}
                  </div>
                  <div v-if="brightDataDiscoveryStatusMessage && !brightDataDiscoveryError" class="mt-2 p-2.5 bg-amber-100 border border-amber-300 text-amber-700 rounded-lg text-xs">
                    {{ brightDataDiscoveryStatusMessage }}
                  </div>
                  
                  <!-- Display Discovered Amazon Products as Cards -->
                  <div v-if="isLoadingDiscoveredAmazonProducts && discoveredAmazonProducts.length === 0" class="mt-2 p-3 text-center bg-gray-50 border border-gray-200 rounded-lg">
                      <ArrowPathIcon class="h-5 w-5 text-gray-500 animate-spin inline-block mr-2" />
                      <p class="text-sm text-text-secondary">Loading discovered products...</p>
                  </div>
                  <div v-if="discoveredAmazonProducts.length > 0" class="mt-4">
                    <h5 class="text-sm font-medium text-text-secondary mb-2">Discovered Products ({{ filteredDiscoveredAmazonProducts.length }} of {{ discoveredAmazonProducts.length }})</h5>
                    
                    <!-- Search bar and Add all buttons -->
                    <div class="mb-4 p-2 bg-amber-100/50 rounded-lg space-y-2 sm:space-y-0 sm:flex sm:items-center sm:justify-between gap-4">
                      <div class="relative flex-grow">
                        <MagnifyingGlassIcon class="h-5 w-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2"/>
                        <input 
                          type="text" 
                          v-model="amazonDiscoverySearchQuery" 
                          placeholder="Search by name, ASIN, or brand..."
                          class="w-full pl-10 pr-10 py-2 rounded-lg border-gray-300 focus:border-amber-500 focus:ring-amber-500 text-sm"
                        >
                        <!-- Clear button -->
                        <button 
                          v-if="amazonDiscoverySearchQuery" 
                          @click="amazonDiscoverySearchQuery = ''" 
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          <XMarkIcon class="h-4 w-4"/>
                        </button>
                      </div>
                      <div class="flex items-center justify-end gap-2 flex-shrink-0">
                        <button @click="addAllVisibleDiscoveredProducts('amazon')" 
                                :disabled="isAddingAllProducts || filteredDiscoveredAmazonProducts.length === 0"
                                class="px-3 py-2 text-xs font-semibold text-white bg-amber-600 rounded-lg hover:bg-amber-700 disabled:bg-gray-400 flex items-center gap-1.5 transition-colors">
                            <PlusIcon class="h-4 w-4"/>
                            <span>Add All for Amazon ({{ filteredDiscoveredAmazonProducts.length }})</span>
                        </button>
                      </div>
                    </div>

                    <!-- No results message when filtered -->
                    <div v-if="amazonDiscoverySearchQuery.trim() && filteredDiscoveredAmazonProducts.length === 0" 
                        class="mt-4 p-4 text-center bg-gray-50 border border-gray-200 rounded-lg">
                      <p class="text-sm text-text-secondary">
                        No products found matching "{{ amazonDiscoverySearchQuery }}". 
                        <button @click="amazonDiscoverySearchQuery = ''" class="text-primary hover:underline">Clear search</button> to see all products.
                      </p>
                    </div>

                    <div v-if="filteredDiscoveredAmazonProducts.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-1 max-h-[500px] overflow-y-auto bg-amber-50/30 rounded-lg">
                      <div v-for="(product, index) in filteredDiscoveredAmazonProducts" :key="product.asin || product.url || index"
                          class="bg-white rounded-xl shadow-md border border-border overflow-hidden flex flex-col text-xs transition-all duration-200 ease-in-out hover:shadow-xl">
                        <a :href="product.url" target="_blank" rel="noopener noreferrer" class="block hover:opacity-90 transition-opacity aspect-square">
                          <img :src="product.image_url || product.image" :alt="product.title || 'Product image'" class="w-full h-full object-contain p-2 bg-gray-50">
                        </a>
                        <div class="p-3 flex-grow flex flex-col">
                          <a :href="product.url" target="_blank" rel="noopener noreferrer" class="block hover:text-primary mb-1" :title="product.title">
                            <h6 class="font-semibold text-text-primary clamp-2 leading-tight text-[13px]">{{ product.title || 'Unnamed Product' }}</h6>
                          </a>

                          <div v-if="typeof parseFloat(product.rating) === 'number' && !isNaN(parseFloat(product.rating)) && parseFloat(product.rating) > 0" class="flex items-center my-1 text-[11px]">
                            <StarIcon v-for="i in 5" :key="`rating-${index}-${i}`" class="h-3.5 w-3.5"
                                      :class="i <= Math.round(parseFloat(product.rating)) ? 'text-amber-400 fill-amber-400' : 'text-gray-300'" />
                            <span class="ml-1.5 text-gray-500">({{ parseFloat(product.rating).toFixed(1) }})</span>
                            <span v-if="product.reviews_count" class="ml-1 text-gray-400">({{ product.reviews_count }})</span>
                          </div>
                          <div v-else class="my-1 h-[19.5px]"> 
                              <span class="text-gray-400 text-[11px] italic">No rating available</span>
                          </div>

                          <div class="text-[11px] text-gray-500 mt-0.5 mb-1.5 space-y-0.5">
                              <span v-if="product.brand" class="block truncate" :title="product.brand">Brand: <span class="text-text-secondary">{{ product.brand }}</span></span>
                              <span v-if="product.asin" class="block">ASIN: <span class="text-text-secondary">{{ product.asin }}</span></span>
                          </div>

                          <div class="flex items-baseline justify-between my-1">
                              <p v-if="product.final_price" class="text-base font-semibold text-text-primary">
                                  {{ product.currency === 'USD' ? '$' : (product.currency_symbol || '') }}{{ Number(product.final_price).toFixed(2) }}
                                  <span v-if="product.currency" class="text-[10px] text-gray-500 ml-0.5">{{ product.currency }}</span>
                              </p>
                              <p v-else class="text-sm text-gray-400 italic">Price N/A</p>
                          </div>

                          <!-- ***** START NEW SCRAPE TARGET SELECTORS ***** -->
                          <div class="my-2 flex items-center space-x-2">
                            <button 
                              @click="toggleScrapeTarget(product, 'amazon')"
                              :class="[
                                'px-1.5 py-0.5 text-[10px] rounded-md border transition-colors focus:outline-none focus:ring-1 focus:ring-offset-1',
                                product.scrapeTargets?.amazon ? 'bg-amber-500 text-white border-amber-600 focus:ring-amber-400' : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200 focus:ring-gray-400'
                              ]">
                              Amazon
                            </button>
                          </div>
                          <!-- ***** END NEW SCRAPE TARGET SELECTORS ***** -->

                          <button @click="addDiscoveredProductToItems(product, currentSourceForDisplay.config)"
                                  class="mt-auto w-full bg-primary/80 text-white py-1.5 px-2 rounded-md hover:bg-primary transition-colors text-[11px] font-medium flex items-center justify-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                                  :disabled="!product.scrapeTargets?.amazon"
                                  title="Add to list based on selected scrape targets">
                            <PlusIcon class="h-4 w-4" />
                            <span>Add to My List</span>
                          </button>
                        </div>
                      </div>
                    </div>
                    <p class="text-xs text-text-secondary mt-2">Select scrape targets (Amazon/Druni) then 'Add to My List'.</p>
                  </div>
                </div>
                <!-- END NEW: Bright Data Amazon Product Discovery Section -->

                <!-- START: Manual Product Lookup and Add Section -->
                <div class="p-4 my-4 border border-dashed border-orange-300 rounded-xl bg-orange-50/50 space-y-3">
                  <div class="flex items-center space-x-2">
                    <MagnifyingGlassIcon class="h-6 w-6 text-orange-600" />
                    <h4 class="text-md font-semibold text-orange-700">Look Up & Add Products Manually</h4>
                  </div>
                  <p class="text-xs text-orange-600">
                    Enter generic product names, separated by new lines.
                  </p>
                  <!-- NEW: Single-select Country selector for manual lookup -->
                  <div class="pt-2">
                    <label class="block text-sm font-medium text-text-secondary mb-2">Country for Look Up</label>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      <div v-for="country in amazonDiscoveryCountries" :key="country.id"
                            @click="amazonCountryForManualLookup = country.id"
                            class="flex items-center space-x-2 p-2 rounded-lg border hover:border-primary/50 cursor-pointer transition-colors"
                            :class="amazonCountryForManualLookup === country.id ? 'bg-primary/10 border-primary shadow-sm' : 'border-border'">
                        <span :class="country.flag" class="text-lg"></span>
                        <span class="text-sm text-text-primary">{{ country.name }}</span>
                      </div>
                    </div>
                  </div>
                <div> 
                    <label for="manualProductInput" class="block text-sm font-medium text-text-secondary mb-1">Product Names</label>
                    <div class="flex items-start space-x-2">
                      <textarea id="manualProductInput" v-model="manualProductInputQuery" rows="3" 
                                placeholder="e.g.,&#10;moisturizing cream&#10;wireless earbuds&#10;running shoes" 
                                class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 flex-grow"
                                :disabled="isFetchingManualProducts"></textarea>
                      <button @click="triggerManualProductLookup"
                              type="button"
                              :disabled="!manualProductInputQuery.trim() || isFetchingManualProducts"
                              class="px-4 py-2 h-full bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors text-sm flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed">
                        <MagnifyingGlassIcon v-if="!isFetchingManualProducts" class="h-5 w-5 mr-1 sm:mr-2" />
                        <ArrowPathIcon v-if="isFetchingManualProducts" class="h-5 w-5 mr-1 sm:mr-2 animate-spin" />
                        <span class="hidden sm:inline">Look Up</span>
                      </button>
                    </div>
                  </div>

                  <!-- Display Status Messages for Manual Lookup -->
                  <div v-if="manualLookupStatusMessageDisplay" class="mt-2 p-2.5 bg-orange-100 border border-orange-300 text-orange-700 rounded-lg text-xs">
                      <div class="flex items-center">
                          <InformationCircleIcon v-if="!manualProductFetchError" class="h-4 w-4 mr-2" />
                          <ExclamationCircleIcon v-if="manualProductFetchError" class="h-4 w-4 mr-2" />
                          <span>{{ manualLookupStatusMessageDisplay }}</span>
                      </div>
                  </div>
                  
                  <div v-if="manuallyFetchedAmazonProducts.length > 0" class="mt-4">
                    <h5 class="text-sm font-medium text-text-secondary mb-2">Found Products ({{ manuallyFetchedAmazonProducts.length }})</h5>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-1 max-h-[500px] overflow-y-auto bg-orange-50/30 rounded-lg">
                      <div v-for="(product, index) in manuallyFetchedAmazonProducts" :key="product._internal_id || `manual-${index}`"
                          class="bg-white rounded-xl shadow-md border border-border overflow-hidden flex flex-col text-xs transition-all duration-200 ease-in-out hover:shadow-xl">
                        <a :href="product.url" target="_blank" rel="noopener noreferrer" class="block hover:opacity-90 transition-opacity aspect-square">
                          <img :src="product.image_url || product.image" :alt="product.title || 'Product image'" class="w-full h-full object-contain p-2 bg-gray-50">
                        </a>
                        <div class="p-3 flex-grow flex flex-col">
                          <a :href="product.url" target="_blank" rel="noopener noreferrer" class="block hover:text-primary mb-1" :title="product.title">
                            <h6 class="font-semibold text-text-primary clamp-2 leading-tight text-[13px]">{{ product.title || 'Unnamed Product' }}</h6>
                          </a>

                          <div v-if="typeof parseFloat(product.rating) === 'number' && !isNaN(parseFloat(product.rating)) && parseFloat(product.rating) > 0" class="flex items-center my-1 text-[11px]">
                            <StarIcon v-for="i in 5" :key="`manual-rating-${index}-${i}`" class="h-3.5 w-3.5"
                                      :class="i <= Math.round(parseFloat(product.rating)) ? 'text-amber-400 fill-amber-400' : 'text-gray-300'" />
                            <span class="ml-1.5 text-gray-500">({{ parseFloat(product.rating).toFixed(1) }})</span>
                            <span v-if="product.reviews_count" class="ml-1 text-gray-400">({{ product.reviews_count }})</span>
                          </div>
                          <div v-else class="my-1 h-[19.5px]"> 
                              <span class="text-gray-400 text-[11px] italic">No rating available</span>
                          </div>

                          <div class="text-[11px] text-gray-500 mt-0.5 mb-1.5 space-y-0.5">
                              <span v-if="product.brand" class="block truncate" :title="product.brand">Brand: <span class="text-text-secondary">{{ product.brand }}</span></span>
                              <span v-if="product.asin" class="block">ASIN: <span class="text-text-secondary">{{ product.asin }}</span></span>
                          </div>

                          <div class="flex items-baseline justify-between my-1">
                              <p v-if="product.final_price && product.final_price !== 'N/A'" class="text-base font-semibold text-text-primary">
                                  {{ product.currency_symbol || (product.currency === 'USD' ? '$' : '') }}{{ Number(product.final_price).toFixed(2) }}
                                  <span v-if="product.currency" class="text-[10px] text-gray-500 ml-0.5">{{ product.currency }}</span>
                              </p>
                              <p v-else class="text-sm text-gray-400 italic">Price N/A</p>
                          </div>
                          
                          <div class="my-2 flex items-center space-x-2">
                            <button 
                              @click="toggleScrapeTarget(product, 'amazon')"
                              :class="[
                                'px-1.5 py-0.5 text-[10px] rounded-md border transition-colors focus:outline-none focus:ring-1 focus:ring-offset-0',
                                product.scrapeTargets?.amazon ? 'bg-amber-500 text-white border-amber-600 focus:ring-amber-400' : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200 focus:ring-gray-400'
                              ]">
                              Amazon
                            </button>
                          </div>

                          <button @click="addDiscoveredProductToItems(product, currentSourceForDisplay.config)"
                                  class="mt-auto w-full bg-primary/80 text-white py-1.5 px-2 rounded-md hover:bg-primary transition-colors text-[11px] font-medium flex items-center justify-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                                  :disabled="!product.scrapeTargets?.amazon"
                                  title="Add to list based on selected scrape targets">
                            <PlusIcon class="h-4 w-4" />
                            <span>Add to My List</span>
                          </button>
                        </div>
                      </div>
                    </div>
                    <p class="text-xs text-text-secondary mt-2">Select scrape targets (Amazon/Druni) then 'Add to My List'.</p>
                  </div>
                  <p v-if="!isFetchingManualProducts && manuallyFetchedAmazonProducts.length === 0" class="mt-2 text-sm text-text-secondary text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                    No products currently displayed. Enter identifiers above and click "Look Up".
                  </p>
                </div>
                <!-- END: Manual Product Lookup and Add Section -->
              </div>
              
              <!-- RETAILERS (DRUNI) VIEW -->
              <div v-if="selectedSourceView === 'products_druni'">
                  <template v-if="hasAnyProducts">
                      <div class="p-4 bg-pink-50 border border-dashed border-pink-300 rounded-xl space-y-3">
                        <div class="flex items-center space-x-3">
                          <img src="/images/druni-logo.png" alt="Druni" class="h-8 w-auto rounded">
                           <h4 class="text-md font-semibold text-pink-700">Configure Druni Scraping</h4>
                        </div>
                        <p class="text-sm text-pink-600">
                          Enable Druni as a scrape target for your existing products. The list below shows all products you've added.
                        </p>
                      </div>
                  </template>
                  <template v-else>
                      <div class="p-6 bg-amber-50 border border-dashed border-amber-300 rounded-2xl text-center flex flex-col items-center">
                          <ExclamationTriangleIcon class="h-10 w-10 text-amber-500 mb-3"/>
                          <h4 class="text-md font-semibold text-amber-800">No Products Added Yet</h4>
                          <p class="mt-1 max-w-md text-sm text-amber-700">
                              To configure Druni scraping, you must first discover and add products to your list using the Amazon tab.
                          </p>
                          <button @click="selectedSourceView = 'products_amazon'" class="mt-4 px-5 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-dark transition-colors shadow-sm flex items-center space-x-2">
                              <ShoppingBagIcon class="h-5 w-5"/>
                              <span>Go to Amazon Tab</span>
                          </button>
                      </div>
                  </template>
              </div>

              <!-- SHARED: Current Product List -->
              <div v-if="currentSourceForDisplay.config.productItems && currentSourceForDisplay.config.productItems.length > 0" class="mt-4">
                <label class="block text-sm font-medium text-text-secondary mb-2">Current Product Identifiers ({{ currentSourceForDisplay.config.productItems.length }})</label>
                <div class="space-y-2 max-h-72 overflow-y-auto pr-2">
                  <div v-for="(item, index) in currentSourceForDisplay.config.productItems" :key="index" 
                       class="flex items-center justify-between p-2.5 bg-white border border-border rounded-lg shadow-sm hover:shadow-md transition-shadow duration-150">
                    <div class="flex items-center space-x-2 overflow-hidden flex-grow">
                      <TagIcon class="h-5 w-5 text-primary flex-shrink-0"/>
                      <span class="text-sm text-text-primary truncate flex-grow" :title="item.title || item.identifier">{{ item.title || item.identifier }}</span>
                    </div>
                    <div class="flex items-center space-x-1.5 ml-2 flex-shrink-0">
                       <button 
                        v-if="selectedSourceView === 'products_amazon'"
                        @click="toggleScrapeTarget(item, 'amazon')"
                        :class="[
                          'px-1.5 py-0.5 text-[10px] rounded border transition-colors focus:outline-none focus:ring-1 focus:ring-offset-0',
                          item.scrapeTargets?.amazon ? 'bg-amber-500 text-white border-amber-600 focus:ring-amber-400' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-gray-200 focus:ring-gray-400'
                        ]" title="Toggle Amazon scraping for this item">
                        Amazon
                      </button>
                      <button 
                        v-if="selectedSourceView === 'products_druni'"
                        @click="toggleScrapeTarget(item, 'druni')"
                        :class="[
                          'px-1.5 py-0.5 text-[10px] rounded border transition-colors focus:outline-none focus:ring-1 focus:ring-offset-0',
                          item.scrapeTargets?.druni ? 'bg-pink-500 text-white border-pink-600 focus:ring-pink-400' : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-gray-200 focus:ring-gray-400'
                        ]" title="Toggle Druni scraping for this item">
                        Druni
                      </button>
                      <button @click="removeProductIdentifier(currentSourceForDisplay.config, index)" 
                              class="p-1 text-red-500 hover:text-red-700 rounded-full hover:bg-red-100 transition-colors"
                              title="Remove this item">
                        <XMarkIcon class="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="mt-4 p-3 text-center bg-gray-50 border border-gray-200 rounded-lg">
                <p class="text-sm text-text-secondary">No product identifiers added yet. Use the discovery tool or add manually above.</p>
              </div>

            </template>


                <!-- Others (Trustpilot, Google My Business) -->
                <template v-else-if="currentSourceForDisplay.id === 'trustpilot'">
                  <!-- Trustpilot Discovery UI -->
                  <div class="p-4 my-4 border border-dashed border-amber-300 rounded-xl bg-amber-50/50 space-y-3">
                    <div class="flex items-center space-x-2">
                      <MagnifyingGlassIcon class="h-6 w-6 text-amber-600" />
                      <h4 class="text-md font-semibold text-gray-700">Discover Trustpilot Page</h4>
                    </div>
                    <p class="text-xs text-gray-600">
                      Enter a brand name to find its official Trustpilot page. Select the correct one from the results below.
                    </p>
                    <div>
                      <label for="trustpilotBrandForDiscovery" class="block text-sm font-medium text-text-secondary mb-1">Brand Name</label>
                      <div class="flex items-stretch gap-2">
                        <input type="text" id="trustpilotBrandForDiscovery" v-model="trustpilotBrandNameForDiscovery"
                              placeholder="e.g., YourBrand, CompetitorBrand"
                              class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 flex-grow"
                              :disabled="isDiscoveringTrustpilotUrls">
                        
                        <button @click="triggerTrustpilotUrlDiscovery"
                                type="button"
                                :disabled="!trustpilotBrandNameForDiscovery.trim() || !trustpilotCountryForDiscovery || isDiscoveringTrustpilotUrls"
                                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed">
                          <MagnifyingGlassIcon class="h-5 w-5 sm:mr-2" />
                          <span class="hidden sm:inline">Discover</span>
                          <ArrowPathIcon v-if="isDiscoveringTrustpilotUrls" class="h-5 w-5 ml-2 animate-spin" />
                        </button>
                      </div>
                    </div>

                    <!-- Single-select Country selector for discovery -->
                    <div class="pt-2">
                      <label class="block text-sm font-medium text-text-secondary mb-2">Country for Discovery</label>
                      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        <div v-for="country in trustpilotDiscoveryCountries" :key="country.id" 
                              @click="trustpilotCountryForDiscovery = country.id"
                              class="flex items-center space-x-2 p-2 rounded-lg border hover:border-primary/50 cursor-pointer transition-colors"
                              :class="trustpilotCountryForDiscovery === country.id ? 'bg-primary/10 border-primary shadow-sm' : 'border-border'">
                          <span :class="country.flag" class="text-lg"></span>
                          <span class="text-sm text-text-primary">{{ country.name }}</span>
                        </div>
                      </div>
                    </div>

                    <div v-if="trustpilotDiscoveryError" class="mt-2 p-2.5 bg-red-100 border border-red-300 text-red-700 rounded-lg text-xs">
                      {{ trustpilotDiscoveryError }}
                    </div>
                  </div>

                  <!-- Discovered Trustpilot URLs Results -->
                  <div v-if="discoveredTrustpilotUrls.length > 0" class="mt-4 space-y-2">
                    <h5 class="text-sm font-medium text-text-secondary mb-2">Select the correct Trustpilot Page:</h5>
                    <div v-for="(item, index) in discoveredTrustpilotUrls" :key="index"
                        class="p-2 rounded-lg border transition-colors"
                        :class="selectedTrustpilotUrl === item.url ? 'bg-primary/10 border-primary' : 'border-border'">
                      <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" v-model="selectedTrustpilotUrl" :value="item.url" name="trustpilot-url-selection" class="h-4 w-4 text-primary focus:ring-primary/50 border-gray-300">
                        <StarIcon class="h-5 w-5 text-green-500" />
                        <span class="text-sm text-text-primary hover:text-primary transition-colors">{{ item.url }}</span>
                      </label>
                    </div>
                  </div>

                  <!-- Number of reviews dropdown -->
                  <div>
                    <label :for="`numReviews_${currentSourceForDisplay.id}`" class="block text-sm font-medium text-text-secondary mb-1">Number of Reviews</label>
                    <select :id="`numReviews_${currentSourceForDisplay.id}`" v-model.number="numberOfReviewsSelectable" class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20">
                      <option :value="500">500</option>
                      <option :value="1000">1000</option>
                      <option :value="1500">1500</option>
                      <option :value="2000">2000</option>
                      <option :value="2500">2500</option>
                      <option :value="3000">3000</option>
                      <option :value="3500">3500</option>
                      <option :value="4000">4000</option>
                      <option :value="4500">4500</option>
                      <option :value="5000">5000</option>
                    </select>
                    <p class="mt-1 text-xs text-text-secondary">Select the maximum number of reviews to gather initially.</p>
                  </div>
                </template>

                <template v-else-if="currentSourceForDisplay.id === 'mybusiness'">
                  <!-- Card 1: Discover Locations by Brand -->
                  <div class="p-4 my-4 border border-dashed border-amber-300 rounded-xl bg-amber-50/50 space-y-4">
                    <div class="flex items-center space-x-2">
                      <MagnifyingGlassIcon class="h-6 w-6 text-amber-600" />
                      <h4 class="text-md font-semibold text-amber-700">Discover Locations by Brand</h4>
                    </div>
                    <p class="text-xs text-amber-600">
                      Enter a brand name/website and select a country to find all associated Google Maps locations.
                    </p>
                    <div>
                      <label class="block text-sm font-medium text-text-secondary mb-1">Brand Name or URL</label>
                      <input type="text" v-model="currentSourceForDisplay.config.brandName" placeholder="e.g., Telepizza or telepizza.es" class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20" />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-text-secondary mb-2">Country</label>
                      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        <div v-for="country in allCountries" :key="country.id" 
                                @click="googleMyBusinessCountry = country.id"
                                class="flex items-center space-x-2 p-2 rounded-lg border hover:border-primary/50 cursor-pointer transition-colors"
                                :class="googleMyBusinessCountry === country.id ? 'bg-primary/10 border-primary shadow-sm' : 'border-border bg-white'">
                          <span :class="country.flag" class="text-lg"></span>
                          <span class="text-sm text-text-primary">{{ country.name }}</span>
                        </div>
                      </div>
                    </div>
                     <div v-if="googleMyBusinessCountry === 'es'" class="pt-2">
                        <label class="block text-sm font-medium text-text-secondary mb-1">Provinces (Spain) (Optional)</label>
                        <select v-model="provinceToAdd" class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20 bg-white">
                            <option disabled value="">-- Select provinces to add --</option>
                            <option value="__ALL__" :disabled="currentSourceForDisplay.config.selectedProvinces.includes('__ALL__')">All Provinces</option>
                            <option v-for="province in spanishProvinces" :key="province" :value="province" :disabled="currentSourceForDisplay.config.selectedProvinces.includes(province)">
                                {{ province }}
                            </option>
                        </select>

                        <div v-if="currentSourceForDisplay.config.selectedProvinces.length > 0" class="mt-2 flex flex-wrap gap-2">
                            <span v-for="province in currentSourceForDisplay.config.selectedProvinces" :key="province" class="flex items-center bg-amber-100 text-amber-800 text-xs font-medium px-2.5 py-1 rounded-full">
                                {{ province === '__ALL__' ? 'All Provinces' : province }}
                                <button @click="removeProvince(province)" class="ml-1.5 -mr-1 p-0.5 rounded-full hover:bg-amber-200">
                                    <XMarkIcon class="h-3 w-3" />
                                </button>
                            </span>
                        </div>
                        <p v-else class="mt-1 text-xs text-text-secondary">No provinces selected. The search will cover all of Spain.</p>
                    </div>
                     <div>
                      <button @click="searchGooglePlaces" :disabled="!canSearchGooglePlaces || isSearchingGooglePlaces" type="button" class="w-full px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center space-x-2" :class="!canSearchGooglePlaces || isSearchingGooglePlaces ? 'bg-gray-200 text-gray-500 cursor-not-allowed' : 'bg-amber-600 text-white hover:bg-amber-700'">
                        <MagnifyingGlassIcon class="h-5 w-5" />
                        <span>Search Locations</span>
                      </button>
                      <p v-if="googleSearchError" class="mt-2 text-xs text-red-600 text-center">{{ googleSearchError }}</p>
                    </div>
                  </div>

                  <!-- Card 2: Add a Specific Place Manually -->
                  <div class="p-4 my-4 border border-dashed border-teal-300 rounded-xl bg-teal-50/50 space-y-4" ref="specificPlaceSearchContainer">
                    <div class="flex items-center space-x-2">
                      <MapPinIcon class="h-6 w-6 text-teal-600" />
                      <h4 class="text-md font-semibold text-teal-700">Add a Specific Place</h4>
                    </div>
                    <p class="text-xs text-teal-600">
                      Search for a specific location on Google Maps to add it directly to your list.
                    </p>
                    <div class="relative">
                      <input type="text" v-model="additionalPlaceQuery" placeholder="Search for a place by name or address..." class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20">
                      <button v-if="additionalPlaceQuery" @click="additionalPlaceQuery = ''" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                        <XMarkIcon class="h-5 w-5"/>
                      </button>
                    </div>
                    <div v-if="isLoadingSpecificPlaceSuggestions" class="text-xs text-amber-600 animate-pulse flex items-center"><ArrowPathIcon class="h-4 w-4 animate-spin mr-2" />Loading suggestions...</div>
                    <p v-if="specificPlaceSuggestionsError && !isLoadingSpecificPlaceSuggestions" class="text-xs text-red-600">{{ specificPlaceSuggestionsError }}</p>

                    <div v-if="specificPlaceSuggestions.length > 0" class="border border-border rounded-lg bg-white shadow-lg max-h-60 overflow-y-auto">
                      <ul>
                        <li v-for="suggestion in specificPlaceSuggestions" :key="suggestion.google_id" @click="toggleSpecificPlaceSelection(suggestion)" class="p-3 hover:bg-primary/10 cursor-pointer border-b border-border last:border-b-0 flex items-center justify-between" :class="{'bg-primary/5': isSpecificPlaceSelected(suggestion)}">
                          <div>
                            <p class="font-medium text-sm text-text-primary">{{ suggestion.name }}</p>
                            <p class="text-xs text-text-secondary">{{ suggestion.full_address }}</p>
                          </div>
                          <input type="checkbox" :checked="isSpecificPlaceSelected(suggestion)" class="ml-2 rounded border-gray-300 text-primary focus:ring-primary/30 pointer-events-none">
                        </li>
                      </ul>
                    </div>
                    <div v-if="selectedSpecificPlaces.length > 0">
                      <button @click="addSelectedSpecificPlacesToMainList" :disabled="isAddingSelectedSpecificPlaces" class="w-full px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center space-x-2" :class="isAddingSelectedSpecificPlaces ? 'bg-gray-200 text-gray-500' : 'bg-teal-600 text-white hover:bg-teal-700'">
                        <PlusIcon class="h-5 w-5" />
                        <span>Add {{ selectedSpecificPlaces.length }} Selected Place(s)</span>
                      </button>
                      <p v-if="addSelectedSpecificPlacesError" class="mt-2 text-xs text-red-600 text-center">{{ addSelectedSpecificPlacesError }}</p>
                    </div>
                  </div>

                  <!-- Section 3: Configured Locations View -->
                  <div v-if="googlePlacesResults.length > 0" class="mt-6 pt-6 border-t border-border">
                    <h3 class="text-lg font-semibold text-text-primary mb-1">Configured Locations ({{ googlePlacesResults.length }})</h3>
                    <p class="text-sm text-text-secondary mb-4">The map is interactive. Click on it to reverse-geocode and add a location.</p>
                     <p v-if="isFetchingPlaceFromMapClick" class="mt-2 text-xs text-amber-600 animate-pulse">Fetching place from map click...</p>
                    <p v-if="mapClickError" class="mt-2 text-xs text-red-600">{{ mapClickError }}</p>
                    
                    <div v-if="googleMapsApiKey" class="grid grid-cols-1 lg:grid-cols-5 gap-6">
                      <div class="lg:col-span-3 google-map-container rounded-lg overflow-hidden border border-border shadow-md">
                        <GoogleMap :api-key="googleMapsApiKey" style="width: 100%; height: 100%" :center="mapCenter" :zoom="mapZoom" @click="handleMapClick">
                          <Marker v-for="marker in mapMarkers" :key="marker.key" :options="marker" />
                        </GoogleMap>
                      </div>
                      <div class="lg:col-span-2 max-h-[400px] overflow-y-auto space-y-2 pr-1">
                        <div v-for="place in googlePlacesResults" :key="place.google_id" class="p-3 bg-white border border-border rounded-lg shadow-sm flex justify-between items-start hover:shadow-md hover:border-primary/30 transition-all duration-200">
                          <div class="flex-grow overflow-hidden">
                            <p class="font-medium text-sm text-text-primary truncate" :title="place.name">{{ place.name }}</p>
                            <p class="text-xs text-text-secondary truncate" :title="place.full_address">{{ place.full_address }}</p>
                            <span class="inline-block mt-1.5 px-1.5 py-0.5 text-[10px] font-medium rounded" :class="place.origin === 'manual' ? 'bg-teal-100 text-teal-800' : 'bg-amber-100 text-amber-800'">
                              {{ place.origin === 'manual' ? 'Manual Add' : 'Brand Search' }}
                            </span>
                          </div>
                          <button @click="removeGooglePlace(place.google_id)" class="ml-2 p-1 text-red-500 hover:text-red-700 hover:bg-red-100 rounded-full flex-shrink-0 transition-colors">
                            <XMarkIcon class="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                     <p v-if="!googleMapsApiKey" class="mt-2 text-sm text-amber-700 bg-amber-100 p-3 rounded-lg border border-amber-200">Google Maps API Key not configured. Map display and click-to-add functionality will be unavailable.</p>
                  </div>
                   <div v-else class="mt-4 p-4 text-center bg-gray-50 border border-gray-200 rounded-lg">
                    <p class="text-sm text-text-secondary">No locations added yet. Use the tools above to find and add them to your list.</p>
                  </div>


                  <!-- Section 4: Global Settings for GMB -->
                  <div class="mt-6 pt-6 border-t border-border">
                    <label :for="`numReviews_mybusiness`" class="block text-sm font-medium text-text-secondary mb-1">Number of Reviews (per location)</label>
                    <select :id="`numReviews_mybusiness`" v-model.number="numberOfReviewsSelectable" class="w-full rounded-lg border-border focus:border-primary-light focus:ring focus:ring-primary/20">
                      <option :value="500">500</option>
                      <option :value="1000">1000</option>
                      <option :value="1500">1500</option>
                      <option :value="2000">2000</option>
                      <option :value="2500">2500</option>
                      <option :value="3000">3000</option>
                      <option :value="3500">3500</option>
                      <option :value="4000">4000</option>
                      <option :value="4500">4500</option>
                      <option :value="5000">5000</option>
                    </select>
                    <p class="mt-1 text-xs text-text-secondary">Select the maximum number of reviews to gather initially from each location.</p>
                  </div>
                </template>

                <div class="flex items-center justify-between p-3 md:p-4 rounded-xl"
                     :class="isSourceConfigured(currentSourceForDisplay) ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'">
              <div class="flex items-center space-x-2">
                    <div class="w-2.5 h-2.5 rounded-full" :class="isSourceConfigured(currentSourceForDisplay) ? 'bg-emerald-500' : 'bg-amber-500'"></div>
                    <span class="text-sm font-medium" :class="isSourceConfigured(currentSourceForDisplay) ? 'text-emerald-700' : 'text-amber-700'">
                      {{ isSourceConfigured(currentSourceForDisplay) ? 'Ready to collect' : 'Configuration needed' }}
                </span>
              </div>
                </div>
              </div>
        </div>
          </div>
        </template>
            
         <div v-if="!currentSourceForDisplay" class="text-center py-10"> 
          <component :is="sourceViews.find(sv => sv.id === selectedSourceView)?.icon || GlobeAltIcon" class="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <p class="text-lg text-text-secondary">Select <span class="font-semibold">{{ sourceViews.find(sv => sv.id === selectedSourceView)?.name || 'a source' }}</span> from the list to begin configuration.</p>
          <p class="text-sm text-gray-400 mt-1">Or, if it's already configured, enable it using the toggle switch.</p>
                </div>
    </div>

      <div class="lg:w-1/3 xl:w-1/4 lg:order-2 space-y-2 lg:sticky lg:top-8 self-start">
        <h2 class="text-base md:text-lg font-semibold text-text-primary mb-3 opacity-90 px-1">Select Source Type</h2>
        <button v-for="view in sourceViews" :key="view.id"
                @click="selectedSourceView = view.id"
                :class="[
                  'w-full flex items-center space-x-3 p-3.5 rounded-xl border transition-all duration-200 ease-in-out text-left focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary/60',
                  selectedSourceView === view.id 
                    ? 'bg-orange-300 text-white shadow-lg border-primary hover:bg-amber-400' 
                    : 'bg-white text-text-primary border-border hover:bg-amber-400 hover:border-gray-300 hover:shadow-sm'
                ]">
          <component :is="view.icon" class="h-5 w-5 md:h-6 md:w-6 flex-shrink-0" 
                     :class="selectedSourceView === view.id ? 'text-white' : 'text-primary'" />
          <span class="text-sm md:text-base font-medium">{{ view.name }}</span>
          <ChevronRightIcon v-if="selectedSourceView === view.id" class="h-5 w-5 ml-auto text-white/70" />
                    </button>
                  </div>
                </div>

    <!-- Global Save & Gather Button Section -->
    <div class="mt-8 pt-8 border-t border-border">
      <div class="bg-gradient-to-r from-amber-50 to-amber-50 rounded-2xl shadow-sm border border-primary/20 p-6 md:p-8">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="text-center">
          <h3 class="text-xl font-display font-semibold text-text-primary mb-2">Ready to Start Gathering Reviews?</h3>
            <p class="text-text-secondary text-sm md:text-base">
            The initial data gathering process can take several hours depending on the number of sources and historical data available. You'll receive notifications as the process advances.
          </p>
                </div>

        <div v-if="reportAndScrapeStore.isScrapingFocusedJob && reportAndScrapeStore.focusedScrapingProgressMessage" 
             class="my-2 p-3 bg-amber-100 border border-amber-300 text-amber-700 rounded-lg text-sm text-center">
          <ArrowPathIcon class="h-5 w-5 animate-spin inline-block mr-2 align-middle" />
          {{ reportAndScrapeStore.focusedScrapingProgressMessage }}
                </div>
        <div v-if="!reportAndScrapeStore.isScrapingFocusedJob && reportAndScrapeStore.focusedScrapingError"
              class="my-2 p-3 bg-red-100 border border-red-300 text-red-700 rounded-lg text-sm text-center">
             Error: {{ reportAndScrapeStore.focusedScrapingError }}
                </div>
                
                      <button 
          @click="saveAndGather"
          :disabled="!canSaveAndGather || reportAndScrapeStore.isScrapingFocusedJob"
            class="w-full px-8 py-3 md:py-4 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 disabled:from-gray-400 disabled:to-gray-500 text-white text-base md:text-lg font-medium rounded-xl transition-all duration-300 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl disabled:shadow-none disabled:cursor-not-allowed"
        >
            <ArrowPathIcon v-if="reportAndScrapeStore.isScrapingFocusedJob" class="h-5 w-5 md:h-6 md:w-6 animate-spin" />
          <span>{{ reportAndScrapeStore.isScrapingFocusedJob ? (reportAndScrapeStore.focusedScrapingProgressMessage || 'Collection Process Running...') : 'Save & Gather Reviews' }}</span>
                      </button>

        <div class="flex items-center justify-center text-sm text-text-secondary">
          <span>💡 Tip: You can continue using the platform while we gather your reviews</span>
                    </div>
                    </div>
                  </div>
                  </div>

    <!-- Coming Soon & Contact Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
      <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
        <div class="flex items-center space-x-4 mb-4">
          <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <PlusIcon class="h-6 w-6 text-primary" />
                        </div>
          <div>
            <h3 class="text-lg font-medium text-text-primary">More Sources Coming Soon</h3>
            <p class="text-sm text-text-secondary">We're constantly adding new review sources</p>
                        </div>
                        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <div v-for="csSource in comingSoonSources" :key="csSource.id" class="text-center p-3 bg-surface rounded-lg border border-border">
                <img :src="csSource.logo" :alt="csSource.name" class="w-10 h-10 mx-auto mb-2 object-contain"/>
                <p class="text-xs font-medium text-text-primary">{{ csSource.name }}</p>
                        </div>
                        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
        <div class="flex items-center space-x-4 mb-4">
          <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <EnvelopeIcon class="h-6 w-6 text-primary" />
                      </div>
          <div>
            <h3 class="text-lg font-medium text-text-primary">Need a Custom Source?</h3>
            <p class="text-sm text-text-secondary">We can help integrate your specific needs</p>
                    </div>
                  </div>
        <div class="p-6 rounded-xl bg-surface border border-border">
          <p class="text-text-secondary mb-4 text-sm">
            Have a specific review source you'd like to integrate? Our team can help create a custom solution for your needs.
          </p>
          <button class="w-full px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-medium rounded-xl transition-all duration-300">
            Contact Us
          </button>
                </div>
              </div>
    </div>

    <!-- FAQ Section -->
    <div class="bg-white rounded-2xl shadow-sm border border-border p-6 mt-8">
      <h2 class="text-xl font-display font-semibold text-text-primary mb-6">Frequently Asked Questions</h2>
      <div class="space-y-4">
        <div v-for="(item, index) in faqItems"
             :key="index"
             class="border border-border rounded-xl overflow-hidden">
          <button
            @click="toggleFaq(index)"
            class="w-full flex items-center justify-between p-4 text-left hover:bg-surface transition-colors duration-200 focus:outline-none"
          >
            <span class="font-medium text-text-primary">{{ item.question }}</span>
            <component :is="openFaqItem === index ? ChevronUpIcon : ChevronDownIcon"
                      class="h-5 w-5 text-text-secondary" />
          </button>
          <div v-if="openFaqItem === index"
               class="p-4 bg-surface border-t border-border">
            <p class="text-text-secondary leading-relaxed">{{ item.answer }}</p>
                </div>
                  </div>
                </div>
                  </div>
                </div>
</template>

<style scoped>
/* Slide transition */
.slide-from-left-enter-active,
.slide-from-left-leave-active {
  transition: transform 0.4s ease-in-out, opacity 0.3s ease-in-out;
}
.slide-from-left-enter-from,
.slide-from-left-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
.slide-from-left-enter-to,
.slide-from-left-leave-from {
  transform: translateX(0);
  opacity: 1;
}

/* Optional: Style scrollbar for the results list */
.overflow-y-auto::-webkit-scrollbar {
    width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
}

.google-map-container {
  height: 300px; 
  width: 100%;
}

@media (min-width: 1024px) { 
  .lg\:sticky {
    position: sticky;
  }
}

.clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>