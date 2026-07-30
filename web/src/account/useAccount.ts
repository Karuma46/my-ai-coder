import { useContext } from 'react'
import { AccountContext } from './context'

export function useAccount() {
  const context = useContext(AccountContext)

  if (!context) {
    throw new Error('useAccount must be used within an AccountProvider.')
  }

  return context
}
