import { useState, useEffect, useCallback, useRef } from 'react'
import { triggerScraper, getScraperStatus, getScraperHistory, getScraperLogs } from '../api'
import { useI18n } from '../i18n.jsx'

const STATUS_STYLES = {
  completed: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  running: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300',
}

export default function ScraperPanel() {
  const { lang, t } = useI18n()
  const [status, setStatus] = useState(null)
  const [history, setHistory] = useState([])
  const [triggering, setTriggering] = useState(false)
  const [error, setError] = useState('')
  const [logs, setLogs] = useState([])
  const lastLogIdRef = useRef(0)
  const logBoxRef = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const [s, h] = await Promise.all([getScraperStatus(), getScraperHistory()])
      setStatus(s)
      setHistory(h)
    } catch (e) {
      console.error(e)
    }
  }, [])

  const fetchLogs = useCallback(async () => {
    try {
      const data = await getScraperLogs(lastLogIdRef.current)
      if (data.lines.length > 0) {
        lastLogIdRef.current = data.lines[data.lines.length - 1].id
        setLogs((prev) => [...prev, ...data.lines].slice(-500))
      }
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    refresh()
    fetchLogs()
    const statusId = setInterval(refresh, 5000)
    const logsId = setInterval(fetchLogs, 2000)
    return () => {
      clearInterval(statusId)
      clearInterval(logsId)
    }
  }, [refresh, fetchLogs])

  // Auto-scroll the log console as new lines arrive
  useEffect(() => {
    const el = logBoxRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [logs])

  const handleStart = async () => {
    setTriggering(true)
    setError('')
    try {
      await triggerScraper()
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setTriggering(false)
    }
  }

  const isRunning = status?.is_running
  const latest = status?.latest_run

  const fmt = (dt) => (dt ? new Date(dt).toLocaleString(lang === 'nl' ? 'nl-BE' : 'en-GB') : '—')

  return (
    <div className="max-w-2xl space-y-6">
      {/* Control card */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">{t('scraper.title')}</h2>

        <div className="flex items-center gap-3 mb-5">
          <span
            className={`w-3 h-3 rounded-full flex-shrink-0 ${
              isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-300 dark:bg-gray-700'
            }`}
          />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isRunning ? t('scraper.running') : t('scraper.idle')}
          </span>
        </div>

        {/* Live progress */}
        {isRunning && latest && (
          <div className="mb-5 bg-blue-50 dark:bg-blue-950 border border-blue-100 dark:border-blue-900 rounded-lg px-4 py-3 text-sm text-blue-800 dark:text-blue-200 grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-2xl font-bold">{latest.products_scraped}</div>
              <div className="text-xs">{t('scraper.scraped')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">{latest.products_new}</div>
              <div className="text-xs">{t('scraper.new')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-500 dark:text-orange-400">{latest.products_updated}</div>
              <div className="text-xs">{t('scraper.updated')}</div>
            </div>
          </div>
        )}

        {error && (
          <p className="mb-4 text-sm text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          onClick={handleStart}
          disabled={isRunning || triggering}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm px-5 py-2.5 rounded-lg transition-colors"
        >
          {isRunning ? t('scraper.busy') : triggering ? t('scraper.starting') : t('scraper.start')}
        </button>

        <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">{t('scraper.hint')}</p>
      </div>

      {/* Live log */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 dark:text-gray-200">{t('scraper.liveLog')}</h3>
          {isRunning && (
            <span className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              {t('scraper.live')}
            </span>
          )}
        </div>

        <div
          ref={logBoxRef}
          className="bg-gray-900 dark:bg-black rounded-lg p-4 h-72 overflow-y-auto font-mono text-xs leading-relaxed"
        >
          {logs.length === 0 ? (
            <p className="text-gray-500">{t('scraper.noLogs')}</p>
          ) : (
            logs.map((line) => (
              <div key={line.id} className="whitespace-pre-wrap break-words">
                <span className="text-gray-500">{line.time}</span>{' '}
                <span
                  className={
                    line.level === 'ERROR'
                      ? 'text-red-400'
                      : line.level === 'WARNING'
                        ? 'text-yellow-400'
                        : 'text-green-400'
                  }
                >
                  {line.level}
                </span>{' '}
                <span className="text-gray-100">{line.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* History */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-6">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4">{t('scraper.history')}</h3>

        {history.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500">{t('scraper.noRuns')}</p>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {history.map((run) => (
              <div key={run.id} className="py-3 flex items-center justify-between gap-4 text-sm">
                <div className="flex items-center gap-3 min-w-0">
                  <span
                    className={`flex-shrink-0 px-2 py-0.5 rounded text-xs font-medium ${
                      STATUS_STYLES[run.status] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {run.status}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400 text-xs truncate">{fmt(run.started_at)}</span>
                </div>
                <div className="text-right flex-shrink-0 text-xs text-gray-600 dark:text-gray-400">
                  <span className="font-medium">{run.products_scraped}</span> {t('scraper.products')}
                  {run.error_message && (
                    <span className="block text-red-500 dark:text-red-400 max-w-xs truncate" title={run.error_message}>
                      {run.error_message}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
