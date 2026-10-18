import { useRef, useState } from 'react'
import type { DocTab } from '../types'

type Props = {
  documents: DocTab[]
  activeId: number
  onSelect: (id: number) => void
  onRename: (id: number, name: string) => void
  onClose: (id: number) => void
  onAdd: () => void
}

/**
 * Shared tab strip (one implementation for Encode and Vault).
 * Every document can be closed, including the last one.
 */
export function DocumentTabs({ documents, activeId, onSelect, onRename, onClose, onAdd }: Props) {
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null)
  const renameButtons = useRef(new Map<number, HTMLButtonElement>())

  function finishRename(id: number) {
    setEditing(null)
    requestAnimationFrame(() => renameButtons.current.get(id)?.focus())
  }

  return (
    <div className="doctabs" role="group" aria-label="Documents">
      {documents.map((doc) => (
        <div key={doc.id} className={`doctab${doc.id === activeId ? ' active' : ''}`}>
          {editing?.id === doc.id ? (
            <form
              className="doctab-rename"
              onSubmit={(e) => {
                e.preventDefault()
                const name = editing.name.trim()
                if (!name) return
                onRename(doc.id, name)
                finishRename(doc.id)
              }}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  e.preventDefault()
                  finishRename(doc.id)
                }
              }}
            >
              <input
                autoFocus
                aria-label="Document name"
                value={editing.name}
                onFocus={(e) => e.currentTarget.select()}
                onChange={(e) => setEditing({ id: doc.id, name: e.target.value })}
              />
              <button type="submit" className="doctab-control" disabled={!editing.name.trim()}>Save</button>
              <button type="button" className="doctab-control" onClick={() => finishRename(doc.id)}>Cancel</button>
            </form>
          ) : (
            <>
              <button
                type="button"
                className="doctab-name"
                aria-pressed={doc.id === activeId}
                title={doc.name}
                onClick={() => {
                  setEditing(null)
                  onSelect(doc.id)
                }}
              >
                {doc.name}
              </button>
              <button
                ref={(button) => { if (button) renameButtons.current.set(doc.id, button); else renameButtons.current.delete(doc.id) }}
                type="button"
                className="doctab-control"
                aria-label={`Rename ${doc.name}`}
                title="Rename document"
                onClick={() => setEditing({ id: doc.id, name: doc.name })}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                  <path d="m16 3 5 5-12 12-6 1 1-6L16 3ZM13 6l5 5" />
                </svg>
              </button>
              <button
                type="button"
                className="doctab-control doctab-x"
                aria-label={`Close ${doc.name}`}
                title="Close document"
                onClick={() => onClose(doc.id)}
              >
                ×
              </button>
            </>
          )}
        </div>
      ))}
      <button type="button" className="doctab add" onClick={() => { setEditing(null); onAdd() }}>
        + New document
      </button>
    </div>
  )
}
