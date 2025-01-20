import { register } from 'register-service-worker';

export default function registerServiceWorker() {
  if (process.env.NODE_ENV === 'production') {
    register(`${process.env.BASE_URL}service-worker.js`, {
      ready() {
        console.log(
          'App is being served from cache by a service worker.\n' +
          'For more details, visit https://goo.gl/AFskqB'
        );
      },
      registered() {
        console.log('Service worker has been registered.');
      },
      cached() {
        console.log('Content has been cached for offline use.');
      },
      updatefound() {
        console.log('New content is downloading.');
        // Show an "Update available" notification/message here
        alert('New version available! Updating...');
      },
      updated(registration) {
        console.log('New content is available; please refresh.');
        // Optionally, show an update message to the user here
        const updateButton = document.createElement('button');
        updateButton.textContent = 'Update Available!';
        updateButton.style.position = 'fixed';
        updateButton.style.bottom = '10px';
        updateButton.style.right = '10px';
        updateButton.style.zIndex = '1000';
        document.body.appendChild(updateButton);
        updateButton.addEventListener('click', () => {
          if (registration.waiting) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
            window.location.reload();
          }
        });
      },
      offline() {
        console.log('No internet connection found. App is running in offline mode.');
      },
      error(error) {
        console.error('Error during service worker registration:', error);
      },
    });
  }
}
