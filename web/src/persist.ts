/** Persist workspace so a page refresh does not wipe documents or the session. */

const DOCS_KEY = 'poco.docs'
const SESSION_KEY = 'poco.sessionId'
const UI_KEY = 'poco.ui'

export type PersistedDoc = {
  id: number
  name: string
  input: string
  reply: string
  output: string
  restored: string
  unknown: string[]
  mappings: { token: string; value: string; category: string; firstOffset: number }[]
  nextIdx: Record<string, number>
  manualMappings?: { token: string; value: string; category: string; firstOffset: number; sourceValue?: string }[]
  excludedValues?: string[]
}

export type PersistedState = {
  documents: PersistedDoc[]
  activeEncode: number | null
  activeVault: number | null
  sessionId: string | null
  docCounter: number
}

export function loadWorkspace(): PersistedState | null {
  try {
    const raw = window.localStorage.getItem(DOCS_KEY)
    const uiRaw = window.localStorage.getItem(UI_KEY)
    const sessionId = window.localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { documents?: PersistedDoc[]; docCounter?: number }
    const ui = uiRaw ? (JSON.parse(uiRaw) as { activeEncode?: number | null; activeVault?: number | null }) : {}
    const documents = parsed.documents
    if (!Array.isArray(documents)) return null
    const fallbackId = documents[0]?.id ?? null
    return {
      documents,
      activeEncode: documents.length ? ui.activeEncode ?? fallbackId : null,
      activeVault: documents.length ? ui.activeVault ?? fallbackId : null,
      sessionId,
      docCounter: parsed.docCounter ?? documents.length,
    }
  } catch {
    return null
  }
}

export function saveWorkspace(state: PersistedState) {
  try {
    window.localStorage.setItem(
      DOCS_KEY,
      JSON.stringify({ documents: state.documents, docCounter: state.docCounter })
    )
    window.localStorage.setItem(
      UI_KEY,
      JSON.stringify({ activeEncode: state.activeEncode, activeVault: state.activeVault })
    )
    if (state.sessionId) window.localStorage.setItem(SESSION_KEY, state.sessionId)
    else window.localStorage.removeItem(SESSION_KEY)
  } catch {
    /* quota / private mode */
  }
}

export function loadSession(): string | null {
  try {
    return window.localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

export function saveSession(id: string) {
  try {
    window.localStorage.setItem(SESSION_KEY, id)
  } catch {
    /* ignore */
  }
}
