const { defineConfig } = require("@vue/cli-service");
module.exports = {
  devServer: {
    proxy: {
      "/api/v1": {
        target: "http://localhost:8000", // 后端服务地址
        changeOrigin: true,
        pathRewrite: { "^/api/v1": "/api/v1" }, // 保持路径不变
      },
    },
    client: {
      overlay: {
        warnings: false,
        runtimeErrors: (error) => {
          const ignoreErrors = [
            "ResizeObserver loop limit exceeded",
            "ResizeObserver loop completed with undelivered notifications.",
          ];
          if (ignoreErrors.includes(error.message)) {
            return false;
          }
        },
      },
    },
  },
};
