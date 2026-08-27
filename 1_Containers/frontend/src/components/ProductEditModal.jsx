import { useState } from 'react'
import { updateProduct } from '../api'
import { useI18n } from '../i18n.jsx'

const FIELDS = [
  { labelKey: 'modal.name', key: 'name' },
  { labelKey: 'modal.brand', key: 'brand' },
  { labelKey: 'modal.price', key: 'price', type: 'number' },
  { labelKey: 'modal.pricePerUnit', key: 'price_per_unit', type: 'number' },
  { labelKey: 'modal.unit', key: 'unit' },
  { labelKey: 'modal.quantity', key: 'quantity' },
  { labelKey: 'modal.category', key: 'category' },
  { labelKey: 'modal.subcategory', key: 'subcategory' },
]

const inputClasses =
  'w-full border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

export default function ProductEditModal({ product, onSave, onClose }) {
  const { t } = useI18n()
  const [form, setForm] = useState({
    name: product.name ?? '',
    brand: product.brand ?? '',
    price: product.price ?? '',
    price_per_unit: product.price_per_unit ?? '',
    unit: product.unit ?? '',
    quantity: product.quantity ?? '',
    category: product.category ?? '',
    subcategory: product.subcategory ?? '',
    description: product.description ?? '',
    is_in_promo: product.is_in_promo ?? false,
    promo_price: product.promo_price ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await updateProduct(product.id, form)
      onSave()
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{t('modal.title')}</h2>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
              Colruyt ID: {product.colruyt_id}
              {product.url && (
                <>
                  {' · '}
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {t('products.view')} ↗
                  </a>
                </>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-6 py-4 space-y-4 flex-1">
          {FIELDS.map(({ labelKey, key, type = 'text' }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{t(labelKey)}</label>
              <input
                type={type}
                step={type === 'number' ? '0.01' : undefined}
                value={form[key]}
                onChange={set(key)}
                className={inputClasses}
              />
            </div>
          ))}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{t('modal.description')}</label>
            <textarea
              value={form.description}
              onChange={set('description')}
              rows={3}
              className={inputClasses}
            />
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_in_promo}
                onChange={set('is_in_promo')}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('modal.inPromo')}</span>
            </label>
            {form.is_in_promo && (
              <input
                type="number"
                step="0.01"
                placeholder={t('modal.promoPrice')}
                value={form.promo_price}
                onChange={set('promo_price')}
                className="border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg px-3 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>
        </div>

        {error && <p className="px-6 pb-2 text-red-600 dark:text-red-400 text-sm">{error}</p>}

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {t('modal.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? t('modal.saving') : t('modal.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
