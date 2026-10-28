import { beforeEach, describe, expect, it, vi } from 'vitest'
import { extractPdfText } from './pdfExtract'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'

vi.mock('pdfjs-dist', () => ({ getDocument: vi.fn(), GlobalWorkerOptions: { workerSrc: '' } }))

beforeEach(() => vi.resetAllMocks())

describe('browser PDF extraction', () => {
  function file() {
    const value = new File(['pdf bytes'], 'report.pdf', { type: 'application/pdf' })
    Object.defineProperty(value, 'arrayBuffer', { value: vi.fn().mockResolvedValue(new ArrayBuffer(4)) })
    return value
  }

  it('extracts pages in order, ignores non-text items and separates pages with newlines', async () => {
    const getPage = vi.fn()
      .mockResolvedValueOnce({ getTextContent: async () => ({ items: [{ str: 'Hello ' }, { markedContent: true }, { str: 'world' }] }) })
      .mockResolvedValueOnce({ getTextContent: async () => ({ items: [{ str: 'Second page' }] }) })
    vi.mocked(getDocument).mockReturnValue({ promise: Promise.resolve({ numPages: 2, getPage }) } as never)
    expect(await extractPdfText(file())).toBe('Hello world\nSecond page')
    expect(getPage.mock.calls).toEqual([[1], [2]])
    expect(getDocument).toHaveBeenCalledWith({ data: expect.any(ArrayBuffer) })
    expect(GlobalWorkerOptions.workerSrc).toContain('pdf.worker.min.mjs')
  })

  it('returns no text for an empty document', async () => {
    vi.mocked(getDocument).mockReturnValue({ promise: Promise.resolve({ numPages: 0 }) } as never)
    expect(await extractPdfText(file())).toBe('')
  })

  it('propagates parser failures so the application can display an upload error', async () => {
    vi.mocked(getDocument).mockReturnValue({ promise: Promise.reject(new Error('invalid PDF')) } as never)
    await expect(extractPdfText(file())).rejects.toThrow('invalid PDF')
  })
})
