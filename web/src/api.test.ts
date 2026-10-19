import { afterEach, describe, expect, it, vi } from 'vitest'
import { encodeText } from './api'

afterEach(() => vi.unstubAllGlobals())

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
