import { useState, useEffect, useCallback } from 'react'
import { getProducts, deleteProduct, getCategories, getSeedInfo, loadSampleData } from '../api'
import ProductEditModal from './ProductEditModal'
import { useI18n } from '../i18n.jsx'

const PAGE_SIZE = 50

const inputClasses =
  'border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

export default function ProductTable() {
  const { t } = useI18n()
  const [products, setProducts] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [inPromo, setInPromo] = useState(false)
  const [categories, setCategories] = useState([])
  const [editProduct, setEditProduct] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [seedInfo, setSeedInfo] = useState(null)
  const [seeding, setSeeding] = useState(false)

  const fetchProducts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getProducts({ page, size: PAGE_SIZE, search, category, inPromo })
      setProducts(data.items)
      setTotal(data.total)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [page, search, category, inPromo])

  useEffect(() => { fetchProducts() }, [fetchProducts])

  useEffect(() => {
    getCategories().then(setCategories).catch(console.error)
    getSeedInfo().then(setSeedInfo).catch(console.error)
  }, [])

  const handleDelete = async (id) => {
    if (!window.confirm(t('products.confirmDelete'))) return
    try {
      await deleteProduct(id)
      fetchProducts()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleSeed = async () => {
    setSeeding(true)
    setError('')
    try {
      await loadSampleData()
      await fetchProducts()
      getCategories().then(setCategories).catch(console.error)
    } catch (e) {
      setError(e.message)
    } finally {
      setSeeding(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const hasFilters = Boolean(search || category || inPromo)
  const isEmptyCatalogue = !loading && total === 0 && !hasFilters

  if (isEmptyCatalogue) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-20">
        <div className="text-5xl mb-4">🛒</div>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
          {t('products.empty.title')}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-6">
          {t('products.empty.desc', { n: (seedInfo?.available ?? 0).toLocaleString() })}
        </p>
        {seedInfo?.available > 0 && (
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-sm px-5 py-2.5 rounded-lg transition-colors"
          >
            {seeding ? t('products.empty.loading') : t('products.empty.load')}
          </button>
        )}
        {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-3 flex-wrap">
        <input
          type="text"
          placeholder={t('products.search')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className={`${inputClasses} flex-1 min-w-48`}
        />
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1) }}
          className={inputClasses}
        >
          <option value="">{t('products.allCategories')}</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={inPromo}
            onChange={(e) => { setInPromo(e.target.checked); setPage(1) }}
            className="rounded accent-blue-600"
          />
          🏷 {t('products.onlyPromo')}
        </label>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {loading ? t('products.loading') : t('products.found', { n: total.toLocaleString() })}
      </p>

      {error && (
        <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-900 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <th className="px-4 py-3 w-14">{t('products.col.image')}</th>
              <th className="px-4 py-3">{t('products.col.name')}</th>
              <th className="px-4 py-3">{t('products.col.category')}</th>
              <th className="px-4 py-3">{t('products.col.quantity')}</th>
              <th className="px-4 py-3">{t('products.col.price')}</th>
              <th className="px-4 py-3">{t('products.col.unit')}</th>
              <th className="px-4 py-3">{t('products.col.status')}</th>
              <th className="px-4 py-3">{t('products.col.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800 bg-white dark:bg-gray-950">
            {products.map((p) => (
              <tr key={p.id} className="hover:bg-blue-50 dark:hover:bg-gray-900 transition-colors">
                <td className="px-4 py-3">
                  {p.image_url ? (
                    <img
                      src={p.image_url}
                      alt={p.name}
                      loading="lazy"
                      className="w-10 h-10 object-contain rounded bg-white"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded bg-gray-100 dark:bg-gray-800" />
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 dark:text-gray-100">{p.name}</div>
                  {p.brand && <div className="text-xs text-gray-400 dark:text-gray-500">{p.brand}</div>}
                </td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">{p.category || '—'}</td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">{p.quantity || '—'}</td>
                <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">
                  {p.price != null ? `€\u00a0${Number(p.price).toFixed(2)}` : '—'}
                </td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">{p.unit || '—'}</td>
                <td className="px-4 py-3">
                  {p.is_in_promo ? (
                    <span className="inline-flex items-center gap-1 bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 text-xs font-medium px-2 py-0.5 rounded-full">
                      🏷 {t('products.promo')}{p.promo_price ? ` €${Number(p.promo_price).toFixed(2)}` : ''}
                    </span>
                  ) : (
                    <span className="text-gray-300 dark:text-gray-700 text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-3 items-center">
                    <button
                      onClick={() => setEditProduct(p)}
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-xs font-medium"
                    >
                      {t('products.edit')}
                    </button>
                    {p.url && (
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={t('products.view')}
                        className="text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-medium"
                      >
                        ↗
                      </a>
                    )}
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 text-xs font-medium"
                    >
                      {t('products.delete')}
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {!loading && products.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-400 dark:text-gray-600">
                  {t('products.none')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-900"
          >
            {t('products.prev')}
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-400 px-2">
            {t('products.page', { a: page, b: totalPages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-900"
          >
            {t('products.next')}
          </button>
        </div>
      )}

      {editProduct && (
        <ProductEditModal
          product={editProduct}
          onSave={() => { setEditProduct(null); fetchProducts() }}
          onClose={() => setEditProduct(null)}
        />
      )}
    </div>
  )
}
