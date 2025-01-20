<template>
  <div class="fixed inset-0 z-50 bg-gray-900 text-white p-4 flex flex-col items-center justify-center">
    <!-- Title and Subtitle -->
    <div v-if="title !== 'Voice Recordings'" class="absolute top-4 w-full text-center px-4">
      <h1 class="text-2xl md:text-4xl lg:text-5xl font-title font-bold tracking-tight leading-tight">{{ title }}</h1>
      <h2 v-if="subtitle" class="text-lg md:text-xl lg:text-2xl font-subtitle text-gray-300 mt-2 leading-tight">
        {{ subtitle }}</h2>
    </div>

    <div v-if="voiceRecordingCount === 0" class="flex flex-col items-center mt-20 md:mt-32 lg:mt-40 text-center">
      <p class="text-lg md:text-xl lg:text-2xl text-gray-400">No audio files available.</p>
    </div>

    <div v-else class="flex flex-col items-center space-y-4 mt-20 md:mt-32 lg:mt-40">
      <img :src="currentRecording.character_photo_url" alt="Character"
           :class="['w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40 rounded-full', isPlaying ? 'animate-speaking' : '']"/>
      <h1 class="text-xl md:text-2xl lg:text-3xl font-title font-bold">{{ currentRecording.character_name }}</h1>
      <p class="text-sm md:text-lg lg:text-xl font-segment" v-html="highlightedSegmentText"></p>
      <p class="text-xs md:text-sm lg:text-base">{{ currentSegmentIndex + 1 }} / {{ totalSegments }}</p>
      <div class="flex space-x-4">
        <button @click.stop="playPreviousSegmentAction" class="p-2">
          <Icon icon="heroicons-outline:rewind" class="w-6 h-6 md:w-8 md:h-8 lg:w-10 lg:h-10"/>
        </button>
        <button @click.stop="togglePlayPause" class="p-2">
          <Icon :icon="isPlaying ? 'heroicons-outline:pause' : 'heroicons-outline:play'"
                class="w-6 h-6 md:w-8 md:h-8 lg:w-10 lg:h-10"/>
        </button>
        <button @click.stop="playNextSegmentAction" class="p-2">
          <Icon icon="heroicons-outline:fast-forward" class="w-6 h-6 md:w-8 md:h-8 lg:w-10 lg:h-10"/>
        </button>
      </div>
    </div>
    <button @click.stop="exitFullScreen" class="absolute top-4 right-4 p-2">
      <Icon icon="heroicons-outline:x" class="w-6 h-6 md:w-8 md:h-8"/>
    </button>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { Icon } from '@iconify/vue';

export default {
  components: {
    Icon,
  },
  data() {
    return {
      currentPlaybackTime: 0,
      playbackInterval: null,
    };
  },
  computed: {
    ...mapState('voiceRecordings', ['currentSegmentIndex', 'isPlaying', 'title', 'subtitle', 'currentPlaybackTime']),
    ...mapGetters('voiceRecordings', ['currentRecording', 'voiceRecordingCount']),
    totalSegments() {
      return this.voiceRecordingCount;
    },
    highlightedSegmentText() {
      const {segment_text, alignment_info} = this.currentRecording;
      if (!alignment_info || !alignment_info.word_start_times || !alignment_info.word_end_times) {
        // If alignment_info is missing or not properly structured, return the segment_text as it is
        return segment_text;
      }

      const words = segment_text.split(' ');
      const {word_start_times, word_end_times} = alignment_info;
      let highlightedText = '';
      const currentTime = this.currentPlaybackTime;

      words.forEach((word, index) => {
        if (currentTime >= word_start_times[index] && currentTime <= word_end_times[index]) {
          highlightedText += `<span class="text-highlight"><b> ${word} </b></span>`;
        } else {
          highlightedText += word + ' ';
        }
      });

      return highlightedText;
    },
  },
  methods: {
    ...mapActions('voiceRecordings', ['playNextSegment', 'playPreviousSegment', 'setIsPlaying', 'setCurrentSegmentIndex', 'initializeAudio', 'loadAudio', 'playAudio', 'pauseAudio']),
    togglePlayPause() {
      if (this.isPlaying) {
        this.pauseAudio();
      } else {
        this.loadAudio(this.currentRecording.audio_segment_url);
      }
    },
    playPreviousSegmentAction() {
      this.playPreviousSegment();
      this.loadAudio(this.currentRecording.audio_segment_url);
    },
    playNextSegmentAction() {
      if (this.currentSegmentIndex < this.totalSegments - 1) {
        this.playNextSegment();
        this.loadAudio(this.currentRecording.audio_segment_url);
      } else {
        this.setIsPlaying(false); // Stop at the last segment
      }
    },
    exitFullScreen() {
      this.$emit('exitFullScreen');
    },
    updatePlaybackTime() {
      if (this.$store.state.voiceRecordings.audio) {
        this.currentPlaybackTime = this.$store.state.voiceRecordings.audio.currentTime;
      }
    },
  },
  watch: {
    isPlaying(newVal) {
      if (newVal) {
        this.playAudio();
      } else {
        this.pauseAudio();
      }
    },
    currentSegmentIndex() {
      this.loadAudio(this.currentRecording.audio_segment_url);
    }
  },
  mounted() {
    this.initializeAudio();
    this.playbackInterval = setInterval(() => {
      this.updatePlaybackTime();
    }, 200);
  },
};
</script>

<style>
.text-highlight {
  color: yellow;
}

.animate-speaking {
  animation: speaking 1s infinite;
}

@keyframes speaking {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.highlight-enter-active,
.highlight-leave-active {
  transition: background-color 0.5s ease, color 0.5s ease;
}

.highlight-enter, .highlight-leave-to /* .highlight-leave-active in <2.1.8 */
{
  background-color: transparent;
  color: white;
}
</style>
