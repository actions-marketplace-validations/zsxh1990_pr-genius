import { defineConfig } from 'tsdown'

export default defineConfig({
  entry: ['src/index.ts', 'src/config.ts', 'src/kb.ts', 'src/mcp-client.ts', 'src/ui/surfaces.ts'],
  format: ['esm'],
  target: 'node22',
  dts: true,
  clean: true,
})
