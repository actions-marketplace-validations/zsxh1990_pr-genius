import { defineConfig } from 'tsdown'

/**
 * 宿主提供的包**必须** external，不能打进 bundle（issue #101）。
 *
 * DSH web 宿主自带 React / Cordis / slots API。若把 React 内联进
 * dist/index.mjs，宿主里的组件会同时存在两份 React —— `useState` 那套
 * hooks 依赖「同一个 React 的 dispatcher」，两份实例会让 3/4 个侧边栏界面
 * 在带自己 React 的宿主上直接抛 "Invalid hook call"。
 *
 * 判据：只要那个包在插件加载时由宿主解析，就 external。
 *   - react / react-dom —— 宿主渲染层
 *   - cordis —— 宿主容器
 *
 * 注意 **不能** 一刀切 external 掉 `@deepseek-ai/*`：源码里唯一运行时的
 * `@deepseek-ai` import 是 `@deepseek-ai/schemastery`，而它只是 devDependency
 * （`dependencies` 里放的是公开的 `schemastery`）。把它设成 external 会让
 * 解包产物 `Cannot find package '@deepseek-ai/schemastery'`，apply() 直接崩
 * —— smoke gate 曾因此 4 个 FAIL。它必须打进 bundle。
 * 另外两个 `@deepseek-ai/*`（cordis、dsh-client-ui-slots）是 type-only，
 * 不进运行时，不需要列。
 *
 * node: 内建模块由 target 处理，不列在这里。
 */
export default defineConfig({
  entry: ['src/index.ts', 'src/config.ts', 'src/kb.ts', 'src/mcp-client.ts', 'src/ui/surfaces.ts'],
  format: ['esm'],
  target: 'node22',
  dts: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    'react/jsx-runtime',
    'react-dom/server',
    'cordis',
    'schemastery',
  ],
})
