import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DocumentTabs } from './DocumentTabs'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('document tabs', () => {
  function setup() {
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => window.setTimeout(() => callback(0), 0))
    const props = { documents: [{ id: 1, name: 'first.txt' }, { id: 2, name: 'second.txt' }], activeId: 1, onSelect: vi.fn(), onRename: vi.fn(), onClose: vi.fn(), onAdd: vi.fn() }
    const user = userEvent.setup()
    render(<DocumentTabs {...props} />)
    return { user, props }
  }

  it('selects, closes and adds documents through their controls', async () => {
    const { user, props } = setup()
    expect(screen.getByRole('button', { name: 'first.txt' }).getAttribute('aria-pressed')).toBe('true')
    await user.click(screen.getByRole('button', { name: 'second.txt' }))
    await user.click(screen.getByRole('button', { name: 'Close first.txt' }))
    await user.click(screen.getByRole('button', { name: '+ New document' }))
    expect(props.onSelect).toHaveBeenCalledWith(2)
    expect(props.onClose).toHaveBeenCalledWith(1)
    expect(props.onAdd).toHaveBeenCalledOnce()
  })

  it('trims saved names, prevents blank saves and returns focus to rename', async () => {
    const { user, props } = setup()
    await user.click(screen.getByRole('button', { name: 'Rename first.txt' }))
    await user.clear(screen.getByLabelText('Document name'))
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true)
    await user.type(screen.getByLabelText('Document name'), '  renamed.txt  {Enter}')
    expect(props.onRename).toHaveBeenCalledWith(1, 'renamed.txt')
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Rename first.txt' })))
  })

  it.each(['Cancel', 'Escape'])('cancels renaming with %s', async (method) => {
    const { user, props } = setup()
    await user.click(screen.getByRole('button', { name: 'Rename first.txt' }))
    await user.type(screen.getByLabelText('Document name'), 'changed')
    if (method === 'Cancel') await user.click(screen.getByRole('button', { name: 'Cancel' }))
    else await user.keyboard('{Escape}')
    expect(screen.queryByLabelText('Document name')).toBeNull()
    expect(props.onRename).not.toHaveBeenCalled()
  })
})
