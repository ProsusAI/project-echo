<template>
  <div class="message mb-4">
    <div class="flex items-center mb-1">
      <Icon :icon="icon" class="w-6 h-6 mr-2 rounded-full" aria-hidden="true"/>
      <span class="font-semibold text-lg">{{ username }}</span>
      <span class="text-gray-500 text-sm ml-2">{{ date }}</span>
    </div>
    <div :class="[
      'p-4 rounded-lg shadow-md message-text break-words',
      username === 'Echo' ? 'bg-white border border-gray-200' : 'bg-gray-100'
    ]">
      <!-- Tool usage updates -->
      <div v-if="toolUsages && toolUsages.length" class="mb-4">
        <div
          class="progress-updates-container cursor-pointer rounded-lg border border-gray-200 overflow-hidden transition-all duration-300 ease-in-out"
          :class="{ 'hover:shadow-md': !isToolUsagesExpanded }"
        >
          <div class="flex items-center justify-between bg-gray-50 px-4 py-2" @click="toggleToolUsages">
            <span class="font-medium text-gray-700">Progress</span>
            <Icon :icon="isToolUsagesExpanded ? 'mdi:chevron-up' : 'mdi:chevron-down'" class="w-5 h-5 text-gray-600" />
          </div>
          <transition name="fade">
            <div v-if="isToolUsagesExpanded" class="px-4 py-2">
              <div class="space-y-2 relative pl-4 max-h-60 overflow-y-auto custom-scrollbar">
                <div class="absolute left-0 top-0 bottom-0 w-px bg-gray-200"></div>
                <div v-for="(usage, index) in reversedToolUsages" :key="usage.tool_call_id"
                     class="progress-update flex items-start space-x-3 relative"
                     :style="{ opacity: 1 - (index * 0.015) }">
                  <div class="absolute left-0 top-2 w-2 h-2 rounded-full bg-gray-400 -ml-[5px]"></div>
                  <Icon :icon="usage.icon"
                        :class="[
                          'w-5 h-5 mt-0.5 flex-shrink-0',
                          usage.message_type === 'tool_progress' ? 'text-green-500' : 'text-red-500'
                        ]"
                        aria-hidden="true"/>
                  <span :class="[
                    'text-sm',
                    usage.message_type === 'tool_progress' ? 'text-green-700' : 'text-red-700'
                  ]">{{ usage.content }}</span>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <MarkdownComponent :content="content"/>
      <div v-if="files && (files.images.length || files.otherFiles.length)" class="mt-4">
        <hr class="border-gray-300 my-2">
        <span class="text-sm text-gray-500">Uploaded files</span>
        <div v-if="files.images.length" class="flex space-x-2 overflow-x-auto mt-2">
          <div v-for="(image, index) in files.images" :key="index" class="relative w-24 h-24 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0 cursor-pointer" @click="showImageModal(image.url)">
            <img :src="image.url" :alt="image.name" class="object-cover w-full h-full" loading="lazy"/>
          </div>
        </div>
        <div v-if="files.otherFiles.length" class="mt-2">
          <div v-if="isMobile" class="text-sm text-gray-500">+{{ files.otherFiles.length }} more file(s) uploaded</div>
          <div v-else>
            <div v-for="(file, index) in files.otherFiles" :key="index" class="flex items-center space-x-2 p-2 bg-gray-100 rounded-lg shadow-sm mb-1">
              <Icon :icon="getFileIcon(file)" class="w-6 h-6"/>
              <a :href="file.url" target="_blank" class="text-sm text-blue-600 hover:underline">{{ file.name }}</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, computed, inject, onMounted, onUnmounted } from 'vue';
import { Icon } from '@iconify/vue';
import MarkdownComponent from '@/components/markdown/MarkdownComponent.vue';

export default defineComponent({
  name: 'MessageComponent',
  components: {
    MarkdownComponent,
    Icon
  },
  props: {
    username: String,
    icon: String,
    date: String,
    content: String,
    files: {
      type: Object,
      default: () => ({
        images: [],
        otherFiles: []
      })
    },
    toolUsages: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const isToolUsagesExpanded = ref(true);
    const isMobile = ref(window.innerWidth < 768);
    const openImageModal = inject('openImageModal');

    const toggleToolUsages = () => {
      isToolUsagesExpanded.value = !isToolUsagesExpanded.value;
    };

    const reversedToolUsages = computed(() => {
      return props.toolUsages.slice().reverse();
    });

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

    const showImageModal = (imageUrl) => {
      openImageModal(imageUrl);
    };

    const checkScreenSize = () => {
      isMobile.value = window.innerWidth < 768;
    };

    onMounted(() => {
      window.addEventListener('resize', checkScreenSize);
      checkScreenSize();
    });

    onUnmounted(() => {
      window.removeEventListener('resize', checkScreenSize);
    });

    return {
      isToolUsagesExpanded,
      toggleToolUsages,
      reversedToolUsages,
      isMobile,
      getFileIcon,
      showImageModal
    };
  }
});
</script>

<style scoped>
.message-text {
  max-width: 100%;
  word-wrap: break-word;
}
.fade-enter-active, .fade-leave-active {
  transition: all 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  max-height: 0;
}
.fade-enter-to, .fade-leave-from {
  opacity: 1;
  max-height: 1000px; /* Adjust this value based on your expected maximum height */
}
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}
.progress-updates-container {
  display: flex;
  flex-direction: column;
}
.progress-update {
  transition: background-color 0.3s ease, opacity 0.3s ease;
}
.progress-update:hover {
  background-color: #e0f7fa;
}
</style>