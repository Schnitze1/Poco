import { describe, expect, it } from 'vitest'
import { nextManualToken, redactableTextParts } from './manualRedaction'

describe('clickable redaction text', () => {
  it('keeps restored full names and emails as single clickable values', () => {
    const parts = redactableTextParts('Sarah Mitchell wrote to sarah@example.com.', ['Sarah Mitchell', 'sarah@example.com'])
    expect(parts.filter((_, index) => index % 2)).toEqual(['Sarah Mitchell', 'wrote', 'to', 'sarah@example.com'])
  })

  it('matches longer restored values first and escapes regex characters', () => {
    const parts = redactableTextParts('Sarah Mitchell-Jones and a+b@example.com', ['Sarah', 'Sarah Mitchell-Jones', 'a+b@example.com'])
    expect(parts.filter((_, index) => index % 2)).toEqual(['Sarah Mitchell-Jones', 'and', 'a+b@example.com'])
  })

  it('keeps substrings inside longer words intact', () => {
    const parts = redactableTextParts('Sarasota meets Sarah.', ['Sarah'])
    expect(parts.filter((_, index) => index % 2)).toEqual(['Sarasota', 'meets', 'Sarah'])
  })

  it('does not reuse a removed token counter after subsequent encodes', () => {
    expect(nextManualToken('Custom', [], { Custom: 3 })).toBe('Custom_3')
  })
})
