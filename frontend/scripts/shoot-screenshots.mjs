/**
 * 批量截取项目界面真实运行截图（用于 README / docs 图示化，与 axe-scan.mjs 同套路）。
 *
 * 前置（本机规范做法，见 MEMORY.md）：
 *   1. 后端：cd backend && F:/Program Files/Python311/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
 *   2. 前端：cd frontend && npm run build && npm run preview -- --port 5188 --strictPort
 *      （vite preview 只监听@localhost/[::1]，127.0.0.1 可能不通，脚本里用 localhost）
 *   3. 换 token：AGRIEYE_TOKEN=$(curl -s --noproxy '*' -X POST http://127.0.0.1:8001/api/auth/login \
 *        -H 'Content-Type: application/json' -d '{"username":"admin","password":"123456"}' | jq -r .access_token)
 *
 * 用法：node scripts/shoot-screenshots.mjs
 * 产物：docs/screenshots/*.png（1.5 倍缩放，5 张约 2.1MB）
 *
 * 坑位备忘：
 * - 识别页上传后必须点「开始批量检测」才会出结果，只 setInputFiles 不会触发推理；
 * - 右侧「结果详情」是 <button class="tab">，无结果时 disabled，直接 click 会一直 retry，
 *   要先 isDisabled() 判断；
 * - 识别结果里那张图是真跑 ONNX 得出的（示例图 backend/uploads/d663a337f32c_t2.jpg）。
 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const BASE = 'http://localhost:5188'
const TOKEN = process.env.AGRIEYE_TOKEN || ''
const OUT = path.resolve('docs/screenshots')
const SAMPLE = path.resolve('backend/uploads/d663a337f32c_t2.jpg')

fs.mkdirSync(OUT, { recursive: true })
if (!TOKEN) { console.error('缺少 AGRIEYE_TOKEN'); process.exit(1) }
if (!fs.existsSync(SAMPLE)) { console.error('缺少示例图：' + SAMPLE); process.exit(1) }

const browser = await chromium.launch()
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5, locale: 'zh-CN',
})
// 绕过登录：后端签发令牌直接塞 localStorage（键名见 src/api/index.js 的 TOKEN_KEY）
await ctx.addInitScript((t) => localStorage.setItem('agrieye_token', t), TOKEN)

const page = await ctx.newPage()
const errs = []
page.on('pageerror', (e) => errs.push(e.message))

async function shot(route, file, wait = 2200) {
  await page.goto(BASE + route, { waitUntil: 'networkidle' })
  await page.waitForTimeout(wait)
  await page.screenshot({ path: path.join(OUT, file) })
  console.log('OK', file)
}

try {
  await shot('/', 'home.png')
  await shot('/history', 'history.png', 2500)
  await shot('/advisor', 'advisor.png', 2500)
  await shot('/calendar', 'calendar.png', 2500)

  // 识别页：真实 UI 上传 + 点「开始批量检测」，确保图里是模型真检出
  await page.goto(BASE + '/recognize', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  await page.locator('input[type=file]').first().setInputFiles(SAMPLE)
  await page.waitForTimeout(1500)
  await page.locator('button:has-text("开始批量检测")').first().click()
  await page.waitForTimeout(14000)
  const tab = page.locator('button.tab:has-text("结果详情")').first()
  try { if (await tab.count() && !(await tab.isDisabled())) await tab.click() } catch {}
  await page.waitForTimeout(2500)
  await page.screenshot({ path: path.join(OUT, 'recognize.png') })
  console.log('OK recognize.png')
  // 注：原本还截了一张 390×844 的移动端口截图，README 已移除（移动端图不要），此处不再生成。
} catch (e) {
  console.error('FAIL', e.message)
} finally {
  if (errs.length) console.error('PAGE_ERRORS', JSON.stringify(errs.slice(0, 5)))
  await browser.close()
}
