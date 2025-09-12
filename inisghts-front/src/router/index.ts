import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import ConnectSources from '@/views/ConnectSources.vue'
import CompetitorSources from '@/views/CompetitorSources.vue'
import ConnectCompetitorSources from '@/views/ConnectCompetitorSources.vue'
import SourcesLanding from '@/views/SourcesLanding.vue'
import MySources from '@/views/MySources.vue'
import Dashboard from '@/views/Dashboard.vue'
import Archetypes from '@/views/Archetypes.vue'
import GenerateReport from '@/views/GenerateReport.vue'
import GeneratedReports from '@/views/GeneratedReports.vue'
import ArchetypeChat from '@/views/ArchetypeChat.vue'
import Analytics from '@/views/Analytics.vue'
import Chat2Data from '@/views/Chat2Data.vue'
import LoginView from '@/views/LoginView.vue'
import AdminLoginView from '@/views/AdminLoginView.vue'
import AdminDashboard from '@/views/AdminDashboard.vue'
import ReportDetail from '@/views/ReportDetail.vue'
import Chat from '@/views/Chat.vue'
import CompetitorsView from '@/views/CompetitorsView.vue'
import ConnectMySources from '@/views/ConnectMySources.vue'
// import Help from '@/views/Help.vue'

// Middleware para verificar autenticación
const requireAuth = (to: any, from: any, next: any) => {
  const token = sessionStorage.getItem('token')
  if (!token) {
    next('/login')
  } else {
    next()
  }
}

const requireAdminAuth = (to: any, from: any, next: any) => {
  const adminToken = sessionStorage.getItem('adminToken');
  const corporateAdminToken = sessionStorage.getItem('corporateAdminToken');
  
  if (!adminToken && !corporateAdminToken) { 
    next('/admin/login');
  } else {
    next();
  }
}

// Middleware para verificar si es admin o usuario admin de marca
const requireAdminOrBrandAdmin = (to: any, from: any, next: any) => {
  const token = sessionStorage.getItem('token')
  const adminToken = sessionStorage.getItem('adminToken')
  
  // Si es admin de sistema, permitir acceso
  if (adminToken) {
    next()
    return
  }
  
  // Si es usuario regular, verificar si tiene rol admin
  if (token) {
    try {
      const user = JSON.parse(sessionStorage.getItem('user') || '{}')
      if (user.is_admin === 1 || user.is_admin === true) {
        next()
      } else {
        // Si no es admin, redirigir al dashboard
        next('/dashboard')
      }
    } catch (e) {
      // Si hay error al parsear, redirigir a login
      next('/login')
    }
  } else {
    // Si no hay token, redirigir a login
    next('/login')
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'root',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: AdminLoginView
    },
    {
      path: '/admin/dashboard',
      name: 'admin-dashboard',
      component: AdminDashboard,
      beforeEnter: requireAdminAuth
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: HomeView,
      beforeEnter: requireAuth
    },
    {
      path: '/settings/sources',
      name: 'connect-sources-landing',
      component: SourcesLanding,
      beforeEnter: requireAdminOrBrandAdmin
    },
    {
      path: '/settings/sources/my-sources',
      name: 'my-sources',
      component: MySources,
      beforeEnter: requireAdminOrBrandAdmin,
    },
    {
      path: '/settings/sources/my-sources/:id/configure',
      name: 'ConnectMySources',
      component: ConnectMySources,
      props: true,
      beforeEnter: requireAdminOrBrandAdmin,
    },
    {
      path: '/settings/sources/configure',
      name: 'configure-my-sources',
      component: ConnectSources,
      beforeEnter: requireAdminOrBrandAdmin
    },
    {
      path: '/settings/sources/competitors',
      name: 'competitor-sources',
      component: CompetitorSources,
      beforeEnter: requireAdminOrBrandAdmin
    },
    {
      path: '/settings/sources/competitors/:competitorName/configure',
      name: 'configure-competitor-sources',
      component: ConnectSources,
      props: true,
      beforeEnter: requireAdminOrBrandAdmin,
    },
    {
      path: '/archetypes',
      name: 'Archetypes',
      component: Archetypes,
      beforeEnter: requireAuth
    },
    {
      path: '/reports/new',
      name: 'generate-report',
      component: GenerateReport,
      meta: { requiresAuth: true }
    },
    {
      path: '/reports',
      name: 'generated-reports',
      component: GeneratedReports,
      meta: { requiresAuth: true }
    },
    {
      path: '/reports/view/:reportId',
      name: 'report-detail',
      component: ReportDetail,
      props: true,
      meta: { requiresAuth: true }
    },
    {
      path: '/chat',
      name: 'ArchetypeChat',
      component: ArchetypeChat,
      beforeEnter: requireAuth
    },
    {
      path: '/analytics',
      name: 'Analytics',
      component: Analytics,
      beforeEnter: requireAuth
    },
    {
      path: '/chat2data',
      name: 'Chat2Data',
      component: Chat2Data,
      beforeEnter: requireAuth
    },
    {
      path: '/chat',
      name: 'Chat',
      component: Chat2Data,
      meta: { requiresAuth: true }
    },
    {
      path: '/competitors',
      name: 'Competitors',
      component: CompetitorSources,
      meta: { requiresAuth: true }
    },
    {
      path: '/competitors/:id/sources',
      name: 'CompetitorSources-details',
      component: ConnectCompetitorSources,
      props: true,
      meta: { requiresAuth: true }
    },
    // Remove Help route if Help.vue doesn't exist
    // {
    //   path: '/help',
    //   name: 'Help',
    //   component: Help,
    //   meta: { requiresAuth: true }
    // },
  ]
})

router.beforeEach((to, from, next) => {
  // Check if the route requires authentication
  if (to.matched.some(record => record.meta.requiresAuth)) {
    // Check for the presence of any of the tokens
    const token = sessionStorage.getItem('token')
    const adminToken = sessionStorage.getItem('adminToken')
    const corporateAdminToken = sessionStorage.getItem('corporateAdminToken')

    if (token || adminToken || corporateAdminToken) {
      // User is authenticated, proceed to the route
      next()
    } else {
      next('/login')
    }
  }
  // Handling for routes that require admin access
  else if (to.matched.some(record => record.meta.requiresAdmin)) {
    const adminToken = sessionStorage.getItem('adminToken');
    const corporateAdminToken = sessionStorage.getItem('corporateAdminToken');

    if (adminToken || corporateAdminToken) {
      next(); // Proceed if admin token is present
    } else {
      next('/login'); // Redirect to login if no admin token
    }
  }
  // Handling for routes that require corporate admin access
  else if (to.matched.some(record => record.meta.requiresCorporateAdmin)) {
    const token = sessionStorage.getItem('token')
    const adminToken = sessionStorage.getItem('adminToken')
    // const corporateAdminToken = localStorage.getItem('corporateAdminToken'); // Ensure this is the correct token check

    if (adminToken && token) { // Example: check if both admin and regular token exist
      next();
    } else {
      next('/login'); // Or an appropriate unauthorized page
    }
  } else if (to.meta.requiresGuest) {
    // If the route requires guest access (like login or register)
    const user = JSON.parse(sessionStorage.getItem('user') || '{}')
    if (user && user.id) {
      // If user is logged in, redirect to home or dashboard
      next({ name: 'Dashboard' })
    } else {
      next('/login')
    }
  } else {
    next()
  }
})

export default router