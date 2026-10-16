import type { Mapping } from './api'

const TOKEN = /(\[[A-Za-z][A-Za-z0-9_:]*_\d+\])/g

export function nextManualToken(category: string, mappings: Mapping[], nextIdx: Record<string, number>): string {
  let index = Math.max(1, nextIdx[category] ?? 1)
  for (const mapping of mappings) {
    if (mapping.token.startsWith(`${category}_`)) {
      const suffix = Number(mapping.token.slice(category.length + 1))
      if (Number.isSafeInteger(suffix)) index = Math.max(index, suffix + 1)
    }
  }
  return `${category}_${index}`
}

/** Reconcile displayed output after edits/deletions without replacing text inside tokens. */
export function updateRedactedOutput(output: string, previous: Mapping[], next: Mapping[]): string {
  const restored = output.split(TOKEN).map(part => {
    const old = previous.find(mapping => `[${mapping.token}]` === part)
    return old && !next.some(mapping => mapping.token === old.token) ? old.value : part
  }).join('')
  const values = [...next].filter(mapping => mapping.value.trim()).sort((a, b) => b.value.length - a.value.length)
  if (!values.length) return restored
  const pattern = new RegExp(values.map(mapping => mapping.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'gu')
  return restored.split(TOKEN).map((part, index) => index % 2 ? part : part.replace(pattern, (value: string, offset: number) => {
    if ((/^[\p{L}\p{N}_]/u.test(value) && /[\p{L}\p{N}_]$/u.test(part.slice(0, offset))) ||
        (/[\p{L}\p{N}_]$/u.test(value) && /^[\p{L}\p{N}_]/u.test(part.slice(offset + value.length)))) return value
    return `[${values.find(mapping => mapping.value === value)!.token}]`
  })).join('')
}
