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
