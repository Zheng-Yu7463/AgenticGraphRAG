import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// 如果你有全局 store，请在此处 import 并 use(store)
// import store from './stores'


const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')




