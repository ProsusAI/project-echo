<template>
  <div>
    <button v-if="deferredPrompt" @click="installApp">Install Project Echo</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      deferredPrompt: null,
    };
  },
  mounted() {
    window.addEventListener('beforeinstallprompt', (event) => {
      // Prevent the default install prompt
      event.preventDefault();
      // Save the event to trigger it later
      this.deferredPrompt = event;
    });
  },
  methods: {
    installApp() {
      if (this.deferredPrompt) {
        this.deferredPrompt.prompt();
        this.deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the A2HS prompt');
          } else {
            console.log('User dismissed the A2HS prompt');
          }
          this.deferredPrompt = null;
        });
      }
    },
  },
};
</script>

<style scoped>
button {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #4DBA87;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 10px 20px;
  cursor: pointer;
}
</style>
