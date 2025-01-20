<template>
  <div class="sessions-drawer fixed bg-white shadow-lg transition-all duration-300 ease-in-out"
       :class="[
         isMobile ? 'top-0 right-0 h-full w-full' : 'inset-0 w-full h-full',
         isMobile ? ['translate-x-full', { 'translate-x-0': isOpen }] : ['translate-y-neg', { 'translate-y-0': isOpen }]
       ]">
    <DrawerHeader
        title="Previous Sessions"
        subtitle="Browse and load your previous conversations"
        @close="$emit('close')"
        :isMobile="isMobile"
        class="px-6 py-4 border-b"
    />

    <div class="overflow-y-auto h-[calc(100vh-80px)] p-6">
      <!-- Error Alert -->
      <div v-if="error" class="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
        {{ error }}
      </div>

      <!-- Empty State -->
      <div v-if="!loading && !error && sessions.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
        <div class="w-24 h-24 mb-6 text-gray-300">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">No Sessions Yet</h3>
        <p class="text-gray-500 max-w-sm">
          Start a new conversation to create your first session. Your creative journey begins here!
        </p>
      </div>

      <!-- Sessions List -->
      <div v-else class="space-y-4">
        <div v-for="session in sessions" :key="session.id" 
             class="bg-white border rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200">
          
          <!-- Session Header -->
          <div class="p-4">
            <div class="flex justify-between items-start mb-2">
              <h3 class="text-lg font-semibold text-gray-900">
                {{ session.content_title || 'Untitled Session' }}
              </h3>
              <span class="text-sm text-gray-500">
                {{ formatDate(session.last_update_datetime) }}
              </span>
            </div>
            
            <!-- Subtitle -->
            <p v-if="session.content_subtitle" class="text-sm text-gray-600 mb-2">
              {{ session.content_subtitle }}
            </p>

            <!-- Content Type & Description -->
            <div v-if="session.content_type || session.content_description" class="mb-2">
              <span v-if="session.content_type" class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mr-2">
                {{ session.content_type }}
              </span>
              <p v-if="session.content_description" class="text-sm text-gray-600 mt-1">
                {{ session.content_description }}
              </p>
            </div>

            <!-- Scenes Count -->
            <div v-if="session.number_of_scenes" class="text-sm text-gray-600">
              {{ session.number_of_scenes }} scene{{ session.number_of_scenes !== 1 ? 's' : '' }}
            </div>

            <!-- Characters -->
            <div v-if="session.characters.length" class="flex -space-x-2 mt-3">
              <img
                v-for="character in session.characters.slice(0, 5)"
                :key="character.name"
                :src="character.photo_url"
                :alt="character.name"
                :title="character.name"
                class="w-8 h-8 rounded-full border-2 border-white"
              >
              <div v-if="session.characters.length > 5" 
                   class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs text-gray-600 border-2 border-white">
                +{{ session.characters.length - 5 }}
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-end space-x-3 mt-4">
              <button @click="loadSession(session.id)" 
                      class="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-all duration-200 flex items-center gap-2 border border-blue-200 hover:border-blue-300">
                <Icon icon="material-symbols:play-arrow-rounded" class="text-xl" />
                Resume
              </button>
              <button @click="deleteSession(session.id)"
                      class="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-all duration-200 flex items-center gap-2 border border-red-200 hover:border-red-300">
                <Icon icon="material-symbols:delete-outline-rounded" class="text-xl" />
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-4">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>

      <!-- Load More Button -->
      <div v-if="hasMore && !loading" class="flex justify-center mt-4">
        <button @click="loadMore" 
                class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors duration-200">
          Load More
        </button>
      </div>
    </div>

    <DeleteConfirmationModal
      v-if="showDeleteModal"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </div>
</template>

<script>
import { defineComponent, onMounted, computed, ref } from 'vue';
import { useStore } from 'vuex';
import { Icon } from '@iconify/vue';
import DrawerHeader from './DrawerHeader.vue';
import DeleteConfirmationModal from './DeleteConfirmationModal.vue';

export default defineComponent({
  name: 'SessionsDrawer',
  components: {
    DrawerHeader,
    Icon,
    DeleteConfirmationModal
  },
  props: {
    isMobile: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const isOpen = ref(true);
    const store = useStore();

    // Computed properties
    const sessions = computed(() => store.getters['sessions/getSessions']);
    const loading = computed(() => store.getters['sessions/isLoading']);
    const error = computed(() => store.getters['sessions/getError']);
    const hasMore = computed(() => store.getters['sessions/hasMoreSessions']);

    // Methods
    const loadMore = () => {
      store.dispatch('sessions/loadMoreSessions');
    };

    const sessionToDelete = ref(null);
    const showDeleteModal = ref(false);

    const deleteSession = async (sessionId) => {
      sessionToDelete.value = sessionId;
      showDeleteModal.value = true;
    };

    const confirmDelete = async () => {
      try {
        await store.dispatch('sessions/deleteSession', sessionToDelete.value);
        
        // Check if the deleted session was the current session
        const currentSessionId = store.getters['messages/currentSessionId'];

        if (currentSessionId === sessionToDelete.value) {
          // Reset current state
          await store.dispatch('messages/setMessages', []);
          await store.dispatch('characters/setCharacters', []);
          await store.dispatch('voiceRecordings/setVoiceRecordings', []);
          await store.dispatch('messages/setCurrentSessionId', null);
          await store.dispatch('voiceRecordings/setTitle', 'Voice Recordings');
          await store.dispatch('voiceRecordings/setSubtitle', null);
          await store.dispatch('followUpResponses/setFollowUpResponses', []);
        }
        
        // Refresh sessions list
        await store.dispatch('sessions/fetchSessions', { reset: true });
        showDeleteModal.value = false;
        sessionToDelete.value = null;
      } catch (error) {
        console.error('Error deleting session:', error);
      }
    };

    const cancelDelete = () => {
      showDeleteModal.value = false;
      sessionToDelete.value = null;
    };

    const loadSession = async (sessionId) => {
      try {
        // Reset current state
        await Promise.all([
          store.dispatch('messages/setMessages', []),
          store.dispatch('characters/setCharacters', []),
          store.dispatch('voiceRecordings/setVoiceRecordings', [])
        ]);
        
        // Load the session data
        const session = await store.dispatch('sessions/loadConversation', sessionId);
        
        if (session) {
          // Transform messages to match the expected format
          const formattedMessages = session.messages.map(msg => ({
            id: msg.id,
            username: msg.message_type === 'user' ? 'You' : 'Echo',
            icon: msg.message_type === 'user' ? 'mdi:account' : 'solar:soundwave-bold-duotone',
            date: new Date(msg.timestamp).toLocaleString(),
            content: msg.text,
            isUser: msg.message_type === 'user',
            files: null,
            toolUsages: []
          }));

          // Update all stores with the session data
          await Promise.all([
            store.dispatch('messages/setMessages', formattedMessages),
            store.dispatch('characters/setCharacters', session.characters_created),
            store.dispatch('voiceRecordings/setVoiceRecordings', session.audio_segments)
          ]);
          
          // Update content information
          if (session.content_title) {
            await store.dispatch('voiceRecordings/setTitle', session.content_title);
          }
          if (session.content_subtitle) {
            await store.dispatch('voiceRecordings/setSubtitle', session.content_subtitle);
          }

          // Update session ID in messages store
          await store.dispatch('messages/setCurrentSessionId', session.id);
          
          // Close the drawer after successful load
          emit('close');
        }
      } catch (error) {
        console.error('Error loading session:', error);
      }
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    };

    // Lifecycle hooks
    onMounted(() => {
      store.dispatch('sessions/fetchSessions', { reset: true });
    });

    return {
      sessions,
      loading,
      error,
      hasMore,
      loadMore,
      loadSession,
      deleteSession,
      formatDate,
      isOpen,
      showDeleteModal,
      confirmDelete,
      cancelDelete
    };
  }
});
</script>

<style scoped>
.sessions-drawer {
  z-index: 40;
}

.translate-x-full {
  transform: translateX(100%);
}

.translate-x-0 {
  transform: translateX(0);
}

.translate-y-neg {
  transform: translateY(-100%);
}

.translate-y-0 {
  transform: translateY(0);
}
</style>