<script setup lang="ts">
import { ref, onMounted, computed } from 'vue' // Add computed
import { useRoute, useRouter } from 'vue-router'
// import axios from 'axios' // REMOVE THIS LINE
import apiClient from '@/services/axiosInstance' // ADD THIS LINE
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import {
  ArrowLeftIcon,
  CalendarIcon,
  UserGroupIcon,
  DocumentTextIcon,
  GlobeEuropeAfricaIcon,
  ChartBarIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  ChevronRightIcon, // Icon for section headers
  BeakerIcon, // For methodology
  LightBulbIcon, // For findings/analysis
  CheckCircleIcon, // For recommendations/conclusion
  ClipboardDocumentListIcon, // Default icon
  ShoppingCartIcon // Added for consistency if needed
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()

const reportDetails = ref<any>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)

const reportId = ref<string | null>(null)

// --- Helper Functions (formatDate, formatRelativeTime remain the same) ---
const formatDate = (dateString: string | undefined) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric'
    })
  } catch (e) {
    return 'Invalid Date'
  }
}

const formatRelativeTime = (timestamp: string | null | undefined) => {
  if (!timestamp) return 'Date unavailable';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);

    if (years > 0) return `${years} year${years > 1 ? 's' : ''} ago`;
    if (months > 0) return `${months} month${months > 1 ? 's' : ''} ago`;
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
  } catch (e) {
    console.error("Error formatting relative time:", e);
    return 'Invalid date';
  }
}

// --- NEW: Section Styling Logic ---
const sectionStylingMap = {
  // Keywords should be lowercase
  summary: { icon: DocumentTextIcon, classes: 'bg-blue-50 border-blue-200 text-blue-800', iconColor: 'text-blue-600' },
  methodology: { icon: BeakerIcon, classes: 'bg-indigo-50 border-indigo-200 text-indigo-800', iconColor: 'text-indigo-600' },
  findings: { icon: LightBulbIcon, classes: 'bg-yellow-50 border-yellow-200 text-yellow-800', iconColor: 'text-yellow-600' },
  results: { icon: LightBulbIcon, classes: 'bg-yellow-50 border-yellow-200 text-yellow-800', iconColor: 'text-yellow-600' },
  analysis: { icon: ChartBarIcon, classes: 'bg-purple-50 border-purple-200 text-purple-800', iconColor: 'text-purple-600' },
  recommendations: { icon: CheckCircleIcon, classes: 'bg-emerald-50 border-emerald-200 text-emerald-800', iconColor: 'text-emerald-600' },
  conclusion: { icon: CheckCircleIcon, classes: 'bg-emerald-50 border-emerald-200 text-emerald-800', iconColor: 'text-emerald-600' },
  default: { icon: ClipboardDocumentListIcon, classes: 'bg-white border-border text-text-primary', iconColor: 'text-gray-500' } // Fallback
}

function getSectionStyle(title: string) {
  const lowerTitle = title.toLowerCase();
  for (const key in sectionStylingMap) {
    if (key !== 'default' && lowerTitle.includes(key)) {
      return sectionStylingMap[key];
    }
  }
  return sectionStylingMap.default;
}

// --- HTML Parsing Logic ---
const parsedSections = computed(() => {
  if (!reportDetails.value?.html_content) return [];
  
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(reportDetails.value.html_content, 'text/html');
    
    const mainContainer = doc.querySelector('body > div.max-w-5xl');
    if (!mainContainer) {
      console.warn("Could not find main container div (body > div.max-w-5xl) in HTML content. Report parsing might be incomplete.");
      // Attempt to parse sections directly from body if main container is missing, though this is less ideal
      const bodySections = doc.querySelectorAll('body section');
      if (bodySections.length > 0) {
        
        return extractSectionsFromSectionElements(bodySections);
      }
      console.error("No main container and no section tags found in body.");
      return [{ title: "Content Error", content: "<p>Report structure not recognized.</p>" }];
    }

    const sections = [];
    // Strategy 1: Look for H2 elements as direct children of mainContainer (Claude's direct output)
    const h2TitleNodes = mainContainer.querySelectorAll(':scope > h2');
    

    if (h2TitleNodes.length > 0) {
      h2TitleNodes.forEach((titleNode, index) => {
        const titleText = titleNode.textContent?.replace(/^\d+\.\s*/, '').trim() || `Section ${index + 1}`;
        let contentHTML = '';
        let currentNode = titleNode.nextElementSibling;
        
        // Collect all sibling elements until the next H2 or the end of mainContainer
        while (currentNode && currentNode.tagName !== 'H2') {
          contentHTML += currentNode.outerHTML;
          currentNode = currentNode.nextElementSibling;
        }
        
        sections.push({ title: titleText, content: contentHTML });
        
      });
    } else {
      // Strategy 2: Fallback if no H2s are direct children.
      // Look for <section> tags generated by Python's render_html_report (when titles were provided).
      const sectionElements = mainContainer.querySelectorAll(':scope > section');
      
      if (sectionElements.length > 0) {
        return extractSectionsFromSectionElements(sectionElements);
      } else {
        // If no H2s and no <section> tags, the content is unstructured or unexpected.
        console.warn("No H2 titles or <section> tags found as direct children of mainContainer. The report content might be flat or not structured as expected for section parsing.");
        // Optionally, you could return the entire mainContainer.innerHTML as a single section
        // return [{ title: "Full Report Content", content: mainContainer.innerHTML }];
        // For now, returning empty array will trigger the "Could not find structured sections..." message
      }
    }
    
    if (sections.length === 0 && reportDetails.value.html_content) {
      console.warn("Parsing logic resulted in zero sections. The UI will show 'Could not find structured sections'.");
    }
    return sections;

  } catch (e) {
    console.error("Error parsing HTML content:", e);
    return [{ title: "Parsing Error", content: `<p>Could not parse the report content. Error: ${e.message}</p>` }];
  }
});

// Helper function to extract from <section> elements
function extractSectionsFromSectionElements(sectionNodes: NodeListOf<Element>) {
    const sections = [];
    sectionNodes.forEach((sectionNode, index) => {
        const titleElement = sectionNode.querySelector('h2');
        // Corrected content selector: look for div.prose (common in Tailwind for articles)
        // or be more generic if prose is not always there.
        // Let's try a more specific selector first, then a more general one.
        let contentElement = sectionNode.querySelector('div.prose'); 
        if (!contentElement) {
            // Fallback to any div that is a direct child and not containing the h2
            const directDivs = Array.from(sectionNode.children).filter(child => child.tagName === 'DIV' && !child.contains(titleElement));
            if (directDivs.length > 0) {
                contentElement = directDivs[0]; // Take the first suitable div
            }
        }
        
        const titleText = titleElement?.textContent?.replace(/^\d+\.\s*/, '').trim() || `Section ${index + 1}`;
        
        if (contentElement) {
            sections.push({ 
                title: titleText, 
                content: contentElement.innerHTML 
            });
            
        } else if (titleElement) { // Has a title but no clear content div
             let contentHTML = '';
             let currentNode = titleElement.nextElementSibling;
             while (currentNode) {
                 contentHTML += currentNode.outerHTML;
                 currentNode = currentNode.nextElementSibling;
             }
             sections.push({ title: titleText, content: contentHTML || '<p>Content not clearly demarcated.</p>' });
             console.warn(`Extracted section (from <section> tag, title only): ${titleText}. Content div not found, took siblings of H2.`);
        } else {
            console.warn(`Could not extract title or standard content div for <section> ${index + 1}. Using full innerHTML of section.`);
            sections.push({ 
                title: `Unnamed Section ${index + 1}`, 
                content: sectionNode.innerHTML 
            });
        }
    });
    return sections;
}

// --- Data Fetching Logic (remains the same) ---
async function fetchReportDetail() {
  isLoading.value = true
  error.value = null
  reportDetails.value = null

  reportId.value = route.params.reportId as string;

  if (!reportId.value) {
    error.value = "Report ID not found in URL."
    isLoading.value = false
    return
  }

  try {
    const token = sessionStorage.getItem('token')
    if (!token) {
      error.value = "Authentication required."
      isLoading.value = false
      router.push('/login') // Redirect to login if no token
      return
    }

    
    const response = await apiClient.get(`/reports/generated/${reportId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    
    if (response.data && response.data._id) {
        reportDetails.value = response.data;
    } else {
        throw new Error("Report data is missing or invalid.");
    }

  } catch (err: any) {
    console.error("Error loading report details:", err)
    if (err.response && err.response.status === 404) {
        error.value = "Report not found or you do not have permission to view it.";
    } else if (err.response && err.response.data && err.response.data.detail) {
      error.value = `Failed to load report: ${err.response.data.detail}`
    } else {
      error.value = 'An unexpected error occurred while loading the report.'
    }
    if (err.response && err.response.status === 401) {
         router.push('/login'); 
    }
  } finally {
    isLoading.value = false
  }
}

// --- Lifecycle Hook (remains the same) ---
onMounted(() => {
  fetchReportDetail()
})

</script>

<template>
  <div class="space-y-6 pb-10">
    <!-- Back Button (remains the same) -->
    <button 
      @click="router.back()" 
      class="inline-flex items-center px-3 py-1.5 text-sm text-text-secondary bg-surface hover:bg-background border border-border rounded-md transition-colors duration-200">
      <ArrowLeftIcon class="h-4 w-4 mr-1.5" />
      Back to Reports
    </button>

    <!-- Loading State (remains the same) -->
    <div v-if="isLoading" class="text-center py-16">
      <ArrowPathIcon class="h-10 w-10 text-primary animate-spin mx-auto mb-4" />
      <p class="text-lg text-text-secondary">Loading Report Details...</p>
    </div>

    <!-- Error State (remains the same) -->
    <div v-else-if="error" class="bg-red-50 border border-red-300 rounded-lg p-6 text-center shadow-sm">
      <ExclamationCircleIcon class="h-12 w-12 text-red-500 mx-auto mb-3" />
      <p class="text-xl font-semibold text-red-700 mb-2">Error Loading Report</p>
      <p class="text-red-600">{{ error }}</p>
    </div>

    <!-- Report Content -->
    <div v-else-if="reportDetails" class="space-y-6">
      
      <!-- Report Header Card (remains similar) -->
      <div class="bg-white rounded-2xl shadow-sm border border-border p-6">
        <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
          <div>
            <h1 class="text-2xl font-display font-bold text-text-primary mb-1">
              Report: {{ reportDetails.report_type?.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'N/A' }}
            </h1>
            <p class="text-text-secondary">
              Analysis focusing on: {{ reportDetails.archetype_identifier || 'General Population' }}
            </p>
          </div>
          <div class="text-sm text-text-secondary text-right flex-shrink-0">
            <div class="flex items-center justify-end space-x-1">
              <CalendarIcon class="h-4 w-4" />
              <span>Generated: {{ formatRelativeTime(reportDetails.generated_at) }}</span> 
            </div>
             <span class="text-xs">({{ formatDate(reportDetails.generated_at) }})</span>
          </div>
        </div>
        
         <!-- Filters Applied (remains similar) -->
         <div class="mt-4 pt-4 border-t border-border flex flex-wrap gap-x-6 gap-y-2 text-sm text-text-secondary">
            <!-- Filters display logic here... -->
             <div v-if="reportDetails.filters?.sources?.length" class="flex items-center space-x-1.5">
                 <ChartBarIcon class="h-4 w-4" />
                 <span>Sources: <strong>{{ reportDetails.filters.sources.join(', ') }}</strong></span>
             </div>
             <div v-if="reportDetails.filters?.countries?.length" class="flex items-center space-x-1.5">
                 <GlobeEuropeAfricaIcon class="h-4 w-4" />
                 <span>Countries: 
                    <span v-for="(country, index) in reportDetails.filters.countries" :key="country">
                        <span :class="`fi fi-${country.toLowerCase()}`" :title="country"></span>{{ index < reportDetails.filters.countries.length - 1 ? ' ' : '' }}
                    </span>
                 </span>
             </div>
             <div v-if="reportDetails.filters?.start_date || reportDetails.filters?.end_date" class="flex items-center space-x-1.5">
                 <CalendarIcon class="h-4 w-4" />
                 <span>Date Range: <strong>{{ formatDate(reportDetails.filters.start_date) }} - {{ formatDate(reportDetails.filters.end_date) }}</strong></span>
             </div>
             <div v-if="reportDetails.filters?.products?.length" class="flex items-center space-x-1.5">
                 <ShoppingCartIcon class="h-4 w-4" /> <!-- Assuming ShoppingCartIcon is imported -->
                 <span>Products: <strong>{{ reportDetails.filters.products.join(', ') }}</strong></span>
             </div>
         </div>
      </div>

      <!-- Render Parsed Sections using CollapsibleSection -->
      <div v-if="parsedSections.length > 0" class="space-y-6">
        <div v-for="(section, index) in parsedSections" 
             :key="index" 
             :class="['rounded-2xl shadow-sm border p-6 report-section', getSectionStyle(section.title).classes]"
             >
           <h2 :class="['text-xl font-display font-semibold mb-4 flex items-center', getSectionStyle(section.title).classes.includes('bg-white') ? 'text-text-primary' : '']">
             <component :is="getSectionStyle(section.title).icon" :class="['h-5 w-5 mr-3 flex-shrink-0', getSectionStyle(section.title).iconColor]" />
             {{ section.title }}
           </h2>
           <!-- Use the CollapsibleSection component -->
           <CollapsibleSection 
              :content="section.content" 
              :class="[getSectionStyle(section.title).classes.includes('bg-white') ? 'text-text-secondary' : '']" 
           />
        </div>
      </div>
      <!-- Fallback if parsing finds no sections -->
      <div v-else-if="!isLoading && reportDetails" class="bg-yellow-50 border border-yellow-300 rounded-lg p-4 text-yellow-800">
          Could not find structured sections within the report content. Displaying raw content might be an option if needed, but is currently disabled.
           <!-- Optional: Display raw iframe as fallback? -->
           <!-- 
           <iframe 
               :srcdoc="reportDetails.html_content"
               class="w-full h-[60vh] border mt-4 rounded"
               sandbox="allow-scripts allow-same-origin" 
               title="Raw Report Content"
               frameborder="0">
           </iframe>
           -->
      </div>

       <!-- REMOVED IFRAME -->
       <!-- 
       <div class="bg-white rounded-2xl shadow-sm border border-border overflow-hidden">
         <iframe 
             :srcdoc="reportDetails.html_content"
             class="w-full h-[80vh] border-0"
             sandbox="allow-scripts allow-same-origin" 
             title="Generated Report Content"
             frameborder="0">
         </iframe>
       </div> 
       -->

    </div>

     <!-- Fallback if no details but no error (remains the same) -->
    <div v-else class="text-center py-16 text-text-secondary">
        Report data could not be loaded.
    </div>

  </div>
</template>

<style scoped>
/* Add styles for the rendered HTML content if needed */
.report-section :deep(h1),
.report-section :deep(h2),
.report-section :deep(h3),
.report-section :deep(h4) {
  /* Example: Adjust heading sizes within the rendered content */
  /* margin-bottom: 0.5em; */
}

.report-section :deep(p) {
  /* Example: Adjust paragraph spacing */
  /* margin-bottom: 1em; */
}

.report-section :deep(ul),
.report-section :deep(ol) {
  /* Example: Adjust list styling */
  /* margin-left: 1.5em; */
  /* margin-bottom: 1em; */
}

.report-section :deep(img) {
    /* Ensure images from the report are constrained */
    max-width: 100%;
    height: auto;
    border-radius: 0.5rem; /* Add rounded corners */
    margin-top: 1rem;
    margin-bottom: 1rem;
}

.report-section :deep(table) {
    /* Basic table styling */
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}

.report-section :deep(th),
.report-section :deep(td) {
    border: 1px solid #e5e7eb; /* border-gray-200 */
    padding: 0.5rem 1rem;
    text-align: left;
}

.report-section :deep(thead) {
    background-color: #f9fafb; /* bg-gray-50 */
}

/* Add more specific styles as needed based on your report HTML structure */
</style> 