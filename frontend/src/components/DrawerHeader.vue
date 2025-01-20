<template>
  <div class="flex justify-between items-start mb-4">
    <div class="flex-grow min-w-0">
      <h2 class="text-lg font-semibold text-gray-900 leading-snug break-words">{{ title }}</h2>
      <div :class="['relative overflow-hidden', isMobile ? 'h-auto' : 'h-6']">
        <p :class="['text-sm text-gray-600 mt-1', isMobile ? 'whitespace-normal' : isLongSubtitle ? 'sliding-text' : 'text-left']">{{ subtitle }}</p>
      </div>
    </div>
    <div class="flex items-center space-x-2">
      <button v-if="showFullScreenButton" @click="$emit('toggleFullScreen')" class="ml-2 text-gray-500 hover:bg-gray-100 p-2 rounded-lg transition-colors duration-200">
        <span class="sr-only">Toggle Fullscreen</span>
        <Icon :icon="'heroicons-outline:arrows-expand'" class="w-6 h-6" aria-hidden="true" />
      </button>
      <button @click="$emit('close')" class="ml-2 text-gray-500 hover:bg-gray-100 p-2 rounded-lg transition-colors duration-200">
        <span class="sr-only">Close sidebar</span>
        <Icon :icon="'heroicons-outline:x'" class="w-6 h-6" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<script>
import { defineComponent, computed, ref, onMounted, onUnmounted } from 'vue';
import { Icon } from '@iconify/vue';

export default defineComponent({
  name: "DrawerHeader",
  props: {
    title: {
      type: String,
      required: true
    },
    subtitle: {
      type: String,
      required: true
    },
    showFullScreenButton: {
      type: Boolean,
      default: false
    }
  },
  components: { Icon },
  setup(props) {
    const isMobile = ref(false);

    const updateIsMobile = () => {
      isMobile.value = window.innerWidth < 768;
    };

    onMounted(() => {
      updateIsMobile();
      window.addEventListener('resize', updateIsMobile);
    });

    onUnmounted(() => {
      window.removeEventListener('resize', updateIsMobile);
    });

    const isLongSubtitle = computed(() => {
      if (isMobile.value) return false;
      const subtitleElement = document.createElement('span');
      subtitleElement.style.fontSize = '14px'; // Match the text-sm class size
      subtitleElement.style.visibility = 'hidden';
      subtitleElement.style.whiteSpace = 'nowrap';
      subtitleElement.innerText = props.subtitle;

      document.body.appendChild(subtitleElement);
      const isLong = subtitleElement.offsetWidth > 250; // Check if the width is greater than the container width
      document.body.removeChild(subtitleElement);

      return isLong;
    });

    return { isMobile, isLongSubtitle };
  }
});
</script>

<style scoped>
.sliding-text {
  display: inline-block;
  white-space: nowrap;
  animation: slide-left 10s linear infinite;
}

@keyframes slide-left {
  0% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}

.whitespace-normal {
  white-space: normal;
}
</style>