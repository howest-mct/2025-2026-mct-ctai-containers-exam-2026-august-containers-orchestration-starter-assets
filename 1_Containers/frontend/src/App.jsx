import { useState } from 'react'
import ProductTable from './components/ProductTable'
import ScraperPanel from './components/ScraperPanel'
import { useI18n } from './i18n.jsx'

export default function App() {
  const [tab, setTab] = useState('products')
  const { lang, setLang, t } = useI18n()

  const tabs = [
    { id: 'products', label: t('app.tab.products') },
    { id: 'scraper', label: t('app.tab.scraper') },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Navbar */}
      <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-blue-700 dark:text-blue-400 text-lg">Colruyt</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-gray-600 dark:text-gray-300 font-medium text-sm">{t('app.title')}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {tabs.map((tb) => (
                <button
                  key={tb.id}
                  onClick={() => setTab(tb.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    tab === tb.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  {tb.label}
                </button>
              ))}
            </div>
            {/* Language switcher */}
            <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden text-xs font-semibold">
              {['nl', 'en'].map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`px-2.5 py-1.5 uppercase transition-colors ${
                    lang === l
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {tab === 'products' ? <ProductTable /> : <ScraperPanel />}
      </main>
    </div>
  )
}
