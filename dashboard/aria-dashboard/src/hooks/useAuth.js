import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

/**
 * Hook that manages Supabase Auth session.
 * Returns: { session, user, loading, signIn, signOut, error }
 */
export function useAuth() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Get the current session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // Listen for auth state changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signIn(email, password) {
    setError(null)
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setError(error.message)
    setLoading(false)
    return !error
  }

  async function signOut() {
    setError(null)
    await supabase.auth.signOut()
  }

  return {
    session,
    user: session?.user ?? null,
    loading,
    error,
    signIn,
    signOut,
  }
}
