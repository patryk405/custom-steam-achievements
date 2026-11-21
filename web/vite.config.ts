import {defineConfig} from 'vite';import react from '@vitejs/plugin-react';import {fileURLToPath} from 'node:url';
export default defineConfig({base:'/custom-steam-achievements/',plugins:[react()],resolve:{alias:{'zod':fileURLToPath(new URL('./node_modules/zod/index.js',import.meta.url)),'@':fileURLToPath(new URL('../website',import.meta.url))}},build:{outDir:'../docs-site',emptyOutDir:true}});
