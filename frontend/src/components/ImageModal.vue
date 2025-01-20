<template>
  <div class="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-75" @click.self="closeModal">
    <div class="relative bg-white rounded-lg overflow-hidden max-w-screen-md w-full mx-4">
      <button @click="closeModal" class="absolute top-2 right-2 text-white bg-black rounded-full p-1 z-10">
        <Icon icon="mdi:close" class="w-6 h-6"/>
      </button>
      <div class="flex items-center justify-center max-h-screen">
        <img :src="imageUrl" alt="Full size image" class="object-contain max-w-full max-h-full"/>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { Icon } from '@iconify/vue';

export default defineComponent({
  name: 'ImageModal',
  components: {
    Icon
  },
  props: {
    imageUrl: {
      type: String,
      required: true
    }
  },
  methods: {
    closeModal() {
      this.$emit('close');
    }
  }
});
</script>

<style scoped>
.fixed {
  z-index: 50;
}
</style>
