/**
 * 知识库定位：TS 直读知识库静态数据文件的路径层。
 *
 * 知识库 = anti-patterns/ + success-patterns/ + profiles/ + docs/policies/
 * （与 Python 引擎 `prgenius/src/prgenius/utils.py::get_repo_root()` 使用的是同一套目录，
 * 只是这里显式配置，不再靠祖先目录嗅探。）
 */
import { existsSync, readFileSync } from 'node:fs'
import { dirname, isAbsolute, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { PrGeniusConfigError } from './config.ts'

/** 包内知识库根（默认值）：包根目录，即 src/ 的上一级。 */
export function defaultKbRoot(): string {
  return dirname(dirname(fileURLToPath(import.meta.url)))
}

export interface KbLayout {
  /** 知识库根（绝对路径）。 */
  root: string
  antiPatterns: string
  successPatterns: string
  profiles: string
  policies: string
}

/**
 * 解析知识库根并检查布局。目录缺失时抛 PrGeniusConfigError —— 配置错误要响亮，不带病运行。
 */
export function resolveKbRoot(kbRoot: string | undefined): KbLayout {
  const raw = kbRoot && kbRoot.trim() !== '' ? kbRoot : defaultKbRoot()
  const root = isAbsolute(raw) ? resolve(raw) : resolve(process.cwd(), raw)
  const layout: KbLayout = {
    root,
    antiPatterns: join(root, 'anti-patterns'),
    successPatterns: join(root, 'success-patterns'),
    profiles: join(root, 'profiles'),
    policies: join(root, 'docs', 'policies'),
  }
  const missing = Object.entries(layout)
    .filter(([key]) => key !== 'root')
    .filter(([, dir]) => !existsSync(dir))
    .map(([key, dir]) => `${key} (${dir})`)
  if (!existsSync(root) || missing.length > 0) {
    throw new PrGeniusConfigError(
      'kbRoot',
      `knowledge base layout not found under ${root}; missing: ${missing.length > 0 ? missing.join(', ') : root}`,
    )
  }
  return layout
}

export interface PackageMeta {
  name: string
  version: string
}

/** 读取包元信息（name/version），供 describe() 与 MCP clientInfo 使用。 */
export function readPackageMeta(packageRoot: string): PackageMeta {
  const file = join(packageRoot, 'package.json')
  const raw = readFileSync(file, 'utf8')
  const data = JSON.parse(raw) as { name?: string; version?: string }
  return { name: data.name ?? 'pr-genius', version: data.version ?? '0.0.0' }
}
