import React, { useState, useEffect } from 'react'
import ClientItem from './ClientItem'

const agencyName = import.meta.env.VITE_AGENCY_NAME || 'Monitor Aria'

/**
 * Left sidebar: header, search bar, filter buttons, and the conversations list.
 * Search covers: name, phone, AND assigned advisor (seguimiento).
 * Filters: human-attended | unread | has-advisor
 */
export default function Sidebar({
  conversations,
  selectedPhone,
  onSelectClient,
  onOpenAdvisors,
  onOpenReports,
  onSignOut,
}) {
  const [searchText, setSearchText] = useState('')
  const [filterHuman, setFilterHuman] = useState(false)
  const [filterUnread, setFilterUnread] = useState(false)
  const [filterWithAdvisor, setFilterWithAdvisor] = useState(false)

  // Sort: bot OFF (human) first → bot ON (AI) last.
  // Only when NOT searching — while searching, keep natural date order so the
  // matched contact appears at the top instead of being buried at the bottom.
  const sorted = searchText
    ? conversations
    : [...conversations].sort((a, b) => {
        const aHuman = a.bot_encendido === false ? 0 : 1
        const bHuman = b.bot_encendido === false ? 0 : 1
        return aHuman - bHuman
      })

  const filtered = sorted.filter((c) => {
    // Normalize helper: removes accents so "jose" matches "José"
    const norm = (str) =>
      String(str)
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')

    const nombre = norm(c.display || '')
    // Strip the "whatsapp:" prefix that Twilio adds before comparing
    const tel = norm((c.telefono || '').replace('whatsapp:', ''))
    const asesor = norm(c.seguimiento || '')
    const query = norm(searchText)

    // Search matches name, phone, OR assigned advisor name
    const matchText = !query || nombre.includes(query) || tel.includes(query) || asesor.includes(query)

    const isBotOn = c.bot_encendido !== false
    const isUnread = !isBotOn && c.leido === false
    const hasAdvisor = Boolean(c.seguimiento)

    const matchHuman = filterHuman ? !isBotOn : true
    const matchUnread = filterUnread ? isUnread : true
    const matchAdvisor = filterWithAdvisor ? hasAdvisor : true

    return matchText && matchHuman && matchUnread && matchAdvisor
  })

  // --- Auto-select when search narrows results to exactly 1 ---
  useEffect(() => {
    if (searchText && filtered.length === 1) {
      onSelectClient(filtered[0])
    }
  }, [filtered.length, searchText]) // eslint-disable-line react-hooks/exhaustive-deps

  // --- Active filters count for badge ---
  const activeFilters = [filterHuman, filterUnread, filterWithAdvisor].filter(Boolean).length

  function toggleHuman() {
    const next = !filterHuman
    setFilterHuman(next)
    if (next) { setFilterUnread(false); setFilterWithAdvisor(false) }
  }

  function toggleUnread() {
    const next = !filterUnread
    setFilterUnread(next)
    if (next) { setFilterHuman(false); setFilterWithAdvisor(false) }
  }

  function toggleAdvisor() {
    const next = !filterWithAdvisor
    setFilterWithAdvisor(next)
    if (next) { setFilterHuman(false); setFilterUnread(false) }
  }

  function clearFilters() {
    setSearchText('')
    setFilterHuman(false)
    setFilterUnread(false)
    setFilterWithAdvisor(false)
  }

  return (
    <div id="panel-lista" className="sidebar">
      {/* Header */}
      <div className="sidebar__header">
        <h2 className="sidebar__title">
          <i className="fa-solid fa-gem" style={{ marginRight: 8 }} />
          {agencyName}
        </h2>
        <div className="sidebar__actions">
          <span className="live-badge">En vivo</span>
          <button className="icon-btn" title="Analítica y Reportes" onClick={onOpenReports}>
            <i className="fa-solid fa-chart-column" />
          </button>
          <button className="icon-btn" title="Gestión de Asesores" onClick={onOpenAdvisors}>
            <i className="fa-solid fa-users-cog" />
          </button>
          <button
            id="logout-btn"
            className="icon-btn"
            title="Cerrar sesión"
            onClick={onSignOut}
          >
            <i className="fa-solid fa-right-from-bracket" />
          </button>
        </div>
      </div>

      {/* Search bar */}
      <div className="sidebar__search-bar">
        <div className="search-input-wrap">
          <i className="fa-solid fa-search search-icon" />
          <input
            type="text"
            placeholder="Buscar por nombre, tel. o asesor..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="search-input"
          />
          {searchText && (
            <button
              className="search-clear-btn"
              onClick={() => setSearchText('')}
              title="Limpiar"
            >
              <i className="fa-solid fa-xmark" />
            </button>
          )}
        </div>
      </div>

      {/* Filter pills */}
      <div className="sidebar__filters">
        <button
          className={`filter-pill ${filterHuman ? 'filter-pill--active-dark' : ''}`}
          title="Chats atendidos por humano"
          onClick={toggleHuman}
        >
          <i className="fa-solid fa-user-tie" style={{ marginRight: 4 }} />
          Humano
        </button>
        <button
          className={`filter-pill ${filterUnread ? 'filter-pill--active-gold' : ''}`}
          title="Mensajes sin leer"
          onClick={toggleUnread}
        >
          <i className="fa-solid fa-bell" style={{ marginRight: 4 }} />
          Sin leer
        </button>
        <button
          className={`filter-pill ${filterWithAdvisor ? 'filter-pill--active-blue' : ''}`}
          title="Con asesor asignado"
          onClick={toggleAdvisor}
        >
          <i className="fa-solid fa-id-badge" style={{ marginRight: 4 }} />
          Con asesor
        </button>
        {activeFilters > 0 && (
          <button className="filter-pill filter-pill--clear" onClick={clearFilters} title="Limpiar filtros">
            <i className="fa-solid fa-xmark" />
          </button>
        )}
      </div>

      {/* Stats bar */}
      <div className="sidebar__stats">
        <span>{filtered.length} de {conversations.length} conversaciones</span>
      </div>

      {/* Client list */}
      <div className="sidebar__list">
        {filtered.length === 0 ? (
          <p className="empty-msg">
            {conversations.length === 0
              ? 'Cargando conversaciones...'
              : 'No hay resultados para tu búsqueda o filtro.'}
          </p>
        ) : (
          filtered.map((c) => (
            <ClientItem
              key={c.telefono}
              client={c}
              isActive={selectedPhone === c.telefono}
              onClick={() => onSelectClient(c)}
            />
          ))
        )}
      </div>
    </div>
  )
}
