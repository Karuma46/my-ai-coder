const apiBaseUrl = import.meta.env.VITE_APP_API_URL?.trim().replace(/\/+$/, '')

export function apiEndpoint(path: string) {
  if (!apiBaseUrl) {
    throw new Error('VITE_APP_API_URL is not configured.')
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return import.meta.env.DEV
    ? `/__api${normalizedPath}`
    : `${apiBaseUrl}${normalizedPath}`
}

export function apiOriginEndpoint(path: string) {
  if (!apiBaseUrl) {
    throw new Error('VITE_APP_API_URL is not configured.')
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (import.meta.env.DEV && normalizedPath === '/health') {
    return '/__health'
  }

  const url = new URL(apiBaseUrl)
  url.pathname = normalizedPath
  url.search = ''
  url.hash = ''

  return url.toString()
}

export function apiWebSocketEndpoint(path: string) {
  if (!apiBaseUrl) {
    throw new Error('VITE_APP_API_URL is not configured.')
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${apiBaseUrl}${normalizedPath}`)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'

  return url.toString()
}
