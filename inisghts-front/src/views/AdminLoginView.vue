<template>
  <div class="min-h-screen flex items-center justify-center relative py-1 px-4 sm:px-6 lg:px-8 overflow-hidden">
    <!-- Fondo abstracto con gradientes y patrones -->
    <div class="absolute inset-0 bg-gradient-to-br from-orange-900 via-amber-800 to-orange-700 z-0"></div>
    
    <!-- Patrón de elementos gráficos -->
    <div class="absolute inset-0 z-0 opacity-10">
      <div class="absolute top-10 left-10 w-40 h-40 rounded-full bg-amber-400 blur-3xl"></div>
      <div class="absolute top-1/4 right-20 w-60 h-60 rounded-full bg-amber-400 blur-3xl"></div>
      <div class="absolute bottom-20 left-1/3 w-80 h-80 rounded-full bg-orange-300 blur-3xl"></div>
    </div>
    
    <!-- Elementos gráficos que representan reviews y análisis -->
    <div class="absolute inset-0 z-0 overflow-hidden">
      <svg class="absolute top-20 right-20 w-80 h-80 text-white opacity-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11 2C13.0609 2 15.0783 2.58695 16.8282 3.6853C18.5782 4.78365 19.9975 6.3459 20.9487 8.17316C21.9 10.0004 22.3445 12.0111 22.2384 14.0297C22.1323 16.0484 21.4799 18.0027 20.3566 19.6822C19.2334 21.3617 17.6804 22.7022 15.8775 23.5623C14.0747 24.4224 12.0991 24.7713 10.1503 24.5756C8.20136 24.3798 6.34582 23.6478 4.77589 22.457C3.20596 21.2662 1.98194 19.6646 1.22965 17.8289" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      
      <!-- Iconos de estrellas (reviews) -->
      <div class="absolute top-1/3 left-10 text-yellow-300 opacity-10 transform rotate-12">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16" viewBox="0 0 20 20" fill="currentColor">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      </div>
      
      <!-- Iconos de personas (arquetipos) -->
      <div class="absolute bottom-1/4 right-14 text-amber-300 opacity-10 transform -rotate-12">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-20 w-20" viewBox="0 0 20 20" fill="currentColor">
          <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
        </svg>
      </div>
      
      <!-- Iconos de gráfico (insights) -->
      <div class="absolute bottom-20 left-20 text-green-300 opacity-10 transform rotate-6">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24" viewBox="0 0 20 20" fill="currentColor">
          <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
        </svg>
      </div>
    </div>
    
    <!-- Logo de TAMA INSIGHTS flotante -->
    <div class="absolute top-6 left-1/2 transform -translate-x-1/2 z-10 text-center">
      <div class="text-white text-4xl font-extrabold tracking-wider font-sans">
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-amber-300 to-orange-300">LLM  &nbsp;</span>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-orange-300 to-amber-300">FLOW</span>
      </div>
      <div class="text-white opacity-80 text-center text-sm mt-1 max-w-xs mx-auto font-light">
        Powering Brand Intelligence with AI
      </div>
    </div>
    
    <!-- Formulario de admin login -->
    <div class="max-w-md w-full space-y-8 bg-white/90 backdrop-blur-lg p-8 rounded-2xl shadow-2xl border border-white/20 relative z-10 mt-12">
      <div>
        <img class="mx-auto h-16 w-auto" src="@/assets/logo.svg" alt="Logo">
        <h2 class="mt-6 text-center text-3xl font-bold text-gray-900">
          Admin Dashboard
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Exclusive access for administrators
        </p>
      </div>

      <form class="mt-8 space-y-6" @submit.prevent="handleAdminLogin">
        <div v-if="loginError" class="rounded-md bg-red-50 p-4 mb-4">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">{{ loginError }}</h3>
            </div>
          </div>
        </div>

        <div class="rounded-md shadow-sm -space-y-px">
          <div>
            <label for="email-address" class="sr-only">Email address</label>
            <input id="email-address" name="email" type="email" autocomplete="email" required
              v-model="loginForm.email"
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-orange-500 focus:border-orange-500 focus:z-10 sm:text-sm"
              placeholder="Email address">
          </div>
          <div>
            <label for="password" class="sr-only">Password</label>
            <input id="password" name="password" type="password" autocomplete="current-password" required
              v-model="loginForm.password"
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-orange-500 focus:border-orange-500 focus:z-10 sm:text-sm"
              placeholder="Password">
          </div>
        </div>

        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <input id="remember-me" name="remember-me" type="checkbox"
              v-model="loginForm.rememberMe"
              class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded">
            <label for="remember-me" class="ml-2 block text-sm text-gray-900">
              Remember me
            </label>
          </div>

          <div class="text-sm">
            <a href="#" class="font-medium text-orange-600 hover:text-orange-500" @click.prevent="openForgotPasswordModal">
              Forgot your password?
            </a>
          </div>
        </div>

        <!-- Desafío Matemático -->
        <div class="border-t border-gray-200 pt-4">
            <label for="math-question-admin" class="block text-sm font-medium text-gray-700 mb-1">
                Security question:
            </label>
            <div class="flex items-center space-x-2">
                <span class="text-gray-900">What is {{ mathNum1 }} + {{ mathNum2 }}?</span>
                <input 
                    id="math-question-admin" 
                    name="math-question-admin" 
                    type="number" 
                    required
                    v-model="mathUserAnswer"
                    class="appearance-none block w-20 px-2 py-1 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-orange-500 focus:border-orange-500 sm:text-sm"
                    placeholder="Answer"
                >
                 <button type="button" @click="generateMathQuestion" title="New question" class="p-1 text-gray-500 hover:text-gray-700">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m-15.357-2a8.001 8.001 0 0115.357 2m0 0H15" />
                    </svg>
                </button>
            </div>
        </div>

        <div>
          <button type="submit" 
            :disabled="isLoggingIn || !isMathCorrect"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed">
            <span v-if="isLoggingIn">Signing in...</span>
            <span v-else>Sign in as Administrator</span>
          </button>
        </div>
      </form>

      <!-- Volver al login normal -->
      <div class="mt-6 text-center">
        <a href="#" class="text-sm font-medium text-orange-600 hover:text-orange-500" @click.prevent="goToUserLogin">
          Return to user login
        </a>
      </div>
    </div>

    <!-- Modal Forgot Password -->
    <div v-if="showForgotPasswordModal" class="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center" aria-labelledby="modal-title-admin" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
      <div class="relative bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-orange-100 sm:mx-0 sm:h-10 sm:w-10">
              <!-- Heroicon name: outline/information-circle -->
              <svg class="h-6 w-6 text-orange-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title-admin">
                Password Recovery
              </h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  To recover your administrator password, please contact the system support or the designated authority.
                </p>
              </div>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button @click="closeForgotPasswordModal" type="button" class="mt-3 w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-orange-600 text-base font-medium text-white hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
            OK
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();

// Login state
const loginForm = reactive({
  email: '',
  password: '',
  rememberMe: false,
});
const isLoggingIn = ref(false);
const loginError = ref('');

// Estado para el desafío matemático
const mathNum1 = ref(0);
const mathNum2 = ref(0);
const mathUserAnswer = ref('');
const mathCorrectAnswer = computed(() => mathNum1.value + mathNum2.value);
const isMathCorrect = computed(() => parseInt(mathUserAnswer.value, 10) === mathCorrectAnswer.value)

// Estado para el modal "Forgot Password"
const showForgotPasswordModal = ref(false);

// Función para generar nueva pregunta
function generateMathQuestion() {
  mathNum1.value = Math.floor(Math.random() * 10) + 1;
  mathNum2.value = Math.floor(Math.random() * 10) + 1;
  mathUserAnswer.value = '';
}

// Generar pregunta al montar el componente
onMounted(() => {
  generateMathQuestion();
});

// Methods
async function handleAdminLogin() {
  loginError.value = '';
  if (!loginForm.email || !loginForm.password) {
    loginError.value = 'Email and password are required.';
    return;
  }
  if (!isMathCorrect.value) {
    loginError.value = 'Incorrect answer to the security question.';
    generateMathQuestion(); 
    return;
  }
  
  isLoggingIn.value = true;
  
  try {
    const response = await axios.post('/api/auth/corporate/login', {
      email: loginForm.email,
      password: loginForm.password,
      remember_me: loginForm.rememberMe
    });
    
    console.log('Corporate Admin login successful, admin data:', response.data.admin);
    console.log('Corporate Admin Token:', response.data.token);

    sessionStorage.setItem('corporateAdminToken', response.data.token);
    sessionStorage.setItem('corporateAdmin', JSON.stringify(response.data.admin));
    
    router.push('/admin/dashboard');

  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      loginError.value = error.response.data.detail;
    } else {
      loginError.value = 'Login error. Check your credentials or contact support.';
    }
    generateMathQuestion(); 
  } finally {
    isLoggingIn.value = false;
  }
}

function goToUserLogin() {
  router.push('/login');
}

// Funciones para el modal
function openForgotPasswordModal() {
    showForgotPasswordModal.value = true;
}

function closeForgotPasswordModal() {
    showForgotPasswordModal.value = false;
}
</script> 