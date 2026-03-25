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
 * The log format is: "[HH:MM] Bot:|Cliente:|Asesor: <text>\n..."
 * @param {string} log
 * @returns {{ role: string, text: string, time: string }[]}
 */
export function parseMessages(log) {
  if (!log) return []

  const lines = log.split(/\r?\n/)
  const grouped = []
  let current = null

  lines.forEach((line) => {
    if (!line.trim() && !current) return
    const isNew = line.match(/^(?:\[\d{2}:\d{2}\]\s*)?(Cliente:|Bot:|Asesor:)/)
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
    const timeMatch = raw.match(/^\[(\d{2}:\d{2})\]\s*/)
    if (timeMatch) {
      timeStr = timeMatch[1]
      raw = raw.replace(timeMatch[0], '')
    }

    let role = 'unknown'
    let text = raw
    if (raw.startsWith('Cliente:')) {
      role = 'Cliente'
      text = raw.replace('Cliente:', '').trim()
    } else if (raw.startsWith('Bot:')) {
      role = 'Bot'
      text = raw.replace('Bot:', '').trim()
    } else if (raw.startsWith('Asesor:')) {
      role = 'Asesor'
      text = raw.replace('Asesor:', '').trim()
    }

    return { role, text, time: timeStr }
  })
}
