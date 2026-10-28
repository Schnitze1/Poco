import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as api from './api'
import { extractPdfText } from './pdfExtract'
import { loadWorkspace, saveWorkspace } from './persist'
import type { PersistedDoc } from './persist'

vi.mock('./api', async (original) => ({
  ...await original<typeof import('./api')>(),
  health: vi.fn(), encodeText: vi.fn(), decodeText: vi.fn(), listMappings: vi.fn(),
  deleteMapping: vi.fn(), upsertMapping: vi.fn(), fileToBase64: vi.fn(), extractFile: vi.fn(),
}))
vi.mock('./pdfExtract', () => ({ extractPdfText: vi.fn() }))

const email = { token: 'Email_1', value: 'person@example.com', category: 'Email', firstOffset: 8 }
const source = 'Contact person@example.com'
function encoded(text = 'Contact [Email_1]', mappings = [email], excludedValues: string[] = []): api.EncodeResult {
  return { sessionId: 'session-123', redactedText: text, mappings, excludedValues, stats: { totalEntities: mappings.length, durationMs: 1 } }
}
function seed(changes: Partial<PersistedDoc> = {}, sessionId: string | null = 'session-123') {
  const doc: PersistedDoc = { id: 1, name: 'contact.txt', input: '', reply: '', output: '', restored: '', unknown: [], mappings: [], nextIdx: {}, ...changes }
  saveWorkspace({ documents: [doc], activeEncode: 1, activeVault: 1, sessionId, docCounter: 1 })
}
function nav(page: string) {
  return within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: new RegExp(`^${page}`) })
}
async function mount() {
  const user = userEvent.setup({ applyAccept: false })
  const clipboard = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: clipboard } })
  const view = render(<App />)
  await waitFor(() => expect(screen.getByText(/API (test|offline)/)).toBeTruthy())
  return { user, clipboard, ...view }
}
async function notice(text: string) {
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain(text))
}
function output() { return document.querySelector('pre.output')?.textContent }

beforeEach(() => {
  window.localStorage.clear()
  vi.resetAllMocks()
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => window.setTimeout(() => callback(0), 0))
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', version: '1', env: 'test' })
  vi.mocked(api.listMappings).mockResolvedValue({ sessionId: 'session-123', mappings: [] })
  vi.mocked(api.encodeText).mockResolvedValue(encoded())
  vi.mocked(api.decodeText).mockResolvedValue({ sessionId: 'session-123', restoredText: source, hallucinations: [] })
  vi.mocked(api.deleteMapping).mockResolvedValue(undefined)
  vi.mocked(api.upsertMapping).mockResolvedValue({ sessionId: 'session-123', mapping: email })
  vi.mocked(api.fileToBase64).mockResolvedValue('ZG9j')
  vi.mocked(api.extractFile).mockResolvedValue({ fileName: 'report.docx', text: source })
  vi.mocked(extractPdfText).mockResolvedValue(source)
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('application user journeys', () => {
  it('encodes, reads the Vault, decodes and copies the restored response', async () => {
    const { user, clipboard } = await mount()
    await user.type(screen.getByLabelText('Original text'), source)
    await user.click(screen.getByRole('button', { name: 'Encode' }))
    await notice('1 values replaced')
    expect(output()).toBe('Contact [Email_1]')
    expect(api.encodeText).toHaveBeenCalledWith(null, source, undefined, [], [])
    await user.click(nav('Vault'))
    expect(screen.getByRole('cell', { name: 'person@example.com' })).toBeTruthy()
    await user.click(nav('Decode'))
    await user.type(screen.getByLabelText('Redacted text', { selector: 'textarea' }), '[[Email_1]')
    await user.click(screen.getByRole('button', { name: 'Decode' }))
    await notice('Response restored')
    expect(output()).toBe(source)
    await user.click(screen.getByRole('button', { name: 'Copy' }))
    expect(clipboard).toHaveBeenCalledWith(source)
    await notice('Copied to clipboard')
    expect(loadWorkspace()?.documents[0].restored).toBe(source)
  })

  it('restores a token, persists its exclusion and allows it to be redacted again', async () => {
    seed({ input: source, output: 'Contact [Email_1]', mappings: [email] })
    const { user } = await mount()
    vi.mocked(api.encodeText).mockResolvedValueOnce(encoded(source, [], [email.value]))
    await user.click(screen.getByRole('button', { name: 'Unredact person@example.com' }))
    await notice('Text restored')
    expect(output()).toBe(source)
    expect(api.deleteMapping).toHaveBeenCalledWith('session-123', 'Email_1')
    expect(loadWorkspace()?.documents[0].excludedValues).toContain(email.value)
    await user.click(screen.getByRole('button', { name: 'Redact person@example.com' }))
    await notice('Text redacted')
    expect(output()).toBe('Contact [Email_1]')
    expect(api.encodeText).toHaveBeenLastCalledWith('session-123', source, undefined, [expect.objectContaining({ value: email.value, category: 'Email' })], [])
  })

  it('keeps document names and separate document contents through navigation', async () => {
    const { user } = await mount()
    await user.type(screen.getByLabelText('Original text'), 'first document')
    await user.click(screen.getByRole('button', { name: 'Rename document-1.txt' }))
    await user.clear(screen.getByLabelText('Document name'))
    await user.type(screen.getByLabelText('Document name'), 'renamed.txt{Enter}')
    await notice('Document renamed')
    await user.click(screen.getByRole('button', { name: '+ New document' }))
    await user.type(screen.getByLabelText('Original text'), 'second document')
    await user.click(screen.getByRole('button', { name: 'renamed.txt' }))
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).value).toBe('first document')
    await user.click(nav('Vault'))
    await user.click(screen.getByRole('button', { name: 'document-2.txt' }))
    await user.click(nav('Encode'))
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).value).toBe('second document')
    await user.click(screen.getByRole('button', { name: 'Close document-2.txt' }))
    await user.click(screen.getByRole('button', { name: 'Close renamed.txt' }))
    expect(screen.getByRole('heading', { name: 'No documents open' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'New document' }))
    expect(screen.getByLabelText('Original text')).toBeTruthy()
  })

  it('restores server mappings into an empty saved workspace without replacing local mappings', async () => {
    seed()
    vi.mocked(api.listMappings).mockResolvedValue({ sessionId: 'session-123', mappings: [email] })
    const first = await mount()
    await first.user.click(nav('Vault'))
    expect(await screen.findByRole('cell', { name: email.value })).toBeTruthy()
    first.unmount()
    seed({ mappings: [{ ...email, value: 'local@example.com' }] })
    const second = await mount()
    await second.user.click(nav('Vault'))
    expect(screen.getByRole('cell', { name: 'local@example.com' })).toBeTruthy()
    expect(screen.queryByRole('cell', { name: email.value })).toBeNull()
  })

  it('handles an offline API and an expired mapping request without losing local input', async () => {
    seed({ input: 'saved text' })
    vi.mocked(api.health).mockRejectedValue(new Error('offline'))
    vi.mocked(api.listMappings).mockRejectedValue(new Error('expired'))
    await mount()
    expect(screen.getByText(/API offline/)).toBeTruthy()
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).value).toBe('saved text')
  })

  it('shows unknown-token warnings and prevents Decode without a session', async () => {
    const { user } = await mount()
    await user.click(nav('Decode'))
    await user.type(screen.getByLabelText('Redacted text', { selector: 'textarea' }), '[[Person_99]')
    await user.click(screen.getByRole('button', { name: 'Decode' }))
    await notice('No session yet')
    expect(api.decodeText).not.toHaveBeenCalled()
    await user.click(nav('Encode'))
    await user.click(screen.getByRole('button', { name: 'Use example' }))
    await user.click(screen.getByRole('button', { name: 'Encode' }))
    await notice('values replaced')
    await user.click(nav('Decode'))
    vi.mocked(api.decodeText).mockResolvedValueOnce({ sessionId: 'session-123', restoredText: '[Person_99]', hallucinations: ['[Person_99]'] })
    await user.click(screen.getByRole('button', { name: 'Use example' }))
    await user.click(screen.getByRole('button', { name: 'Decode' }))
    await notice('unknown token(s)')
    expect(screen.getByRole('alert').textContent).toContain('[Person_99]')
  })

  it('reports Encode and Decode failures and restores the controls', async () => {
    seed({ input: source, reply: '[Email_1]' })
    const { user } = await mount()
    vi.mocked(api.encodeText).mockRejectedValueOnce(new Error('encode unavailable'))
    await user.click(screen.getByRole('button', { name: 'Encode' }))
    await notice('Encode failed: encode unavailable')
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).disabled).toBe(false)
    await user.click(nav('Decode'))
    vi.mocked(api.decodeText).mockRejectedValueOnce('decode unavailable')
    await user.click(screen.getByRole('button', { name: 'Decode' }))
    await notice('Decode failed: decode unavailable')
  })

  it('disables input and duplicate submissions while encoding', async () => {
    const { user } = await mount()
    let finish!: (result: api.EncodeResult) => void
    vi.mocked(api.encodeText).mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    await user.type(screen.getByLabelText('Original text'), source)
    await user.click(screen.getByRole('button', { name: 'Encode' }))
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Working…' }) as HTMLButtonElement).disabled).toBe(true)
    await act(async () => finish(encoded()))
    await notice('values replaced')
    expect(api.encodeText).toHaveBeenCalledOnce()
  })

  it('saves a new Vault token before any Encode and rejects duplicate values', async () => {
    const { user } = await mount()
    await user.click(nav('Vault'))
    await user.click(screen.getByRole('button', { name: '+ Add token' }))
    await user.type(screen.getByLabelText('Token value'), 'private phrase')
    await user.selectOptions(screen.getByLabelText('Token class'), 'Organization')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await notice('Token saved to the server vault')
    expect(api.upsertMapping).toHaveBeenCalledWith(expect.any(String), { token: 'Organization_1', value: 'private phrase', category: 'Organization' })
    await user.click(screen.getByRole('button', { name: '+ Add token' }))
    await user.type(screen.getByLabelText('Token value'), 'private phrase')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await notice('already has a token')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('form', { name: 'New token' })).toBeNull()
  })

  it('re-encodes manual tokens and preserves a failed draft for retry', async () => {
    seed({ input: source })
    const { user } = await mount()
    await user.click(nav('Vault'))
    await user.click(screen.getByRole('button', { name: '+ Add token' }))
    await user.type(screen.getByLabelText('Token value'), 'private phrase')
    vi.mocked(api.encodeText).mockRejectedValueOnce(new Error('retry later'))
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await notice('Vault sync failed: retry later')
    expect((screen.getByLabelText('Token value') as HTMLInputElement).value).toBe('private phrase')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await notice('Token saved and redacted output updated')
    expect(api.encodeText).toHaveBeenLastCalledWith('session-123', source, undefined, [expect.objectContaining({ token: 'Custom_1', value: 'private phrase' })], [])
  })

  it('edits server mappings, retains source values, and resets the Vault', async () => {
    seed({ input: source, output: 'Contact [Email_1]', mappings: [email] })
    const { user } = await mount()
    await user.click(nav('Vault'))
    await user.click(screen.getByRole('button', { name: 'Edit Email_1' }))
    await user.clear(screen.getByLabelText('Value for Email_1'))
    await user.type(screen.getByLabelText('Value for Email_1'), 'new@example.com')
    await user.click(screen.getByRole('button', { name: 'Save Email_1' }))
    await notice('Vault updated on the server')
    expect(api.upsertMapping).toHaveBeenCalledWith('session-123', { token: 'Email_1', value: 'new@example.com', category: 'Email' })
    expect(loadWorkspace()?.documents[0].manualMappings?.[0].sourceValue).toBe(email.value)
    await user.click(screen.getByRole('button', { name: 'Reset vault' }))
    await notice('Vault updated on the server')
    await waitFor(() => expect(screen.getByText('No tokens yet. Encode an example or add a token.')).toBeTruthy())
    expect(api.deleteMapping).toHaveBeenCalledWith('session-123', 'Email_1')
  })

  it('keeps mappings visible when a server deletion fails', async () => {
    seed({ mappings: [email] })
    const { user } = await mount()
    await user.click(nav('Vault'))
    vi.mocked(api.deleteMapping).mockRejectedValueOnce(new Error('delete denied'))
    await user.click(screen.getByRole('button', { name: 'Delete Email_1' }))
    await notice('Vault sync failed: delete denied')
    expect(screen.getByRole('cell', { name: email.value })).toBeTruthy()
  })

  it.each([
    ['person@example.com', 'Email'], ['+61 400 123 456', 'Phone'],
    ['4111111111111111', 'CreditCard'], ['5555 5555 5555 4444', 'CreditCard'],
    ['4111111111111112', 'Phone'], ['Alice Smith', 'Name'], ['private-code', 'Custom'],
  ])('inspects a selected value and infers %s as %s', async (word, category) => {
    seed({ input: word })
    const { user } = await mount()
    const input = screen.getByLabelText('Original text') as HTMLTextAreaElement
    await user.click(input)
    input.setSelectionRange(0, word.includes(' ') || word.startsWith('+') ? word.length : 0)
    await user.click(screen.getByRole('button', { name: 'Inspect PII' }))
    await notice('Text redacted')
    expect(api.encodeText).toHaveBeenCalledWith('session-123', word, undefined, [expect.objectContaining({ value: word, category })], [])
  })

  it('navigates to the Vault when there is no selected value and can return home', async () => {
    const { user } = await mount()
    await user.click(screen.getByRole('button', { name: 'Inspect PII' }))
    expect(screen.getByRole('heading', { name: 'Vault' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Poco home' }))
    expect(screen.getByRole('heading', { name: 'Encode' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Switch to light theme' }))
    expect(document.querySelector('.app-shell.light')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(document.querySelector('.app-shell.light')).toBeNull()
  })

  it.each(['report.txt', 'report.md', 'report.pdf', 'report.docx'])('imports %s through the appropriate extraction path', async (name) => {
    const { user } = await mount()
    const file = new File(['text'], name)
    Object.defineProperty(file, 'text', { value: async () => source })
    await user.click(screen.getByRole('button', { name: 'Upload file' }))
    await user.upload(screen.getByLabelText('Upload text, PDF, or DOCX file'), file)
    await waitFor(() => expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).value).toBe(source))
    expect(screen.getByRole('button', { name })).toBeTruthy()
    if (name.endsWith('.pdf')) expect(extractPdfText).toHaveBeenCalledWith(file)
    if (name.endsWith('.docx')) expect(api.extractFile).toHaveBeenCalledWith(name, { fileBase64: 'ZG9j' })
  })

  it('imports Decode text without renaming the document and reports validation failures', async () => {
    const { user } = await mount()
    await user.click(nav('Decode'))
    const file = new File(['reply'], 'reply.txt')
    Object.defineProperty(file, 'text', { value: async () => '[Email_1]' })
    const picker = screen.getByLabelText('Upload text, PDF, or DOCX file')
    await user.upload(picker, file)
    await notice('Ready to decode')
    expect((screen.getByLabelText('Redacted text', { selector: 'textarea' }) as HTMLTextAreaElement).value).toBe('[Email_1]')
    expect(screen.getByRole('button', { name: 'document-1.txt' })).toBeTruthy()
    await user.upload(picker, new File(['x'], 'program.exe'))
    await notice('Choose a .txt, .md, .pdf, or .docx file')
    const large = new File(['x'], 'large.txt')
    Object.defineProperty(large, 'size', { value: 25_000_001 })
    await user.upload(picker, large)
    await notice('Choose a file smaller than 25 MB')
    fireEvent.change(picker, { target: { files: [] } })
    expect(api.extractFile).not.toHaveBeenCalled()
  })

  it('reports extraction and clipboard failures without losing text', async () => {
    seed({ input: source, output: 'Contact [Email_1]', mappings: [email] })
    const { user, clipboard } = await mount()
    vi.mocked(extractPdfText).mockRejectedValueOnce(new Error('invalid PDF'))
    await user.upload(screen.getByLabelText('Upload text, PDF, or DOCX file'), new File(['bad'], 'broken.pdf'))
    await notice('Upload failed: invalid PDF')
    clipboard.mockRejectedValueOnce(new Error('permission denied'))
    await user.click(screen.getByRole('button', { name: 'Copy' }))
    await notice('Could not copy automatically')
    expect((screen.getByLabelText('Original text') as HTMLTextAreaElement).value).toBe(source)
  })

  it('reports redaction and restoration failures while retaining the displayed output', async () => {
    seed({ input: source, output: 'Contact [Email_1]', mappings: [email] })
    const { user } = await mount()
    vi.mocked(api.encodeText).mockRejectedValueOnce(new Error('unavailable'))
    await user.click(screen.getByRole('button', { name: 'Unredact person@example.com' }))
    await notice('Unredaction failed: unavailable')
    expect(output()).toBe('Contact [Email_1]')
    vi.mocked(api.encodeText).mockRejectedValueOnce('unavailable')
    await user.click(screen.getByRole('button', { name: 'Redact Contact' }))
    await notice('Redaction failed: unavailable')
    expect(output()).toBe('Contact [Email_1]')
  })
})
