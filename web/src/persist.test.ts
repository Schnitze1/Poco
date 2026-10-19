import { beforeEach, describe, expect, it } from 'vitest'
import { loadSession, loadWorkspace, saveWorkspace } from './persist'
import type { PersistedState } from './persist'

function exampleWorkspace(): PersistedState {
  return {
    documents: [
      {
        id: 10,
        name: 'contact.txt',
        input: 'Contact alice@example.com',
        reply: 'I emailed [Email_1].',
        output: 'Contact [Email_1]',
        restored: 'I emailed alice@example.com.',
        unknown: [],
        mappings: [
          { token: 'Email_1', value: 'alice@example.com', category: 'Email', firstOffset: 8 },
        ],
        nextIdx: { Email: 2 },
      },
      {
        id: 20,
        name: 'follow-up.txt',
        input: '',
        reply: 'Hello [Person_99]',
        output: '',
        restored: 'Hello [Person_99]',
        unknown: ['[Person_99]'],
        mappings: [],
        nextIdx: {},
      },
    ],
    activeEncode: 10,
    activeVault: 20,
    sessionId: 'test-session',
    docCounter: 3,
  }
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('workspace persistence', () => {
  it('returns no workspace or session when storage is empty', () => {
    expect(loadWorkspace()).toBeNull()
    expect(loadSession()).toBeNull()
  })

  it('restores documents, mappings, selected tabs, and the session after saving', () => {
    const workspace = exampleWorkspace()

    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual(workspace)
    expect(loadSession()).toBe(workspace.sessionId)
  })

  it('restores a new workspace saved before a session has been created', () => {
    const workspace = exampleWorkspace()
    workspace.sessionId = null

    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual(workspace)
    expect(loadSession()).toBeNull()
  })

  it('restores manual redactions and exclusions independently for each document', () => {
    const workspace = exampleWorkspace()
    workspace.documents[0].excludedValues = ['alice@example.com']
    workspace.documents[1].manualMappings = [{ token: 'Custom_1', value: 'readout', category: 'Custom', firstOffset: 0 }]
    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual(workspace)
    expect(loadWorkspace()?.documents[1].excludedValues).toBeUndefined()
  })

  it('keeps the workspace empty after the last document is closed and the page reloads', () => {
    const workspace = exampleWorkspace()
    workspace.documents = []
    workspace.activeEncode = null
    workspace.activeVault = null

    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual(workspace)
    expect(loadSession()).toBe(workspace.sessionId)
  })

  it('clears stale selected document IDs when restoring an empty workspace', () => {
    const workspace = exampleWorkspace()
    workspace.documents = []
    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual({ ...workspace, activeEncode: null, activeVault: null })
  })

  it('clears the previous session when saving a workspace without a session', () => {
    const workspace = exampleWorkspace()
    saveWorkspace(workspace)

    workspace.sessionId = null
    saveWorkspace(workspace)

    expect(loadWorkspace()).toEqual(workspace)
    expect(loadSession()).toBeNull()
  })

  it.each(['poco.docs', 'poco.ui'])(
    'returns no workspace rather than throwing when %s contains malformed JSON',
    (key) => {
      saveWorkspace(exampleWorkspace())
      window.localStorage.setItem(key, '{invalid json')

      expect(loadWorkspace()).toBeNull()
    },
  )
})
