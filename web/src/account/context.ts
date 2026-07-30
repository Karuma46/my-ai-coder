import { createContext } from 'react'
import type { Company, UpdateCompany, UpdateProfile, User } from './types'

export type AccountContextValue = {
  user: User | null
  companies: Company[]
  isLoading: boolean
  startSession: (accessToken: string, user: User) => void
  refreshCompanies: () => Promise<Company[]>
  updateProfile: (changes: UpdateProfile) => Promise<User>
  updateCompany: (
    companyId: string,
    changes: UpdateCompany,
  ) => Promise<Company>
  signOut: () => void
}

export const AccountContext = createContext<AccountContextValue | null>(null)
