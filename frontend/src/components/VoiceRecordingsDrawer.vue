<template>
  <aside :class="['drawer fixed top-0 right-0 z-40 h-screen transition-transform bg-gray-50', { 'translate-x-0': isOpen, 'translate-x-full': !isOpen }]" aria-label="Sidebar">
    <div class="h-full px-4 py-6 overflow-y-auto custom-scrollbar">
      <DrawerHeader :title="title" :subtitle="subtitleText" :showFullScreenButton="true" @close="$emit('close')" @toggleFullScreen="$emit('toggleFullScreen')" />
      <div v-if="allVoiceRecordings.length === 0" class="flex justify-center items-center h-full text-gray-500">
        No audio files available.
      </div>
      <ul v-else class="space-y-2 font-medium mt-4 pb-20"> <!-- Added padding-bottom to avoid overlap with media player -->
        <li v-for="(recording, index) in allVoiceRecordings" :key="recording.id" class="p-4 rounded shadow transition-all duration-300 relative"
            :style="{ backgroundColor: recording.character_colour }"
            :class="{ 'border-animation': index === currentSegmentIndex, 'active-segment': index === currentSegmentIndex }"
            :ref="el => segmentsRefs[index] = el">
          <div class="scene-indicator">Scene {{ recording.scene_index }}</div>
          <span class="absolute top-1 left-1 text-xs text-gray-500 opacity-60">{{ recording.segment_index }}</span>
          <div v-if="index !== currentSegmentIndex" class="flex items-center">
            <img :src="recording.character_photo_url" alt="Character" class="w-10 h-10 rounded-full mr-4" />
            <span class="font-bold text-gray-900">{{ recording.character_name }}</span>
          </div>
          <div v-else class="flex flex-col items-center">
            <span class="font-bold text-gray-900 mb-2">{{ recording.character_name }}</span>
            <img :src="recording.character_photo_url" alt="Character" class="large-image rounded-full"
                 :class="{ 'animate-bounce': isPlaying }" />
          </div>
        </li>
      </ul>
    </div>
    <MediaPlayer />
  </aside>
</template>

<script>
import { defineComponent, computed, ref, watch } from 'vue';
import { useStore } from 'vuex';
import DrawerHeader from './DrawerHeader.vue';
import MediaPlayer from './voiceRecordings/MediaPlayer.vue';

export default defineComponent({
  name: "VoiceRecordingsDrawer",
  props: {
    isOpen: {
      type: Boolean,
      required: true
    },
    isMobile: {
      type: Boolean,
      required: true
    }
  },
  components: { DrawerHeader, MediaPlayer },
  setup() {
    const store = useStore();
    const allVoiceRecordings = computed(() => store.getters['voiceRecordings/allVoiceRecordings']);
    const title = computed(() => store.getters['voiceRecordings/title']);
    const subtitle = computed(() => store.getters['voiceRecordings/subtitle']);
    const currentSegmentIndex = computed(() => store.getters['voiceRecordings/currentSegmentIndex']);
    const isPlaying = computed(() => store.getters['voiceRecordings/isPlaying']);

    const drawer = ref(null);
    const segmentsRefs = ref([]);

    const subtitleText = computed(() => {
      const count = allVoiceRecordings.value.length;
      return subtitle.value || `${count} audio segments available`;
    });

    // Watch for changes in the current segment index to auto-scroll
    watch(currentSegmentIndex, (newIndex) => {
      if (segmentsRefs.value[newIndex]) {
        segmentsRefs.value[newIndex].scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    });

    return { allVoiceRecordings, title, subtitleText, currentSegmentIndex, isPlaying, drawer, segmentsRefs };
  }
});
</script>

<style scoped>
.drawer {
  width: 100%;
  transition: transform 0.3s ease;
}
@media (min-width: 768px) {
  .drawer {
    width: 250px;
  }
}

/* Animation for active segment photo */
@keyframes bounce {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}
.animate-bounce {
  animation: bounce 1s infinite;
}

/* Border animation for active segment */
@keyframes borderAnimation {
  0% {
    border-color: transparent;
  }
  50% {
    border-color: rgba(0, 0, 0, 0.5);
  }
  100% {
    border-color: transparent;
  }
}
.border-animation {
  border: 2px solid transparent;
  animation: borderAnimation 2s infinite;
}

/* Active segment styling */
.active-segment {
  text-align: center;
}

.large-image {
  width: 100px; /* Adjust size as needed */
  height: 100px; /* Adjust size as needed */
}

.custom-scrollbar {
  -ms-overflow-style: none; /* Internet Explorer 10+ */
  scrollbar-width: none; /* Firefox */
}

.custom-scrollbar::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}

/* Scene indicator styling */
.scene-indicator {
  position: absolute;
  top: 2px;
  right: 2px;
  background-color: rgba(0, 0, 0, 0.1);
  color: rgba(0, 0, 0, 0.6);
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 0.6rem;
  font-weight: normal;
}
</style>