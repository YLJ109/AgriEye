// ESLint 扁平配置（UX-001）
// 原则：只对新代码把关，不因存量代码的历史问题阻塞开发。
//   - 统一用 warn 级别，CI 与本地都不因存量告警失败
//   - 关掉与本项目风格冲突的规则（单文件组件名、模板里的 v-html 等）
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'node_modules/**', 'public/**'] },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],

  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      // 单文件组件名（如 Home.vue）在本项目是既定风格
      'vue/multi-word-component-names': 'off',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-undef': 'warn',
      'no-empty': ['warn', { allowEmptyCatch: true }],
      'no-console': 'off',
      'vue/no-v-html': 'off',   // MarkdownView 内已用 DOMPurify 净化，见 SEC-004
    },
  },
]
