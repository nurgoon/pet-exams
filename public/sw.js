self.addEventListener('push', (event) => {
  let payload = { title: 'Protocol', body: 'New notification' }
  try {
    payload = event.data ? event.data.json() : payload
  } catch (err) {
    payload = { title: 'Protocol', body: event.data ? event.data.text() : 'New notification' }
  }

  const title = payload.title || 'Protocol'
  const options = {
    body: payload.body || '',
    icon: '/pwa-192.png',
    badge: '/pwa-192.png',
    data: payload.data || {},
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url && 'focus' in client) {
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/')
      }
      return undefined
    })
  )
})
