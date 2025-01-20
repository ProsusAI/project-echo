<template>
  <div v-if="files.length" class="uploaded-files-container mt-2 w-full">
    <div class="text-sm text-gray-600 mb-2">Uploaded files</div>
    <div class="relative bg-gray-100 rounded-lg overflow-hidden">
      <div ref="scrollContainer" class="flex overflow-x-auto space-x-2 py-2 px-4 scrollbar-hide">
        <div v-for="file in files" :key="file.url" class="flex-shrink-0 w-20 h-20 relative bg-white rounded-lg shadow-sm border border-gray-300 overflow-hidden group">
          <img v-if="isImage(file)" :src="file.url" :alt="file.name" class="w-full h-full object-cover" loading="lazy" />
          <div v-else class="w-full h-full flex flex-col items-center justify-center p-1">
            <Icon :icon="getFileIcon(file)" class="w-8 h-8 mb-1" />
            <div class="text-xs text-center truncate w-full">{{ file.name }}</div>
          </div>
          <button @click="removeFile(file)" class="absolute top-0 right-0 p-1 bg-white bg-opacity-75 rounded-bl focus:outline-none z-10">
            <Icon icon="mdi:close" class="w-4 h-4" />
          </button>
          <div class="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75 text-white text-sm opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity duration-300">
            <div class="scrolling-text-container">
              <span class="scrolling-text">{{ file.name }}</span>
            </div>
          </div>
        </div>
        <div v-for="n in uploadingCount" :key="n" class="flex-shrink-0 w-20 h-20 relative bg-white rounded-lg shadow-sm border border-gray-300 overflow-hidden group">
          <div class="w-full h-full flex flex-col items-center justify-center p-1">
            <Icon icon="mdi:loading" class="w-8 h-8 mb-1 animate-spin" />
            <div class="text-xs text-center truncate w-full">Uploading...</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue';
import { useStore } from 'vuex';
import { Icon } from '@iconify/vue';

export default {
  name: 'UploadedFileDisplay',
  components: { Icon },
  props: {
    uploadingCount: {
      type: Number,
      default: 0
    }
  },
  setup(props) {
    const store = useStore();
    const scrollContainer = ref(null);

    const files = computed(() => {
      const imageFiles = store.state.files.imageFiles || [];
      const otherFiles = store.state.files.otherFiles || [];
      return [...imageFiles, ...otherFiles];
    });

    const isImage = (file) => file.type?.startsWith('image/');

    const getFileIcon = (file) => {
      if (file.name?.includes('md')) return 'mdi:file-markdown';
      if (file.name?.includes('doc')) return 'mdi:file-word';
      if (file.name?.includes('docx')) return 'mdi:file-word';
      if (file.name?.includes('ppt')) return 'mdi:file-powerpoint';
      if (file.name?.includes('pptx')) return 'mdi:file-powerpoint';
      if (file.type?.includes('pdf')) return 'mdi:file-pdf';
      if (file.type?.includes('zip')) return 'mdi:folder-zip';
      if (file.type?.includes('text')) return 'mdi:file-document';
      return 'mdi:file';
    };

    const removeFile = (file) => {
      const sessionId = store.getters['messages/currentSessionId'];
      store.dispatch('files/removeFile', { file, sessionId });
    };

    return {
      files,
      isImage,
      getFileIcon,
      removeFile,
      scrollContainer,
      props
    };
  }
};
</script>

<style scoped>
.uploaded-files-container {
  @apply mt-2;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.scrolling-text {
  display: inline-block;
  white-space: nowrap;
}

.scrolling-text-container {
  width: 100%;
  overflow: hidden;
}

.scrolling-text {
  display: inline-block;
  white-space: nowrap;
  animation: scrollText 10s linear infinite;
}

@keyframes scrollText {
  0% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}
</style>

