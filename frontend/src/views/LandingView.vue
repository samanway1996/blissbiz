<script setup>
import SiteHeader from '../components/SiteHeader.vue'
import { site } from '../composables/useSite.js'
const development = import.meta.env.DEV
</script>

<template>
  <SiteHeader />
  <main id="main-content" tabindex="-1" class="landing-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow"><span class="small-dot" aria-hidden="true"></span> FOR SMALL BUSINESSES WITH BIG IDEAS</p>
        <h1>Your business.<br>Your very own<br><em>place online.</em></h1>
        <p class="hero-description">Turn what you make into something the world can discover. Create a website, showcase your products, and share your story.</p>
        <a class="button" :href="site.adminUrl('/register')">Start a business today <span aria-hidden="true">→</span></a>
        <p class="hero-footnote">Your name. Your products. Your own storefront.</p>
      </div>
      <div class="example-wrap">
        <div class="example-label"><span class="small-dot" aria-hidden="true"></span> EXAMPLE STOREFRONT</div>
        <div class="example-browser">
          <div class="browser-bar"><div class="browser-dots" aria-hidden="true"><span></span><span></span><span></span></div><span>mydreambakery.yourdomain.com</span></div>
          <div class="example-content">
            <div class="example-brand"><span class="bakery-mark" aria-hidden="true">M</span><span>MyDreamBakery<small>MADE WITH LOVE, EVERY MORNING</small></span></div>
            <h2>A little joy,<br>freshly baked.</h2><p>Good ingredients. Slow mornings. Something delicious.</p>
            <div class="example-products">
              <article><div class="sample-photo bread-photo" role="img" aria-label="Illustration of a sourdough loaf"><div class="loaf"><span></span><span></span><span></span></div></div><h3>Sourdough loaf</h3><span>₹180.00</span></article>
              <article><div class="sample-photo cake-photo" role="img" aria-label="Illustration of a chocolate cake"><div class="cake"><span></span></div></div><h3>Chocolate cake</h3><span>₹499.00</span></article>
            </div>
          </div>
        </div>
        <span class="example-caption">Something like this could be yours.</span>
      </div>
    </section>
    <section class="how-section" aria-labelledby="how-title"><div class="section-intro"><p class="eyebrow">FROM IDEA TO ONLINE</p><h2 id="how-title">A simple start. A world of possibility.</h2></div><div class="steps"><article><span class="step-number">01</span><h3>Make it yours</h3><p>Tell us about your business and choose your website address.</p></article><article><span class="step-number">02</span><h3>Show what you do</h3><p>Add your products, photos, descriptions, and prices.</p></article><article><span class="step-number">03</span><h3>Open your doors</h3><p>Publish your products and share your storefront with customers.</p></article></div></section>
  </main>
  <footer class="site-footer"><span class="brand">blissbiz.</span><span>A home for your next chapter.</span><RouterLink v-if="development && site.isLanding" to="/development">Development status</RouterLink></footer>
</template>
