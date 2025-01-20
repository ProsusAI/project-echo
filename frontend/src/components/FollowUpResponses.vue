<template>
  <div v-if="followUpResponses.length" class="flex flex-wrap gap-2 p-4 bg-white justify-center md:justify-start rounded-lg">
    <button
      v-for="(response, index) in followUpResponses"
      :key="index"
      class="follow-up-card cursor-pointer text-left text-primary px-4 py-2 rounded-lg border border-solid border-secondary bg-gray-100 hover:bg-gray-50 transition duration-200 shadow-md"
      @click="sendFollowUpResponse(response)"
    >
      {{ response }}
    </button>
  </div>
</template>

<script>
import WebSocketService from "@/websocket";

export default {
  name: 'FollowUpResponses',
  computed: {
    followUpResponses() {
      return this.$store.getters['followUpResponses/allFollowUpResponses'];
    }
  },
  methods: {
    async sendFollowUpResponse(response) {
      let message = {
        message_type: 'user_message',
        content: response,
        files: {
          images: [],
          otherFiles: [],
        },
      };
      const sessionId = this.$store.getters['messages/currentSessionId'];
      await WebSocketService.verifyConnection(sessionId);
      await WebSocketService.sendMessage(message);

      message.id = Date.now();
      message.username = 'You';
      message.icon = 'mdi:account';
      message.isUser = true;
      this.$store.dispatch('followUpResponses/clearFollowUpResponses');
      this.$store.dispatch('messages/addMessage', message);
    }
  }
};
</script>

<style scoped>
.follow-up-card {
  box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
  font-size: 14px;
  flex: 1 1 calc(33.33% - 1rem);
  max-width: calc(33.33% - 1rem);
  height: 3rem; /* Fixed height */
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-wrap: break-word; /* Ensure text wraps */
  word-wrap: break-word;
  word-break: break-word;
  border-radius: 0.75rem; /* Rounded corners */
  transition: transform 0.2s ease-in-out; /* Smooth transition */
}

.follow-up-card:hover {
  transform: scale(1.02); /* Slightly increase size on hover */
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .follow-up-card {
    flex: 1 1 calc(100% - 1rem);
    max-width: calc(100% - 1rem);
  }
}

@media (min-width: 641px) and (max-width: 1024px) {
  .follow-up-card {
    flex: 1 1 calc(50% - 1rem);
    max-width: calc(50% - 1rem);
  }
}
</style>
