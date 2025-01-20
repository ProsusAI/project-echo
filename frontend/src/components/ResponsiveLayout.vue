<template>
  <div class="responsive-layout flex h-screen relative">
    <!-- Left sidebar for large displays -->
    <div v-if="!isMobile" @click="toggleLeftDrawer" class="w-16 flex-shrink-0 flex flex-col items-center justify-center bg-gray-100 border-r border-gray-200 cursor-pointer hover:bg-gray-200 transition-colors duration-200">
      <div class="mb-4">
        <IconWithBadge icon="heroicons-solid:user-group" label="Characters" :count="characterCount" />
      </div>
    </div>

    <!-- Main content area -->
    <div class="flex-1 flex overflow-hidden">
      <Transition name="slide-left">
        <CharactersDrawer v-if="isLeftDrawerOpen" @close="closeLeftDrawer" :class="{ 'mobile-overlay': isMobile }" :isMobile="isMobile" :is-open="true" />
      </Transition>

      <Transition name="slide-left">
        <SessionsDrawer v-if="isSessionsDrawerOpen" @close="closeSessionsDrawer" :class="{ 'mobile-overlay': isMobile }" :isMobile="isMobile" />
      </Transition>

      <div :class="['chat-container flex-grow overflow-hidden transition-all duration-300 ease-in-out', { 'ml-64': isLeftDrawerOpen && !isMobile, 'mr-64': isRightDrawerOpen && !isMobile }]">
        <slot></slot>
      </div>

      <Transition name="slide-right">
        <VoiceRecordingsDrawer v-if="isRightDrawerOpen" @close="closeRightDrawer" :class="{ 'mobile-overlay': isMobile }" :isMobile="isMobile" :is-open="true" @toggleFullScreen="toggleFullScreen" />
      </Transition>
    </div>

    <!-- Right sidebar for large displays -->
    <div v-if="!isMobile" @click="toggleRightDrawer" class="w-16 flex-shrink-0 flex flex-col items-center justify-center bg-gray-100 border-l border-gray-200 cursor-pointer hover:bg-gray-200 transition-colors duration-200">
      <IconWithBadge icon="heroicons:play-20-solid" label="Voice Recordings" :count="voiceRecordingCount" class="mb-4" />
    </div>

    <!-- Floating buttons for small displays -->
    <FloatingButtons 
      :is-mobile="isMobile" 
      @toggleLeftDrawer="toggleLeftDrawer" 
      @toggleRightDrawer="toggleRightDrawer" 
      @toggleSessionsDrawer="toggleSessionsDrawer"
      @newConversation="createNewConversation" 
      class="z-30" 
    />

    <!-- FullScreenAudio component rendered outside of the drawers for full-screen functionality -->
    <FullScreenAudio v-if="isFullScreen" @exitFullScreen="toggleFullScreen" :showHeader="false" />

    <!-- ImageModal component -->
    <ImageModal v-if="isImageModalOpen" :imageUrl="imageModalUrl" @close="closeImageModal" />
  </div>
</template>

<script>
import { defineComponent, ref, onMounted, onUnmounted, computed, provide } from 'vue';
import { useStore } from 'vuex';
import CharactersDrawer from './CharactersDrawer.vue';
import VoiceRecordingsDrawer from './VoiceRecordingsDrawer.vue';
import SessionsDrawer from './SessionsDrawer.vue';
import FullScreenAudio from './voiceRecordings/FullScreenAudio.vue';
import FloatingButtons from './FloatingButtons.vue';
import IconWithBadge from './IconWithBadge.vue';
import ImageModal from './ImageModal.vue';
import WebSocketService from "@/websocket";

export default defineComponent({
  name: 'ResponsiveLayout',
  components: {
    CharactersDrawer,
    VoiceRecordingsDrawer,
    SessionsDrawer,
    FullScreenAudio,
    FloatingButtons,
    IconWithBadge,
    ImageModal,
  },
  setup() {
    const store = useStore();
    const isLeftDrawerOpen = ref(false);
    const isRightDrawerOpen = ref(false);
    const isSessionsDrawerOpen = ref(false);
    const isFullScreen = ref(false);
    const isMobile = ref(window.innerWidth < 768);
    const isImageModalOpen = ref(false);
    const imageModalUrl = ref('');

    const characterCount = computed(() => store.getters['characters/characterCount']);
    const voiceRecordingCount = computed(() => store.getters['voiceRecordings/voiceRecordingCount']);

    const checkMobile = () => {
      isMobile.value = window.innerWidth < 768;
    };

    const toggleLeftDrawer = () => {
      if (isRightDrawerOpen.value && isMobile.value) closeRightDrawer();
      if (isSessionsDrawerOpen.value) closeSessionsDrawer();
      isLeftDrawerOpen.value = !isLeftDrawerOpen.value;
    };

    const toggleRightDrawer = () => {
      if (isLeftDrawerOpen.value && isMobile.value) closeLeftDrawer();
      if (isSessionsDrawerOpen.value) closeSessionsDrawer();
      isRightDrawerOpen.value = !isRightDrawerOpen.value;
    };

    const toggleSessionsDrawer = () => {
      if (isLeftDrawerOpen.value && isMobile.value) closeLeftDrawer();
      if (isRightDrawerOpen.value && isMobile.value) closeRightDrawer();
      isSessionsDrawerOpen.value = !isSessionsDrawerOpen.value;
    };

    const closeLeftDrawer = () => {
      isLeftDrawerOpen.value = false;
    };

    const closeRightDrawer = () => {
      isRightDrawerOpen.value = false;
    };

    const closeSessionsDrawer = () => {
      isSessionsDrawerOpen.value = false;
    };

    const toggleFullScreen = () => {
      isFullScreen.value = !isFullScreen.value;
    };

    const openImageModal = (imageUrl) => {
      imageModalUrl.value = imageUrl;
      isImageModalOpen.value = true;
    };

    const closeImageModal = () => {
      isImageModalOpen.value = false;
      imageModalUrl.value = '';
    };

    const createNewConversation = async () => {
      await WebSocketService.disconnect();
      store.dispatch('messages/setMessages', []);
      store.dispatch('characters/setCharacters', []);
      store.dispatch('voiceRecordings/setVoiceRecordings', []);
      store.dispatch('voiceRecordings/setCurrentSegmentIndex', 0);
      store.dispatch('voiceRecordings/pauseAudio');
      store.dispatch('voiceRecordings/setIsPlaying', false);
      store.dispatch('voiceRecordings/setTitle', 'Voice Recordings');
      store.dispatch('voiceRecordings/setSubtitle', null);
      store.dispatch('followUpResponses/clearFollowUpResponses');
      store.dispatch('files/clearFiles');
      store.dispatch('messages/setLoading', false);
      await WebSocketService.verifyConnection();
    };

    onMounted(() => {
      checkMobile();
      window.addEventListener('resize', checkMobile);
    });

    onUnmounted(() => {
      window.removeEventListener('resize', checkMobile);
    });

    provide('openImageModal', openImageModal);

    return {
      isLeftDrawerOpen,
      isRightDrawerOpen,
      isSessionsDrawerOpen,
      isFullScreen,
      isMobile,
      characterCount,
      voiceRecordingCount,
      toggleLeftDrawer,
      toggleRightDrawer,
      toggleSessionsDrawer,
      closeLeftDrawer,
      closeRightDrawer,
      closeSessionsDrawer,
      toggleFullScreen,
      isImageModalOpen,
      imageModalUrl,
      openImageModal,
      closeImageModal,
      createNewConversation,
    };
  },
});
</script>

<style scoped>
.responsive-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.chat-container {
  flex: 1 1 auto;
  min-width: 0;
  position: relative;
  z-index: 10;
}

.mobile-overlay {
  position: fixed;
  top: 0;
  bottom: 0;
  width: 100%;
  z-index: 40;
}

.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease-in-out;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-100%);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
