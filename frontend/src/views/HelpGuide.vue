<template>
  <div class="help-guide">
    <div class="help-header card">
      <div class="help-header-inner">
        <div>
          <h1>使用帮助</h1>
          <p class="subtitle">面向教务老师的网页操作说明</p>
        </div>
        <div class="help-actions">
          <el-button @click="reloadGuide" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button type="primary" plain @click="openStaticPage">
            <el-icon><Link /></el-icon>
            新窗口打开
          </el-button>
          <el-button @click="$router.push('/dashboard')">
            <el-icon><Back /></el-icon>
            返回首页
          </el-button>
        </div>
      </div>
    </div>

    <div class="help-body card" v-loading="loading">
      <el-alert
        v-if="error"
        type="error"
        :title="error"
        show-icon
        :closable="false"
        class="help-error"
      />
      <article v-else class="help-doc" v-html="htmlContent" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { Refresh, Link, Back } from '@element-plus/icons-vue'

const loading = ref(true)
const error = ref('')
const htmlContent = ref('')

marked.setOptions({
  gfm: true,
  breaks: true
})

/** 将仓库内 Markdown 链接转为纯文本，避免 Web 端 404 */
function prepareMarkdown(md) {
  return md
    .replace(/\[([^\]]+)\]\(\.\/[^)]+\.md\)/g, '$1')
    .replace(/^> \*\*适用对象\*\*：.*$/m, '')
    .replace(/^> \*\*最后更新\*\*：.*$/m, '')
    .replace(/^> \*\*说明\*\*：.*$/m, '')
}

async function loadGuide() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}guide.md`, { cache: 'no-cache' })
    if (!res.ok) {
      throw new Error(`无法加载指南文件 (${res.status})`)
    }
    const text = await res.text()
    htmlContent.value = marked.parse(prepareMarkdown(text))
  } catch (e) {
    error.value = e.message || '加载失败'
    htmlContent.value = ''
  } finally {
    loading.value = false
  }
}

function reloadGuide() {
  loadGuide()
}

function openStaticPage() {
  const base = import.meta.env.BASE_URL || '/'
  const url = `${window.location.origin}${base}help/index.html`
  window.open(url, '_blank', 'noopener')
}

onMounted(() => {
  loadGuide()
})
</script>

<style lang="scss" scoped>
.help-guide {
  max-width: 960px;
  margin: 0 auto;
}

.help-header {
  margin-bottom: 20px;
  padding: 20px 24px;

  .help-header-inner {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    flex-wrap: wrap;
  }

  h1 {
    margin: 0 0 8px;
    font-size: 24px;
    color: var(--el-text-color-primary);
  }

  .subtitle {
    margin: 0;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }

  .help-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
}

.help-body {
  padding: 28px 32px 40px;
  min-height: 400px;
}

.help-error {
  margin-bottom: 16px;
}

.help-doc {
  :deep(h1) {
    display: none;
  }

  :deep(h2) {
    margin: 32px 0 16px;
    padding-bottom: 8px;
    font-size: 20px;
    border-bottom: 2px solid var(--el-color-primary-light-7);
    color: #1e3a5f;
  }

  :deep(h3) {
    margin: 24px 0 12px;
    font-size: 16px;
    color: #334155;
  }

  :deep(p),
  :deep(li) {
    line-height: 1.75;
    color: var(--el-text-color-regular);
  }

  :deep(blockquote) {
    margin: 16px 0;
    padding: 12px 16px;
    background: #eff6ff;
    border-left: 4px solid var(--el-color-primary);
    border-radius: 0 8px 8px 0;
    color: #475569;
  }

  :deep(table) {
    width: 100%;
    margin: 16px 0;
    border-collapse: collapse;
    font-size: 14px;
  }

  :deep(th),
  :deep(td) {
    border: 1px solid var(--el-border-color);
    padding: 10px 12px;
    text-align: left;
  }

  :deep(th) {
    background: #f1f5f9;
    font-weight: 600;
  }

  :deep(tr:nth-child(even) td) {
    background: #f8fafc;
  }

  :deep(code) {
    padding: 2px 6px;
    background: #f1f5f9;
    border-radius: 4px;
    font-size: 13px;
  }

  :deep(pre) {
    margin: 16px 0;
    padding: 16px;
    background: #1e293b;
    color: #e2e8f0;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.6;
  }

  :deep(pre code) {
    padding: 0;
    background: none;
    color: inherit;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 1.5em;
    margin: 12px 0;
  }

  :deep(hr) {
    margin: 28px 0;
    border: none;
    border-top: 1px solid var(--el-border-color);
  }

  :deep(strong) {
    color: #0f172a;
  }
}
</style>
