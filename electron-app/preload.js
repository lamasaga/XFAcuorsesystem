/**
 * Electron Preload 脚本
 * 
 * 安全地暴露 Electron API 给渲染进程。
 * 当前暂无需暴露的 API，保留此文件以备后续扩展。
 */

const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true
})
