import { createApp } from 'vue';
import App from './App.vue';
import store from './store';
import "./utils/marked";
import './assets/markdown.css';
import './assets/tailwind.css';
import registerServiceWorker from './registerServiceWorker';
import registerBeforeInstallPrompt from './registerBeforeInstallPrompt';
import tooltip from "./directives/tooltip.js";
import "@/assets/tooltip.css";

const app = createApp(App);
app.use(store);
app.directive("tooltip", tooltip);
app.mount('#app');

registerServiceWorker();
registerBeforeInstallPrompt();