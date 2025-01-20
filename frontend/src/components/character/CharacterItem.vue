<template>
  <li class="flex items-center p-2 bg-white rounded shadow mb-2">
    <div class="flex items-center mr-3">
      <div class="w-4 h-4 rounded-full mr-2" :style="{ backgroundColor: character.background_colour }"></div>
      <img :src="character.photo_url" alt="character photo" class="w-10 h-10 rounded-full" />
    </div>
    <div class="flex-grow">
      <div class="font-semibold">{{ character.name }}</div>
      <div class="text-sm text-gray-500">{{ character.role }}</div>
    </div>
    <button @click="toggleAudio" class="text-blue-500 hover:text-blue-700">
      <Icon :icon="isPlaying ? 'heroicons-outline:pause' : 'heroicons-outline:play'" class="w-6 h-6" />
    </button>
    <button @click="$emit('show-details', character)" class="text-gray-500 hover:text-gray-700 ml-2">
      <Icon icon="heroicons-outline:information-circle" class="w-6 h-6" />
    </button>
  </li>
</template>

<script>
import { defineComponent, ref, watch } from 'vue';
import { Icon } from '@iconify/vue';
import eventBus from '@/utils/eventBus';

export default defineComponent({
  name: "CharacterItem",
  components: { Icon },
  props: {
    character: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const audio = ref(new Audio(props.character.introduction_audio_url));
    const isPlaying = ref(false);

    watch(() => props.character, (newCharacter) => {
      audio.value = new Audio(newCharacter.introduction_audio_url);
    }, { immediate: true });

    const toggleAudio = () => {
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

    return { isPlaying, toggleAudio };
  }
});
</script>

<style scoped>
</style>

<style scoped>
</style>
