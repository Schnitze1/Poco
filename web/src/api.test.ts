import { afterEach, describe, expect, it, vi } from 'vitest'
import { decodeText, deleteMapping, encodeText, extractFile, fileToBase64, health, listMappings, presignUpload, uploadToS3, upsertMapping } from './api'

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('encode exclusions', () => {
  it('sends document rules and exclusions to the backend together', async () => {
    const response = { sessionId: 'session', redactedText: 'Visible', mappings: [], stats: {}, excludedValues: ['Visible'] }
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)))
    vi.stubGlobal('fetch', fetch)
    await encodeText('session', 'Visible', undefined, [{ token: 'Custom_1', value: 'secret', category: 'Custom', firstOffset: 0 }], ['Visible'])

    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body.excludedValues).toEqual(['Visible'])
    expect(body.manualMappings).toEqual([{ token: 'Custom_1', value: 'secret' }])
  })

  it('rejects an older backend that silently ignores unredaction requests', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ mappings: [], redactedText: 'Visible' }))))
    await expect(encodeText(null, 'Visible', undefined, [], ['Visible'])).rejects.toThrow('does not support keeping values unredacted')
  })
})

describe('API requests and failures', () => {
  function response(value: unknown, status = 200) {
    const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify(value), { status }))
    vi.stubGlobal('fetch', fetch)
    return fetch
  }

  it('encodes text and selects either uploaded bytes or an S3 key', async () => {
    const fetch = response({ mappings: [], excludedValues: [] })
    await encodeText(null, 'plain text')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ text: 'plain text' })
    await encodeText('session', '', { fileName: 'report.docx', fileBase64: 'ZG9j' })
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ sessionId: 'session', fileName: 'report.docx', fileBase64: 'ZG9j' })
    await encodeText('session', '', { fileName: 'report.pdf', fileBase64: 'ignored', s3Key: 'uploads/report.pdf' })
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ sessionId: 'session', fileName: 'report.pdf', s3Key: 'uploads/report.pdf' })
  })

  it('sends extraction, decode, presign and mapping payloads to their routes', async () => {
    const fetch = response({})
    await extractFile('report.docx', { fileBase64: 'ZG9j' })
    await extractFile('report.pdf', { s3Key: 'uploads/report.pdf' })
    await decodeText('session', '[Email_1]')
    await presignUpload('report.pdf', 'application/pdf')
    await presignUpload('report.pdf', 'application/pdf', 'session')
    await upsertMapping('session', { token: 'Email_1', value: 'a@example.com' })
    expect(fetch.mock.calls.map(([url]) => new URL(url).pathname.split('/').pop())).toEqual(['extract', 'extract', 'decode', 'presign', 'presign', 'mappings'])
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ fileName: 'report.docx', fileBase64: 'ZG9j' })
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ fileName: 'report.pdf', s3Key: 'uploads/report.pdf' })
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ sessionId: 'session', text: '[Email_1]' })
    expect(JSON.parse(fetch.mock.calls[3][1].body)).not.toHaveProperty('sessionId')
    expect(JSON.parse(fetch.mock.calls[4][1].body).sessionId).toBe('session')
    expect(fetch.mock.calls[5][1].method).toBe('POST')
  })

  it.each([
    [JSON.stringify({ error: 'invalid session' }), 400, 'invalid session'],
    [JSON.stringify({}), 503, 'HTTP 503'],
    ['', 502, 'HTTP 502'],
    ['upstream unavailable', 502, 'upstream unavailable'],
  ])('exposes useful request errors for %s', async (body, status, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status })))
    await expect(decodeText('session', 'text')).rejects.toThrow(message)
  })

  it('returns health and session mappings without a request body', async () => {
    const fetch = response({ status: 'ok', mappings: [] })
    expect(await health()).toHaveProperty('status', 'ok')
    expect(await listMappings('session')).toHaveProperty('mappings', [])
    expect(fetch.mock.calls[1][0]).toContain('/sessions/session/mappings')
    expect(fetch.mock.calls[1][1]).toBeUndefined()
  })

  it('reports a failed health check', async () => {
    response({}, 503)
    await expect(health()).rejects.toThrow('health HTTP 503')
  })

  it.each([
    ['not JSON', 500, 'not JSON'],
    [JSON.stringify({ error: 'expired' }), 404, 'expired'],
    ['{}', 500, 'HTTP 500'],
    ['', 500, 'HTTP 500'],
  ])('reports mapping retrieval errors for %s', async (body, status, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status })))
    await expect(listMappings('session')).rejects.toThrow(message)
  })

  it('uploads a blob directly to S3 and handles storage failures', async () => {
    const blob = new Blob(['document'])
    const fetch = response({})
    await uploadToS3('https://storage.example/upload', blob, 'text/plain')
    expect(fetch).toHaveBeenCalledWith('https://storage.example/upload', { method: 'PUT', headers: { 'Content-Type': 'text/plain' }, body: blob })
    fetch.mockResolvedValueOnce(new Response('denied', { status: 403 }))
    await expect(uploadToS3('https://storage.example/upload', blob, 'text/plain')).rejects.toThrow('denied')
    fetch.mockResolvedValueOnce(new Response('', { status: 500 }))
    await expect(uploadToS3('https://storage.example/upload', blob, 'text/plain')).rejects.toThrow('S3 upload HTTP 500')
  })

  it('deletes URL-encoded token names and accepts an empty 204 response', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    await deleteMapping('session', 'Custom:phone_1')
    expect(fetch.mock.calls[0]).toEqual([expect.stringContaining('/Custom%3Aphone_1'), { method: 'DELETE' }])
    fetch.mockResolvedValueOnce(new Response('denied', { status: 403 }))
    await expect(deleteMapping('session', 'Email_1')).rejects.toThrow('denied')
    fetch.mockResolvedValueOnce(new Response('', { status: 500 }))
    await expect(deleteMapping('session', 'Email_1')).rejects.toThrow('HTTP 500')
  })

  it('converts an actual browser File into base64', async () => {
    expect(await fileToBase64(new File(['hello'], 'hello.txt'))).toBe('aGVsbG8=')
  })

  it('accepts a raw base64 result and rejects an unreadable result', async () => {
    vi.spyOn(FileReader.prototype, 'readAsDataURL').mockImplementation(function (this: FileReader) {
      Object.defineProperty(this, 'result', { value: 'raw-base64' })
      this.onload?.({} as ProgressEvent<FileReader>)
    })
    expect(await fileToBase64(new File([], 'empty.txt'))).toBe('raw-base64')
    vi.spyOn(FileReader.prototype, 'readAsDataURL').mockImplementation(function (this: FileReader) {
      Object.defineProperty(this, 'result', { value: null })
      this.onload?.({} as ProgressEvent<FileReader>)
    })
    await expect(fileToBase64(new File([], 'empty.txt'))).rejects.toThrow('Could not read file')
  })

  it.each([null, new DOMException('read denied')])('rejects FileReader errors', async (error) => {
    vi.spyOn(FileReader.prototype, 'readAsDataURL').mockImplementation(function (this: FileReader) {
      Object.defineProperty(this, 'error', { value: error })
      this.onerror?.({} as ProgressEvent<FileReader>)
    })
    await expect(fileToBase64(new File([], 'empty.txt'))).rejects.toThrow(error?.message ?? 'Could not read file')
  })
})
