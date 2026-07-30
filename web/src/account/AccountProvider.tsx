import axios from 'axios'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from '../utilities/authToken'
import { useApi } from '../utilities/useApi'
import { AccountContext } from './context'
import type {
  Company,
  UpdateCompany,
  UpdateProfile,
  User,
} from './types'

type AccountProviderProps = {
  children: ReactNode
}

export function AccountProvider({ children }: AccountProviderProps) {
  const { showAlert } = useAlerts()
  const { get: getCurrentUser } = useApi<User>()
  const { patch: patchCurrentUser } = useApi<User>()
  const { get: listCompanies } = useApi<Company[]>()
  const { patch: patchCompany } = useApi<Company>()
  const [user, setUser] = useState<User | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const signOut = useCallback(() => {
    clearAccessToken()
    setUser(null)
    setCompanies([])
  }, [])

  const startSession = useCallback((accessToken: string, sessionUser: User) => {
    setAccessToken(accessToken)
    setUser(sessionUser)
    setCompanies([])
  }, [])

  const refreshCompanies = useCallback(async () => {
    const { data } = await listCompanies(
      apiEndpoint('/companies'),
      undefined,
      { retries: 1 },
    )
    setCompanies(data)
    return data
  }, [listCompanies])

  const updateProfile = useCallback(
    async (changes: UpdateProfile) => {
      try {
        const { data } = await patchCurrentUser(
          apiEndpoint('/me'),
          changes,
        )
        setUser(data)
        showAlert({
          title: 'Account saved',
          description: 'Your profile details have been updated.',
          variant: 'success',
        })
        return data
      } catch (error) {
        showAlert({
          title: 'Account could not be saved',
          description: 'Check your details and try again.',
          variant: 'error',
        })
        throw error
      }
    },
    [patchCurrentUser, showAlert],
  )

  const updateCompany = useCallback(
    async (companyId: string, changes: UpdateCompany) => {
      try {
        const { data } = await patchCompany(
          apiEndpoint(`/companies/${companyId}`),
          changes,
        )
        setCompanies((current) =>
          current.map((company) =>
            company.id === data.id ? data : company,
          ),
        )
        showAlert({
          title: 'Company saved',
          description: 'The company details have been updated.',
          variant: 'success',
        })
        return data
      } catch (error) {
        showAlert({
          title: 'Company could not be saved',
          description: 'Check your permissions and try again.',
          variant: 'error',
        })
        throw error
      }
    },
    [patchCompany, showAlert],
  )

  useEffect(() => {
    const accessToken = getAccessToken()

    if (!accessToken) {
      setIsLoading(false)
      return
    }

    const controller = new AbortController()

    void Promise.all([
      getCurrentUser(apiEndpoint('/me'), undefined, {
        signal: controller.signal,
        retries: 1,
      }),
      listCompanies(apiEndpoint('/companies'), undefined, {
        signal: controller.signal,
        retries: 1,
      }),
    ])
      .then(([userResponse, companiesResponse]) => {
        setUser(userResponse.data)
        setCompanies(companiesResponse.data)
      })
      .catch((error: unknown) => {
        if (axios.isCancel(error)) {
          return
        }

        if (axios.isAxiosError(error) && error.response?.status === 401) {
          signOut()
          return
        }

        showAlert({
          title: 'Account unavailable',
          description: 'Your account details could not be loaded. Try again.',
          variant: 'error',
        })
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [getCurrentUser, listCompanies, showAlert, signOut])

  const value = useMemo(
    () => ({
      user,
      companies,
      isLoading,
      startSession,
      refreshCompanies,
      updateProfile,
      updateCompany,
      signOut,
    }),
    [
      companies,
      isLoading,
      refreshCompanies,
      signOut,
      startSession,
      updateCompany,
      updateProfile,
      user,
    ],
  )

  return (
    <AccountContext.Provider value={value}>
      {children}
    </AccountContext.Provider>
  )
}
