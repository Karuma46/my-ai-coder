export type User = {
  id: string
  name: string
  email: string
  avatarUrl: string | null
  initials: string
  createdAt?: string
  updatedAt?: string
}

export type Company = {
  id: string
  name: string
  role: 'owner' | 'member'
  memberCount: number
  projectCount: number
  createdAt: string
  updatedAt: string
}

export type TokenResponse = {
  accessToken: string
  tokenType: 'bearer'
  expiresIn: number
  user: User
}

export type UpdateProfile = {
  name: string
  avatarUrl: string | null
}

export type UpdateCompany = {
  name: string
}
