import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import Toast, { type PluginOptions } from 'vue-toastification';
// Import the CSS or use your own custom styling
import 'vue-toastification/dist/index.css';

// Import Chart.js components
import { Chart, Filler } from 'chart.js';

// Register Chart.js plugins globally
Chart.register(Filler); // Add other necessary plugins like Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement if you use them globally

const app = createApp(App)
const pinia = createPinia()

const options: PluginOptions = {
  transition: "Vue-Toastification__bounce",
  maxToasts: 5,
  newestOnTop: true,
  position: "top-right",
  timeout: 3000, // Default timeout for toasts
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: "button",
  icon: true,
  rtl: false
};

app.use(pinia)
app.use(router)
app.use(Toast, options);
app.mount('#app')