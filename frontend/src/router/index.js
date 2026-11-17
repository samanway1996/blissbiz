import { createRouter, createWebHistory } from 'vue-router'
import DevelopmentView from '../views/DevelopmentView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: DevelopmentView }],
})

