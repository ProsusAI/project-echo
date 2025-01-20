<template>
  <div class="relative inline-block">
    <div class="p-2 text-gray-500">
      <span class="sr-only">{{ label }}</span>
      <Icon :icon="icon" class="w-6 h-6" aria-hidden="true" />
    </div>
    <span v-if="count > 0" class="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
      {{ count }}
    </span>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { Icon } from '@iconify/vue';

export default defineComponent({
  name: 'IconWithBadge',
  components: {
    Icon
  },
  props: {
    icon: {
      type: String,
      required: true
    },
    label: {
      type: String,
      required: true
    },
    count: {
      type: Number,
      default: 0
    }
  }
});
</script>