<template>
  <aside :class="['drawer fixed top-0 left-0 z-40 h-screen transition-transform bg-gray-50', isOpen ? 'translate-x-0' : '-translate-x-full']" aria-label="Sidebar">
    <div class="h-full px-4 py-6 overflow-y-auto custom-scrollbar">
      <DrawerHeader :title="title" :subtitle="subtitleText" @close="$emit('close')" />
      <div v-if="allCharacters.length === 0" class="flex justify-center items-center h-full text-gray-500">
        No characters have been added yet.
      </div>
      <ul v-else class="space-y-2 font-medium mt-4">
        <CharacterItem
          v-for="character in allCharacters"
          :key="character.id"
          :character="character"
          :currentPlayingCharacter="currentPlayingCharacter"
          @show-details="showDetails"
          @audio-toggled="setCurrentPlayingCharacter"
        />
      </ul>
      <CharacterModal
        v-if="isMobile && isModalOpen"
        :isOpen="isModalOpen"
        :character="selectedCharacter"
        :isMobile="isMobile"
        :currentPlayingCharacter="currentPlayingCharacter"
        @close="closeModal"
        @audio-toggled="setCurrentPlayingCharacter"
      />
    </div>
  </aside>
</template>

<script>
import { defineComponent, ref, computed } from 'vue';
import { useStore } from 'vuex';
import CharacterItem from './character/CharacterItem.vue';
import CharacterModal from './character/CharacterModal.vue';
import DrawerHeader from './DrawerHeader.vue';

export default defineComponent({
  name: "CharactersDrawer",
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
  components: { DrawerHeader, CharacterItem, CharacterModal },
  setup(props) {
    const store = useStore();
    const allCharacters = computed(() => store.getters['characters/allCharacters']);
    const isModalOpen = ref(false);
    const selectedCharacter = ref(null);
    const currentPlayingCharacter = ref(null);
    const title = ref("Character List");

    const subtitleText = computed(() => {
      const count = allCharacters.value.length;
      return count > 0 ? `${count} characters available` : '';
    });

    const showDetails = (character) => {
      selectedCharacter.value = character;
      isModalOpen.value = true;
      if (!props.isMobile) {
        document.dispatchEvent(new CustomEvent('show-details', { detail: character }));
      }
    };

    const closeModal = () => {
      isModalOpen.value = false;
      selectedCharacter.value = null;
    };

    const setCurrentPlayingCharacter = ({ character, isPlaying }) => {
      if (isPlaying) {
        currentPlayingCharacter.value = character;
      } else {
        currentPlayingCharacter.value = null;
      }
    };

    return { allCharacters, isModalOpen, selectedCharacter, currentPlayingCharacter, showDetails, closeModal, setCurrentPlayingCharacter, title, subtitleText };
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

.custom-scrollbar {
  -ms-overflow-style: none; /* Internet Explorer 10+ */
  scrollbar-width: none; /* Firefox */
}

.custom-scrollbar::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}
</style>
