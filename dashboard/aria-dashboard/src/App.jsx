import React, { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import AdvisorsModal from './components/modals/AdvisorsModal'
import ReportsModal from './components/modals/ReportsModal'
import LoginPage from './components/LoginPage'
import { useConversations } from './hooks/useConversations'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const { session, loading: authLoading, error: authError, signIn, signOut } = useAuth()

  const {
    conversations,
    setConversations,
    loading,
    refetch,
    markAsRead,
    toggleBot,
  } = useConversations()

  const [selectedClient, setSelectedClient] = useState(null)
  const [botActive, setBotActive] = useState(true)
  const [mobileShowChat, setMobileShowChat] = useState(false)
  const [showAdvisors, setShowAdvisors] = useState(false)
  const [showReports, setShowReports] = useState(false)

  // ── Auth guard ────────────────────────────────────────────────────
  // Show a blank screen while Supabase resolves the session
  if (authLoading) return null

  // If no session → show login
  if (!session) {
    return <LoginPage onLogin={signIn} loading={authLoading} error={authError} />
  }
  // ─────────────────────────────────────────────────────────────────

  // Select a client from the sidebar
  const handleSelectClient = async (client) => {
    const isBotOn = client.bot_encendido !== false
    const isUnread = !isBotOn && client.leido === false

    setSelectedClient(client)
    setBotActive(isBotOn)
    setMobileShowChat(true)

    if (isUnread) {
      await markAsRead(client.telefono)
    }
  }

  // Toggle bot on/off
  async function handleToggleBot() {
    if (!selectedClient) return
    const newState = !botActive
    setBotActive(newState)

    const success = await toggleBot(selectedClient.telefono, newState)
    if (!success) {
      setBotActive(!newState)
    }
  }

  function handleBack() {
    setMobileShowChat(false)
  }

  return (
    <div
      className={`app-layout ${mobileShowChat ? 'mobile-chat-active' : ''}`}
      style={{ position: 'fixed', inset: 0 }}
    >
      <Sidebar
        conversations={conversations}
        selectedPhone={selectedClient?.telefono ?? null}
        onSelectClient={handleSelectClient}
        onOpenAdvisors={() => setShowAdvisors(true)}
        onOpenReports={() => setShowReports(true)}
        onSignOut={signOut}
      />

      <ChatArea
        selectedClient={selectedClient}
        botActive={botActive}
        onToggleBot={handleToggleBot}
        onBack={handleBack}
        onConversationsRefetch={refetch}
      />

      <AdvisorsModal isOpen={showAdvisors} onClose={() => setShowAdvisors(false)} />
      <ReportsModal isOpen={showReports} onClose={() => setShowReports(false)} />
    </div>
  )
}
