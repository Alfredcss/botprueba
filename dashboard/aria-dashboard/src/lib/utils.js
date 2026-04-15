/**
 * Parses Markdown-style links and bare URLs into clickable <a> tags.
 * Port of the `formatearEnlaces` function from the original dashboard.html.
 * @param {string} text
 * @returns {string} HTML string with links replaced
 */
export function formatearEnlaces(text) {
  if (!text) return ''

  // 1. Named markdown links: [label](url)
  let processed = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_, label, url) =>
      `<a href="${url}" target="_blank" rel="noopener noreferrer" class="link-style">${label} <i class="fa-solid fa-external-link-alt" style="font-size:10px;margin-left:2px;"></i></a>`
  )

  // 2. Bare URLs (not already inside an href)
  processed = processed.replace(/(^|\s)(https?:\/\/[^\s)]+)/g, (match, space, url) => {
    let tail = ''
    if (['.', ',', ';', ':'].includes(url.slice(-1))) {
      tail = url.slice(-1)
      url = url.slice(0, -1)
    }
    return `${space}<a href="${url}" target="_blank" rel="noopener noreferrer" class="link-style">${url}</a>${tail}`
  })

  return processed
}

/**
 * Parses the raw conversation log string into an array of message objects.
 * Supports multiple timestamp formats from the Python backend.
 * @param {string} log
 * @param {string} [fallbackDate] - "DD/MM" used for legacy [HH:MM]-only timestamps
 * @returns {{ role: string, text: string, time: string, date: string }[]}
 */
export function parseMessages(log, fallbackDate = '') {
  if (!log) return []

  const lines = log.split(/\r?\n/)
  const grouped = []
  let current = null

  lines.forEach((line) => {
    if (!line.trim() && !current) return
    // Match lines that start with an optional timestamp then a role prefix
    const isNew = line.match(/^(?:\[[\d/: -]+\]\s*)?(Cliente:|Bot:|Asesor:)/)
    if (isNew) {
      if (current) grouped.push(current)
      current = line
    } else if (current) {
      current += '\n' + line
    }
  })
  if (current) grouped.push(current)

  return grouped.map((raw) => {
    let timeStr = ''
    let dateStr = ''
    let rest = raw

    // Format 1: [DD/MM/YYYY HH:MM]  e.g. [15/04/2025 13:30]
    const fmt1 = rest.match(/^\[(\d{2})\/(\d{2})\/\d{4} (\d{2}:\d{2})\]\s*/)
    if (fmt1) {
      dateStr = `${fmt1[1]}/${fmt1[2]}`   // "15/04"
      timeStr = fmt1[3]                    // "13:30"
      rest = rest.replace(fmt1[0], '')
    } else {
      // Format 2: [DD/MM HH:MM]  e.g. [15/04 13:30]
      const fmt2 = rest.match(/^\[(\d{2}\/\d{2}) (\d{2}:\d{2})\]\s*/)
      if (fmt2) {
        dateStr = fmt2[1]   // "15/04"
        timeStr = fmt2[2]   // "13:30"
        rest = rest.replace(fmt2[0], '')
      } else {
        // Format 3: [YYYY-MM-DD HH:MM]  e.g. [2025-04-15 13:30]
        const fmt3 = rest.match(/^\[(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})\]\s*/)
        if (fmt3) {
          dateStr = `${fmt3[3]}/${fmt3[2]}`   // "15/04"
          timeStr = fmt3[4]                    // "13:30"
          rest = rest.replace(fmt3[0], '')
        } else {
          // Format 4 (legacy): [HH:MM] — use fallbackDate if provided
          const fmt4 = rest.match(/^\[(\d{2}:\d{2})\]\s*/)
          if (fmt4) {
            timeStr = fmt4[1]
            dateStr = fallbackDate   // use contact date as fallback
            rest = rest.replace(fmt4[0], '')
          }
        }
      }
    }

    let role = 'unknown'
    let text = rest
    if (rest.startsWith('Cliente:')) {
      role = 'Cliente'
      text = rest.replace('Cliente:', '').trim()
    } else if (rest.startsWith('Bot:')) {
      role = 'Bot'
      text = rest.replace('Bot:', '').trim()
    } else if (rest.startsWith('Asesor:')) {
      role = 'Asesor'
      text = rest.replace('Asesor:', '').trim()
    }

    return { role, text, time: timeStr, date: dateStr }
  })
}
