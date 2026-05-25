/**
 * 将 docs/系统使用指南.md 同步到 frontend/public/guide.md（构建前可手动执行）
 * 用法: node scripts/sync-guide.mjs
 */
import { copyFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const src = join(root, '..', 'docs', '系统使用指南.md')
const dest = join(root, 'public', 'guide.md')

if (!existsSync(src)) {
  console.warn('Skip sync: source not found:', src)
  process.exit(0)
}

copyFileSync(src, dest)
console.log('Synced:', dest)
