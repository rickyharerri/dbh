import { useEffect, useRef, useState } from 'react'
import { fmtCoord } from '../lib/format'
import { useActions, useAppState, useHealth, type ChatMessage } from '../state/AppContext'
import { Spinner } from '../components/LoadingState'
import { EmptyState, Notice, PageTitle } from '../components/ui'
import type { GenieTable } from '../types/groundwater'

const SUGGESTIONS = [
  'How many water wells are near Cochrane?',
  'What is the typical well depth around Okotoks?',
  'Which nearby wells have low recorded yields?',
  'Compare historical groundwater conditions in two areas.',
  'What water-quality information is available?',
]
const MAX = 1000

function ResultTable({ t }: { t: GenieTable }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table className="w-full min-w-[320px] text-left text-sm">
        <caption className="sr-only">Query result table</caption>
        <thead className="bg-slate-50"><tr>{t.columns.map((c) => <th key={c} scope="col" className="px-3 py-1.5">{c}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">
          {t.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j} className="px-3 py-1.5 tabular-nums">{v ?? 'Not available'}</td>)}</tr>)}
        </tbody>
      </table>
      {t.truncated && <p className="border-t border-slate-200 p-2 text-xs text-slate-600">Showing the first {t.rows.length} of {t.row_count} rows.</p>}
    </div>
  )
}

function Bubble({ m }: { m: ChatMessage }) {
  if (m.role === 'user') {
    return (
      <li className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-teal-700 px-4 py-2 text-white">{m.text}</p>
      </li>
    )
  }
  const r = m.response
  const error = m.role === 'error'
  return (
    <li className="flex justify-start">
      <div className={`max-w-[92%] rounded-2xl rounded-bl-sm border px-4 py-3 ${error ? 'border-red-300 bg-red-50 text-red-900' : 'border-slate-200 bg-slate-50'}`}
           role={error ? 'alert' : undefined}>
        <p className="whitespace-pre-wrap">{m.text}</p>
        {!error && r?.data && <ResultTable t={r.data} />}
        {!error && r?.query?.sql && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-medium text-sky-800">View the query behind this answer</summary>
            {r.query.description && <p className="mt-1 text-slate-700">{r.query.description}</p>}
            <pre className="mt-1 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">{r.query.sql}</pre>
          </details>
        )}
      </div>
    </li>
  )
}

export default function GeniePage({ active }: { active: boolean }) {
  const { chat, location, radiusKm } = useAppState()
  const a = useActions()
  const health = useHealth()
  const [draft, setDraft] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const configured = health?.features.genie ?? false

  useEffect(() => {
    if (active) end.current?.scrollIntoView({ block: 'end' })
  }, [chat.messages.length, chat.sending, active])

  const send = (text: string) => {
    if (!text.trim() || chat.sending || !configured) return
    setDraft('')
    void a.sendChat(text)
  }

  return (
    <div className="space-y-5">
      <PageTitle title="Ask AquaWise">Ask questions about Alberta’s historical groundwater information.</PageTitle>

      {health && !configured && (
        <EmptyState title="AI assistant not configured">
          <p>
            {health.mode === 'demo'
              ? 'Demo mode only contains synthetic wells, so the AI assistant is turned off to avoid answers that look real.'
              : 'Ask AquaWise needs a Databricks Genie space. An administrator can enable it by setting GENIE_SPACE_ID.'}
          </p>
        </EmptyState>
      )}

      <section className="panel" aria-label="Conversation">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
          <h2 className="text-lg font-semibold">Conversation</h2>
          <button type="button" className="btn btn-secondary !min-h-[40px]" onClick={a.clearChat}
                  disabled={chat.messages.length === 0 && !chat.sending}>Clear conversation</button>
        </div>

        <div className="max-h-[55vh] min-h-[200px] overflow-y-auto p-4">
          {chat.messages.length === 0 && !chat.sending ? (
            <p className="text-slate-700">No messages yet. Pick a suggested question or type your own below.</p>
          ) : (
            <ol className="space-y-3" aria-live="polite" aria-label="Messages">
              {chat.messages.map((m) => <Bubble key={m.id} m={m} />)}
            </ol>
          )}
          {chat.sending && (
            <p role="status" className="mt-3 flex items-center gap-2 text-slate-700">
              <Spinner className="h-5 w-5 text-teal-700" /> AquaWise is working on your question… this can take up to a minute.
            </p>
          )}
          <div ref={end} />
        </div>

        <div className="space-y-3 border-t border-slate-200 p-4">
          <div>
            <p className="mb-1 text-sm font-semibold text-slate-700">Suggested questions</p>
            <ul className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <li key={q}>
                  <button type="button" className="min-h-[44px] rounded-full border border-slate-300 bg-white px-3 text-left text-base hover:bg-slate-50 disabled:opacity-50"
                          disabled={!configured || chat.sending} onClick={() => send(q)}>{q}</button>
                </li>
              ))}
            </ul>
          </div>

          <label className="flex items-start gap-2 text-base">
            <input type="checkbox" className="mt-1 h-5 w-5" checked={chat.includeLocation && !!location}
                   disabled={!location || !configured} onChange={(e) => a.setIncludeLocation(e.target.checked)} />
            <span>
              Include my selected map location with my question
              <span className="block text-sm text-slate-600">
                {location
                  ? `Sends ${fmtCoord(location)} and a ${radiusKm} km radius to the assistant as part of your question. Otherwise it does not know where you clicked.`
                  : 'Choose a location on the Explore Property tab to use this.'}
              </span>
            </span>
          </label>

          <div className="flex items-end gap-2">
            <div className="grow">
              <label htmlFor="chat-input" className="text-sm font-semibold text-slate-700">Your question</label>
              <textarea
                id="chat-input" className="field mt-1 resize-y" rows={2} maxLength={MAX} value={draft} disabled={!configured}
                placeholder="e.g. What is the deepest recorded well near Cochrane?"
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(draft) } }}
              />
              <p className="text-right text-xs text-slate-600">{draft.length}/{MAX} · Enter to send, Shift+Enter for a new line</p>
            </div>
            <button type="button" className="btn btn-primary mb-6" disabled={!configured || chat.sending || !draft.trim()} onClick={() => send(draft)}>
              Send
            </button>
          </div>
        </div>
      </section>

      <Notice>
        Answers come from Databricks Genie and are generated from the groundwater tables. Check important figures against the
        records, and remember these are historical records — not a water safety certification.
      </Notice>
    </div>
  )
}
