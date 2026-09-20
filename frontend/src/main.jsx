import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

// =========================================================
// GLOBAL AUDIO MANAGER & ORPHAN AUDIO KILLER
// Guarantees zero background/ghost audio playback across HMR & tabs
// =========================================================
if (typeof window !== 'undefined') {
  window.__allStreamHubAudios = window.__allStreamHubAudios || new Set();

  // Patch Audio constructor to register all created audio instances
  if (!window.__streamhub_audio_patched) {
    const OriginalAudio = window.Audio;
    window.Audio = function (...args) {
      const instance = new OriginalAudio(...args);
      window.__allStreamHubAudios.add(instance);
      return instance;
    };
    window.Audio.prototype = OriginalAudio.prototype;
    window.__streamhub_audio_patched = true;
  }

  // Global helper to instantly silence every audio instance in the browser
  window.stopAllStreamHubAudio = () => {
    // 1. Stop all registered Audio objects
    if (window.__allStreamHubAudios) {
      window.__allStreamHubAudios.forEach((a) => {
        try {
          a.pause();
          a.currentTime = 0;
          a.src = '';
        } catch (e) {}
      });
      window.__allStreamHubAudios.clear();
    }

    // 2. Stop all DOM audio / video elements
    document.querySelectorAll('audio, video').forEach((media) => {
      try {
        media.pause();
        media.currentTime = 0;
        media.src = '';
      } catch (e) {}
    });

    // 3. Stop singleton ref if present
    if (window.__STREAMHUB_AUDIO__) {
      try {
        window.__STREAMHUB_AUDIO__.pause();
        window.__STREAMHUB_AUDIO__.currentTime = 0;
        window.__STREAMHUB_AUDIO__.src = '';
      } catch (e) {}
    }
  };

  // Stop any pre-existing audio from previous hot reload
  window.stopAllStreamHubAudio();

  // Cross-tab synchronization to kill audio across multiple open tabs
  try {
    const channel = new BroadcastChannel('streamhub_audio_sync');
    channel.onmessage = (event) => {
      if (event.data?.action === 'STOP' || event.data?.action === 'PAUSE') {
        window.stopAllStreamHubAudio();
      }
    };
    window.__streamhub_audio_channel = channel;
  } catch (e) {
    // BroadcastChannel unsupported fallback
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
