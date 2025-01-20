<template>
  <div @click="setExampleMessage" class="example-card">
    <Icon :icon="icon" class="icon" />
    <span class="title">{{ title }}</span>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { Icon } from '@iconify/vue';
import { useStore } from 'vuex';

export default defineComponent({
  name: 'ExampleCard',
  props: {
    title: String,
    icon: String,
    messages: Array
  },
  components: {
    Icon
  },
  setup(props) {
    const store = useStore();

    const setExampleMessage = () => {
      const randomMessage = props.messages[Math.floor(Math.random() * props.messages.length)];
      store.dispatch('messages/setInputMessage', randomMessage);
    };

    return {
      setExampleMessage
    };
  }
});
</script>

<style scoped>
.example-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  margin: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  background-color: #fff;
  cursor: pointer;
  transition: transform 0.2s;
}

.example-card:hover {
  transform: scale(1.05);
}

.icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: #555;
}

.title {
  font-size: 1rem;
  text-align: center;
  color: #333;
}

@media (max-width: 1024px) {
  .example-card {
    padding: 0.75rem;
    margin: 0.25rem;
  }

  .icon {
    font-size: 1.75rem;
    margin-bottom: 0.4rem;
  }

  .title {
    font-size: 0.9rem;
  }
}

@media (max-width: 768px) {
  .example-card {
    padding: 0.5rem;
    margin: 0.2rem;
  }

  .icon {
    font-size: 1.5rem;
    margin-bottom: 0.3rem;
  }

  .title {
    font-size: 0.8rem;
  }
}

@media (max-width: 480px) {
  .example-card {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding: 0.4rem;
    margin: 0.1rem;
    justify-content: flex-start;
  }

  .icon {
    font-size: 1.5rem;
    margin-bottom: 0;
    margin-right: 0.25rem;
  }

  .title {
    font-size: 0.7rem;
    display: inline;
  }
}
</style>
