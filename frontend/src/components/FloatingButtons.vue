<template>
  <div v-if="isMobile" class="floating-buttons fixed top-14 right-4 flex space-x-2 z-30">
    <button v-tooltip="{
                    text: 'New Conversation',
                    theme: {
                        placement: 'right',
                    },
                }" @click="emitNewConversation" class="floating-button">
      <Icon icon="mdi:conversation-plus-outline" :width="20" :height="20" />
    </button>
    <button v-tooltip="{
                    text: 'Previous Sessions',
                    theme: {
                        placement: 'bottom',
                    },
                }" @click="emitToggleSessionsDrawer" class="floating-button">
      <Icon icon="heroicons-solid:clock" :width="20" :height="20" />
    </button>
    <button v-tooltip="{
                    text: 'Characters',
                    theme: {
                        placement: 'bottom',
                    },
                }" @click="emitToggleLeftDrawer" class="floating-button">
      <Icon icon="heroicons-solid:user-group" :width="20" :height="20" />
      <span v-if="characterCount > 0" class="badge">{{ characterCount }}</span>
    </button>
    <button v-tooltip="{
                    text: 'Voice Recordings',
                    theme: {
                        placement: 'bottom',
                    },
                }" @click="emitToggleRightDrawer" class="floating-button">
      <Icon icon="heroicons:play-20-solid" :width="20" :height="20" />
      <span v-if="voiceRecordingCount > 0" class="badge">{{ voiceRecordingCount }}</span>
    </button>
  </div>
  <div v-else class="desktop-buttons fixed top-4 right-4 z-30 flex space-x-2">
    <button @click="emitNewConversation" class="desktop-button">
      <Icon icon="mdi:conversation-plus-outline" :width="20" :height="20" class="mr-2" />
      New Conversation
    </button>
    <button @click="emitToggleSessionsDrawer" class="desktop-button">
      <Icon icon="heroicons-solid:clock" :width="20" :height="20" class="mr-2" />
      Previous Sessions
    </button>
  </div>
</template>

<script>
import { defineComponent, computed } from 'vue';
import { useStore } from 'vuex';
import { Icon } from '@iconify/vue';

export default defineComponent({
  name: 'FloatingButtons',
  components: {
    Icon,
  },
  props: {
    isMobile: Boolean,
  },
  setup(_, { emit }) {
    const store = useStore();
    const characterCount = computed(() => store.getters['characters/characterCount']);
    const voiceRecordingCount = computed(() => store.getters['voiceRecordings/voiceRecordingCount']);

    const emitToggleLeftDrawer = () => {
      emit('toggleLeftDrawer');
    };

    const emitToggleRightDrawer = () => {
      emit('toggleRightDrawer');
    };

    const emitToggleSessionsDrawer = () => {
      emit('toggleSessionsDrawer');
    };

    const emitNewConversation = () => {
      emit('newConversation');
    };

    return {
      characterCount,
      voiceRecordingCount,
      emitToggleLeftDrawer,
      emitToggleRightDrawer,
      emitToggleSessionsDrawer,
      emitNewConversation,
    };
  },
});
</script>

<style scoped>
.floating-buttons {
  top: 3.3rem;
  left: 0.85rem;
}

.floating-button {
  @apply p-2 rounded-full bg-black text-white hover:bg-gray-800 transition-colors;
  position: relative;
}

.badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background-color: red;
  color: white;
  border-radius: 50%;
  padding: 2px 6px;
  font-size: 0.75rem;
  font-weight: bold;
}

.desktop-buttons {
  top: 1rem;
  right: 1.5rem;
}

.desktop-button {
  @apply px-4 py-2 bg-white text-black rounded-md hover:bg-gray-200 transition-colors flex items-center shadow-sm;
}
</style>
