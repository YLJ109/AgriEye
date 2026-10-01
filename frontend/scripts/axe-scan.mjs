// 无障碍扫描（UX-002）：注入 axe-core 对多个页面跑一遍，输出 critical/serious 违规。
// 用法：node scripts/axe-scan.mjs [baseURL] [token]
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { chromium } from 'playwright-core'

const require = createRequire(import.meta.url)
const axePath = require.resolve('axe-core/axe.min.js')
const axeSource = readFileSync(axePath, 'utf8')

const baseURL = process.argv[2] || 'http://localhost:5188'
const token = process.argv[3] || ''

const routes = ['/', '/recognize', '/advisor', '/history', '/calendar']

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
if (token) {
  // 登录后才能进内页：把 JWT 写进同源 localStorage
  await context.addInitScript((t) => {
    if (t) window.localStorage.setItem('agrieye_token', t)
  }, token)
}

let totalCritical = 0
let totalSerious = 0

for (const route of routes) {
  const page = await context.newPage()
  try {
    await page.goto(baseURL + route, { waitUntil: 'networkidle', timeout: 30000 })
    await page.waitForTimeout(1200)
    await page.addScriptTag({ content: axeSource })
    const result = await page.evaluate(async () => {
      // @ts-ignore
      return await window.axe.run(document, {
        resultTypes: ['violations'],
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
      })
    })
    const bad = result.violations.filter(v => ['critical', 'serious'].includes(v.impact))
    const crit = result.violations.filter(v => v.impact === 'critical').length
    const seri = result.violations.filter(v => v.impact === 'serious').length
    totalCritical += crit
    totalSerious += seri
    console.log(`\n=== ${route} ===  违规 ${result.violations.length}（critical ${crit} / serious ${seri}）`)
    for (const v of bad) {
      console.log(`  [${v.impact}] ${v.id}: ${v.help}`)
      const nodes = v.nodes.slice(0, 3).map(n => n.target.join(' '))
      console.log(`      影响 ${v.nodes.length} 处，例：${nodes.join(' | ')}`)
    }
  } catch (e) {
    console.log(`\n=== ${route} === 扫描失败：${e.message}`)
  } finally {
    await page.close()
  }
}

await browser.close()
console.log(`\n合计 critical=${totalCritical} serious=${totalSerious}`)
process.exit(totalCritical === 0 ? 0 : 1)
