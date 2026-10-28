import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Vault } from './Vault'

afterEach(cleanup)

describe('vault mapping controls', () => {
  const mapping = { token: 'Email_1', value: 'old@example.com', category: 'Email', firstOffset: 0 }
  function setup(saved = true) {
    const onChange = vi.fn().mockResolvedValue(saved)
    const onAdd = vi.fn()
    const user = userEvent.setup()
    const view = render(<Vault mappings={[mapping]} onChange={onChange} onAdd={onAdd} busy={false} />)
    return { user, onChange, onAdd, ...view }
  }

  it('filters mappings and clears the filter when adding a token', async () => {
    const { user, onAdd } = setup()
    await user.type(screen.getByLabelText('Filter mappings'), 'missing')
    expect(screen.getByText('No matching tokens.')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: '+ Add token' }))
    expect((screen.getByLabelText('Filter mappings') as HTMLInputElement).value).toBe('')
    expect(screen.getByText('old@example.com')).toBeTruthy()
    expect(onAdd).toHaveBeenCalledOnce()
  })

  it('saves edited values and categories with Enter', async () => {
    const { user, onChange } = setup()
    await user.click(screen.getByRole('button', { name: 'Edit Email_1' }))
    await user.clear(screen.getByLabelText('Value for Email_1'))
    expect((screen.getByRole('button', { name: 'Save Email_1' }) as HTMLButtonElement).disabled).toBe(true)
    await user.type(screen.getByLabelText('Value for Email_1'), '  new@example.com  ')
    await user.selectOptions(screen.getByLabelText('Class for Email_1'), 'Custom')
    await user.click(screen.getByLabelText('Value for Email_1'))
    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenCalledWith([{ ...mapping, value: 'new@example.com', category: 'Custom' }])
    await waitFor(() => expect(screen.queryByLabelText('Value for Email_1')).toBeNull())
  })

  it('keeps a failed edit open for retry and supports cancelling', async () => {
    const { user, onChange } = setup(false)
    await user.click(screen.getByRole('button', { name: 'Edit Email_1' }))
    await user.type(screen.getByLabelText('Value for Email_1'), 'changed')
    await user.click(screen.getByRole('button', { name: 'Save Email_1' }))
    expect(onChange).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('Value for Email_1')).toBeTruthy()
    await user.click(screen.getByLabelText('Value for Email_1'))
    await user.keyboard('{Escape}')
    expect(screen.queryByLabelText('Value for Email_1')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Edit Email_1' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Value for Email_1')).toBeNull()
  })

  it('deletes a mapping and closes its editor after a successful save', async () => {
    const { user, onChange } = setup()
    await user.click(screen.getByRole('button', { name: 'Edit Email_1' }))
    await user.click(screen.getByRole('button', { name: 'Delete Email_1' }))
    expect(onChange).toHaveBeenCalledWith([])
    await waitFor(() => expect(screen.queryByLabelText('Value for Email_1')).toBeNull())
  })

  it('shows an empty state and disables mutations while busy', () => {
    const onChange = vi.fn()
    const { rerender } = render(<Vault mappings={[]} onChange={onChange} onAdd={vi.fn()} busy={false} />)
    expect(screen.getByText('No tokens yet. Encode an example or add a token.')).toBeTruthy()
    rerender(<Vault mappings={[mapping]} onChange={onChange} onAdd={vi.fn()} busy />)
    expect((screen.getByRole('button', { name: 'Edit Email_1' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Delete Email_1' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
