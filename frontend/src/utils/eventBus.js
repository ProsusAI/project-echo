import { ref } from 'vue';

const currentPlayingCharacter = ref(null);

const setCurrentPlayingCharacter = (character) => {
    if (currentPlayingCharacter.value && currentPlayingCharacter.value !== character) {
        currentPlayingCharacter.value.audio.pause();
        currentPlayingCharacter.value.isPlaying = false;
    }
    currentPlayingCharacter.value = character;
};

const clearCurrentPlayingCharacter = () => {
    currentPlayingCharacter.value = null;
};

export default {
    currentPlayingCharacter,
    setCurrentPlayingCharacter,
    clearCurrentPlayingCharacter
};
