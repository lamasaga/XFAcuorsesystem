/**
 * ========================================
 * Electron 主进程
 * ========================================
 *
 * 职责：
 * 1. 启动 Python 后端进程（SQLite 模式）
 * 2. 等待后端就绪
 * 3. 加载前端页面
 * 4. 应用退出时清理后端进程
 */

const { app, BrowserWindow, dialog } = require('electron')
const { spawn, execFile } = require('child_process')
const path = require('path')
const http = require('http')
const fs = require('fs')

// 是否为开发模式
const isDev = !app.isPackaged

let mainWindow = null
let backendProcess = null
const BACKEND_PORT = 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

// ============================================================
// 后端进程管理
// ============================================================

/**
 * 启动 Python 后端
 */
function startBackend() {
  let backendPath, backendExe

  if (isDev) {
    // 开发模式：直接用 Python 运行
    backendPath = path.join(__dirname, '..', 'backend')
    console.log('[Electron] 开发模式 - 使用 Python 脚本启动后端')
    backendProcess = spawn('python', ['run_desktop.py'], {
      cwd: backendPath,
      env: { ...process.env, USE_SQLITE: 'true' },
      stdio: ['pipe', 'pipe', 'pipe']
    })
  } else {
    // 生产模式：使用 PyInstaller 打包的可执行文件
    backendPath = path.join(process.resourcesPath, 'backend')
    const exeName = process.platform === 'win32' ? 'run_desktop.exe' : 'run_desktop'
    backendExe = path.join(backendPath, exeName)

    console.log(`[Electron] 生产模式 - 启动后端: ${backendExe}`)

    if (!fs.existsSync(backendExe)) {
      dialog.showErrorBox(
        '启动失败',
        `找不到后端程序:\n${backendExe}\n\n请确保安装完整。`
      )
      app.quit()
      return
    }

    backendProcess = execFile(backendExe, [], {
      cwd: backendPath,
      env: { ...process.env, USE_SQLITE: 'true' },
      stdio: ['pipe', 'pipe', 'pipe']
    })
  }

  // 监听后端输出
  if (backendProcess.stdout) {
    backendProcess.stdout.on('data', (data) => {
      console.log(`[Backend] ${data.toString().trim()}`)
    })
  }
  if (backendProcess.stderr) {
    backendProcess.stderr.on('data', (data) => {
      console.error(`[Backend ERR] ${data.toString().trim()}`)
    })
  }

  backendProcess.on('error', (err) => {
    console.error('[Electron] 后端进程启动失败:', err)
    dialog.showErrorBox(
      '后端启动失败',
      `无法启动排课引擎:\n${err.message}\n\n请检查 Python 环境是否正确安装。`
    )
  })

  backendProcess.on('exit', (code, signal) => {
    console.log(`[Electron] 后端进程退出: code=${code}, signal=${signal}`)
    backendProcess = null
  })
}

/**
 * 等待后端就绪（轮询健康检查接口）
 */
function waitForBackend(maxRetries = 30, interval = 1000) {
  return new Promise((resolve, reject) => {
    let retries = 0

    const check = () => {
      const req = http.get(`${BACKEND_URL}/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[Electron] 后端已就绪')
          resolve()
        } else {
          retry()
        }
      })

      req.on('error', () => {
        retry()
      })

      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }

    const retry = () => {
      retries++
      if (retries >= maxRetries) {
        reject(new Error('后端启动超时'))
      } else {
        setTimeout(check, interval)
      }
    }

    check()
  })
}

/**
 * 停止后端进程
 */
function stopBackend() {
  if (backendProcess) {
    console.log('[Electron] 正在停止后端进程...')
    if (process.platform === 'win32') {
      // Windows: 用 taskkill 杀掉进程树
      spawn('taskkill', ['/pid', backendProcess.pid.toString(), '/f', '/t'])
    } else {
      backendProcess.kill('SIGTERM')
    }
    backendProcess = null
  }
}

// ============================================================
// 窗口管理
// ============================================================

/**
 * 创建主窗口
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: '智能排课系统',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false  // 先隐藏，等加载完再显示
  })

  // 移除默认菜单栏
  mainWindow.setMenuBarVisibility(false)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

/**
 * 加载前端页面
 */
function loadFrontend() {
  if (isDev) {
    // 开发模式：加载 Vite 开发服务器
    mainWindow.loadURL('http://localhost:3000')
  } else {
    // 生产模式：加载构建好的静态文件
    const frontendPath = path.join(process.resourcesPath, 'frontend', 'index.html')
    mainWindow.loadFile(frontendPath)
  }

  // 页面加载完成后显示窗口
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.show()
  })
}

/**
 * 显示加载画面
 */
function showLoading() {
  const loadingPath = path.join(__dirname, 'loading.html')
  if (fs.existsSync(loadingPath)) {
    mainWindow.loadFile(loadingPath)
    mainWindow.show()
  }
}

// ============================================================
// 应用生命周期
// ============================================================

app.whenReady().then(async () => {
  console.log('[Electron] 应用启动')

  createWindow()
  showLoading()

  // 启动后端
  startBackend()

  try {
    // 等待后端就绪（最多等 30 秒）
    await waitForBackend(30, 1000)

    // 加载前端
    loadFrontend()
  } catch (error) {
    console.error('[Electron] 启动失败:', error)
    dialog.showErrorBox(
      '启动失败',
      '后端服务启动超时，请检查：\n' +
      '1. Python 环境是否正确\n' +
      '2. 端口 8000 是否被占用\n\n' +
      '详细错误信息请查看控制台日志。'
    )
    app.quit()
  }
})

// 所有窗口关闭时退出应用（macOS 除外）
app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// 应用退出前清理
app.on('before-quit', () => {
  stopBackend()
})

// macOS: 点击 dock 图标时重新创建窗口
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
    loadFrontend()
  }
})
