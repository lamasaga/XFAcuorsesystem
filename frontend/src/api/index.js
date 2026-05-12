/**
 * ========================================
 * API 请求基础配置
 * ========================================
 * 
 * 这个文件创建了一个 Axios 实例，用于发送 HTTP 请求到后端 API。
 * 
 * Axios 是什么？
 *   - 一个流行的 HTTP 请求库
 *   - 比原生 fetch 更易用，功能更强大
 *   - 支持请求/响应拦截器
 * 
 * 为什么要创建实例？
 *   - 可以设置统一的配置（如 baseURL）
 *   - 可以添加通用的拦截器
 *   - 方便管理和维护
 * 
 * 使用方法：
 *   import request from '@/api'
 *   
 *   // GET 请求
 *   const res = await request.get('/teachers')
 *   
 *   // POST 请求
 *   const res = await request.post('/teachers', { name: '张三' })
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// -----------------------------------------
// 创建 Axios 实例
// -----------------------------------------
/**
 * 动态获取 API 基础地址
 * 
 * 优先级：
 * 1. 环境变量 VITE_API_BASE（构建时注入）
 * 2. 同域模式：当前域名下的 /api/v1（Nginx 反向代理时使用）
 * 3. 开发默认：http://localhost:8000/api/v1
 */
function getBaseURL() {
  // 构建时通过环境变量注入
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  // Electron 桌面模式或开发模式
  return 'http://localhost:8000/api/v1'
}

const request = axios.create({
  baseURL: getBaseURL(),
  
  // 排课求解可能耗时较长，设置 5 分钟超时
  timeout: 300000,
  
  headers: {
    'Content-Type': 'application/json'
  }
})


// -----------------------------------------
// 请求拦截器
// -----------------------------------------
// 在请求发送之前执行，可以用来：
// - 添加 token 等认证信息
// - 显示 loading 状态
// - 记录日志
request.interceptors.request.use(
  (config) => {
    // 这里可以添加 token
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    
    // 打印请求信息（调试用）
    console.log(`[API] ${config.method.toUpperCase()} ${config.url}`)
    
    return config
  },
  (error) => {
    console.error('[API] 请求错误:', error)
    return Promise.reject(error)
  }
)


// -----------------------------------------
// 响应拦截器
// -----------------------------------------
// 在收到响应之后执行，可以用来：
// - 统一处理错误
// - 提取响应数据
// - 处理登录过期等情况
request.interceptors.response.use(
  (response) => {
    // 请求成功
    // response.data 是后端返回的数据
    const res = response.data
    
    // 如果后端返回的 code 不是 200，说明业务出错
    if (res.code && res.code !== 200) {
      // 显示错误提示
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    
    // 返回数据
    return res
  },
  (error) => {
    // 请求失败（网络错误、超时、服务器错误等）
    console.error('[API] 响应错误:', error)
    
    // 根据错误类型显示不同的提示
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status
      const message = error.response.data?.detail || error.response.data?.message
      
      switch (status) {
        case 400:
          ElMessage.error(message || '请求参数错误')
          break
        case 404:
          ElMessage.error(message || '请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(message || `请求失败 (${status})`)
      }
    } else if (error.code === 'ECONNABORTED') {
      // 请求超时
      ElMessage.error('请求超时，请稍后重试')
    } else {
      // 网络错误
      ElMessage.error('网络连接失败，请检查后端服务是否启动')
    }
    
    return Promise.reject(error)
  }
)


// 导出实例
export default request
