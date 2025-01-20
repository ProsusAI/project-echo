<template>
  <div class="media-player fixed bottom-0 left-0 right-0 bg-gray-800 p-4 flex items-center justify-between text-white">
    <button v-tooltip="'Previous'" @click.stop="playPreviousSegmentAction" class="p-2">
      <Icon icon="heroicons-outline:rewind" class="w-6 h-6"/>
    </button>
    <button v-tooltip="isPlaying ? 'Pause' : 'Play'" @click.stop="togglePlayPause" class="p-2">
      <Icon :icon="isPlaying ? 'heroicons-outline:pause' : 'heroicons-outline:play'" class="w-6 h-6"/>
    </button>
    <button v-tooltip="'Next'" @click.stop="playNextSegmentAction" class="p-2">
      <Icon icon="heroicons-outline:fast-forward" class="w-6 h-6"/>
    </button>
    <button :disabled="isLoading || voiceRecordingCount === 0" v-tooltip="'Download'" @click.stop="downloadAudio" class="p-2" :class="{ 'cursor-not-allowed opacity-50': isLoading || voiceRecordingCount === 0 }">
      <Icon icon="heroicons-outline:download" class="w-6 h-6"/>
    </button>
  </div>
</template>

<script>
import {mapActions, mapGetters, mapState} from 'vuex';
import {Icon} from '@iconify/vue';
import WebSocketService from "@/websocket";

export default {
  components: {Icon},
  computed: {
    ...mapState('voiceRecordings', ['currentSegmentIndex', 'isPlaying']),
    ...mapGetters('voiceRecordings', ['currentRecording', 'voiceRecordingCount']),
    ...mapGetters('messages', ['isLoading', 'allMessages']),
  },
  methods: {
    ...mapActions('voiceRecordings', ['setIsPlaying', 'playNextSegment', 'playPreviousSegment', 'setCurrentSegmentIndex', 'initializeAudio', 'loadAudio', 'playAudio', 'pauseAudio']),
    ...mapActions('messages', ['updateLastMessage', 'setLoading']),
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
      if (this.currentSegmentIndex < this.voiceRecordingCount - 1) {
        this.playNextSegment();
        this.loadAudio(this.currentRecording.audio_segment_url);
      } else {
        this.setIsPlaying(false); // Stop at the last segment
      }
    },
    async downloadAudio() {
      this.setLoading(true);
      const message = {
        message_type: 'audio_download',
        files: {}
      }

      // get the last message and check if it is a user message
      const lastMessage = this.allMessages[this.allMessages.length - 1];
      if (!lastMessage.isUser) {
        this.updateLastMessage("<br/><br/>");
      }

      await WebSocketService.verifyConnection(this.$store.getters['messages/currentSessionId']);
      await WebSocketService.sendMessage(message);
    }
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
  },
};
</script>

<style scoped>
.media-player {
  width: 100%;
  transition: transform 0.3s ease;
}

.cursor-not-allowed {
  cursor: not-allowed;
}

.opacity-50 {
  opacity: 0.5;
}
</style>
