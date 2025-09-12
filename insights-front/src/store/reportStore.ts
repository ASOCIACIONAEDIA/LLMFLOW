import { defineStore } from 'pinia'
import apiClient from '@/services/axiosInstance'

// Define the structure of an SSE event's data (can be reused or made more generic)
interface SseEventData {
  status: string;
  message?: string;
  html_content?: string; // Specific to reports
  brand_name?: string;   // Specific to reports
  report_type?: string;  // Specific to reports
  error?: string;
  error_detail?: string; // Added for more detailed error messages
  report_mongo_id?: string; // Specific to reports

  // Scraping specific fields
  job_id?: string; // This is often the same as the 'id' in the event_wrapper
  source_type?: string;
  s3_path?: string;
  s3_paths?: Record<string, string>;
  processed_sources?: number;
  total_sources_to_track?: number;
  region?: string;

  // Archetype specific fields (though message/error/status are generic)
  // task_id is often the same as 'id' in event_wrapper for archetypes
}

// --- NEW: Unified structure for activity updates pushed to Dashboard ---
interface ActivityUpdateInfo {
  id: string; // Truly unique ID (e.g., job_xxx, report_yyy)
  type: 'report' | 'scraping_job' | 'archetype_generation' | 'discovery_job';
  status: string; // e.g. 'pending', 'generating_html', 'source_complete', 'completed', 'failed'
  description: string;
  dateObject: string; // ISO string of the latest update for this activity
  progress?: number; // 0-100
  iconKey: string;
  iconColor: string;
  // Optional: include original event data if dashboard needs more context, but prefer processed fields
  originalEventData?: SseEventData; // For potential debugging or complex description generation
  brandName?: string; // Added for report/archetype context
  reportType?: string; // Added for report context
  processedSources?: number; // Added for scraping context
  totalSourcesTracked?: number; // Added for scraping context
}

// --- Define the type for archetypesLastRefreshedForBrand ---
interface ArchetypeRefreshInfo {
  brandName: string;
  timestamp: number;
  taskId?: string | null;
}

// --- Define the type for lastSuccessfullyGeneratedArchetype ---
interface GeneratedArchetypeInfo {
  taskId: string;
  brandName: string;
}

export interface PiniaReportStoreState {
  // Primary task/job IDs for focused UI updates
  activeReportTaskId: string | null;
  activeScrapingJobId: string | null;
  activeArchetypeTaskId: string | null;

  // State for the focused report generation
  isGeneratingFocusedReport: boolean;
  focusedReportProgressMessage: string | null;
  focusedReportHtmlContent: string | null;
  focusedReportBrandName: string | null;
  focusedReportType: string | null;
  focusedReportGenerationError: string | null;

  // State for the focused scraping job
  isScrapingFocusedJob: boolean;
  focusedScrapingProgressMessage: string | null;
  focusedScrapingError: string | null;

  // State for focused archetype generation
  isGeneratingFocusedArchetype: boolean;
  focusedArchetypeProgressMessage: string | null;
  focusedArchetypeGenerationError: string | null;

  // --- NEW: Reactive properties for latest activity updates ---
  latestReportActivityUpdate: ActivityUpdateInfo | null;
  latestScrapingActivityUpdate: ActivityUpdateInfo | null;
  latestArchetypeActivityUpdate: ActivityUpdateInfo | null;
  latestDiscoveryActivityUpdate: ActivityUpdateInfo | null;

  // Multiplexed SSE Client
  sseClient: EventSource | null;
  sseClientId: string | null; 
  activeTaskSubscriptions: string[]; 
  activeJobSubscriptions: string[];  
  activeArchetypeTaskSubscriptions: string[];

  // Global notification (can be shared)
  notification: { type: 'success' | 'error' | 'info' | 'warning'; message: string } | null;

  // --- NEW State for brand-wide archetype updates ---
  currentUserBrandName: string | null; // To store the user's current brand
  archetypesLastRefreshedForBrand: ArchetypeRefreshInfo | null; // Use the defined interface here
  lastSuccessfullyGeneratedArchetype: GeneratedArchetypeInfo | null; // Use the defined interface here

  // In state:
  activeDiscoverySubscriptions: string[]; // For Bright Data snapshot_ids

  // --- New state for Amazon Product Discovery specific to a snapshot ID ---
  amazonDiscoveryResultsReadySnapshotId: string | null;
  amazonDiscoveryErrorSnapshotId: string | null;
  amazonDiscoveryErrorMessage: string | null;

  // --- NEW State for Manual Product Lookup ---
  activeManualLookupTaskId: string | null; // Snapshot ID for the current manual lookup
  manualLookupStatusMessage: string | null;    // User-facing status/progress message
  manualLookupError: string | null;            // Error message if lookup fails
  manualLookupResultsReadyTaskId: string | null; // Snapshot ID for which results are ready
  manualLookupErrorTaskId: string | null; // Snapshot ID for which an error occurred
  manualLookupLastErrorMessage: string | null; // Specific error message for the failed snapshot
  manualLookupProducts: any[];                 // NEW: To store products from the event

  // --- NEW State for Trustpilot URL Discovery ---
  activeTrustpilotDiscoveryTaskId: string | null;
  isDiscoveringTrustpilotUrls: boolean;
  trustpilotDiscoveryError: string | null;
  trustpilotDiscoveredUrls: { url: string }[];

  // --- NEW Initial State for TripAdvisor URL Discovery ---
  activeTripadvisorDiscoveryTaskId: string | null;
  isDiscoveringTripadvisorUrls: boolean;
  tripadvisorDiscoveryError: string | null;
  tripadvisorDiscoveredUrls: { url: string }[];

  // --- NEW State for Google Places Discovery ---
  activeGooglePlacesDiscoveryTaskId: string | null;
  isDiscoveringGooglePlaces: boolean;
  googlePlacesDiscoveryError: string | null;
  googlePlacesDiscoveredResults: any[];
  googlePlacesDiscoveryMessage: string | null;
  googlePlacesDiscoveryCompleted: boolean;

  // New state for Amazon Product Discovery
  isDiscoveringAmazonProducts: boolean;
  isLoadingDiscoveredAmazonProducts: boolean;
  amazonDiscoveredProducts: any[];
  amazonDiscoveryStatusMessage: string | null;
  amazonDiscoveryError: string | null;
  amazonDiscoveryCompletedTaskId: string | null; // NEW: to signal completion
  amazonDiscoveryErrorTaskId: string | null; // NEW: to signal error

  sseEventSource: EventSource | null;
  activeSubscriptions: Map<string, 'scraping' | 'report' | 'archetype' | 'discovery' | 'manual_lookup' | 'trustpilot_discovery' | 'tripadvisor_discovery' | 'google_places_discovery'>;
  
  // --- NEW: State for SSE connection management ---
  sseReconnectTimerId: any | null;
  sseCurrentReconnectDelay: number;
}

export const useReportStore = defineStore('reportAndScrape', {
  state: (): PiniaReportStoreState => ({
    // Primary task/job IDs for focused UI updates
    activeReportTaskId: null,
    activeScrapingJobId: null,
    activeArchetypeTaskId: null,

    // State for the focused report generation
    isGeneratingFocusedReport: false,
    focusedReportProgressMessage: null,
    focusedReportHtmlContent: null,
    focusedReportBrandName: null,
    focusedReportType: null,
    focusedReportGenerationError: null,

    // State for the focused scraping job
    isScrapingFocusedJob: false,
    focusedScrapingProgressMessage: null,
    focusedScrapingError: null,

    // State for focused archetype generation
    isGeneratingFocusedArchetype: false,
    focusedArchetypeProgressMessage: null,
    focusedArchetypeGenerationError: null,

    // --- NEW: Reactive properties for latest activity updates ---
    latestReportActivityUpdate: null,
    latestScrapingActivityUpdate: null,
    latestArchetypeActivityUpdate: null,
    latestDiscoveryActivityUpdate: null,

    // Multiplexed SSE Client
    sseClient: null,
    sseClientId: null, 
    activeTaskSubscriptions: [], 
    activeJobSubscriptions: [],  
    activeArchetypeTaskSubscriptions: [],

    // Global notification (can be shared)
    notification: null,

    // --- NEW State for brand-wide archetype updates ---
    currentUserBrandName: null, // To store the user's current brand
    archetypesLastRefreshedForBrand: null, // Use the defined interface here
    lastSuccessfullyGeneratedArchetype: null, // Use the defined interface here

    // In state:
    activeDiscoverySubscriptions: [], // For Bright Data snapshot_ids

    // --- Initialize new state ---
    amazonDiscoveryResultsReadySnapshotId: null,
    amazonDiscoveryErrorSnapshotId: null,
    amazonDiscoveryErrorMessage: null,

    // --- NEW Initial State for Manual Lookup ---
    activeManualLookupTaskId: null,
    manualLookupStatusMessage: null,
    manualLookupError: null,
    manualLookupResultsReadyTaskId: null,
    manualLookupErrorTaskId: null,
    manualLookupLastErrorMessage: null,
    manualLookupProducts: [],

    // --- NEW Initial State for Trustpilot URL Discovery ---
    activeTrustpilotDiscoveryTaskId: null,
    isDiscoveringTrustpilotUrls: false,
    trustpilotDiscoveryError: null,
    trustpilotDiscoveredUrls: [],

    // --- NEW Initial State for TripAdvisor URL Discovery ---
    activeTripadvisorDiscoveryTaskId: null,
    isDiscoveringTripadvisorUrls: false,
    tripadvisorDiscoveryError: null,
    tripadvisorDiscoveredUrls: [],

    // --- NEW Initial State for Google Places Discovery ---
    activeGooglePlacesDiscoveryTaskId: null,
    isDiscoveringGooglePlaces: false,
    googlePlacesDiscoveryError: null,
    googlePlacesDiscoveredResults: [],
    googlePlacesDiscoveryMessage: null,
    googlePlacesDiscoveryCompleted: false,

    // New state for Amazon Product Discovery
    isDiscoveringAmazonProducts: false,
    isLoadingDiscoveredAmazonProducts: false,
    amazonDiscoveredProducts: [],
    amazonDiscoveryStatusMessage: null,
    amazonDiscoveryError: null,
    amazonDiscoveryCompletedTaskId: null,
    amazonDiscoveryErrorTaskId: null,

    sseEventSource: null,
    activeSubscriptions: new Map(),

    // --- NEW: Initial state for SSE connection management ---
    sseReconnectTimerId: null,
    sseCurrentReconnectDelay: 2000, // Start with a 2-second delay
  }),

  getters: {
    isFocusedReportGenerating: (state) => state.activeReportTaskId ? state.isGeneratingFocusedReport : false,
    isFocusedScraping: (state) => state.activeScrapingJobId ? state.isScrapingFocusedJob : false,
    isFocusedArchetypeGenerating: (state) => state.activeArchetypeTaskId ? state.isGeneratingFocusedArchetype : false,
    isPerformingManualLookup: (state) => !!state.activeManualLookupTaskId && 
                                         !state.manualLookupResultsReadyTaskId && 
                                         !state.manualLookupErrorTaskId,
    isDiscoveringTrustpilot: (state) => state.isDiscoveringTrustpilotUrls,
    isDiscoveringTripadvisor: (state) => state.isDiscoveringTripadvisorUrls,
  },

  actions: {
    // NEW ACTIONS FOR STATE PERSISTENCE
    persistState() {
      const stateToPersist = {
        activeTaskSubscriptions: this.activeTaskSubscriptions,
        activeJobSubscriptions: this.activeJobSubscriptions,
        activeArchetypeTaskSubscriptions: this.activeArchetypeTaskSubscriptions,
        activeDiscoverySubscriptions: this.activeDiscoverySubscriptions,
        activeManualLookupTaskId: this.activeManualLookupTaskId,
        activeTrustpilotDiscoveryTaskId: this.activeTrustpilotDiscoveryTaskId,
        activeTripadvisorDiscoveryTaskId: this.activeTripadvisorDiscoveryTaskId,
        activeGooglePlacesDiscoveryTaskId: this.activeGooglePlacesDiscoveryTaskId,

        activeReportTaskId: this.activeReportTaskId,
        activeScrapingJobId: this.activeScrapingJobId,
        activeArchetypeTaskId: this.activeArchetypeTaskId,
      };
      sessionStorage.setItem('reportStoreSubscriptions', JSON.stringify(stateToPersist));
      console.log("SSE Store: Persisted subscriptions to sessionStorage.");
    },

    rehydrateStateAndReconnect() {
      const persistedStateJSON = sessionStorage.getItem('reportStoreSubscriptions');
      if (persistedStateJSON) {
        try {
          const persistedState = JSON.parse(persistedStateJSON);

          this.activeTaskSubscriptions = persistedState.activeTaskSubscriptions || [];
          this.activeJobSubscriptions = persistedState.activeJobSubscriptions || [];
          this.activeArchetypeTaskSubscriptions = persistedState.activeArchetypeTaskSubscriptions || [];
          this.activeDiscoverySubscriptions = persistedState.activeDiscoverySubscriptions || [];
          this.activeManualLookupTaskId = persistedState.activeManualLookupTaskId || null;
          this.activeTrustpilotDiscoveryTaskId = persistedState.activeTrustpilotDiscoveryTaskId || null;
          this.activeTripadvisorDiscoveryTaskId = persistedState.activeTripadvisorDiscoveryTaskId || null;
          this.activeGooglePlacesDiscoveryTaskId = persistedState.activeGooglePlacesDiscoveryTaskId || null;

          this.activeReportTaskId = persistedState.activeReportTaskId || null;
          this.activeScrapingJobId = persistedState.activeScrapingJobId || null;
          this.activeArchetypeTaskId = persistedState.activeArchetypeTaskId || null;
          
          this.isGeneratingFocusedReport = !!this.activeReportTaskId && this.activeTaskSubscriptions.includes(this.activeReportTaskId);
          this.isScrapingFocusedJob = !!this.activeScrapingJobId && this.activeJobSubscriptions.includes(this.activeScrapingJobId);
          this.isGeneratingFocusedArchetype = !!this.activeArchetypeTaskId && this.activeArchetypeTaskSubscriptions.includes(this.activeArchetypeTaskId);
          this.isDiscoveringTrustpilotUrls = !!this.activeTrustpilotDiscoveryTaskId;
          this.isDiscoveringTripadvisorUrls = !!this.activeTripadvisorDiscoveryTaskId;
          this.isDiscoveringGooglePlaces = !!this.activeGooglePlacesDiscoveryTaskId;
          
          console.log("SSE Store: Rehydrated state from sessionStorage.", persistedState);

          if (
            this.activeTaskSubscriptions.length > 0 ||
            this.activeJobSubscriptions.length > 0 ||
            this.activeArchetypeTaskSubscriptions.length > 0 ||
            this.activeDiscoverySubscriptions.length > 0 ||
            this.activeManualLookupTaskId ||
            this.activeTrustpilotDiscoveryTaskId ||
            this.activeTripadvisorDiscoveryTaskId ||
            this.activeGooglePlacesDiscoveryTaskId
          ) {
            this.connectOrUpdateSse();
          }

        } catch (error) {
          console.error("SSE Store: Failed to rehydrate state from sessionStorage.", error);
          sessionStorage.removeItem('reportStoreSubscriptions');
        }
      }
    },
    clearNotification() {
      this.notification = null;
    },

    // --- NEW Action to set current user's brand ---
    setCurrentUserBrandName(brandName: string | null) {
        if (this.currentUserBrandName !== brandName) {
            this.currentUserBrandName = brandName;
            // If brand name changes, we need to update SSE subscriptions
            this.connectOrUpdateSse();
        }
    },

    _buildSseUrlWithSubscriptions(): string | null {
      // Correctly build the base URL, mirroring axiosInstance.ts
      let sseBaseUrl = '/api/sse/stream'; // Default for relative paths
      if (import.meta.env.VITE_API_BASE_URL) {
        sseBaseUrl = `${import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')}/api/sse/stream`;
      }

      const params = new URLSearchParams();
      
      const taskIds = this.activeTaskSubscriptions.join(',');
      const jobIds = this.activeJobSubscriptions.join(',');
      const brandEvents = this.activeArchetypeTaskSubscriptions.join(',');
      const discoveryIds = this.activeDiscoverySubscriptions.join(',');
      const manualLookupIds = this.activeManualLookupTaskId ? this.activeManualLookupTaskId : '';
      const trustpilotIds = this.activeTrustpilotDiscoveryTaskId ? this.activeTrustpilotDiscoveryTaskId : '';
      const tripadvisorIds = this.activeTripadvisorDiscoveryTaskId ? this.activeTripadvisorDiscoveryTaskId : '';
      const googlePlacesIds = this.activeGooglePlacesDiscoveryTaskId ? this.activeGooglePlacesDiscoveryTaskId : '';

      if (taskIds) params.append('subscribe_task_ids', taskIds);
      if (jobIds) params.append('subscribe_job_ids', jobIds);
      if (brandEvents) params.append('subscribe_brand_events', brandEvents);
      if (discoveryIds) params.append('subscribe_discovery_ids', discoveryIds);
      if (manualLookupIds) params.append('subscribe_manual_lookup_ids', manualLookupIds);
      if (trustpilotIds) params.append('subscribe_trustpilot_discovery_ids', trustpilotIds);
      if (tripadvisorIds) params.append('subscribe_tripadvisor_discovery_ids', tripadvisorIds);
      if (googlePlacesIds) params.append('subscribe_google_places_discovery_ids', googlePlacesIds);

      if (params.toString() === "") {
        console.log("SSE Store: No subscriptions needed. SSE connection will not be established.");
        return null;
      }
      
      return `${sseBaseUrl}?${params.toString()}`;
    },

    // --- NEW: Connection Management ---
    connectOrUpdateSse() {
      this._clearReconnectTimer();
      this._establishSseConnection();
    },

    _clearReconnectTimer() {
      if (this.sseReconnectTimerId) {
        clearTimeout(this.sseReconnectTimerId);
        this.sseReconnectTimerId = null;
      }
    },

    _scheduleReconnect() {
      this._clearReconnectTimer();
      
      this.notification = { type: 'error', message: `Connection lost. Reconnecting in ${this.sseCurrentReconnectDelay / 1000}s...` };
      
      this.sseReconnectTimerId = setTimeout(() => {
        console.log(`SSE Store: Attempting to reconnect... (delay: ${this.sseCurrentReconnectDelay}ms)`);
        this._establishSseConnection();
        // Exponentially increase delay for the next potential failure
        this.sseCurrentReconnectDelay = Math.min(this.sseCurrentReconnectDelay * 2, 30000); // Double delay up to 30s
      }, this.sseCurrentReconnectDelay);
    },
    
    _establishSseConnection() {
      const url = this._buildSseUrlWithSubscriptions();

      // If a URL can't be built (e.g., no subscriptions), ensure any old connection is closed.
      if (!url) {
        if (this.sseClient) {
          this.sseClient.close();
          this.sseClient = null;
          console.log("SSE Store: Closed existing SSE connection as there are no active subscriptions.");
        }
        return;
      }

      // If the URL is the same and the connection is open, do nothing.
      if (this.sseClient && this.sseClient.url.endsWith(url.substring(1)) && this.sseClient.readyState === EventSource.OPEN) {
        console.log("SSE Store: Connection already open with the same subscriptions.");
        return;
      }
      
      // Close any existing connection before creating a new one
      if (this.sseClient) {
        this.sseClient.close();
      }

      console.log(`SSE Store: Establishing new connection to ${url}`);
      const eventSource = new EventSource(url);
      this.sseClient = eventSource;

      eventSource.onopen = () => {
        console.log("SSE connection opened successfully.");
        this.notification = { type: 'success', message: 'Real-time connection established.' };
        // Reset reconnect delay on successful connection
        this.sseCurrentReconnectDelay = 2000;
        this._clearReconnectTimer();
      };

      eventSource.onerror = (error) => {
        console.error("SSE connection error:", error);
        eventSource.close();
        this._scheduleReconnect();
      };

      eventSource.onmessage = (event) => {
        try {
          const eventWrapper = JSON.parse(event.data);
          const { event_group, id, data } = eventWrapper;

          // Dispatch based on the event group
          if (event_group === 'report_generation') {
            this._handleReportGenerationEvent(id, data);
          } else if (event_group === 'scrape_tracking') {
            this._handleScrapingEvent(id, data);
          } else if (event_group === 'archetype_generation') {
              this._handleArchetypeGenerationEvent(id, data);
          } else if (event_group === 'archetype_brand_refresh') {
              this._handleArchetypeBrandRefreshEvent(id, data);
          } else if (event_group === 'amazon_discovery_update') {
              this._handleAmazonDiscoveryEvent(id, data);
          } else if (event_group === 'manual_lookup_discovery') {
              this._handleManualLookupEvent(id, data);
          } else if (event_group === 'trustpilot_discovery') {
              this._handleTrustpilotDiscoveryEvent(id, data);
          } else if (event_group === 'tripadvisor_discovery') {
              this._handleTripadvisorDiscoveryEvent(id, data);
          } else if (event_group === 'google_places_discovery') {
              this._handleGooglePlacesDiscoveryEvent(id, data);
          }
        } catch (e) {
            console.error("SSE Store: Failed to parse or handle event.", e, event.data);
        }
      };
    },

    disconnectSse() {
        if (this.sseClient) {
            this.sseClient.close();
            this.sseClient = null;
            console.log("SSE Store: Manually disconnected SSE client.");
        }
        this._clearReconnectTimer();
    },

    // --- Subscription Management ---
    _addSubscription(id: string, type: 'task' | 'job' | 'archetype_task' | 'discovery' | 'manual_lookup' | 'trustpilot_discovery' | 'tripadvisor_discovery' | 'google_places_discovery') {
        let changed = false;
        if (type === 'task' && !this.activeTaskSubscriptions.includes(id)) {
            this.activeTaskSubscriptions.push(id);
            changed = true;
        } else if (type === 'job' && !this.activeJobSubscriptions.includes(id)) {
            this.activeJobSubscriptions.push(id);
            changed = true;
        } else if (type === 'archetype_task' && !this.activeArchetypeTaskSubscriptions.includes(id)) { 
            this.activeArchetypeTaskSubscriptions.push(id);
            changed = true;
        } else if (type === 'discovery' && !this.activeDiscoverySubscriptions.includes(id)) {
            this.activeDiscoverySubscriptions.push(id);
            changed = true;
        } else if (type === 'manual_lookup' && this.activeManualLookupTaskId !== id) {
            this.activeManualLookupTaskId = id;
            changed = true;
        } else if (type === 'trustpilot_discovery') {
            if (this.activeTrustpilotDiscoveryTaskId !== id) {
                this.activeTrustpilotDiscoveryTaskId = id;
                changed = true;
            }
        } else if (type === 'tripadvisor_discovery') {
            if (this.activeTripadvisorDiscoveryTaskId !== id) {
                this.activeTripadvisorDiscoveryTaskId = id;
                changed = true;
            }
        } else if (type === 'google_places_discovery') {
            if (this.activeGooglePlacesDiscoveryTaskId !== id) {
                this.activeGooglePlacesDiscoveryTaskId = id;
                changed = true;
            }
        }
        if (changed) {
          this.connectOrUpdateSse();
          this.persistState();
        }
    },

    _removeSubscription(idToRemove: string, type: 'task' | 'job' | 'archetype_task' | 'discovery' | 'manual_lookup' | 'trustpilot_discovery' | 'tripadvisor_discovery' | 'google_places_discovery') {
        let changed = false;
        if (type === 'task') {
            const initialLength = this.activeTaskSubscriptions.length;
            this.activeTaskSubscriptions = this.activeTaskSubscriptions.filter(id => id !== idToRemove);
            if (this.activeTaskSubscriptions.length !== initialLength) changed = true;
        } else if (type === 'job') {
            const initialLength = this.activeJobSubscriptions.length;
            this.activeJobSubscriptions = this.activeJobSubscriptions.filter(id => id !== idToRemove);
            if(this.activeJobSubscriptions.length !== initialLength) changed = true;
        } else if (type === 'archetype_task') { 
            const initialLength = this.activeArchetypeTaskSubscriptions.length;
            this.activeArchetypeTaskSubscriptions = this.activeArchetypeTaskSubscriptions.filter(id => id !== idToRemove);
            if(this.activeArchetypeTaskSubscriptions.length !== initialLength) changed = true;
        } else if (type === 'discovery') {
            const initialLength = this.activeDiscoverySubscriptions.length;
            this.activeDiscoverySubscriptions = this.activeDiscoverySubscriptions.filter(id => id !== idToRemove);
            if(this.activeDiscoverySubscriptions.length !== initialLength) changed = true;
        } else if (type === 'manual_lookup' && this.activeManualLookupTaskId === idToRemove) {
            this.activeManualLookupTaskId = null;
            this.manualLookupResultsReadyTaskId = null;
            this.manualLookupErrorTaskId = null;
            this.manualLookupStatusMessage = null;
            this.manualLookupError = null;
            this.manualLookupProducts = [];
            changed = true;
        } else if (type === 'trustpilot_discovery' && this.activeTrustpilotDiscoveryTaskId === idToRemove) {
            this.activeTrustpilotDiscoveryTaskId = null;
            changed = true;
        } else if (type === 'tripadvisor_discovery' && this.activeTripadvisorDiscoveryTaskId === idToRemove) {
            this.activeTripadvisorDiscoveryTaskId = null;
            changed = true;
        } else if (type === 'google_places_discovery' && this.activeGooglePlacesDiscoveryTaskId === idToRemove) {
            this.activeGooglePlacesDiscoveryTaskId = null;
            changed = true;
        }

        if (changed) {
          this.connectOrUpdateSse();
          this.persistState();
        }
    },

    // --- Report Generation Actions ---
    async initiateReportGeneration(payload: any) {
      this.activeReportTaskId = null; 
      this.isGeneratingFocusedReport = true; 
      this.focusedReportProgressMessage = 'Initiating report generation...';
      this.focusedReportHtmlContent = null;
      this.focusedReportBrandName = null;
      this.focusedReportType = null;
      this.focusedReportGenerationError = null;
      this.notification = { type: 'info', message: 'Report generation started...' };

      try {
        const response = await apiClient.post('/reports/generate', payload);
        const newTaskId = response.data.task_id;

        if (newTaskId) {
          this.activeReportTaskId = newTaskId; 
          this._addSubscription(newTaskId, 'task'); // 'task' covers both report and archetype gen via query param

          // --- ADD INITIAL ACTIVITY ---
          this.latestReportActivityUpdate = {
            id: `report_${newTaskId}`, // Ensure unique ID
            type: 'report',
            status: 'initiated',
            description: `Report generation (type: ${payload.report_type || 'Unknown'}) for brand initiated...`,
            dateObject: new Date().toISOString(),
            progress: 5,
            iconKey: 'DocumentChartBarIcon',
            iconColor: 'text-blue-500', // Or a specific "pending" color
          };
          console.log(`%c[STORE] latestReportActivityUpdate set by initiateReportGeneration. ID: ${this.latestReportActivityUpdate.id}, Status: ${this.latestReportActivityUpdate.status}, Progress: ${this.latestReportActivityUpdate.progress}`, "color: magenta; font-weight: bold;");

        } else {
          this.isGeneratingFocusedReport = false;
          this.focusedReportGenerationError = response.data.message || 'Could not initiate report generation (no task ID).';
          this.notification = { type: 'error', message: this.focusedReportGenerationError || 'Failed to start report generation.' };
        }
      } catch (error: any) {
        this.isGeneratingFocusedReport = false;
        this.activeReportTaskId = null;
        if (error.response?.data?.detail) {
          this.focusedReportGenerationError = `Error: ${error.response.data.detail}`;
        } else {
          this.focusedReportGenerationError = 'An unexpected error occurred while initiating the report.';
        }
        this.notification = { type: 'error', message: this.focusedReportGenerationError || 'An unexpected error occurred.' };
        console.error("Error initiating report generation:", error);
      }
    },

    _handleReportGenerationEvent(taskId: string, eventData: SseEventData) {
      console.log(`%c[STORE _handleReportGenerationEvent ENTRY] ID: ${taskId}, Event Status: ${eventData.status}`, "color: #FF69B4; font-weight: bold;");

      let description = eventData.message || 'Report generation updated.';
      let iconKey = 'DocumentChartBarIcon';
      let iconColor = 'text-blue-500';
      let progress = 10; 

      switch (eventData.status) {
        case 'starting': progress = 10; break;
        case 'fetching_reviews': progress = 25; iconColor = 'text-sky-500'; break;
        case 'reviews_fetched': progress = 40; iconColor = 'text-sky-500'; break;
        case 'fetching_archetype': progress = 50; iconColor = 'text-indigo-500'; break;
        case 'archetype_fetched': progress = 60; iconColor = 'text-indigo-500'; break;
        case 'generating_html': progress = 75; iconColor = 'text-purple-500'; break;
        case 'html_generated': progress = 85; iconColor = 'text-purple-500'; break;
        case 'saving_report': progress = 95; iconColor = 'text-pink-500'; break;
        case 'report_saved':
        case 'completed':
        case 'empty_report':
          progress = 100;
          iconKey = 'CheckCircleIcon';
          iconColor = 'text-green-500';
          description = eventData.message || `Report (${taskId.substring(0,6)}) completed.`;
          break;
        case 'failed':
        case 'generation_error':
        case 'save_failed':
        case 'archetype_not_found': 
        case 'archetype_error':
          progress = 100; 
          iconKey = 'ExclamationCircleIcon';
          iconColor = 'text-red-500';
          description = eventData.message || eventData.error || `Report (${taskId.substring(0,6)}) failed.`;
          break;
        default:
          progress = this.latestReportActivityUpdate?.progress || 10; 
      }
      
      this.latestReportActivityUpdate = {
        id: `report_${taskId}`, 
        type: 'report',
        status: eventData.status,
        description: description,
        dateObject: new Date().toISOString(),
        progress: progress,
        iconKey: iconKey,
        iconColor: iconColor,
        brandName: eventData.brand_name, // Ensure this comes from backend
        reportType: eventData.report_type, // Ensure this comes from backend
        originalEventData: eventData,
      };
      console.log(`%c[STORE _handleReportGenerationEvent] latestReportActivityUpdate JUST SET. ID: ${this.latestReportActivityUpdate.id}, Status: ${this.latestReportActivityUpdate.status}, Progress: ${this.latestReportActivityUpdate.progress}`, "color: red; font-weight: bold;");

      if (eventData.message) {
          const notificationType = (iconColor === 'text-red-500') ? 'error' :
                                   (iconColor === 'text-green-500') ? 'success' : 'info';
          this.notification = { type: notificationType, message: `Report (${taskId.substring(0,6)}): ${eventData.message}` };
      }

      if (this.activeReportTaskId === taskId) {
          this.focusedReportProgressMessage = description;
          if (!['completed', 'report_saved', 'empty_report', 'failed', 'generation_error', 'save_failed', 'archetype_not_found', 'archetype_error'].includes(eventData.status)) {
              this.isGeneratingFocusedReport = true;
          } else {
            this.isGeneratingFocusedReport = false;
          }

          if (eventData.status === 'html_generated' || eventData.status === 'empty_report' || eventData.status.includes('fail') || eventData.status.includes('error')) {
              this.focusedReportHtmlContent = eventData.html_content || (eventData.status.includes('fail') || eventData.status.includes('error') ? '<html><body>Error generating report.</body></html>' : null);
              this.focusedReportBrandName = eventData.brand_name || null; 
              this.focusedReportType = eventData.report_type || null;     
          }

          if (['completed', 'report_saved', 'empty_report', 'failed', 'generation_error', 'save_failed', 'archetype_not_found', 'archetype_error'].includes(eventData.status)) {
              if (eventData.status.includes('fail') || eventData.status.includes('error') || eventData.status.includes('not_found')) {
                this.focusedReportGenerationError = description;
              } else {
                this.focusedReportGenerationError = null;
              }
          }
      }
      if (['completed', 'report_saved', 'empty_report', 'failed', 'generation_error', 'save_failed', 'archetype_not_found', 'archetype_error'].includes(eventData.status)) {
        this._removeSubscription(taskId, 'task');
        if (this.activeReportTaskId === taskId) this.activeReportTaskId = null;
      }
    },

    // --- Scraping Job Actions ---
    async initiateScrapingProcess(payload: any): Promise<string | null> {
      this.activeScrapingJobId = null; 
      this.isScrapingFocusedJob = true;
      this.focusedScrapingProgressMessage = 'Initiating review scraping...';
      this.focusedScrapingError = null;
      this.notification = { type: 'info', message: 'Review scraping process started...' };

        try {
            const response = await apiClient.post('/reviews/', payload);
            const newJobId = response.data.job_id;

            if (newJobId) {
              this.activeScrapingJobId = newJobId;
              this._addSubscription(newJobId, 'job');
              // --- ADD INITIAL ACTIVITY ---
              this.latestScrapingActivityUpdate = {
                id: `job_${newJobId}`, // Ensure unique ID
                type: 'scraping_job',
                status: 'initiated',
                description: `Scraping job ${newJobId.substring(0,8)} initiated...`,
                dateObject: new Date().toISOString(),
                progress: 5,
                iconKey: 'CircleStackIcon',
                iconColor: 'text-blue-500',
              };
              return newJobId;
            } else {
          this.isScrapingFocusedJob = false;
          this.focusedScrapingError = response.data.message || 'Could not initiate scraping (no job ID).';
          this.notification = { type: 'error', message: this.focusedScrapingError || 'Failed to start scraping.' };
                return null;
            }
        } catch (error: any) {
        this.isScrapingFocusedJob = false;
        this.activeScrapingJobId = null;
        if (error.response?.data?.detail) {
          this.focusedScrapingError = `Error: ${error.response.data.detail}`;
        } else if (error.response?.data?.message) {
          this.focusedScrapingError = `Error: ${error.response.data.message}`;
        } else {
          this.focusedScrapingError = 'An unexpected error occurred while initiating scraping.';
        }
        this.notification = { type: 'error', message: this.focusedScrapingError || 'An unexpected error occurred.' };
            console.error("Error initiating scraping process:", error);
            return null;
        }
    },

    _handleScrapingEvent(jobId: string, eventData: SseEventData) {
      console.log(`%c[STORE _handleScrapingEvent ENTRY] ID: ${jobId}, Event Status: ${eventData.status}`, "color: #FFD700; font-weight: bold;"); // Gold for entry
      let description = eventData.message || `Scraping job (${jobId.substring(0,6)}) updated.`;
      let iconKey = 'CircleStackIcon'; 
      let iconColor = 'text-blue-500';
      let progress = 10;

      const currentActivity = this.latestScrapingActivityUpdate?.id === `job_${jobId}` ? this.latestScrapingActivityUpdate : null;
      progress = currentActivity?.progress || 5;

      if (eventData.status === 'pending') {
        description = `Scraping job (${jobId.substring(0,6)}) pending for ${eventData.total_sources_to_track || 'multiple'} sources.`;
        progress = Math.max(progress, 10);
      } else if (eventData.status === 'source_triggered') {
        description = `Scraping job (${jobId.substring(0,6)}): Source ${eventData.source_type || ''} ${eventData.region ? '('+eventData.region+') ' : ''}triggered.`;
        progress = Math.max(progress, (currentActivity?.progress || 5) + 5); // Increment slightly
      } else if (eventData.status === 'source_complete') {
        progress = (eventData.processed_sources && eventData.total_sources_to_track && eventData.total_sources_to_track > 0) ?
                   Math.round((eventData.processed_sources / eventData.total_sources_to_track) * 90) : // Cap at 90 before final completion
                   (currentActivity?.progress || 10);
        progress = Math.max(progress, 10);
        description = `Scraping job (${jobId.substring(0,6)}): ${eventData.processed_sources || 0}/${eventData.total_sources_to_track || '?'} sources completed.`;
        iconKey = 'CircleStackIcon'; // Still in progress
        iconColor = 'text-sky-500';
      } else if (eventData.status === 'no_async_tracking') {
        description = `Scraping job (${jobId.substring(0,6)}): Some sources (e.g., Amazon) tracked separately.`;
        progress = 100; // Assume main part is done for this tracker
        iconKey = 'CheckCircleIcon';
        iconColor = 'text-green-500';
      } else if (eventData.status === 'completed') {
        description = `Scraping job (${jobId.substring(0,6)}) completed successfully.`;
        progress = 100;
        iconKey = 'CheckCircleIcon';
        iconColor = 'text-green-500';
      } else if (eventData.status === 'failed' || eventData.status === 'timeout') {
        description = `Scraping job (${jobId.substring(0,6)}) ${eventData.status}. ${eventData.message || ''}`;
        progress = 100; // Or keep current progress to show where it stalled
        iconKey = 'ExclamationCircleIcon';
        iconColor = eventData.status === 'failed' ? 'text-red-500' : 'text-orange-500';
      } else {
        description = eventData.message || `Scraping job (${jobId.substring(0,6)}) status: ${eventData.status}`;
      }

      this.latestScrapingActivityUpdate = {
        id: `job_${jobId}`, // Consistent unique ID
        type: 'scraping_job',
        status: eventData.status,
        description: description,
        dateObject: new Date().toISOString(),
        progress: Math.min(progress, 100), // Ensure progress doesn't exceed 100
        iconKey: iconKey,
        iconColor: iconColor,
        processedSources: eventData.processed_sources,
        totalSourcesTracked: eventData.total_sources_to_track,
        originalEventData: eventData,
      };
      console.log(`%c[STORE _handleScrapingEvent] latestScrapingActivityUpdate JUST SET. ID: ${this.latestScrapingActivityUpdate.id}, Status: ${this.latestScrapingActivityUpdate.status}, Progress: ${this.latestScrapingActivityUpdate.progress}`, "color: darkgoldenrod; font-weight: bold;");
      
      // General notification update
      if (description) { // Use the generated description for notification
          const notificationType = (iconColor === 'text-red-500' || iconColor === 'text-orange-500') ? 'error' :
                                   (iconColor === 'text-green-500') ? 'success' : 'info';
          const sourceInfo = eventData.source_type ? ` (${eventData.source_type}${eventData.region ? ' - '+eventData.region : ''})` : '';
          // Make notification more concise if it's just a progress update.
          let notificationMessage = (eventData.status === 'source_complete' && (eventData.processed_sources || 0) < (eventData.total_sources_to_track || Infinity)) ?
            `Scraping (${jobId.substring(0,6)})${sourceInfo}: ${eventData.processed_sources}/${eventData.total_sources_to_track} done.` :
            description;
          this.notification = { type: notificationType, message: notificationMessage };
      }

      // Update state for the "focused" scraping job
      if (this.activeScrapingJobId === jobId) {
          this.focusedScrapingProgressMessage = description;
          
          if (['completed', 'failed', 'timeout', 'no_async_tracking'].includes(eventData.status)) {
              this.isScrapingFocusedJob = false;
              if(eventData.status === 'failed' || eventData.status === 'timeout') {
                this.focusedScrapingError = description;
              } else {
                this.focusedScrapingError = null;
              }
              // Do not remove subscription immediately from here.
          } else {
              this.isScrapingFocusedJob = true; // Still in progress
          }
      }
      // If terminal, remove subscription
      if (['completed', 'failed', 'timeout', 'no_async_tracking'].includes(eventData.status)) {
         this._removeSubscription(jobId, 'job');
         if (this.activeScrapingJobId === jobId) this.activeScrapingJobId = null;
      }
    },
    
    // ++ Archetype Generation Actions ++
    async initiateArchetypeGeneration() { 
        this.activeArchetypeTaskId = null;
        this.isGeneratingFocusedArchetype = true;
        this.focusedArchetypeProgressMessage = 'Initiating archetype generation...';
        this.focusedArchetypeGenerationError = null;
        this.notification = { type: 'info', message: 'Archetype generation started...' };

        try {
            const response = await apiClient.post('/archetypes/generate');
            const newTaskId = response.data.task_id;

            if (newTaskId) {
                this.activeArchetypeTaskId = newTaskId;
                this._addSubscription(newTaskId, 'archetype_task'); 
                this.latestArchetypeActivityUpdate = {
                  id: `archetype_${newTaskId}`, 
                  type: 'archetype_generation',
                  status: 'initiated',
                  description: `Archetype generation (task ${newTaskId.substring(0,6)}) initiated...`,
                  dateObject: new Date().toISOString(),
                  progress: 5,
                  iconKey: 'CpuChipIcon',
                  iconColor: 'text-indigo-500',
                };
            } else {
                this.isGeneratingFocusedArchetype = false;
                this.focusedArchetypeGenerationError = response.data.message || 'Could not initiate archetype generation (no task ID).';
                this.notification = { type: 'error', message: this.focusedArchetypeGenerationError || 'Failed to start archetype generation.' };
            }
        } catch (error: any) {
            this.isGeneratingFocusedArchetype = false;
            this.activeArchetypeTaskId = null;
            this.focusedArchetypeGenerationError = error.response?.data?.detail || 'An unexpected error occurred while initiating archetype generation.';
            this.notification = { type: 'error', message: this.focusedArchetypeGenerationError || 'An unexpected error occurred.' };
            console.error("Error initiating archetype generation:", error);
        }
    },

    _handleArchetypeGenerationEvent(taskId: string, eventData: SseEventData) {
        console.log(`%c[STORE _handleArchetypeGenerationEvent ENTRY] ID: ${taskId}, Event Status: ${eventData.status}`, "color: #9370DB; font-weight: bold;");
        let description = eventData.message || `Archetype generation (${taskId.substring(0,6)}) updated.`;
        let iconKey = 'CpuChipIcon';
        let iconColor = 'text-indigo-500';
        let progress = 10;

        const currentActivity = this.latestArchetypeActivityUpdate?.id === `archetype_${taskId}` ? this.latestArchetypeActivityUpdate : null;
        progress = currentActivity?.progress || 5;

        switch (eventData.status) {
            case 'starting': progress = Math.max(progress, 10); break;
            case 'fetching_reviews': progress = Math.max(progress, 25); break;
            case 'reviews_fetched': progress = Math.max(progress, 40); break;
            case 'generating_archetypes': progress = Math.max(progress, 70); break;
            case 'archetypes_generated': progress = Math.max(progress, 85); break;
            case 'saving_archetypes': progress = Math.max(progress, 95); break;
            case 'completed':
                progress = 100;
                iconKey = 'CheckCircleIcon';
                iconColor = 'text-purple-500';
                description = eventData.message || `Archetype generation (${taskId.substring(0,6)}) completed.`;
                
                // This is a task-specific completion. Update relevant states.
                if (eventData.brand_name) { // brand_name should be in the eventData on completion
                    this.lastSuccessfullyGeneratedArchetype = { taskId, brandName: eventData.brand_name };
                    // Also trigger the general brand refresh signal
                    this.archetypesLastRefreshedForBrand = {
                        brandName: eventData.brand_name,
                        timestamp: Date.now(),
                        taskId: taskId // Mark that this refresh was due to this specific task
                    };
                     console.log(`%c[STORE _handleArchetypeGenerationEvent] archetypesLastRefreshedForBrand updated by task ${taskId} completion. Brand: ${eventData.brand_name}`, "color: green;");
                }
                break;
            case 'failed':
                progress = 100; 
                iconKey = 'ExclamationCircleIcon';
                iconColor = 'text-red-500';
                description = eventData.message || eventData.error || `Archetype generation (${taskId.substring(0,6)}) failed.`;
                break;
            default:
                 progress = currentActivity?.progress || 10;
        }

        this.latestArchetypeActivityUpdate = {
            id: `archetype_${taskId}`, 
            type: 'archetype_generation',
            status: eventData.status,
            description: description,
            dateObject: new Date().toISOString(),
            progress: Math.min(progress, 100),
            iconKey: iconKey,
            iconColor: iconColor,
            brandName: eventData.brand_name || this.currentUserBrandName || undefined, 
            originalEventData: eventData,
        };
        if (this.latestArchetypeActivityUpdate) {
          console.log(`%c[STORE _handleArchetypeGenerationEvent] latestArchetypeActivityUpdate JUST SET. ID: ${this.latestArchetypeActivityUpdate.id}, Status: ${this.latestArchetypeActivityUpdate.status}, Progress: ${this.latestArchetypeActivityUpdate.progress}`, "color: purple; font-weight: bold;");
        }

        if (description) {
             const notificationType = (iconColor === 'text-red-500') ? 'error' :
                                     (iconColor === 'text-purple-500' && progress === 100) ? 'success' : 'info';
            this.notification = { type: notificationType, message: `Archetypes (${taskId.substring(0,6)}): ${description}` };
        }

        if (this.activeArchetypeTaskId === taskId) {
            this.focusedArchetypeProgressMessage = description;
            if (!['completed', 'failed'].includes(eventData.status)) {
                this.isGeneratingFocusedArchetype = true;
            } else {
                this.isGeneratingFocusedArchetype = false;
                 if (eventData.status === 'failed') {
                    this.focusedArchetypeGenerationError = description;
                } else {
                    this.focusedArchetypeGenerationError = null;
                }
            }
        }
      if (['completed', 'failed'].includes(eventData.status)) {
         this._removeSubscription(taskId, 'archetype_task');
         if (this.activeArchetypeTaskId === taskId) this.activeArchetypeTaskId = null;
      }
    },

    // --- NEW Handler for brand-wide archetype refresh events ---
    _handleArchetypeBrandRefreshEvent(eventKey: string, eventData: SseEventData) {
        // eventKey is like 'brand_archetype_update_mybrand'
        // eventData is { status: "updated", brand_name: "MyBrand", message: "..." }
        console.log(`%c[STORE _handleArchetypeBrandRefreshEvent] Key: ${eventKey}, Brand: ${eventData.brand_name}`, "color: cyan; font-weight: bold;");

        if (eventData.brand_name && eventData.brand_name === this.currentUserBrandName) {
            // Update for the current user's brand
            const now = Date.now();
            // Only update if it's a genuinely new refresh signal
            if (!this.archetypesLastRefreshedForBrand || this.archetypesLastRefreshedForBrand.timestamp < now - 1000) { // Buffer to avoid rapid updates from same source
                this.archetypesLastRefreshedForBrand = {
                    brandName: eventData.brand_name,
                    timestamp: now,
                    // No specific taskId, as this is a general brand update not tied to a task *this client* initiated
                };
                this.notification = { type: 'info', message: eventData.message || `Archetypes for your brand '${eventData.brand_name}' have been updated.` };
                
                this.latestArchetypeActivityUpdate = {
                    id: `archetype_refresh_${eventData.brand_name}_${now}`, 
                    type: 'archetype_generation', 
                    status: 'updated', 
                    description: eventData.message || `Archetypes for brand ${eventData.brand_name} were refreshed.`,
                    dateObject: new Date().toISOString(),
                    progress: 100, 
                    iconKey: 'SparklesIcon', 
                    iconColor: 'text-yellow-500',
                    brandName: eventData.brand_name,
                };
                console.log(`%c[STORE] archetypesLastRefreshedForBrand updated due to BRAND REFRESH event. Brand: ${this.currentUserBrandName}, Timestamp: ${now}`, "color: green;");
            } else {
                console.log(`%c[STORE] archetypesLastRefreshedForBrand - Brand refresh event for ${eventData.brand_name} too close to previous or identical. Skipping.`, "color: orange;");
            }
        } else if (eventData.brand_name) {
            console.log(`%c[STORE] Received archetype_brand_refresh for OTHER brand: ${eventData.brand_name}. Current user brand: ${this.currentUserBrandName}. Ignoring for direct reload signal.`, "color: gray;");
        }
    },

    // This method is called by the central SSE handler when an 'amazon_discovery_update' event comes in.
    // The `id` parameter here is the discovery_task_id we are subscribed to.
    _handleAmazonDiscoveryEvent(id: string, eventData: SseEventData) {
      console.log(`%c[STORE _handleAmazonDiscoveryEvent] Received for task_id: ${id}`, "color: orange; font-weight: bold;", eventData);

      // const snapshotId = eventData.snapshot_id; // The snapshot_id is in the event payload
      let description = eventData.message || `Processing discovery...`;
      let progress = 50;
      let iconKey = 'ArrowPathIcon';
      let iconColor = 'text-blue-500';
      let notificationType: 'info' | 'success' | 'error' | 'warning' = 'info';

      this.amazonDiscoveryStatusMessage = description;

      if (eventData.status === 'processing' || eventData.status === 'triggered') {
        progress = 25;
        this.isDiscoveringAmazonProducts = false; // The trigger is done
        this.isLoadingDiscoveredAmazonProducts = true; // Now we are waiting
      } else if (eventData.status === 'completed') {
        progress = 100;
        description = eventData.message || `Discovery completed successfully.`;
        iconKey = 'CheckCircleIcon';
        iconColor = 'text-green-500';
        notificationType = 'success';
        
        const products = (eventData as any).products || [];
        this.amazonDiscoveredProducts = products.map((p: any) => ({
          ...p,
          scrapeTargets: { amazon: true, druni: false }
        }));
        
        this.isLoadingDiscoveredAmazonProducts = false;
        this.isDiscoveringAmazonProducts = false;
        this.amazonDiscoveryCompletedTaskId = id; 

      } else if (eventData.status === 'failed') {
        progress = 100;
        description = eventData.error_detail || eventData.message || `Discovery failed.`;
        iconKey = 'XCircleIcon';
        iconColor = 'text-red-500';
        notificationType = 'error';
        
        this.amazonDiscoveryError = description;
        this.isLoadingDiscoveredAmazonProducts = false;
        this.isDiscoveringAmazonProducts = false;
        this.amazonDiscoveryErrorTaskId = id;
      }

      // Update the generic activity tracker
      if (id) {
          this.latestDiscoveryActivityUpdate = {
            id: id, // Use the task_id as the unique identifier for the activity
            type: 'discovery_job',
            status: eventData.status,
            description: description,
            dateObject: new Date().toISOString(),
            progress: progress,
            iconKey: iconKey,
            iconColor: iconColor,
            originalEventData: eventData,
          };
      }
    },

    setAmazonDiscoveryResultsReady(snapshotId: string) {
      this.isDiscoveringAmazonProducts = false;
      this.isLoadingDiscoveredAmazonProducts = false;
      this.amazonDiscoveredProducts = [];
      this.amazonDiscoveryStatusMessage = null;
      this.amazonDiscoveryError = null;
      this.amazonDiscoveryCompletedTaskId = null;
      this.amazonDiscoveryErrorTaskId = null;
      this.amazonDiscoveryResultsReadySnapshotId = snapshotId;
      this.amazonDiscoveryErrorSnapshotId = null;
      this.amazonDiscoveryErrorMessage = null;
    },

    // Add this new action for Amazon Product Discovery
    async initiateAmazonProductDiscovery(brandName: string, country: string): Promise<string | null> {
      this.clearAmazonDiscoveryStates(); // Clear previous state
      this.isDiscoveringAmazonProducts = true; // Set loading state immediately

      try {
        const response = await apiClient.post('/amazon/brightdata/discover-products', { 
          brand_name: brandName,
          country: country 
        });
        const discoveryTaskId = response.data.discovery_task_id;

        if (discoveryTaskId) {
          this.notification = { type: 'info', message: `Amazon discovery process initiated for '${brandName}' in ${country}.` };
          this._addSubscription(discoveryTaskId, 'discovery'); // Subscribe to SSE with the task ID
          
          return discoveryTaskId;
        } else {
          this.isDiscoveringAmazonProducts = false;
          const errorMessage = response.data.message || 'Could not initiate Amazon discovery (no task ID received).';
          this.notification = { type: 'error', message: errorMessage };
          this.amazonDiscoveryError = errorMessage;
          console.error("Error initiating Amazon discovery:", errorMessage);
          return null;
        }
      } catch (error: any) {
        this.isDiscoveringAmazonProducts = false;
        const detail = error.response?.data?.detail || error.message || 'An unexpected error occurred while triggering Amazon discovery.';
        this.notification = { type: 'error', message: `Amazon Discovery Error: ${detail}` };
        this.amazonDiscoveryError = detail;
        console.error("Error initiating Amazon product discovery:", error);
        return null;
      }
    },

    // This action handles the result of a manual product lookup (different from keyword discovery)
    async initiateManualProductLookup(identifiers: string[], country: string): Promise<string | null> {
      if (this.isPerformingManualLookup) {
        this.notification = { type: 'warning', message: 'A manual product lookup is already in progress.' };
        return null;
      }
      // State resets are now handled cleanly within _addSubscription
      
      try {
        const response = await apiClient.post('/products/manual-lookup/trigger', { 
          identifiers,
          country 
        });
        if (response.data && response.data.task_id) {
          const taskId = response.data.task_id;
          this._addSubscription(taskId, 'manual_lookup'); // This will now correctly set state and trigger SSE update
          this.notification = { type: 'info', message: `Product lookup started. You'll be notified.` };
          return taskId;
        } else {
          this.manualLookupError = "Failed to start manual product lookup: No Task ID received from server.";
          this.notification = { type: 'error', message: this.manualLookupError };
          return null;
        }
      } catch (error: any) {
        console.error("Error initiating manual product lookup:", error);
        this.manualLookupError = error.response?.data?.detail || "An error occurred trying to start product lookup.";
        this.notification = { type: 'error', message: this.manualLookupError || 'An error occurred.' };
        this.activeManualLookupTaskId = null; // Clear on error
        return null;
      }
    },

    _handleManualLookupEvent(taskId: string, eventData: SseEventData) {
      if (this.activeManualLookupTaskId !== taskId) {
        // console.log(`[SSE ManualLookup] Event for non-active task ${taskId}. Current: ${this.activeManualLookupTaskId}`);
        return; // Ignore events for tasks not currently active in the store's focus
      }
      
      this.manualLookupStatusMessage = eventData.message || this.manualLookupStatusMessage;

      if (eventData.status === 'failed') {
        this.manualLookupError = eventData.error || 'Manual lookup failed.';
        this.manualLookupErrorTaskId = taskId;
        this.manualLookupLastErrorMessage = this.manualLookupError;
        this.notification = { type: 'error', message: this.manualLookupError };
        // Optionally, call _removeSubscription here if we don't expect more updates
        // this._removeSubscription(snapshotId, 'manual_lookup'); 
        // For now, keep subscription to see if backend sends a final "cleaned_up" or similar.
      } else if (eventData.status === 'completed' || eventData.status === 'completed_empty') {
        this.manualLookupProducts = (eventData as any).products || [];
        this.manualLookupResultsReadyTaskId = taskId;
        this.manualLookupStatusMessage = eventData.message || `Lookup for ${taskId.substring(0,8)} completed.`;
        const messageType = eventData.status === 'completed_empty' ? 'warning' : 'success';
        const messageText = eventData.status === 'completed_empty' 
            ? (eventData.message || `Lookup for ${taskId.substring(0,8)} completed, but no products found.`)
            : (eventData.message || `Product data ready for ${taskId.substring(0,8)}.`);
        this.notification = { type: messageType, message: messageText };
        // Don't remove subscription immediately; user might re-trigger or another component might need status.
        // Frontend component will fetch results upon seeing manualLookupResultsReadyTaskId.
      } else if (eventData.status === 'triggered') {
         // Already handled by the initial API call response mostly
         this.manualLookupStatusMessage = eventData.message || `Lookup for ${taskId.substring(0,8)} is running...`;
      }
      // Potentially add other statuses like 'processing_download', 'mapping_data' if backend sends them
    },
    
    clearManualLookupStates() {
        if (this.activeManualLookupTaskId) {
            this._removeSubscription(this.activeManualLookupTaskId, 'manual_lookup');
        }
        this.activeManualLookupTaskId = null;
        this.manualLookupStatusMessage = null;
        this.manualLookupError = null;
        this.manualLookupResultsReadyTaskId = null;
        this.manualLookupErrorTaskId = null;
        this.manualLookupLastErrorMessage = null;
        this.manualLookupProducts = [];
    },

    // --- NEW: Handle Trustpilot Discovery Events ---
    _handleTrustpilotDiscoveryEvent(taskId: string, eventData: any) {
        if (this.activeTrustpilotDiscoveryTaskId !== taskId) {
            return; // Not the discovery task we're currently tracking.
        }

        const { status, message, urls, error } = eventData;

        switch (status) {
            case 'started':
                this.isDiscoveringTrustpilotUrls = true;
                this.trustpilotDiscoveryError = null;
                this.trustpilotDiscoveredUrls = [];
                this.notification = { type: 'info', message: message || `Trustpilot discovery process started.` };
                break;
            case 'completed':
                this.isDiscoveringTrustpilotUrls = false;
                // Ensure urls is an array before assigning
                this.trustpilotDiscoveredUrls = Array.isArray(urls) ? urls.map((url: string) => ({ url })) : [];
                this.notification = { type: 'success', message: message || 'Trustpilot discovery finished successfully.' };
                this._removeSubscription(taskId, 'trustpilot_discovery'); // Unsubscribe after completion
                break;
            case 'failed':
                this.isDiscoveringTrustpilotUrls = false;
                this.trustpilotDiscoveryError = error || 'An unknown error occurred during Trustpilot discovery.';
                this.notification = { type: 'error', message: this.trustpilotDiscoveryError || 'An error occurred.' };
                this._removeSubscription(taskId, 'trustpilot_discovery'); // Unsubscribe after failure
                break;
            default:
                // We can also handle other statuses like 'progress' if the backend sends them
                break;
        }
    },

    // --- NEW: Trustpilot URL Discovery Action ---
    async initiateTrustpilotUrlDiscovery(brandName: string, country: string): Promise<string | null> {
        this.isDiscoveringTrustpilotUrls = true;
        this.trustpilotDiscoveryError = null;
        this.trustpilotDiscoveredUrls = [];
        this.activeTrustpilotDiscoveryTaskId = null;

        try {
            const response = await apiClient.post('/trustpilot/discover', {
                brand_name: brandName,
                country: country,
            });

            if (response.data && response.data.discovery_task_id) {
                const taskId = response.data.discovery_task_id;
                this._addSubscription(taskId, 'trustpilot_discovery');
                this.notification = { type: 'info', message: `Trustpilot discovery for "${brandName}" started.` };
                return taskId;
            } else {
                const errorMsg = 'Failed to start Trustpilot discovery: No task ID received.';
                this.trustpilotDiscoveryError = errorMsg;
                this.notification = { type: 'error', message: errorMsg };
                this.isDiscoveringTrustpilotUrls = false;
                return null;
            }
        } catch (error: any) {
            console.error("Error initiating Trustpilot URL discovery:", error);
            const errorMsg = error.response?.data?.detail || "An unexpected error occurred while starting Trustpilot discovery.";
            this.trustpilotDiscoveryError = errorMsg;
            this.notification = { type: 'error', message: errorMsg };
            this.isDiscoveringTrustpilotUrls = false;
            return null;
        }
    },

    // --- NEW: Handle TripAdvisor Discovery Events ---
    _handleTripadvisorDiscoveryEvent(taskId: string, eventData: any) {
        if (this.activeTripadvisorDiscoveryTaskId !== taskId) {
            return; // Not the discovery task we're currently tracking.
        }

        const { status, message, urls, error } = eventData;

        switch (status) {
            case 'started':
                this.isDiscoveringTripadvisorUrls = true;
                this.tripadvisorDiscoveryError = null;
                this.tripadvisorDiscoveredUrls = [];
                this.notification = { type: 'info', message: message || `TripAdvisor discovery process started.` };
                break;
            case 'completed':
                this.isDiscoveringTripadvisorUrls = false;
                // Ensure urls is an array before assigning
                this.tripadvisorDiscoveredUrls = Array.isArray(urls) ? urls.map((url: string) => ({ url })) : [];
                this.notification = { type: 'success', message: message || 'TripAdvisor discovery finished successfully.' };
                this._removeSubscription(taskId, 'tripadvisor_discovery'); // Unsubscribe after completion
                break;
            case 'failed':
                this.isDiscoveringTripadvisorUrls = false;
                this.tripadvisorDiscoveryError = error || 'An unknown error occurred during TripAdvisor discovery.';
                this.notification = { type: 'error', message: this.tripadvisorDiscoveryError || 'An error occurred.' };
                this._removeSubscription(taskId, 'tripadvisor_discovery'); // Unsubscribe after failure
                break;
            default:
                // We can also handle other statuses like 'progress' if the backend sends them
                break;
        }
    },

    // --- NEW: Action to initiate TripAdvisor URL Discovery ---
    async initiateTripadvisorUrlDiscovery(brandName: string, country: string): Promise<string | null> {
        this.isDiscoveringTripadvisorUrls = true;
        this.tripadvisorDiscoveryError = null;
        this.tripadvisorDiscoveredUrls = [];
        this.activeTripadvisorDiscoveryTaskId = null;

        try {
            const response = await apiClient.post('/tripadvisor/discover', {
                brand_name: brandName,
                country: country,
            });

            if (response.data && response.data.discovery_task_id) {
                const taskId = response.data.discovery_task_id;
                this._addSubscription(taskId, 'tripadvisor_discovery');
                this.notification = { type: 'info', message: `TripAdvisor discovery for "${brandName}" started.` };
                return taskId;
            } else {
                const errorMsg = 'Failed to start TripAdvisor discovery: No task ID received.';
                this.tripadvisorDiscoveryError = errorMsg;
                this.notification = { type: 'error', message: errorMsg };
                this.isDiscoveringTripadvisorUrls = false;
                return null;
            }
        } catch (error: any) {
            console.error("Error initiating TripAdvisor URL discovery:", error);
            const errorMsg = error.response?.data?.detail || "An unexpected error occurred while starting TripAdvisor discovery.";
            this.tripadvisorDiscoveryError = errorMsg;
            this.notification = { type: 'error', message: errorMsg };
            this.isDiscoveringTripadvisorUrls = false;
            return null;
        }
    },

    // --- Google Places Discovery Actions ---
    clearGooglePlacesDiscoveryState() {
      this.isDiscoveringGooglePlaces = false;
      this.googlePlacesDiscoveryError = null;
      this.googlePlacesDiscoveredResults = [];
      this.googlePlacesDiscoveryMessage = null;
      this.googlePlacesDiscoveryCompleted = false;
      if (this.activeGooglePlacesDiscoveryTaskId) {
        // DO NOT remove the subscription here. A new search will create a new subscription
        // which will trigger a single, clean SSE reconnection. This prevents a race condition.
        this.activeGooglePlacesDiscoveryTaskId = null;
      }
    },

    _handleGooglePlacesDiscoveryEvent(taskId: string, eventData: any) {
      if (this.activeGooglePlacesDiscoveryTaskId !== taskId) return;

      this.googlePlacesDiscoveryMessage = eventData.message || this.googlePlacesDiscoveryMessage;

      switch (eventData.status) {
        case 'processing':
          this.isDiscoveringGooglePlaces = true;
          this.googlePlacesDiscoveryCompleted = false;
          break;
        case 'completed':
          this.isDiscoveringGooglePlaces = false;
          this.googlePlacesDiscoveryCompleted = true;
          this.googlePlacesDiscoveredResults = eventData.results || [];
          if (eventData.results.length === 0) {
              this.googlePlacesDiscoveryError = "Search completed, but no locations were found."
              this.notification = { type: 'info', message: eventData.message || 'Search finished, but no locations were found.' };
          } else {
              this.notification = { type: 'success', message: eventData.message || `Successfully found ${eventData.results.length} locations.` };
          }
          // Unsubscribe after completion
          this._removeSubscription(taskId, 'google_places_discovery');
          break;
        case 'failed':
          this.isDiscoveringGooglePlaces = false;
          this.googlePlacesDiscoveryCompleted = true;
          this.googlePlacesDiscoveryError = eventData.error || 'An unknown error occurred during Google Places discovery.';
          this.notification = { type: 'error', message: this.googlePlacesDiscoveryError || 'An error occurred.' };
          // Unsubscribe after failure
          this._removeSubscription(taskId, 'google_places_discovery');
          break;
      }
    },

    async initiateGooglePlacesDiscovery(payload: any): Promise<string | null> {
      this.clearGooglePlacesDiscoveryState();
      this.isDiscoveringGooglePlaces = true;
      this.googlePlacesDiscoveryMessage = 'Initiating Google Places search...';

      try {
        const response = await apiClient.post('/reviews/google/places', payload);
        if (response.data && response.data.discovery_task_id) {
          const taskId = response.data.discovery_task_id;
          // this.activeGooglePlacesDiscoveryTaskId = taskId; // DO NOT set it here. Let _addSubscription handle it.
          this._addSubscription(taskId, 'google_places_discovery');
          return taskId;
        } else {
          throw new Error('Invalid response from server when initiating Google Places discovery.');
        }
      } catch (error: any) {
        console.error("Error initiating Google Places discovery:", error);
        this.googlePlacesDiscoveryError = error.response?.data?.detail || 'Failed to start Google Places search task.';
        this.isDiscoveringGooglePlaces = false;
        this.notification = { type: 'error', message: this.googlePlacesDiscoveryError || 'An error occurred.' };
        return null;
      }
    },

    async fetchGooglePlaceSuggestions(payload: any): Promise<any[] | null> {
        this.googlePlacesDiscoveryError = null;
        try {
            // This reuses the same endpoint but we handle the response directly
            const response = await apiClient.post('/reviews/google/places', payload);

            // Since this is for suggestions, the backend should return data directly now.
            // Let's assume the fix was on the backend to return an array for this specific use case,
            // or the component needs to be adapted to the task_id flow for suggestions too.
            // Let's modify the component to use the task_id flow for suggestions as well.
            // Okay, let's assume the backend returns an array directly for now to simplify.
            // Re-reading my changes, the backend returns a task_id now. The component must adapt.
            // I'll make this action also use the async flow.
            
            const taskId = await this.initiateGooglePlacesDiscovery(payload);
            if (taskId) {
              return [];
            }
            return null;
        } catch (error: any) {
            this.googlePlacesDiscoveryError = error.response?.data?.detail || 'Failed to fetch suggestions.';
            return null;
        }
    },

    clearAmazonDiscoveryStates() {
      this.isDiscoveringAmazonProducts = false;
      this.isLoadingDiscoveredAmazonProducts = false;
      this.amazonDiscoveredProducts = [];
      this.amazonDiscoveryStatusMessage = null;
      this.amazonDiscoveryError = null;
      this.amazonDiscoveryCompletedTaskId = null;
      this.amazonDiscoveryErrorTaskId = null;
      this.amazonDiscoveryResultsReadySnapshotId = null;
      this.amazonDiscoveryErrorSnapshotId = null;
      this.amazonDiscoveryErrorMessage = null;
    },

    unsubscribeFromActivity(id: string, type: 'task' | 'job' | 'archetype_task' | 'discovery') { 
      this._removeSubscription(id, type);
      if (type === 'task' && this.activeReportTaskId === id) {
        this.activeReportTaskId = null;
        this.isGeneratingFocusedReport = false;
      } else if (type === 'job' && this.activeScrapingJobId === id) {
        this.activeScrapingJobId = null;
        this.isScrapingFocusedJob = false;
      } else if (type === 'archetype_task' && this.activeArchetypeTaskId === id) { 
        this.activeArchetypeTaskId = null;
        this.isGeneratingFocusedArchetype = false;
      } else if (type === 'discovery' && id === this.amazonDiscoveryResultsReadySnapshotId) {
        this.clearAmazonDiscoveryStates();
      } else if (type === 'discovery' && id === this.amazonDiscoveryErrorSnapshotId) {
        this.clearAmazonDiscoveryStates();
      }
    },
  },
})
