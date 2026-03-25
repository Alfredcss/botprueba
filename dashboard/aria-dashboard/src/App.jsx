import React, { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import AdvisorsModal from './components/modals/AdvisorsModal'
import ReportsModal from './components/modals/ReportsModal'
import { useConversations } from './hooks/useConversations'

export default function App() {
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

  // Select a client from the sidebar
  const handleSelectClient = useCallback(
    async (client) => {
      const isBotOn = client.bot_encendido !== false
      const isUnread = !isBotOn && client.leido === false

      setSelectedClient(client)
      setBotActive(isBotOn)
      setMobileShowChat(true)

      // Mark as read directly via Supabase (hook handles optimistic update)
      if (isUnread) {
        await markAsRead(client.telefono)
      }
    },
    [markAsRead]
  )

  // Toggle bot on/off — writes directly to Supabase (source of truth)
  async function handleToggleBot() {
    if (!selectedClient) return
    const newState = !botActive
    setBotActive(newState) // Optimistic UI update

    const success = await toggleBot(selectedClient.telefono, newState)
    if (!success) {
      setBotActive(!newState) // Revert if Supabase write failed
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
