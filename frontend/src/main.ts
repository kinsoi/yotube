import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'
import { i18n } from './lib/i18n.svelte'
import { startRouter } from './lib/router.svelte'

document.documentElement.lang = i18n.locale
startRouter()

export default mount(App, { target: document.getElementById('app')! })
