import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

export default defineConfig({
  test: {
    // 测试环境
    environment: 'happy-dom',
    
    // 全局设置
    globals: true,
    
    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        'unpackage/',
        '**/*.config.js',
        '**/*.config.ts',
        'tests/',
        '**/*.test.js',
        '**/*.test.ts',
        '**/*.spec.js',
        '**/*.spec.ts'
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        }
      }
    },
    
    // 设置文件
    setupFiles: ['./tests/setup.js'],
    
    // 包含的测试文件
    include: [
      'tests/**/*.{test,spec}.{js,ts}',
      'components/**/*.{test,spec}.{js,ts}',
      'utils/**/*.{test,spec}.{js,ts}',
      'stores/**/*.{test,spec}.{js,ts}'
    ],
    
    // 排除的文件
    exclude: [
      'node_modules/',
      'dist/',
      'unpackage/',
      '.git/'
    ],
    
    // 测试超时时间
    testTimeout: 10000,
    
    // 钩子超时时间
    hookTimeout: 10000,
    
    // 并发测试
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        maxThreads: 4,
        minThreads: 1
      }
    }
  },
  
  resolve: {
    alias: {
      '@': resolve(__dirname, '.'),
      '~': resolve(__dirname, '.'),
      '@/components': resolve(__dirname, 'components'),
      '@/utils': resolve(__dirname, 'utils'),
      '@/stores': resolve(__dirname, 'stores'),
      '@/pages': resolve(__dirname, 'pages'),
      '@/static': resolve(__dirname, 'static')
    }
  },
  
  define: {
    // 定义全局变量
    __UNI_PLATFORM__: '"h5"',
    __UNI_FEATURE_LONGPRESS__: true,
    process: {
      env: {
        NODE_ENV: 'test'
      }
    }
  }
})