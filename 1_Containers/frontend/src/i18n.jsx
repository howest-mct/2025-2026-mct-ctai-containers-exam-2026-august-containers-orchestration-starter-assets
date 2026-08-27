import { createContext, useContext, useState, useEffect } from 'react'

const translations = {
  en: {
    'app.title': 'Product Catalogue',
    'app.tab.products': 'Products',
    'app.tab.scraper': 'Scraper',

    'products.search': 'Search by name or brand…',
    'products.allCategories': 'All categories',
    'products.onlyPromo': 'Only promotions',
    'products.found': '{n} products found',
    'products.loading': 'Loading…',
    'products.col.image': '',
    'products.col.name': 'Name',
    'products.col.category': 'Category',
    'products.col.quantity': 'Quantity',
    'products.col.price': 'Price',
    'products.col.unit': 'Unit',
    'products.col.status': 'Status',
    'products.col.actions': 'Actions',
    'products.edit': 'Edit',
    'products.delete': 'Delete',
    'products.view': 'View on Colruyt',
    'products.promo': 'Promo',
    'products.none': 'No products found',
    'products.empty.title': 'No products yet',
    'products.empty.desc': 'Run the scraper, or load the bundled sample dataset ({n} products) to get started.',
    'products.empty.load': 'Load sample data',
    'products.empty.loading': 'Loading sample data…',
    'products.page': 'Page {a} of {b}',
    'products.prev': '‹ Previous',
    'products.next': 'Next ›',
    'products.confirmDelete': 'Permanently delete this product?',

    'modal.title': 'Edit product',
    'modal.name': 'Name',
    'modal.brand': 'Brand',
    'modal.price': 'Price (€)',
    'modal.pricePerUnit': 'Price per unit (€)',
    'modal.unit': 'Unit',
    'modal.quantity': 'Quantity',
    'modal.category': 'Category',
    'modal.subcategory': 'Subcategory',
    'modal.description': 'Description',
    'modal.inPromo': 'In promotion',
    'modal.promoPrice': 'Promo price (€)',
    'modal.cancel': 'Cancel',
    'modal.save': 'Save',
    'modal.saving': 'Saving…',

    'scraper.title': 'Scraper management',
    'scraper.running': 'Scraper is running…',
    'scraper.idle': 'Scraper is idle',
    'scraper.scraped': 'scraped',
    'scraper.new': 'new',
    'scraper.updated': 'updated',
    'scraper.start': '▶ Start scraper',
    'scraper.starting': 'Starting…',
    'scraper.busy': 'Scraping in progress…',
    'scraper.hint':
      'The scraper visits every category on colruyt.be and stores each product in the database. This can take several minutes.',
    'scraper.history': 'History',
    'scraper.noRuns': 'No scraper runs yet',
    'scraper.products': 'products',
    'scraper.liveLog': 'Live log',
    'scraper.live': 'live',
    'scraper.noLogs': 'No log lines yet — start the scraper to see activity.',
  },
  nl: {
    'app.title': 'Productcatalogus',
    'app.tab.products': 'Producten',
    'app.tab.scraper': 'Scraper',

    'products.search': 'Zoek op naam of merk…',
    'products.allCategories': 'Alle categorieën',
    'products.onlyPromo': 'Alleen promoties',
    'products.found': '{n} producten gevonden',
    'products.loading': 'Laden…',
    'products.col.image': '',
    'products.col.name': 'Naam',
    'products.col.category': 'Categorie',
    'products.col.quantity': 'Hoeveelheid',
    'products.col.price': 'Prijs',
    'products.col.unit': 'Eenheid',
    'products.col.status': 'Status',
    'products.col.actions': 'Acties',
    'products.edit': 'Bewerken',
    'products.delete': 'Verwijder',
    'products.view': 'Bekijk op Colruyt',
    'products.promo': 'Promo',
    'products.none': 'Geen producten gevonden',
    'products.empty.title': 'Nog geen producten',
    'products.empty.desc': 'Start de scraper, of laad de meegeleverde voorbeelddataset ({n} producten) om te beginnen.',
    'products.empty.load': 'Voorbeelddata laden',
    'products.empty.loading': 'Voorbeelddata laden…',
    'products.page': 'Pagina {a} van {b}',
    'products.prev': '‹ Vorige',
    'products.next': 'Volgende ›',
    'products.confirmDelete': 'Dit product permanent verwijderen?',

    'modal.title': 'Product bewerken',
    'modal.name': 'Naam',
    'modal.brand': 'Merk',
    'modal.price': 'Prijs (€)',
    'modal.pricePerUnit': 'Prijs per eenheid (€)',
    'modal.unit': 'Eenheid',
    'modal.quantity': 'Hoeveelheid',
    'modal.category': 'Categorie',
    'modal.subcategory': 'Subcategorie',
    'modal.description': 'Beschrijving',
    'modal.inPromo': 'In promotie',
    'modal.promoPrice': 'Promo prijs (€)',
    'modal.cancel': 'Annuleren',
    'modal.save': 'Opslaan',
    'modal.saving': 'Opslaan…',

    'scraper.title': 'Scraper beheer',
    'scraper.running': 'Scraper is bezig…',
    'scraper.idle': 'Scraper is inactief',
    'scraper.scraped': 'gescraped',
    'scraper.new': 'nieuw',
    'scraper.updated': 'bijgewerkt',
    'scraper.start': '▶ Start scraper',
    'scraper.starting': 'Starten…',
    'scraper.busy': 'Bezig met scrapen…',
    'scraper.hint':
      'De scraper bezoekt alle categorieën op colruyt.be en slaat elk product op in de database. Dit kan meerdere minuten duren.',
    'scraper.history': 'Geschiedenis',
    'scraper.noRuns': 'Nog geen scraper-runs',
    'scraper.products': 'producten',
    'scraper.liveLog': 'Live log',
    'scraper.live': 'live',
    'scraper.noLogs': 'Nog geen logregels — start de scraper om activiteit te zien.',
  },
}

const LanguageContext = createContext(null)

function detectLanguage() {
  const saved = localStorage.getItem('lang')
  if (saved === 'en' || saved === 'nl') return saved
  return navigator.language?.toLowerCase().startsWith('nl') ? 'nl' : 'en'
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(detectLanguage)

  useEffect(() => {
    localStorage.setItem('lang', lang)
    document.documentElement.lang = lang
  }, [lang])

  const t = (key, vars = {}) => {
    let text = translations[lang][key] ?? key
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(`{${k}}`, v)
    }
    return text
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useI18n() {
  return useContext(LanguageContext)
}
