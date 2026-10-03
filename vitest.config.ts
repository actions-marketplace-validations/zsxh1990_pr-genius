import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['test/**/*.ts'],
    // fixtures 是上游 catalog 的字节快照（被测试当纯文本解析），不是测试文件
    exclude: ['test/fixtures/**', '**/node_modules/**'],
    environment: 'node',
  },
  esbuild: {
    jsx: 'automatic',
  },
})
