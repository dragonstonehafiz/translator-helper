// Nav dropdowns: keep one menu open at a time, close on outside click or Escape.
const menus = document.querySelectorAll('.nav-menu')

menus.forEach(menu => {
  menu.addEventListener('toggle', () => {
    if (!menu.open) return
    menus.forEach(other => { if (other !== menu) other.open = false })
  })
})

document.addEventListener('click', event => {
  menus.forEach(menu => { if (!menu.contains(event.target)) menu.open = false })
})

document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return
  menus.forEach(menu => { menu.open = false })
})

// Tabs: build a tab strip from each .tabs block's .tab-panel[data-tab] children and show one panel at a time.
document.querySelectorAll('.tabs').forEach(tabs => {
  const panels = [...tabs.querySelectorAll(':scope > .tab-panel')]
  const list = document.createElement('div')
  list.className = 'tab-list'
  list.setAttribute('role', 'tablist')

  const select = index => {
    panels.forEach((panel, i) => { panel.hidden = i !== index })
    list.querySelectorAll('button').forEach((button, i) => button.setAttribute('aria-selected', String(i === index)))
  }

  panels.forEach((panel, index) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.setAttribute('role', 'tab')
    button.textContent = panel.dataset.tab
    button.addEventListener('click', () => select(index))
    list.appendChild(button)
    panel.setAttribute('role', 'tabpanel')
  })

  tabs.prepend(list)
  select(0)
})
