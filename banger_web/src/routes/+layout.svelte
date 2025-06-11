<script>
  import '@fontsource-variable/space-grotesk';
  import '../app.css';
  import { page } from '$app/stores';
  import { Home, BarChart2 } from 'lucide-svelte';
</script>

<main class="min-h-screen bg-gray-900 text-white">
  <!-- Navigation -->
  <nav class="bg-gray-800 border-b border-gray-700">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <div class="flex items-center space-x-8">
          <a href="/" class="flex items-center space-x-2 text-white hover:text-purple-300 transition-colors">
            <span class="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">Banger's Society</span>
          </a>
          <div class="hidden md:flex items-center space-x-1">
            <a 
              href="/" 
              class="px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-1 transition-colors {!$page.url.pathname || $page.url.pathname === '/' ? 'bg-gray-900 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'}"
            >
              <Home class="w-4 h-4" />
              <span>Home</span>
            </a>
            <a 
              href="/stats" 
              class="px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-1 transition-colors {$page.url.pathname === '/stats' ? 'bg-gray-900 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'}"
            >
              <BarChart2 class="w-4 h-4" />
              <span>Stats</span>
            </a>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Mobile menu -->
    <div class="md:hidden border-t border-gray-700">
      <div class="px-2 pt-2 pb-3 space-y-1">
        <a 
          href="/" 
          class="flex items-center px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white"
        >
          <Home class="w-5 h-5 mr-2" />
          Home
        </a>
        <a 
          href="/stats" 
          class="flex items-center px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white"
        >
          <BarChart2 class="w-5 h-5 mr-2" />
          Stats
        </a>
      </div>
    </div>
  </nav>

  <div class="container mx-auto px-4 py-8">
    <slot />
  </div>
</main>
