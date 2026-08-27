const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function getProducts({ page = 1, size = 50, search = '', category = '', inPromo = false } = {}) {
  const params = new URLSearchParams({ page, size })
  if (search) params.append('search', search)
  if (category) params.append('category', category)
  if (inPromo) params.append('in_promo', 'true')
  return request(`/products?${params}`)
}

export function getCategories() {
  return request('/products/categories')
}

export function getSeedInfo() {
  return request('/products/seed/info')
}

export function loadSampleData() {
  return request('/products/seed', { method: 'POST' })
}

export function updateProduct(id, data) {
  return request(`/products/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function deleteProduct(id) {
  return request(`/products/${id}`, { method: 'DELETE' })
}

export function triggerScraper() {
  return request('/scraper/run', { method: 'POST' })
}

export function getScraperStatus() {
  return request('/scraper/status')
}

export function getScraperHistory() {
  return request('/scraper/history')
}

export function getScraperLogs(after = 0) {
  return request(`/scraper/logs?after=${after}`)
}
