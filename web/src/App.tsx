import { useEffect, useMemo, useRef, useState } from 'react'
import { sampleReply, sampleText } from './mocks/demo'
import type { Mapping } from './api'
import {
  decodeText,
  deleteMapping,
  encodeText,
  extractFile,
  fileToBase64,
  health,
  listMappings,
  upsertMapping,
  API_STAGE,
} from './api'
import { extractPdfText } from './pdfExtract'
import { loadWorkspace, saveWorkspace, loadSession, saveSession } from './persist'
import type { DocTab } from './types'
import { DocumentTabs } from './components/DocumentTabs'
import { Vault } from './components/Vault'
import { nextManualToken, redactableTextParts, updateRedactedOutput } from './manualRedaction'
import './App.css'

type Page = 'Encode' | 'Decode' | 'Vault'

type Document = {
  id: number
  name: string
  input: string
  reply: string
  output: string
  restored: string
  unknown: string[]
  mappings: Mapping[]
  nextIdx: Record<string, number>
  manualMappings?: Mapping[]
  excludedValues?: string[]
}

function newDocument(id: number, name?: string): Document {
  return {
    id,
    name: name ?? `document-${id}.txt`,
    input: '',
    reply: '',
    output: '',
    restored: '',
    unknown: [],
    mappings: [],
    nextIdx: {},
  }
}

function loadSessionId(): string | null {
  return loadSession()
}

function saveSessionId(id: string) {
  saveSession(id)
}

function NavIcon({ page }: { page: Page }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      {page === 'Vault' ? (
        <>
          <rect x="3" y="4" width="18" height="5" rx="1" />
          <path d="M5 9v11h14V9M10 13h4" />
        </>
      ) : (
        <>
          <rect x="5" y="10" width="14" height="11" rx="2" />
          <path d={page === 'Encode' ? 'M8 10V6a4 4 0 0 1 8 0v4' : 'M8 10V6a4 4 0 0 1 8 0'} />
        </>
      )}
    </svg>
  )
}

function TokenText({ text, mappings, excludedValues, onPick, onRestore, busy }: {
  text: string; mappings: Mapping[]; excludedValues: string[]
  onPick: (word: string) => void; onRestore: (mapping: Mapping) => void; busy: boolean
}) {
  return text.split(/(\[[A-Za-z][A-Za-z0-9_:]*_\d+\])/g).map((part, index) => {
    const mapping = mappings.find((m) => `[${m.token}]` === part)
    if (mapping) return <button key={index} type="button" className={`token-restore token-${mapping.category.toLowerCase()}`}
      disabled={busy} aria-label={`Unredact ${mapping.value}`} title="Click to unredact this value"
      onClick={() => onRestore(mapping)}>{part}</button>
    if (index % 2) return part
    return <span key={index}>{redactableTextParts(part, excludedValues).map((word, i) => (
      i % 2 && word.length >= 2
        ? <button key={i} type="button" className="word-redact" disabled={busy}
            aria-label={`Redact ${word}`} title="Click to redact this text" onClick={() => onPick(word)}>{word}</button>
        : word
    ))}</span>
  })
}

function wordAtSelection(textarea: HTMLTextAreaElement): string {
  const text = textarea.value
  let start = textarea.selectionStart
  let end = textarea.selectionEnd
  if (start === end) {
    while (start > 0 && /[\p{L}\p{N}'’@._+-]/u.test(text[start - 1] ?? '')) start -= 1
    while (end < text.length && /[\p{L}\p{N}'’@._+-]/u.test(text[end] ?? '')) end += 1
  }
  return text.slice(start, end).trim()
}

const CLASS_OPTIONS = ['Name', 'Email', 'Phone', 'Location', 'Date', 'Passport', 'Ssn', 'Iban', 'CreditCard', 'Organization', 'Custom']

function guessClass(word: string): string {
  if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(word)) return 'Email'
  if (/^[+()\d][\d\s()-]{6,}$/.test(word)) return 'Phone'
  if (/^\d{4}[-\s]?\d{4}/.test(word.replace(/\s/g, ''))) return 'CreditCard'
  if (/^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$/.test(word)) return 'Name'
  return 'Custom'
}

function App() {
  const restored = useRef(loadWorkspace()).current
  const [page, setPage] = useState<Page>('Encode')
  const [light, setLight] = useState(false)
  /** 1. One shared documents array — single source of truth. */
  const [documents, setDocuments] = useState<Document[]>(() => restored?.documents ?? [newDocument(1)])
  /** 2. Two independent active-id pointers, one per view. */
  const [activeEncode, setActiveEncode] = useState<number | null>(restored ? restored.activeEncode : 1)
  const [activeVault, setActiveVault] = useState<number | null>(restored ? restored.activeVault : 1)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [apiStatus, setApiStatus] = useState<string>('checking…')
  const [sessionId, setSessionId] = useState<string | null>(loadSessionId)
  const [draftToken, setDraftToken] = useState<{ value: string; cls: string } | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  /** 3. Naming counter only — never used as an id. */
  const docCounter = useRef(restored?.docCounter ?? 1)

  const encoding = page === 'Encode'
  const activeViewId = page === 'Vault' ? activeVault : activeEncode
  const active: Document | undefined = documents.find((doc) => doc.id === activeViewId) ?? documents[0]
  const input = (encoding ? active?.input : active?.reply) ?? ''
  const output = (encoding ? active?.output : active?.restored) ?? ''

  // Persist workspace (documents + view pointers + session) on every change.
  useEffect(() => {
    saveWorkspace({
      documents,
      activeEncode,
      activeVault,
      sessionId,
      docCounter: docCounter.current,
    })
  }, [documents, activeEncode, activeVault, sessionId])

  useEffect(() => {
    health()
      .then((h) => setApiStatus(`API ${h.env} · v${h.version}`))
      .catch(() => setApiStatus('API offline'))
    // Re-hydrate mappings from the server session so a refresh keeps the vault.
    const sid = loadSessionId()
    if (sid) {
      listMappings(sid)
        .then((res) => {
          setDocuments((prev) => {
            if (prev.some((d) => d.mappings.length > 0 || d.excludedValues?.length)) return prev
            return prev.map((d, i) => (i === 0 ? { ...d, mappings: res.mappings } : d))
          })
        })
        .catch(() => {
          /* session may have expired */
        })
    }
  }, [])

  const tabDocs: DocTab[] = useMemo(() => documents.map((d) => ({ id: d.id, name: d.name })), [documents])

  function updateDocument(id: number, changes: Partial<Document>) {
    setDocuments((previous) => previous.map((doc) => (doc.id === id ? { ...doc, ...changes } : doc)))
  }

  function navigate(next: Page) {
    setPage(next)
    setNotice('')
    setDraftToken(null)
  }

  /** Jump keeps the same document scoped in the destination view. */
  function jumpTo(target: Page) {
    if (active) {
      if (target === 'Vault') setActiveVault(active.id)
      else setActiveEncode(active.id)
    }
    navigate(target)
  }

  /** Close reconciles both views, including an empty workspace. */
  function closeDocument(id: number) {
    const remaining = documents.filter((doc) => doc.id !== id)
    const nextId = remaining[0]?.id ?? null
    setDocuments(remaining)
    if (activeEncode === id || !remaining.length) setActiveEncode(nextId)
    if (activeVault === id || !remaining.length) setActiveVault(nextId)
    setNotice('Document closed.')
    setDraftToken(null)
  }

  /** Add: new empty doc; both views jump to it. */
  function addDocument() {
    docCounter.current += 1
    const id = Date.now() + docCounter.current
    const doc = newDocument(id, `document-${docCounter.current}.txt`)
    setDocuments((previous) => [...previous, doc])
    setActiveEncode(doc.id)
    setActiveVault(doc.id)
    setNotice('')
    setDraftToken(null)
  }

  async function syncRedactions(document: Document, manualMappings = document.manualMappings ?? [], excludedValues = document.excludedValues ?? []) {
    const result = await encodeText(sessionId, document.input, undefined, manualMappings, excludedValues)
    for (const old of document.mappings) {
      if (!result.mappings.some(mapping => mapping.token === old.token)) await deleteMapping(result.sessionId, old.token)
    }
    const nextIdx = { ...document.nextIdx }
    for (const mapping of result.mappings) {
      const index = Number(mapping.token.match(/_(\d+)$/)?.[1] ?? 0)
      nextIdx[mapping.category] = Math.max(nextIdx[mapping.category] ?? 1, index + 1)
    }
    updateDocument(document.id, {
      output: result.redactedText, mappings: result.mappings, manualMappings, excludedValues,
      restored: '', unknown: [], nextIdx,
    })
    saveSessionId(result.sessionId)
    setSessionId(result.sessionId)
    return result
  }

  async function encode() {
    if (!active || busy) return
    setBusy(true)
    setNotice('')
    try {
      const result = await syncRedactions(active)
      setNotice(`${result.mappings.length} values replaced · session ${result.sessionId.slice(0, 8)}…`)
    } catch (e) {
      setNotice(`Encode failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function decode() {
    if (!active) return
    if (!sessionId) {
      setNotice('No session yet. Encode text first so the server can store mappings.')
      return
    }
    setBusy(true)
    setNotice('')
    try {
      const result = await decodeText(sessionId, active.reply)
      updateDocument(active.id, {
        restored: result.restoredText,
        unknown: result.hallucinations,
      })
      setNotice(
        result.hallucinations.length
          ? `Restored with ${result.hallucinations.length} unknown token(s) left unchanged.`
          : 'Response restored from the server session vault.'
      )
    } catch (e) {
      setNotice(`Decode failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function changeMappings(mappings: Mapping[]): Promise<boolean> {
    if (busy || !active) return false
    const document = active
    const sid = sessionId ?? crypto.randomUUID()
    setBusy(true)
    setNotice('')
    try {
      for (const old of document.mappings) {
        if (!mappings.some((m) => m.token === old.token)) await deleteMapping(sid, old.token)
      }
      for (const next of mappings) {
        const before = document.mappings.find((p) => p.token === next.token)
        if (!before || before.value !== next.value || before.category !== next.category) {
          await upsertMapping(sid, { token: next.token, value: next.value, category: next.category })
        }
      }
      const manualMappings = mappings.flatMap(mapping => {
        const rule = document.manualMappings?.find(entry => entry.token === mapping.token)
        const before = document.mappings.find(entry => entry.token === mapping.token)
        if (!rule && before?.value === mapping.value) return []
        return [{ ...mapping, sourceValue: rule?.sourceValue ?? rule?.value ?? before?.value ?? mapping.value }]
      })
      updateDocument(document.id, {
        mappings, manualMappings,
        output: updateRedactedOutput(document.output, document.mappings, mappings),
        restored: '', unknown: [],
      })
      saveSessionId(sid)
      setSessionId(sid)
      setNotice('Vault updated on the server.')
      return true
    } catch (e) {
      setNotice(`Vault sync failed: ${e instanceof Error ? e.message : String(e)}`)
      return false
    } finally {
      setBusy(false)
    }
  }

  async function addTokenFromWord(word: string) {
    if (!active || busy || !word.trim()) return
    const category = guessClass(word)
    const token = nextManualToken(category, documents.flatMap(doc => doc.mappings), active.nextIdx)
    const mapping: Mapping = { token, value: word, category, firstOffset: Math.max(0, active.input.indexOf(word)) }
    const rules = [...(active.manualMappings ?? []), mapping]
    const excludedValues = (active.excludedValues ?? []).filter(value => value !== word)
    setBusy(true)
    setNotice('')
    try {
      await syncRedactions(active, rules, excludedValues)
      setNotice('Text redacted. Click its token to restore it.')
    } catch (e) {
      setNotice(`Redaction failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function restoreToken(mapping: Mapping) {
    if (!active || busy) return
    const rule = active.manualMappings?.find(entry => entry.token === mapping.token)
    const sourceValue = rule?.sourceValue ?? rule?.value ?? mapping.value
    const rules = (active.manualMappings ?? []).filter(entry => entry.token !== mapping.token)
    const excludedValues = [...new Set([...(active.excludedValues ?? []), sourceValue, mapping.value])]
    setBusy(true)
    setNotice('')
    try {
      await syncRedactions(active, rules, excludedValues)
      setNotice('Text restored. It will stay visible when you encode again.')
    } catch (e) {
      setNotice(`Unredaction failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function commitDraftToken() {
    if (!active || !draftToken || busy || !draftToken.value.trim()) return
    const draft = draftToken
    const document = active
    const value = draft.value.trim()
    if (document.mappings.some(mapping => mapping.value === value)) {
      setNotice('This value already has a token. Edit its existing mapping instead.')
      return
    }
    const token = nextManualToken(draft.cls, documents.flatMap(doc => doc.mappings), document.nextIdx)
    const mapping: Mapping = { token, value, category: draft.cls, firstOffset: Math.max(0, document.input.indexOf(value)) }
    const manualMappings = [...(document.manualMappings ?? []), mapping]
    const sid = sessionId ?? crypto.randomUUID()
    setBusy(true)
    setNotice('')
    try {
      let mappings = [...document.mappings, mapping]
      let output = document.output
      if (document.input.trim()) {
        // Apply manual rules on the server so the redacted output, mappings and S3 archive agree.
        const result = await encodeText(sid, document.input, undefined, manualMappings, document.excludedValues ?? [])
        mappings = result.mappings
        output = result.redactedText
      } else {
        await upsertMapping(sid, { token, value, category: draft.cls })
      }
      const nextIdx = { ...document.nextIdx }
      for (const entry of mappings) {
        const index = Number(entry.token.match(/_(\d+)$/)?.[1] ?? 0)
        nextIdx[entry.category] = Math.max(nextIdx[entry.category] ?? 1, index + 1)
      }
      updateDocument(document.id, { mappings, output, manualMappings, nextIdx, restored: '', unknown: [] })
      saveSessionId(sid)
      setSessionId(sid)
      setDraftToken(current => current === draft ? null : current)
      setNotice(document.input.trim() ? 'Token saved and redacted output updated.' : 'Token saved to the server vault.')
    } catch (e) {
      // Keep the form and its value available for correction/retry.
      setNotice(`Vault sync failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  /**
   * 5. Upload writes only to the active document.
   * PDF text is extracted in the browser (avoids HTTP 413 on large PDFs).
   * DOCX still goes through /extract (base64) — those files are much smaller.
   */
  async function upload(file?: File) {
    if (!file || !active) return
    if (!/\.(txt|md|pdf|docx)$/i.test(file.name)) {
      setNotice('Choose a .txt, .md, .pdf, or .docx file.')
      return
    }
    if (file.size > 25_000_000) {
      setNotice('Choose a file smaller than 25 MB.')
      return
    }
    const documentId = active.id
    setBusy(true)
    try {
      let text = ''
      if (/\.pdf$/i.test(file.name)) {
        text = await extractPdfText(file)
        setNotice(`Extracted ${text.length} characters from ${file.name} in the browser.`)
      } else if (/\.docx$/i.test(file.name)) {
        const fileBase64 = await fileToBase64(file)
        const extracted = await extractFile(file.name, { fileBase64 })
        text = extracted.text
        setNotice(`Extracted ${text.length} characters from ${file.name}.`)
      } else {
        text = await file.text()
        setNotice(`File loaded. Ready to ${encoding ? 'encode' : 'decode'}.`)
      }
      updateDocument(
        documentId,
        encoding ? { name: file.name, input: text, output: '' } : { reply: text, restored: '', unknown: [] }
      )
    } catch (e) {
      setNotice(`Upload failed: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setNotice('Copied to clipboard.')
    } catch {
      setNotice('Could not copy automatically. Select the output and copy it manually.')
    }
  }

  const descriptions = {
    Encode: 'Click a word to redact it. Click a token to restore its text.',
    Decode: 'Restore tokens using the server session vault.',
    Vault: 'Inspect and edit mappings for the active document.',
  }

  return (
    <div className={`app-shell${light ? ' light' : ''}`}>
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate('Encode')} aria-label="Poco home">
          <span className="logo-frame">
            <img src={`${import.meta.env.BASE_URL}poco_logo.png`} alt="" />
          </span>
          <span>Poco</span>
        </button>
        <nav aria-label="Main navigation">
          {(['Encode', 'Decode', 'Vault'] as const).map((item) => (
            <button
              key={item}
              className={`nav-item${page === item ? ' active' : ''}`}
              aria-current={page === item ? 'page' : undefined}
              onClick={() => jumpTo(item)}
            >
              <NavIcon page={item} />
              <span>
                <strong>{item}</strong>
                <small>
                  {
                    {
                      Encode: 'Protect sensitive text',
                      Decode: 'Restore original text',
                      Vault: 'Inspect stored mappings',
                    }[item]
                  }
                </small>
              </span>
            </button>
          ))}
        </nav>
        <p className="demo-note">
          Stage: <strong>{API_STAGE}</strong>
          <br />
          {apiStatus}
          {sessionId ? (
            <>
              <br />
              Session: <code>{sessionId.slice(0, 8)}…</code>
            </>
          ) : null}
        </p>
      </aside>
      <div className="main-shell">
        <main>
          <div className="page-heading">
            <div>
              <h1>{page}</h1>
              <p>{descriptions[page]}</p>
            </div>
            <div className="page-actions">
              {active && page === 'Vault' && (
                <button
                  className="danger"
                  disabled={busy || !active.mappings.length}
                  onClick={() => {
                    void changeMappings([])
                  }}
                >
                  Reset vault
                </button>
              )}
              <button
                className="theme-button"
                onClick={() => setLight(!light)}
                aria-label={`Switch to ${light ? 'dark' : 'light'} theme`}
              >
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2" />
                </svg>
              </button>
            </div>
          </div>

          {/* Shared strip: each view passes its own activeId + switch callback */}
          {active && (
            <DocumentTabs
              documents={tabDocs}
              activeId={active.id}
              onSelect={(id) => {
                if (page === 'Vault') setActiveVault(id)
                else setActiveEncode(id)
                setNotice('')
                setDraftToken(null)
              }}
              onClose={closeDocument}
              onAdd={addDocument}
              onRename={(id, name) => {
                updateDocument(id, { name })
                setNotice('Document renamed.')
              }}
            />
          )}

          {!active && (
            <section className="workspace-empty" aria-labelledby="workspace-empty-title">
              <h2 id="workspace-empty-title">No documents open</h2>
              <p>Create a document to get started.</p>
              <button className="secondary" autoFocus onClick={addDocument}>New document</button>
            </section>
          )}

          {active && page !== 'Vault' && (
            <>
              <div className="editors">
                <section className="editor">
                  <div className="editor-heading">
                    <label htmlFor="source-input">{encoding ? 'Original text' : 'Redacted text'}</label>
                    <div>
                      <button className="quiet" onClick={() => fileInput.current?.click()}>
                        Upload file
                      </button>
                      <button
                        className="quiet"
                        onClick={() => {
                          updateDocument(
                            active.id,
                            encoding
                              ? { input: sampleText, output: '' }
                              : { reply: sampleReply, restored: '', unknown: [] }
                          )
                          setNotice('Example loaded.')
                        }}
                      >
                        Use example
                      </button>
                      <input
                        ref={fileInput}
                        type="file"
                        accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        className="sr-only"
                        tabIndex={-1}
                        aria-label="Upload text, PDF, or DOCX file"
                        onChange={(e) => {
                          void upload(e.target.files?.[0])
                          e.target.value = ''
                        }}
                      />
                    </div>
                  </div>
                  <div>
                    <textarea
                      id="source-input"
                      ref={inputRef}
                      disabled={busy}
                      value={input}
                      onChange={(e) => {
                        updateDocument(
                          active.id,
                          encoding ? { input: e.target.value, output: '' } : { reply: e.target.value, restored: '', unknown: [] }
                        )
                        setNotice('')
                      }}
                      placeholder={
                        encoding
                          ? 'Type or paste text here, or upload a file…'
                          : 'Paste text with redactions here, or upload a file…'
                      }
                      spellCheck={false}
                    />
                  </div>
                </section>
                <section className="editor">
                  <div className="editor-heading">
                    <h2 id="output-label">{encoding ? 'Redacted text' : 'Restored text'}</h2>
                    <button className="quiet" disabled={!output} onClick={() => copy(output)}>
                      Copy
                    </button>
                  </div>
                  <pre className="output" tabIndex={0} aria-labelledby="output-label">
                    {output ? (
                      encoding ? (
                        <TokenText text={output} mappings={active.mappings} excludedValues={active.excludedValues ?? []}
                          onPick={(word) => void addTokenFromWord(word)} onRestore={(mapping) => void restoreToken(mapping)} busy={busy} />
                      ) : (
                        output
                      )
                    ) : (
                      <span className="placeholder">
                        {encoding ? 'Run Encode to see tokenized output.' : 'Run Decode to see restored text.'}
                      </span>
                    )}
                  </pre>
                </section>
              </div>
              <div className="actions">
                <button
                  className="primary"
                  disabled={!input.trim() || busy}
                  onClick={() => void (encoding ? encode() : decode())}
                >
                  {busy ? 'Working…' : page}
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => {
                    const el = inputRef.current
                    const word = el ? wordAtSelection(el) : ''
                    if (encoding && word.length >= 2) {
                      void addTokenFromWord(word)
                      return
                    }
                    jumpTo('Vault')
                  }}
                >
                  Inspect PII
                </button>
              </div>
              {!encoding && !!active.unknown.length && (
                <p className="warning" role="alert">
                  Unknown tokens left unchanged: {active.unknown.join(', ')}
                </p>
              )}
            </>
          )}

          {active && page === 'Vault' && (
            <>
              {draftToken && (
                <form className="draft-token" aria-label="New token" onSubmit={(event) => { event.preventDefault(); void commitDraftToken() }}>
                  <strong>New token</strong>
                  <input
                    aria-label="Token value"
                    autoFocus
                    disabled={busy}
                    value={draftToken.value}
                    onChange={(e) => setDraftToken({ ...draftToken, value: e.target.value })}
                  />
                  <select
                    aria-label="Token class"
                    disabled={busy}
                    value={draftToken.cls}
                    onChange={(e) => setDraftToken({ ...draftToken, cls: e.target.value })}
                  >
                    {CLASS_OPTIONS.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                  <button type="submit" className="primary" disabled={busy || !draftToken.value.trim()}>
                    {busy ? 'Saving…' : 'Save'}
                  </button>
                  <button type="button" className="quiet" disabled={busy} onClick={() => setDraftToken(null)}>
                    Cancel
                  </button>
                </form>
              )}
              <Vault
                key={active.id}
                mappings={active.mappings}
                busy={busy}
                onChange={changeMappings}
                onAdd={() => {
                  setDraftToken({ value: '', cls: 'Custom' })
                  setNotice('Enter the value and choose a class, then save.')
                }}
              />
            </>
          )}
          <p className="status" role="status">
            {notice}
          </p>
        </main>
      </div>
    </div>
  )
}

export default App
