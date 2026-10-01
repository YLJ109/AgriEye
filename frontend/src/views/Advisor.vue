<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { Plus, MessageSquare, Trash2, Settings, Bot, User, Leaf, ImagePlus, X, SendHorizontal, Lightbulb, Bug, TrendingDown, AlertTriangle, ClipboardList } from 'lucide-vue-next'

const settings = ref(JSON.parse(localStorage.getItem('advisor_settings') || 'null') || {
  apiKey: '', textModel: 'glm-4-flash', visionModel: 'glm-4v-flash',
})
const showSettings = ref(false)
const settingsForm = ref({ ...settings.value })

function saveSettings() {
  settings.value = { ...settingsForm.value }
  localStorage.setItem('advisor_settings', JSON.stringify(settings.value))
  showSettings.value = false
  ElMessage.success('设置已保存')
}

const conversations = ref(JSON.parse(localStorage.getItem('advisor_conversations') || '[]'))
const currentId = ref(conversations.value[0]?.id || '')
const current = computed(() => conversations.value.find(c => c.id === currentId.value))

function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8) }

function newConversation() {
  const conv = { id: genId(), title: '新对话', messages: [], createdAt: Date.now(), updatedAt: Date.now() }
  conversations.value.unshift(conv)
  currentId.value = conv.id
  saveConversations()
}

function deleteConversation(id) {
  conversations.value = conversations.value.filter(c => c.id !== id)
  if (currentId.value === id) currentId.value = conversations.value[0]?.id || ''
  saveConversations()
}

function selectConversation(id) { currentId.value = id }
function saveConversations() { localStorage.setItem('advisor_conversations', JSON.stringify(conversations.value)) }

const question = ref('')
const loading = ref(false)
const chatRef = ref(null)
const imagePreview = ref('')

const suggestions = [
  { icon: Leaf, text: '水稻稻瘟病怎么防治？' },
  { icon: AlertTriangle, text: '小麦叶片发黄是什么原因？' },
  { icon: Bug, text: '玉米螟什么时候防治最好？' },
  { icon: Leaf, text: '番茄晚疫病用什么药？' },
  { icon: TrendingDown, text: '缺钾有什么症状怎么补？' },
  { icon: AlertTriangle, text: '农药药害怎么处理？' },
]

function renderMd(text) {
  try {
    return marked.parse(text)
  } catch {
    return text
  }
}

async function send() {
  const text = question.value.trim()
  if ((!text && !imagePreview.value) || loading.value) return
  if (!settings.value.apiKey) {
    ElMessage.warning('请先配置 API Key')
    showSettings.value = true
    settingsForm.value = { ...settings.value }
    return
  }
  if (!current.value) newConversation()
  loading.value = true
  const hasImage = !!imagePreview.value
  const userMsg = { role: 'user', content: text || '请分析这张图片', time: Date.now(), image: imagePreview.value || null }
  current.value.messages.push(userMsg)
  const pendingIdx = current.value.messages.push({ role: 'assistant', content: '', pending: true, time: Date.now() }) - 1
  if (current.value.title === '新对话' && text) current.value.title = text.slice(0, 20)
  question.value = ''
  const sentImage = imagePreview.value
  imagePreview.value = ''
  await scrollToBottom()
  try {
    const contextMessages = current.value.messages.filter(m => !m.pending && !m.error).slice(-10).map(m => ({ role: m.role, content: m.content }))
    const res = await api.chatCompletions({
      messages: contextMessages,
      api_key: settings.value.apiKey,
      model: hasImage ? settings.value.visionModel : settings.value.textModel,
      image_base64: sentImage || null,
      stream: true,
    })
    current.value.messages[pendingIdx] = { role: 'assistant', content: res.content || '', time: Date.now() }
  } catch (e) {
    current.value.messages[pendingIdx] = { role: 'assistant', content: '请求失败，请稍后重试', error: true, time: Date.now() }
  } finally {
    loading.value = false
    current.value.updatedAt = Date.now()
    saveConversations()
    await scrollToBottom()
  }
}

async function scrollToBottom() { await nextTick(); if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight }
function useSuggestion(s) { question.value = s; send() }

function onImageChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 4 * 1024 * 1024) { ElMessage.warning('图片不能超过 4MB'); return }
  const reader = new FileReader()
  reader.onload = () => { imagePreview.value = reader.result }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function clearImage() { imagePreview.value = '' }
function formatTime(t) { const d = new Date(t); return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}` }

onMounted(() => {
  if (!conversations.value.length) newConversation()
  else if (!currentId.value) currentId.value = conversations.value[0].id
})
</script>

<template>
  <div class="advisor-layout">
    <aside class="conv-sidebar">
      <div class="conv-header">
        <button class="new-conv-btn" @click="newConversation">
          <Plus :size="16" /> 新建对话
        </button>
      </div>
      <div class="conv-list">
        <div v-for="conv in conversations" :key="conv.id" class="conv-item" :class="{ active: conv.id === currentId }" @click="selectConversation(conv.id)">
          <MessageSquare :size="16" class="conv-item-icon" />
          <div class="conv-item-body">
            <div class="conv-item-title">{{ conv.title }}</div>
            <div class="conv-item-time">{{ formatTime(conv.updatedAt) }}</div>
          </div>
          <button class="conv-item-del" @click.stop="deleteConversation(conv.id)">
            <Trash2 :size="14" />
          </button>
        </div>
        <div v-if="!conversations.length" class="conv-empty">暂无对话</div>
      </div>
      <div class="conv-footer">
        <button class="settings-btn" @click="settingsForm = { ...settings }; showSettings = true">
          <Settings :size="16" /> API 设置
        </button>
      </div>
    </aside>

    <main class="conv-main">
      <div class="conv-topbar" v-if="current">
        <span class="conv-topbar-title">{{ current.title }}</span>
        <span class="conv-topbar-count">{{ current.messages.filter(m => !m.pending).length }} 条消息</span>
      </div>
      <div class="chat-body" ref="chatRef">
        <div v-if="current && !current.messages.length" class="welcome">
          <div class="welcome-glyph animate-float"><Bot :size="48" /></div>
          <h3>农智 AI 顾问已就绪</h3>
          <p>基于智谱 GLM 大模型，为您解答病虫害防治、施肥管理、农事安排等问题</p>
          <div class="sug-grid">
            <button v-for="s in suggestions" :key="s.text" class="sug-card" @click="useSuggestion(s.text)">
              <component :is="s.icon" :size="16" class="sug-icon" />{{ s.text }}
            </button>
          </div>
        </div>
        <div v-for="(msg, i) in (current?.messages || [])" :key="i" class="msg" :class="msg.role">
          <div class="msg-avatar">
            <User v-if="msg.role === 'user'" :size="18" />
            <Leaf v-else :size="18" />
          </div>
          <div class="msg-bubble" :class="{ error: msg.error }">
            <img v-if="msg.image" :src="msg.image" class="msg-image" alt="upload" />
            <div v-if="msg.pending" class="typing"><span></span><span></span><span></span></div>
            <div v-else-if="msg.error" class="msg-content">{{ msg.content }}</div>
            <div v-else class="msg-content md-content" v-html="renderMd(msg.content)"></div>
          </div>
        </div>
      </div>
      <div class="chat-input">
        <div class="input-toolbar">
          <label class="img-btn" v-if="!imagePreview">
            <ImagePlus :size="18" />
            <input type="file" accept="image/*" @change="onImageChange" hidden />
          </label>
          <div v-if="imagePreview" class="img-preview">
            <img :src="imagePreview" alt="preview" />
            <button @click="clearImage"><X :size="14" /></button>
          </div>
        </div>
        <div class="input-row">
          <el-input v-model="question" placeholder="输入农业问题，或上传图片让 AI 分析..." type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }" @keydown.enter.exact.prevent="send()" :disabled="loading" />
          <el-button type="primary" :loading="loading" @click="send()" :disabled="!question.trim() && !imagePreview" class="send-btn">
            <SendHorizontal v-if="!loading" :size="18" />
          </el-button>
        </div>
      </div>
    </main>

    <el-dialog v-model="showSettings" title="API 配置" width="480px">
      <div class="settings-form">
        <div class="setting-row">
          <label>智谱 API Key</label>
          <el-input v-model="settingsForm.apiKey" placeholder="请输入智谱 API Key" type="password" show-password />
          <a href="https://open.bigmodel.cn/usercenter/apikeys" target="_blank" class="setting-link">获取 API Key</a>
        </div>
        <div class="setting-row">
          <label>文字模型</label>
          <el-select v-model="settingsForm.textModel" style="width: 100%">
            <el-option label="GLM-4-Flash（免费）" value="glm-4-flash" />
            <el-option label="GLM-4-Plus（高级）" value="glm-4-plus" />
          </el-select>
        </div>
        <div class="setting-row">
          <label>图片理解模型</label>
          <el-select v-model="settingsForm.visionModel" style="width: 100%">
            <el-option label="GLM-4V-Flash（免费）" value="glm-4v-flash" />
            <el-option label="GLM-4V-Plus（高级）" value="glm-4v-plus" />
          </el-select>
        </div>
        <div class="setting-tip">
          <Lightbulb :size="16" />
          <span>智谱 GLM 系列提供免费额度，Flash 版本完全免费。配置后即可使用 AI 对话与图片分析功能。</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.advisor-layout { display: flex; height: calc(100vh - var(--topbar-height) - var(--content-padding) * 2); gap: 10px; overflow: hidden; }

.conv-sidebar { width: 260px; display: flex; flex-direction: column; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; flex-shrink: 0; }
.conv-header { padding: var(--space-3); border-bottom: 1px solid var(--border); }
.new-conv-btn { width: 100%; display: flex; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-elevated); color: var(--fg-secondary); font-size: var(--text-sm); font-weight: 600; cursor: pointer; transition: var(--transition); }
.new-conv-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }

.conv-list { flex: 1; overflow-y: auto; padding: var(--space-2); display: flex; flex-direction: column; gap: 4px; }
.conv-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); border-radius: var(--radius-md); cursor: pointer; transition: var(--transition); }
.conv-item:hover { background: var(--bg-muted); }
.conv-item.active { background: var(--accent-soft); }
.conv-item.active .conv-item-title { color: var(--accent); font-weight: 600; }
.conv-item-icon { color: var(--fg-subtle); flex-shrink: 0; }
.conv-item.active .conv-item-icon { color: var(--accent); }
.conv-item-body { flex: 1; min-width: 0; }
.conv-item-title { font-size: var(--text-sm); color: var(--fg-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-item-time { font-size: var(--text-xs); color: var(--fg-subtle); margin-top: 2px; }
.conv-item-del { opacity: 0; border: none; background: transparent; color: var(--fg-subtle); cursor: pointer; padding: var(--space-3); border-radius: var(--radius-sm); display: flex; align-items: center; transition: var(--transition); }
.conv-item:hover .conv-item-del { opacity: 1; }
.conv-item-del:hover { color: var(--danger); background: var(--bg-muted); }
.conv-empty { text-align: center; color: var(--fg-subtle); font-size: var(--text-sm); padding: var(--space-3); }

.conv-footer { padding: var(--space-3); border-top: 1px solid var(--border); }
.settings-btn { width: 100%; display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); border: none; border-radius: var(--radius-md); background: var(--bg-muted); color: var(--fg-secondary); font-size: var(--text-sm); font-weight: 600; cursor: pointer; transition: var(--transition); }
.settings-btn:hover { background: var(--accent-soft); color: var(--accent); }

.conv-main { flex: 1; display: flex; flex-direction: column; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; min-width: 0; }
.conv-topbar { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3); border-bottom: 1px solid var(--border); }
.conv-topbar-title { font-size: var(--text-md); font-weight: 600; color: var(--fg); }
.conv-topbar-count { font-size: var(--text-xs); color: var(--fg-subtle); }

.chat-body { flex: 1; overflow-y: auto; padding: var(--space-3); display: flex; flex-direction: column; gap: 10px; }

.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }
.welcome-glyph { margin-bottom: 16px; color: var(--accent); display: flex; justify-content: center; filter: drop-shadow(0 8px 24px rgba(31,185,107,0.45)); animation: glyphFloat 4s ease-in-out infinite; }
@keyframes glyphFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.welcome h3 { font-size: var(--text-xl); font-family: var(--font-display); font-weight: 700; color: var(--fg); margin-bottom: 8px; }
.welcome p { color: var(--fg-muted); font-size: var(--text-sm); margin-bottom: 20px; max-width: 420px; }
.sug-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-width: 560px; width: 100%; }
.sug-card { display: flex; align-items: center; gap: 10px; padding: var(--space-3); background: var(--bg-muted); border: 1px solid var(--border); border-radius: var(--radius-md); font-size: var(--text-sm); color: var(--fg-secondary); cursor: pointer; transition: var(--transition); text-align: left; }
.sug-card:hover { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); transform: translateY(-2px); box-shadow: var(--shadow-sm); }
.sug-card:hover .sug-icon { color: var(--lime); }
.sug-icon { color: var(--accent); flex-shrink: 0; transition: var(--transition); }

.msg { display: flex; gap: 10px; animation: fadeInUp 0.4s var(--ease-out) both; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.msg.user .msg-avatar { background: var(--tech); color: var(--fg-on-accent); }
.msg.assistant .msg-avatar { background: var(--accent); color: var(--fg-on-accent); }
.msg-bubble { max-width: 78%; border-radius: var(--radius-lg); padding: var(--space-3); overflow: hidden; word-break: break-word; }
.msg.user .msg-bubble { background: var(--tech); color: var(--fg-on-accent); }
.msg.assistant .msg-bubble { background: var(--bg-muted); border: 1px solid var(--border); border-left: 3px solid var(--accent); color: var(--fg); }
.msg.assistant .msg-bubble.error { border-color: var(--danger); color: var(--danger); }
.msg-content { line-height: 1.6; color: inherit; }
.msg-content.md-content h1, .msg-content.md-content h2, .msg-content.md-content h3 { color: var(--fg); margin: 8px 0 4px; font-family: var(--font-display); font-weight: 700; }
.msg-content.md-content h1 { font-size: 17px; }
.msg-content.md-content h2 { font-size: 15px; }
.msg-content.md-content h3 { font-size: 14px; }
.msg-content.md-content p { margin: 4px 0; color: var(--fg); line-height: 1.7; }
.msg-content.md-content ul, .msg-content.md-content ol { padding-left: 20px; margin: 6px 0; color: var(--fg); }
.msg-content.md-content ul { list-style: disc; }
.msg-content.md-content ol { list-style: decimal; }
.msg-content.md-content li { margin: 4px 0; line-height: 1.6; }
.msg-content.md-content li ul, .msg-content.md-content li ol { margin: 2px 0; }
.msg-content.md-content li > ul { list-style: circle; }
.msg-content.md-content li > ul > li { list-style: square; }
.msg-content.md-content strong { color: var(--accent); font-weight: 700; }
.msg-content.md-content code { background: var(--bg-hover); padding: var(--space-3); border-radius: 4px; font-family: var(--font-mono); font-size: 13px; color: var(--fg); }
.msg-content.md-content pre { background: var(--bg-hover); padding: var(--space-3); border-radius: 8px; overflow-x: auto; margin: 8px 0; }
.msg-content.md-content pre code { background: none; padding: 0; }
.msg-content.md-content blockquote { border-left: 3px solid var(--accent); padding-left: 12px; color: var(--fg-muted); margin: 8px 0; }
.msg-content.md-content hr { border: none; border-top: 1px solid var(--border); margin: 10px 0; }
.msg-content.md-content table { border-collapse: collapse; width: 100%; margin: 8px 0; }
.msg-content.md-content th, .msg-content.md-content td { border: 1px solid var(--border); padding: var(--space-3) 10px; text-align: left; font-size: 13px; }
.msg-content.md-content th { background: var(--bg-muted); font-weight: 700; }
.msg-content.md-content pre { background: var(--bg-hover); padding: var(--space-3); border-radius: var(--radius-md); overflow-x: auto; }
.msg-content.md-content pre code { background: none; padding: 0; }
.msg-content.md-content blockquote { border-left: 3px solid var(--accent); padding-left: 12px; color: var(--fg-muted); margin: 4px 0; }
.msg-content.md-content hr { border: none; border-top: 1px solid var(--border); margin: 6px 0; }
.msg-content.md-content table { border-collapse: collapse; width: 100%; margin: 4px 0; }
.msg-content.md-content th, .msg-content.md-content td { border: 1px solid var(--border); padding: var(--space-3); text-align: left; }
.msg-content.md-content th { background: var(--bg-muted); font-weight: 600; }
.msg-image { max-width: 240px; border-radius: var(--radius-md); margin-bottom: var(--space-2); display: block; }

.typing { display: flex; gap: 6px; padding: var(--space-3); }
.typing span { width: 8px; height: 8px; border-radius: 50%; background: var(--fg-subtle); animation: typing 1.4s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 60%, 100% { opacity: 0.3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }

.chat-input { padding: var(--space-3) 16px; border-top: 1px solid var(--border); background: var(--bg-elevated); display: flex; flex-direction: column; gap: 6px; }
.input-toolbar { display: flex; align-items: center; gap: var(--space-2); min-height: 28px; }
.img-btn { display: flex; align-items: center; cursor: pointer; color: var(--fg-subtle); padding: var(--space-3); border-radius: var(--radius-sm); transition: var(--transition); }
.img-btn:hover { color: var(--accent); background: var(--accent-soft); }
.img-preview { display: flex; align-items: center; gap: var(--space-2); }
.img-preview img { height: 48px; border-radius: var(--radius-sm); border: 1px solid var(--border); }
.img-preview button { border: none; background: var(--bg-muted); color: var(--fg-subtle); cursor: pointer; padding: var(--space-3); border-radius: 50%; display: flex; align-items: center; }
.img-preview button:hover { color: var(--danger); }
.input-row { display: flex; gap: 10px; align-items: flex-end; }
.send-btn { height: 38px; min-width: 44px; display: flex; align-items: center; justify-content: center; }

.settings-form { display: flex; flex-direction: column; gap: var(--space-4); }
.setting-row { display: flex; flex-direction: column; gap: var(--space-2); }
.setting-row label { font-size: var(--text-sm); font-weight: 600; color: var(--fg-secondary); }
.setting-link { font-size: var(--text-xs); color: var(--accent); text-decoration: none; }
.setting-link:hover { text-decoration: underline; }
.setting-tip { display: flex; align-items: flex-start; gap: var(--space-2); padding: var(--space-3); background: var(--accent-soft); border-radius: var(--radius-md); color: var(--fg-secondary); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.setting-tip svg { color: var(--accent); flex-shrink: 0; margin-top: 2px; }

@keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>