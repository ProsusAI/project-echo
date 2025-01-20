<template>
  <div class="flex flex-col h-screen bg-white">
    <NavbarComponent />
    <ResponsiveLayout >
      <ChatInterface />
    </ResponsiveLayout>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import NavbarComponent from './components/NavbarComponent.vue';
import ResponsiveLayout from './components/ResponsiveLayout.vue';
import ChatInterface from './components/ChatInterface.vue';

export default defineComponent({
  name: 'App',
  components: {
    NavbarComponent,
    ResponsiveLayout,
    ChatInterface,
  },
});
</script>

<style>
</style>
