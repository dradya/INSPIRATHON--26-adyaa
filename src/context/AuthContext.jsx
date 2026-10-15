import { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase.js'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchProfile = async (uid) => {
    if (!uid) return setProfile(null)
    const { data } = await supabase.from('profiles').select('*').eq('id', uid).single()
    if (data) setProfile(data)
  }

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user || null)
      if (data.session?.user) fetchProfile(data.session.user.id).finally(() => setLoading(false))
      else setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user || null)
      if (session?.user) fetchProfile(session.user.id)
      else setProfile(null)
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  const signUp = (email, password, full_name) =>
    supabase.auth.signUp({ email, password, options: { data: { full_name } } })
  const signIn = (email, password) =>
    supabase.auth.signInWithPassword({ email, password })
  const signInGoogle = () =>
    supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } })
  const signOut = () => supabase.auth.signOut()

  return (
    <AuthCtx.Provider value={{ user, profile, loading, signUp, signIn, signInGoogle, signOut }}>
      {children}
    </AuthCtx.Provider>
  )
}
