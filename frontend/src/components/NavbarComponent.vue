<template>
  <nav class="bg-gray-800 p-4 flex justify-between items-center relative">
    <div class="flex items-center space-x-4">
      <Icon icon="solar:soundwave-bold-duotone" class="text-white text-4xl"></Icon>
      <span class="text-white text-2xl">Project Echo</span>
    </div>
  </nav>
</template>

<script>
import { defineComponent } from 'vue';
import { Icon } from '@iconify/vue';

export default defineComponent({
  name: 'NavbarComponent',
  components: {
    Icon,
  },
});
</script>

<style scoped>
/* Add any scoped styles for the Navbar here */
</style>
