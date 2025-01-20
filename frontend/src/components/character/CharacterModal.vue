<template>
  <div v-if="isOpen" :class="['modal-container', modalClass]">
    <div class="modal-content bg-white rounded-lg p-6 w-full max-w-lg mx-auto relative z-50">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">{{ character?.name }}</h2>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <Icon :icon="'heroicons-outline:x'" class="w-6 h-6" />
        </button>
      </div>
      <div class="flex items-center mb-4">
        <div class="flex items-center mr-4">
          <div class="w-4 h-4 rounded-full mr-2" :style="{ backgroundColor: character?.background_colour }"></div>
          <img :src="character?.photo_url" alt="character photo" class="w-24 h-24 rounded-full" v-if="character"/>
        </div>
        <div>
          <div class="text-sm font-medium">{{ character?.role }}</div>
          <div class="text-xs text-gray-500">{{ character?.personality }}</div>
        </div>
      </div>
      <div class="mb-4">
        <p class="text-gray-700">{{ character?.description }}</p>
      </div>
      <button @click="toggleAudio" class="text-blue-500 hover:text-blue-700 flex items-center" v-if="character">
        <Icon :icon="isPlaying ? 'heroicons-outline:pause' : 'heroicons-outline:play'" class="w-6 h-6 mr-2" />
        {{ isPlaying ? 'Pause' : 'Play' }} Introduction
      </button>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, watch, computed } from 'vue';
import { Icon } from '@iconify/vue';
import eventBus from '@/utils/eventBus';

export default defineComponent({
  name: "CharacterModal",
  components: { Icon },
  props: {
    isOpen: {
      type: Boolean,
      required: true
    },
    character: {
      type: Object,
      required: false,
      default: null
    },
    isMobile: {
      type: Boolean,
      required: true
    }
  },
  setup(props) {
    const audio = ref(null);
    const isPlaying = ref(false);

    watch(() => props.character, (newCharacter) => {
      audio.value = new Audio(newCharacter.introduction_audio_url);
    }, { immediate: true });

    const toggleAudio = () => {
      if (!audio.value) return;
      if (isPlaying.value) {
        audio.value.pause();
        isPlaying.value = false;
      } else {
        eventBus.setCurrentPlayingCharacter({ character: props.character, audio: audio.value, isPlaying });
        audio.value.play();
        isPlaying.value = true;
      }
    };

    watch(eventBus.currentPlayingCharacter, (newCharacter) => {
      if (newCharacter?.character?.id !== props.character.id) {
        audio.value.pause();
        isPlaying.value = false;
      }
    });

    const modalClass = computed(() => {
      return props.isMobile ? 'fixed inset-0 bg-gray-800 bg-opacity-50 flex items-center justify-center z-40' : 'absolute inset-0 bg-gray-800 bg-opacity-50 flex items-center justify-center z-40';
    });

    return { isPlaying, toggleAudio, modalClass };
  }
});
</script>

<style scoped>
.modal-container {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 50;
}

.modal-content {
  z-index: 60;
}
</style>
