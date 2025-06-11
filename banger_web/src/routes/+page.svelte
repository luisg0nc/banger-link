<script>
  import { onMount } from 'svelte';
  import { Flame, Heart, Clock, Search, Youtube, RefreshCw, Star } from 'lucide-svelte';
  
  let songs = [];
  let loading = true;
  let error = null;
  let searchQuery = '';
  let activeTab = 'trending';
  let lastUpdated = null;
  let isRefreshing = false;
  
  // Fetch songs from the API
  async function fetchSongs() {
    try {
      isRefreshing = true;
      error = null;
      
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const response = await fetch(`/api/songs?t=${timestamp}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      songs = data;
      lastUpdated = new Date();
    } catch (err) {
      console.error('Error fetching songs:', err);
      error = 'Failed to load songs. Please try again later.';
    } finally {
      loading = false;
      isRefreshing = false;
    }
  }
  
  // Set up auto-refresh
  let refreshInterval;
  
  onMount(() => {
    // Initial fetch
    fetchSongs();
    
    // Set up auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
      if (!document.hidden) { // Only refresh if tab is active
        fetchSongs();
      }
    }, 30000);
    
    // Also refresh when the tab becomes visible again
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchSongs();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Cleanup function
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  });
  
  // Computed properties for filtering and sorting
  $: filteredSongs = searchQuery
    ? songs.filter(song => 
        song.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        song.artist?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : songs;
    
  $: sortedSongs = {
    trending: [...filteredSongs].sort((a, b) => (b.plays || 0) - (a.plays || 0)),
    popular: [...filteredSongs].sort((a, b) => (b.likes || 0) - (a.likes || 0)),
    recent: [...filteredSongs].sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
  };
  
  $: activeSongs = sortedSongs[activeTab] || filteredSongs;
  
  // Format date for display
  function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }
  
  // Extract YouTube video ID from URL
  function getYoutubeId(url) {
    if (!url) return '';
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : '';
  }
  
  // Refresh data manually
  async function refreshData() {
    await fetchSongs();
  }
</script>

<div class="max-w-4xl mx-auto px-4">
  <!-- Header -->
  <header class="text-center mb-8">
    <h1 class="text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent mb-2">
      Music Shared
    </h1>
    <div class="flex items-center justify-center gap-4">
      <p class="text-gray-400">Powered by Banger Link</p>
      <button 
        class="flex items-center gap-1 text-sm text-gray-400 hover:text-purple-400 transition-colors"
        class:animate-spin={isRefreshing}
        on:click={refreshData}
        title="Refresh"
        disabled={isRefreshing}
      >
        <RefreshCw size={16} class={isRefreshing ? 'text-purple-500' : 'text-gray-400'} />
        {#if lastUpdated}
          <span>Updated: {new Date(lastUpdated).toLocaleTimeString()}</span>
        {/if}
      </button>
    </div>
  </header>
  
  <!-- Search and Filter -->
  <div class="mb-8">
    <div class="relative max-w-xl mx-auto mb-6">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search songs..."
        class="w-full px-4 py-3 pl-12 rounded-full bg-gray-800 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
      />
      <Search size={20} class="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" />
    </div>
    
    <div class="flex justify-center space-x-4 mb-8">
      <button
        class="px-6 py-2 rounded-full transition-colors flex items-center"
        class:bg-purple-600={activeTab === 'trending'}
        class:text-white={activeTab === 'trending'}
        class:bg-gray-800={activeTab !== 'trending'}
        class:text-gray-300={activeTab !== 'trending'}
        class:hover:bg-gray-700={activeTab !== 'trending'}
        on:click={() => activeTab = 'trending'}
      >
        <Flame size={16} class="mr-2" /> Trending
      </button>
      <button
        class="px-6 py-2 rounded-full transition-colors flex items-center"
        class:bg-purple-600={activeTab === 'popular'}
        class:text-white={activeTab === 'popular'}
        class:bg-gray-800={activeTab !== 'popular'}
        class:text-gray-300={activeTab !== 'popular'}
        class:hover:bg-gray-700={activeTab !== 'popular'}
        on:click={() => activeTab = 'popular'}
      >
        <Heart size={16} class="mr-2" /> Popular
      </button>
      <button
        class="px-6 py-2 rounded-full transition-colors flex items-center"
        class:bg-purple-600={activeTab === 'recent'}
        class:text-white={activeTab === 'recent'}
        class:bg-gray-800={activeTab !== 'recent'}
        class:text-gray-300={activeTab !== 'recent'}
        class:hover:bg-gray-700={activeTab !== 'recent'}
        on:click={() => activeTab = 'recent'}
      >
        <Clock size={16} class="mr-2" /> Recent
      </button>
    </div>
  </div>
  
  <!-- Songs List -->
  {#if loading}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
      <p class="mt-4 text-gray-400">Loading bangers...</p>
    </div>
  {:else if activeSongs.length === 0}
    <div class="text-center py-12">
      <p class="text-gray-400">No songs found. Try a different search term.</p>
    </div>
  {:else}
    <div class="space-y-6">
      {#each activeSongs as song (song.id)}
        <div class="bg-gray-800 rounded-xl overflow-hidden hover:bg-gray-750 transition-all duration-300 shadow-lg">
          <div class="p-6">
            <div class="flex flex-col sm:flex-row gap-6">
              <!-- YouTube Thumbnail -->
              {#if song.thumbnailUrl}
                <div class="relative w-full sm:w-1/3 lg:w-1/4 aspect-video bg-black rounded-lg overflow-hidden group">
                  <img 
                    src={song.thumbnailUrl}
                    alt={`${song.title || 'Song'} thumbnail`}
                    class="w-full h-full object-cover"
                  />
                  <div class="absolute inset-0 flex items-center justify-center group-hover:bg-black group-hover:bg-opacity-30 transition-all duration-200">
                    {#if song.id}
                      <a 
                        href={song.id}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="w-16 h-16 bg-red-600 hover:bg-red-700 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 transform hover:scale-110"
                        title="Watch on YouTube"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white">
                          <path d="M8 5v14l11-7z"/>
                        </svg>
                      </a>
                    {/if}
                  </div>
                </div>
              {/if}
              
              <div class="flex-1">
                <div class="flex justify-between items-start gap-4">
                  <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                      <h3 class="text-xl font-semibold">{song.title || 'Untitled'}</h3>
                      {#if song.likes > 0}
                        <span class="flex items-center text-yellow-400 text-sm">
                          <Star size={16} class="text-yellow-400 mr-1" />
                          {song.likes}
                        </span>
                      {/if}
                    </div>
                    <p class="text-gray-400">{song.artist || 'Unknown Artist'}</p>
                    
                    <!-- Added by and date -->
                    <div class="mt-2 text-sm text-gray-500">
                      {#if song.addedBy}
                        <span>Added by {song.addedBy} • </span>
                      {/if}
                      {formatDate(song.date)}
                    </div>
                  </div>
                  
                  <!-- YouTube Link -->
                  {#if song.youtubeUrl}
                    <a 
                      href={song.youtubeUrl}
                      target="_blank" 
                      rel="noopener noreferrer"
                      class="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-full text-sm transition-colors h-8 self-center"
                      title="Watch on YouTube"
                    >
                      <Youtube size={16} />
                      <span class="hidden sm:inline">Watch</span>
                    </a>
                  {/if}
                </div>
                
                <!-- Stats -->
                <div class="mt-4 pt-4 border-t border-gray-700 flex flex-wrap items-center text-sm text-gray-400 gap-4 sm:gap-6">
                  <div class="flex items-center" title="Plays">
                    <Flame size={16} class="mr-2 text-yellow-400 flex-shrink-0" />
                    <span>{(song.plays || 0).toLocaleString()} plays</span>
                  </div>
                  <div class="flex items-center" title="Likes">
                    <Heart size={16} class="mr-2 text-pink-500 flex-shrink-0" />
                    <span>{(song.likes || 0).toLocaleString()} likes</span>
                  </div>
                  <div class="flex items-center" title="Dislikes">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2 text-gray-500 flex-shrink-0">
                      <path d="M17 14V2"/>
                      <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z"/>
                    </svg>
                    <span>{(song.dislikes || 0).toLocaleString()} dislikes</span>
                  </div>
                  {#if song.mentions > 0}
                    <div class="flex items-center" title="Mentions">
                      <span class="text-gray-500">Mentioned {song.mentions} time{song.mentions !== 1 ? 's' : ''}</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
