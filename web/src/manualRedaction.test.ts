import { describe, expect, it } from 'vitest'
import { nextManualToken, redactableTextParts, updateRedactedOutput } from './manualRedaction'

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

  it('advances beyond existing tokens without using invalid counters or other categories', () => {
    const mappings = ['Custom_7', 'Custom_nope', 'Email_40'].map(token => ({ token, value: 'value', category: 'Custom', firstOffset: 0 }))
    expect(nextManualToken('Custom', mappings, { Custom: -5 })).toBe('Custom_8')
    expect(nextManualToken('Name', mappings, {})).toBe('Name_1')
  })

  it('restores removed mappings without changing retained or unknown tokens', () => {
    const previous = [
      { token: 'Email_1', value: 'a@example.com', category: 'Email', firstOffset: 0 },
      { token: 'Name_1', value: 'Ann', category: 'Name', firstOffset: 20 },
    ]
    expect(updateRedactedOutput('[Email_1] [Name_1] [Unknown_9]', previous, [previous[1]])).toBe('a@example.com [Name_1] [Unknown_9]')
    expect(updateRedactedOutput('[Email_1]', previous, [])).toBe('a@example.com')
  })

  it('redacts literal values with regex characters, longest first and only at word boundaries', () => {
    const mappings = [
      { token: 'Name_1', value: 'Ann', category: 'Name', firstOffset: 0 },
      { token: 'Name_2', value: 'Ann Lee', category: 'Name', firstOffset: 0 },
      { token: 'Email_1', value: 'a+b@example.com', category: 'Email', firstOffset: 0 },
      { token: 'Custom_1', value: ' ', category: 'Custom', firstOffset: 0 },
    ]
    expect(updateRedactedOutput('Ann Lee met Annette and Ann. _Ann Ann_ a+b@example.com [Name_1]', [], mappings))
      .toBe('[Name_2] met Annette and [Name_1]. _Ann Ann_ [Email_1] [Name_1]')
  })
})
