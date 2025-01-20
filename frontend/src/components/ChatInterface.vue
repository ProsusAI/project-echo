<template>
  <div class="chat-interface flex flex-col h-full relative" @dragover.prevent="onDragOver" @drop.prevent="handleDrop" @paste="handlePaste" @dragleave.prevent="onDragLeave">
    <Transition name="fade">
      <div v-if="showHistoryIndicator && !isMobile"
           class="history-indicator fixed top-5 left-1/2 transform -translate-x-1/2 z-20">
        <span
            class="indicator-content flex items-center bg-black bg-opacity-60 text-white px-4 py-2 rounded-full text-sm">
          <Icon icon="mdi:info-outline" class="mr-2"/>
          Scroll up for history
        </span>
      </div>
    </Transition>

    <div ref="messagesContainer" class="messages flex-grow overflow-y-scroll p-4" @scroll="handleScroll">
      <TransitionGroup name="message-slide" tag="div">
        <Message
            v-for="message in allMessages"
            :key="message.id"
            :id="`message-${message.id}`"
            :username="message.username"
            :icon="message.icon"
            :date="message.date"
            :content="message.content"
            :files="message.files"
            :tool-usages="message.toolUsages"
            :class="[
            { 'new-message-animation': message.id === lastAddedMessageId },
            { 'mb-8': !message.isUser, 'mb-4': message.isUser }
          ]"
        />
      </TransitionGroup>
      <div v-if="isLoading" class="loading-indicator flex justify-center items-center p-5">
        <div class="dot-flashing"></div>
      </div>
      <div v-if="allMessages.length === 0" class="examples-grid-container flex justify-center items-center h-full">
        <div class="examples-grid">
          <ExampleCard v-for="example in allExamples" :key="example.id" :title="example.title" :icon="example.icon"
                       :messages="example.messages"/>
        </div>
      </div>
    </div>

    <!-- Follow up responses area -->
    <div class="compose-message-container p-4 bg-white flex-shrink-0 relative">
      <Transition name="fade">
        <div v-if="showScrollButton" @click="scrollToBottom"
             class="scroll-button absolute left-1/2 transform -translate-x-1/2 -top-6 bg-black bg-opacity-50 text-white rounded-full p-2 cursor-pointer flex items-center justify-center transition-all duration-300 ease-in-out z-10 hover:bg-opacity-70">
          <Icon icon="mdi:chevron-down" width="20" height="20"/>
        </div>
      </Transition>
      <FollowUpResponses class="mb-4 p-4 bg-white" v-if="!isMobile || (isMobile && !composeMessageVisible)"/>
      <transition name="fade">
        <div
          v-if="isDragOver"
          class="border-2 border-dashed border-gray-300 rounded-lg p-4 flex items-center justify-center text-gray-500 transition-colors duration-300"
        >
          <span>Drag & drop files here</span>
        </div>
      </transition>
      <UploadedFileDisplay :uploadingCount="uploadingCount"/>
      <Transition name="fade-slide">
        <div
            v-if="(isMobile && composeMessageVisible) || !isMobile"
            :class="['compose-message flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-2 p-2 bg-white rounded-2xl shadow-lg', inputHighlighted ? 'highlight' : '']">
          <div class="w-full relative flex flex-row items-center">
            <textarea
                ref="messageTextarea"
                v-model="newMessage"
                class="w-full p-2 border rounded-xl resize-none scrollable-textarea"
                :class="{ 'border-red-500': isOverCharLimit }"
                @input="autoResize"
                @keydown.enter.exact.prevent="handleEnterKey"
                @keydown.shift.enter.prevent="handleShiftEnter"
                :disabled="isLoading"
                :placeholder="isLoading ? 'Please wait for the current message to finish...' : 'Type your message...'"
            ></textarea>
            <div class="character-counter absolute bottom-2 right-2 text-xs text-gray-500">
              {{ newMessage.length }}/50000
            </div>
            <div class="flex space-x-2 buttons-container ml-2">
              <input type="file" ref="fileInput" @change="handleFileUpload" class="hidden" multiple accept="image/*,.txt,.md,.pdf,.doc,.docx,.ppt,.pptx"/>
              <button @click="triggerFileUpload"
                      class="p-2 border rounded-full bg-black text-white hover:bg-gray-800 transition-colors"
                      :disabled="isLoading || fileUploading">
                <Icon icon="mdi:paperclip" v-if="!fileUploading" width="18" height="18"/>
                <Icon icon="mdi:loading" v-else class="animate-spin" width="18" height="18"/>
              </button>
              <button @click="sendMessage"
                      class="p-2 border rounded-full bg-black text-white hover:bg-gray-800 transition-colors"
                      :disabled="isLoading || isOverCharLimit || fileUploading">
                <Icon icon="mdi:send" width="18" height="18"/>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
    <Transition name="fade-slide">
      <div v-if="isMobile" class="fixed bottom-4 right-4 z-10">
        <button @click="toggleComposeMessage"
                class="p-2 bg-black text-white rounded-full shadow-lg hover:bg-gray-800 transition-colors">
          <Icon :icon="composeMessageVisible ? 'mdi:chevron-down' : 'mdi:chevron-up'" width="18" height="18"/>
        </button>
      </div>
    </Transition>
    <CharacterModal
        v-if="!isMobile && isModalOpen"
        :isOpen="isModalOpen"
        :character="selectedCharacter"
        :isMobile="isMobile"
        :currentPlayingCharacter="currentPlayingCharacter"
        @close="closeModal"
        @audio-toggled="setCurrentPlayingCharacter"
    />
  </div>
</template>

<script>
import {defineComponent, nextTick} from 'vue';
import {Icon} from '@iconify/vue';
import Message from './MessageComponent.vue';
import ExampleCard from './ExampleCard.vue';
import CharacterModal from './character/CharacterModal.vue';
import UploadedFileDisplay from './UploadedFileDisplay.vue';
import FollowUpResponses from './FollowUpResponses.vue';
import WebSocketService from '@/websocket';

export default defineComponent({
  components: {Message, ExampleCard, Icon, CharacterModal, UploadedFileDisplay, FollowUpResponses},
  data() {
    return {
      newMessage: '',
      websocket: null,
      messagesContainer: null,
      isAutoScrolling: true,
      showScrollButton: false,
      showHistoryIndicator: false,
      inputHighlighted: false,
      lastAddedMessageId: null,
      isModalOpen: false,
      selectedCharacter: null,
      currentPlayingCharacter: null,
      isMobile: window.innerWidth < 768,
      fileInput: null,
      fileUploading: false,
      maxFiles: parseInt(process.env.VUE_APP_MAX_FILES, 10) || 10,
      composeMessageVisible: true,
      isDragOver: false,
      uploadingCount: 0
    };
  },
  computed: {
    allMessages() {
      return this.$store.getters['messages/allMessages'];
    },
    allExamples() {
      return this.$store.getters['examples/allExamples'];
    },
    isLoading() {
      return this.$store.getters['messages/isLoading'];
    },
    isOverCharLimit() {
      return this.newMessage.length > 50000;
    },
    files() {
      return this.$store.state.files.imageFiles.concat(this.$store.state.files.otherFiles);
    }
  },
  methods: {
    handleEnterKey(event) {
      event.preventDefault();
      if (!this.fileUploading) {
        this.sendMessage();
      } else {
        alert('Please wait for the file upload to finish.');
      }
    },
    handleShiftEnter() {
      this.newMessage += '\n';
    },
    async sendMessage() {
      if (this.newMessage.trim() && !this.isLoading && !this.isOverCharLimit && !this.fileUploading) {
        const messageId = Date.now();
        const files = {
          images: this.$store.state.files.imageFiles,
          otherFiles: this.$store.state.files.otherFiles
        };

        const message = {
          message_type: 'user_message',
          content: this.newMessage.trim(),
          files: files
        };
        try {
          this.$store.dispatch('followUpResponses/clearFollowUpResponses');
          const sessionId = this.$store.getters['messages/currentSessionId'];
          await WebSocketService.verifyConnection(sessionId);
          await WebSocketService.sendMessage(message);

          this.$store.dispatch('messages/addMessage', {
            id: messageId,
            username: 'You',
            icon: 'mdi:account',
            date: new Date().toLocaleString(),
            content: this.newMessage.trim(),
            isUser: true,
            files: files,
          });
          this.lastAddedMessageId = messageId;
          this.newMessage = '';
          this.$nextTick(() => this.autoResize());
          this.$store.commit('files/CLEAR_FILES');
          setTimeout(() => {
            this.scrollToBottom();
          }, 200);
        } catch (e) {
          console.error("Error sending message:", e);
          this.$store.commit("messages/SET_LOADING", false); // Ensure the loading state is reset
        }
      }
    },
    triggerFileUpload() {
      this.$refs.fileInput.click();
    },
    isDuplicateFile(file, files) {
      return files.some(existingFile => existingFile.name === file.name && existingFile.size === file.size);
    },
    async handleFileUpload(event) {
      this.fileUploading = true;
      this.uploadingCount += event.target.files.length;
      const files = Array.from(event.target.files);
      const existingFiles = [
        ...this.$store.state.files.imageFiles,
        ...this.$store.state.files.otherFiles
      ];

      if (files.length + existingFiles.length > this.maxFiles) {
        alert(`You can upload a maximum of ${this.maxFiles} files per message.`);
        this.fileUploading = false;
        return;
      }

      for (const file of files) {
        if (this.isDuplicateFile(file, existingFiles)) {
          alert(`The file "${file.name}" already exists.`);
          continue;
        }
        const sessionId = this.$store.getters['messages/currentSessionId'];
        await this.$store.dispatch('files/uploadFile', {file, sessionId});
        this.uploadingCount -= 1;
      }
      this.fileUploading = false;

      this.scrollToBottom();
    },
    async handleDrop(event) {
      event.preventDefault();
      this.isDragOver = false;
      this.fileUploading = true;
      const files = Array.from(event.dataTransfer.files);
      await this.handleFileProcessing(files);
      this.fileUploading = false;
      this.scrollToBottom();
    },
    async handlePaste(event) {
      const items = event.clipboardData.items;
      const files = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === 'file') {
          files.push(items[i].getAsFile());
        }
      }
      if (files.length > 0) {
        this.fileUploading = true;
        await this.handleFileProcessing(files);
        this.fileUploading = false;
        this.scrollToBottom();
      }
    },
    async handleFileProcessing(files) {
      const existingFiles = [
        ...this.$store.state.files.imageFiles,
        ...this.$store.state.files.otherFiles
      ];
      this.uploadingCount += files.length;

      if (files.length + existingFiles.length > this.maxFiles) {
        alert(`You can upload a maximum of ${this.maxFiles} files per message.`);
        return;
      }

      for (const file of files) {
        if (this.isDuplicateFile(file, existingFiles)) {
          alert(`The file "${file.name}" already exists.`);
          continue;
        }
        const sessionId = this.$store.getters['messages/currentSessionId'];
        await this.$store.dispatch('files/uploadFile', {file, sessionId});
        this.uploadingCount -= 1;
      }
    },
    handleScroll() {
      const {scrollTop, scrollHeight, clientHeight} = this.messagesContainer;
      this.isAutoScrolling = scrollTop + clientHeight >= scrollHeight - 50;
      this.showScrollButton = !this.isAutoScrolling;
      this.showHistoryIndicator = scrollTop > 200;
    },
    scrollToTop() {
      this.messagesContainer.scrollTop = 0;
      this.isAutoScrolling = true;
      this.showScrollButton = false;
      this.showHistoryIndicator = false;
    },
    scrollToBottom() {
      if (this.messagesContainer) {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        this.isAutoScrolling = true;
        this.showScrollButton = false;
        this.showHistoryIndicator = false;
      }
    },
    autoResize() {
      const textarea = this.$refs.messageTextarea;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
      }
    },
    showDetails(character) {
      this.selectedCharacter = character;
      this.isModalOpen = true;
    },
    closeModal() {
      this.isModalOpen = false;
      this.selectedCharacter = null;
    },
    setCurrentPlayingCharacter({character, isPlaying}) {
      if (isPlaying) {
        this.currentPlayingCharacter = character;
      } else {
        this.currentPlayingCharacter = null;
      }
    },
    highlightInput() {
      this.inputHighlighted = true;
      setTimeout(() => {
        this.inputHighlighted = false;
      }, 1000);
    },
    handleShowDetailsEvent(event) {
      this.showDetails(event.detail);
    },
    toggleComposeMessage() {
      this.composeMessageVisible = !this.composeMessageVisible;
      if (this.composeMessageVisible) {
        this.$nextTick(() => {
          this.$refs.messageTextarea.focus();
        });
      }
    },
    onDragOver() {
      this.isDragOver = true;
    },
    onDragLeave() {
      this.isDragOver = false;
    }
  },
  watch: {
    allMessages: {
      handler() {
        if (this.isAutoScrolling) {
          nextTick(() => this.scrollToBottom());
        }
      },
      deep: true
    },
    '$store.state.messages.inputMessage': {
      handler(newVal) {
        this.newMessage = newVal;
        this.highlightInput();
      }
    }
  },
  async mounted() {
    try {
      await WebSocketService.verifyConnection();
    } catch (e) {
      console.error(e)
    }
    this.messagesContainer = this.$refs.messagesContainer;
    this.fileInput = this.$refs.fileInput;
    this.scrollToBottom();
    document.addEventListener('show-details', this.handleShowDetailsEvent);
  },
  unmounted() {
    WebSocketService.disconnect();
    document.removeEventListener('show-details', this.handleShowDetailsEvent);
  }
});
</script>

<style scoped>
.chat-interface {
  @apply flex flex-col h-screen relative transition-all duration-300 ease-in-out;
}

.left-drawer-open .chat-interface {
  @apply ml-44;
  /* Adjust based on drawer width */
}

.right-drawer-open .chat-interface {
  @apply mr-44;
  /* Adjust based on drawer width */
}

.messages {
  overflow-y: scroll; /* Enable scrolling */
  scrollbar-width: none; /* Hide scrollbar in Firefox */
  -ms-overflow-style: none; /* Hide scrollbar in Internet Explorer and Edge */
}

.messages::-webkit-scrollbar {
  display: none; /* Hide scrollbar in Chrome, Safari, and Opera */
}

.scroll-button {
  transition: opacity 0.3s ease-in-out, transform 0.3s ease-in-out;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.dot-flashing {
  @apply relative w-2.5 h-2.5 rounded-full bg-black;
  animation: dot-flashing 1s infinite linear alternate;
  animation-delay: 0.5s;
}

.dot-flashing::before, .dot-flashing::after {
  content: '';
  @apply absolute top-0 w-2.5 h-2.5 rounded-full bg-black;
}

.dot-flashing::before {
  @apply -left-4;
  animation: dot-flashing 1s infinite alternate;
  animation-delay: 0s;
}

.dot-flashing::after {
  @apply left-4;
  animation: dot-flashing 1s infinite alternate;
  animation-delay: 1s;
}

@keyframes dot-flashing {
  0% {
    @apply bg-black;
  }
  50%, 100% {
    @apply bg-opacity-50;
  }
}

.history-indicator {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
}

.indicator-content {
  display: flex;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.fade-slide-enter-active, .fade-slide-leave-active {
  transition: opacity 0.5s, transform 0.5s;
}

.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.examples-grid-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

@media (max-width: 1024px) {
  .examples-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .examples-grid {
    grid-template-columns: 1fr;
  }
}

.compose-message-container {
  flex-shrink: 0;
}

.compose-message.highlight {
  animation: highlight-animation 0.5s ease-in-out;
}

@keyframes highlight-animation {
  0% {
    @apply bg-gray-200;
  }
  100% {
    @apply bg-white;
  }
}

.new-message-animation {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    @apply opacity-0 -translate-y-5;
  }
  to {
    @apply opacity-100 translate-y-0;
  }
}

.scrollable-textarea {
  @apply max-h-[300px] min-h-[120px] overflow-y-auto;
}

/* Styling adjustments for small displays */
@media (max-width: 768px) {
  .chat-interface {
    height: calc(100vh - 100px); /* Adjust 100px if needed based on your mobile header height */
  }

  .compose-message-container {
    @apply p-2;
  }

  .scrollable-textarea {
    @apply max-h-[200px];
  }

  .scroll-button {
    @apply -top-8;
  }

  .character-counter {
    @apply absolute bottom-2 left-2 text-xs text-gray-500;
  }

  .buttons-container {
    @apply absolute bottom-3 right-2 flex space-x-2;
  }
}

/* Styling adjustments for large displays */
@media (min-width: 769px) {
  .chat-interface {
    height: calc(100vh - 4rem); /* Adjust 4rem if needed based on your header height */
  }

  .compose-message-container {
    @apply p-4;
  }

  .scrollable-textarea {
    @apply max-h-[300px];
    padding-right: 5rem;
  }

  .buttons-container {
    @apply relative flex space-x-2 ml-2;
  }

  .character-counter {
    @apply absolute bottom-2 text-xs text-gray-500;
    right: 6.5rem;
  }
}

.drag-over {
  @apply bg-gray-200 border-gray-500;
}
</style>

