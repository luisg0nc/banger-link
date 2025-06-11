<script>
  import { onMount } from 'svelte';
  import { BarChart2, Users, Music, TrendingUp } from 'lucide-svelte';
  
  let stats = {
    totalSongs: 0,
    userStats: []
  };
  let loading = true;
  let error = null;
  
  // Fetch stats from the API
  async function fetchStats() {
    try {
      loading = true;
      error = null;
      
      const response = await fetch('/api/songs/stats/');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      stats = data;
    } catch (err) {
      console.error('Error fetching stats:', err);
      error = 'Failed to load statistics. Please try again later.';
    } finally {
      loading = false;
    }
  }
  
  onMount(() => {
    fetchStats();
  });
</script>

<div class="max-w-4xl mx-auto px-4 py-8">
  <!-- Header -->
  <header class="text-center mb-12">
    <h1 class="text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent mb-4">
      Statistics
    </h1>
    <p class="text-gray-400 text-lg">
      Track the Banger's Society community
    </p>
  </header>

  {#if loading}
    <div class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
    </div>
  {:else if error}
    <div class="bg-red-900/50 border border-red-700 text-red-200 px-6 py-4 rounded-lg mb-8">
      <div class="flex items-center">
        <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{error}</span>
      </div>
      <button 
        on:click={fetchStats}
        class="mt-3 px-4 py-2 bg-red-700 hover:bg-red-600 rounded-md transition-colors text-sm font-medium"
      >
        Retry
      </button>
    </div>
  {:else}
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <!-- Total Songs -->
      <div class="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm font-medium">Total Songs</p>
            <p class="text-3xl font-bold text-white mt-1">{stats.totalSongs}</p>
          </div>
          <div class="p-3 bg-purple-600/20 rounded-lg">
            <Music class="w-6 h-6 text-purple-400" />
          </div>
        </div>
      </div>

      <!-- Total Users -->
      <div class="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm font-medium">Active Users</p>
            <p class="text-3xl font-bold text-white mt-1">{stats.userStats.length}</p>
          </div>
          <div class="p-3 bg-blue-600/20 rounded-lg">
            <Users class="w-6 h-6 text-blue-400" />
          </div>
        </div>
      </div>

      <!-- Total Shares -->
      <div class="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm font-medium">Total Shares</p>
            <p class="text-3xl font-bold text-white mt-1">
              {stats.userStats.reduce((sum, user) => sum + user.shares, 0)}
            </p>
          </div>
          <div class="p-3 bg-green-600/20 rounded-lg">
            <TrendingUp class="w-6 h-6 text-green-400" />
          </div>
        </div>
      </div>
    </div>

    <!-- User Leaderboard -->
    <div class="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
      <div class="px-6 py-4 border-b border-gray-700">
        <h2 class="text-xl font-semibold flex items-center">
          <BarChart2 class="w-5 h-5 mr-2 text-purple-400" />
          User Leaderboard
        </h2>
      </div>
      
      <div class="divide-y divide-gray-700">
        {#if stats.userStats.length === 0}
          <div class="p-6 text-center text-gray-400">
            No user data available yet.
          </div>
        {:else}
          {#each stats.userStats as user, i (user.username)}
            <div class="p-4 hover:bg-gray-750 transition-colors">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center text-white font-bold mr-4">
                    {i + 1}
                  </div>
                  <div>
                    <p class="font-medium">{user.username}</p>
                    <div class="text-sm text-gray-400 mt-1">
                      <span class="flex items-center">
                        <span class="w-2 h-2 rounded-full bg-purple-500 mr-1"></span>
                        {user.shares} {user.shares === 1 ? 'share' : 'shares'}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-lg font-bold">{user.shares}</p>
                  <p class="text-xs text-gray-400">total</p>
                </div>
              </div>
              
              <!-- Progress bar -->
              {#if i === 0}
                <div class="mt-3 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    class="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                    style={`width: ${(user.shares / stats.userStats[0].shares) * 100}%`}
                  ></div>
                </div>
              {:else}
                <div class="mt-3 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    class="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                    style={`width: ${(user.totalShares / stats.userStats[0].totalShares) * 100}%`}
                  ></div>
                </div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>
