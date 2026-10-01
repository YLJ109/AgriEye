// vite.config.js
import { defineConfig } from "file:///D:/front-back/AgriculturalScience/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/front-back/AgriculturalScience/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import AutoImport from "file:///D:/front-back/AgriculturalScience/frontend/node_modules/unplugin-auto-import/dist/vite.js";
import Components from "file:///D:/front-back/AgriculturalScience/frontend/node_modules/unplugin-vue-components/dist/vite.js";
import { ElementPlusResolver } from "file:///D:/front-back/AgriculturalScience/frontend/node_modules/unplugin-vue-components/dist/resolvers.js";
import { fileURLToPath, URL } from "node:url";
var __vite_injected_original_import_meta_url = "file:///D:/front-back/AgriculturalScience/frontend/vite.config.js";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] })
  ],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url)) }
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8001", changeOrigin: true },
      "/uploads": { target: "http://localhost:8001", changeOrigin: true }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "echarts": ["echarts"],
          "element-plus": ["element-plus"],
          "vue-vendor": ["vue", "vue-router", "pinia"]
        }
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxmcm9udC1iYWNrXFxcXEFncmljdWx0dXJhbFNjaWVuY2VcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXGZyb250LWJhY2tcXFxcQWdyaWN1bHR1cmFsU2NpZW5jZVxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovZnJvbnQtYmFjay9BZ3JpY3VsdHVyYWxTY2llbmNlL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXHJcbmltcG9ydCBBdXRvSW1wb3J0IGZyb20gJ3VucGx1Z2luLWF1dG8taW1wb3J0L3ZpdGUnXHJcbmltcG9ydCBDb21wb25lbnRzIGZyb20gJ3VucGx1Z2luLXZ1ZS1jb21wb25lbnRzL3ZpdGUnXHJcbmltcG9ydCB7IEVsZW1lbnRQbHVzUmVzb2x2ZXIgfSBmcm9tICd1bnBsdWdpbi12dWUtY29tcG9uZW50cy9yZXNvbHZlcnMnXHJcbmltcG9ydCB7IGZpbGVVUkxUb1BhdGgsIFVSTCB9IGZyb20gJ25vZGU6dXJsJ1xyXG5cclxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcclxuICBwbHVnaW5zOiBbXHJcbiAgICB2dWUoKSxcclxuICAgIEF1dG9JbXBvcnQoeyByZXNvbHZlcnM6IFtFbGVtZW50UGx1c1Jlc29sdmVyKCldIH0pLFxyXG4gICAgQ29tcG9uZW50cyh7IHJlc29sdmVyczogW0VsZW1lbnRQbHVzUmVzb2x2ZXIoKV0gfSksXHJcbiAgXSxcclxuICByZXNvbHZlOiB7XHJcbiAgICBhbGlhczogeyAnQCc6IGZpbGVVUkxUb1BhdGgobmV3IFVSTCgnLi9zcmMnLCBpbXBvcnQubWV0YS51cmwpKSB9LFxyXG4gIH0sXHJcbiAgc2VydmVyOiB7XHJcbiAgICBwb3J0OiA1MTczLFxyXG4gICAgcHJveHk6IHtcclxuICAgICAgJy9hcGknOiB7IHRhcmdldDogJ2h0dHA6Ly9sb2NhbGhvc3Q6ODAwMScsIGNoYW5nZU9yaWdpbjogdHJ1ZSB9LFxyXG4gICAgICAnL3VwbG9hZHMnOiB7IHRhcmdldDogJ2h0dHA6Ly9sb2NhbGhvc3Q6ODAwMScsIGNoYW5nZU9yaWdpbjogdHJ1ZSB9LFxyXG4gICAgfSxcclxuICB9LFxyXG4gIGJ1aWxkOiB7XHJcbiAgICByb2xsdXBPcHRpb25zOiB7XHJcbiAgICAgIG91dHB1dDoge1xyXG4gICAgICAgIG1hbnVhbENodW5rczoge1xyXG4gICAgICAgICAgJ2VjaGFydHMnOiBbJ2VjaGFydHMnXSxcclxuICAgICAgICAgICdlbGVtZW50LXBsdXMnOiBbJ2VsZW1lbnQtcGx1cyddLFxyXG4gICAgICAgICAgJ3Z1ZS12ZW5kb3InOiBbJ3Z1ZScsICd2dWUtcm91dGVyJywgJ3BpbmlhJ10sXHJcbiAgICAgICAgfSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgfSxcclxufSkiXSwKICAibWFwcGluZ3MiOiAiO0FBQXdULFNBQVMsb0JBQW9CO0FBQ3JWLE9BQU8sU0FBUztBQUNoQixPQUFPLGdCQUFnQjtBQUN2QixPQUFPLGdCQUFnQjtBQUN2QixTQUFTLDJCQUEyQjtBQUNwQyxTQUFTLGVBQWUsV0FBVztBQUxnSyxJQUFNLDJDQUEyQztBQU9wUCxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTO0FBQUEsSUFDUCxJQUFJO0FBQUEsSUFDSixXQUFXLEVBQUUsV0FBVyxDQUFDLG9CQUFvQixDQUFDLEVBQUUsQ0FBQztBQUFBLElBQ2pELFdBQVcsRUFBRSxXQUFXLENBQUMsb0JBQW9CLENBQUMsRUFBRSxDQUFDO0FBQUEsRUFDbkQ7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU8sRUFBRSxLQUFLLGNBQWMsSUFBSSxJQUFJLFNBQVMsd0NBQWUsQ0FBQyxFQUFFO0FBQUEsRUFDakU7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVEsRUFBRSxRQUFRLHlCQUF5QixjQUFjLEtBQUs7QUFBQSxNQUM5RCxZQUFZLEVBQUUsUUFBUSx5QkFBeUIsY0FBYyxLQUFLO0FBQUEsSUFDcEU7QUFBQSxFQUNGO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixjQUFjO0FBQUEsVUFDWixXQUFXLENBQUMsU0FBUztBQUFBLFVBQ3JCLGdCQUFnQixDQUFDLGNBQWM7QUFBQSxVQUMvQixjQUFjLENBQUMsT0FBTyxjQUFjLE9BQU87QUFBQSxRQUM3QztBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
