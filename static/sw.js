// =============================================
// Service Worker for White Neuron
// Offline support & Caching strategy
// =============================================

const CACHE_NAME = 'whiteneuron-v1.0.0';
const STATIC_CACHE = 'whiteneuron-static-v1';
const DYNAMIC_CACHE = 'whiteneuron-dynamic-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/WhiteNeuron.css',
    '/static/js/WhiteNeuron.js',
    '/static/imgs/logo/LOGO-circle-white.png',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
            });
        })
    );
    self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
                    .map(key => {
                        return caches.delete(key);
                    })
            );
        })
    );
    return self.clients.claim(); // Take control immediately
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip admin and API requests
    if (request.url.includes('/admin') || 
        request.url.includes('/api/') ||
        request.url.includes('/dashboard/')) {
        return;
    }
    
    event.respondWith(
        caches.match(request).then((response) => {
            // Return cached response if found
            if (response) {
                return response;
            }
            
            // Otherwise fetch from network
            return fetch(request).then((networkResponse) => {
                // Cache successful responses
                if (networkResponse && networkResponse.status === 200) {
                    // Only cache same-origin requests
                    if (request.url.startsWith(self.location.origin)) {
                        const responseClone = networkResponse.clone();
                        caches.open(DYNAMIC_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                }
                return networkResponse;
            }).catch(() => {
                // Return offline page if available
                return caches.match('/offline.html');
            });
        })
    );
});

// Background sync (if needed)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-data') {
        event.waitUntil(syncData());
    }
});

// Push notifications (if needed)
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'White Neuron';
    const options = {
        body: data.body || 'You have a new notification',
        icon: '/static/imgs/logo/LOGO-circle-white.png',
        badge: '/static/imgs/logo/LOGO-circle-white.png',
        data: data.url
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.notification.data) {
        event.waitUntil(
            clients.openWindow(event.notification.data)
        );
    }
});

// Helper function for background sync
async function syncData() {
    // Implement your sync logic here
    return Promise.resolve();
}

