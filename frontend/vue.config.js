const { defineConfig } = require('@vue/cli-service');
const webpack = require("webpack");
// const { GenerateSW } = require('workbox-webpack-plugin');
const path = require("path");

const pickVueEnv = () => {
  const env = {};
  for (const key in process.env) {
    if (key.startsWith("VUE_APP_")) {
      env[key] = JSON.stringify(process.env[key]);
    }
  }
  return env;
};

module.exports = defineConfig({
  transpileDependencies: true,
  css: {
    loaderOptions: {
      postcss: {
        postcssOptions: {
          plugins: [
            require('tailwindcss'),
            require('autoprefixer'),
          ],
        },
      },
    },
  },
  devServer: {
    allowedHosts: "all",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
    client: {
      webSocketURL: "ws://127.0.0.1:8080/ws",
    },
  },
  configureWebpack: {
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    plugins: [
      // new GenerateSW({
      //   clientsClaim: true,
      //   skipWaiting: true,
      //   runtimeCaching: [
      //     {
      //       urlPattern: ({ url }) => url.href.includes('s3.amazonaws.com') && /\.(?:png|jpg|jpeg|svg|gif)$/.test(url.pathname),
      //       handler: 'CacheFirst',
      //       options: {
      //         cacheName: 'images',
      //         expiration: {
      //           maxEntries: 50,
      //           maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
      //         },
      //         cacheableResponse: {
      //           statuses: [0, 200],
      //         },
      //         // Normalize the URL by stripping query parameters
      //         matchOptions: {
      //           ignoreSearch: true,
      //         },
      //       },
      //     },
      //   ],
      // }),
      new webpack.DefinePlugin({
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: "false",
        "process.env": pickVueEnv(),
      }),
    ],
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: "babel-loader",
            options: {
              presets: ["@babel/preset-env"],
              plugins: ["@babel/plugin-transform-private-methods"],
            },
          },
        },
      ],
    },
  },
  pwa: {
    name: 'Project Echo',
    themeColor: '#ffffff',
    msTileColor: '#000000',
    manifestOptions: {
      short_name: 'Echo',
      description: 'An engaging audio content creation app.',
      background_color: '#ffffff',
      icons: [
        {
          src: "favicons/android-chrome-192x192.png",
          sizes: "192x192",
          type: "image/png"
        },
        {
          src: "favicons/android-chrome-512x512.png",
          sizes: "512x512",
          type: "image/png"
        },
        {
          src: "favicons/android-chrome-maskable-192x192.png",
          sizes: "192x192",
          type: "image/png",
          purpose: "maskable"
        },
        {
          src: "favicons/android-chrome-maskable-512x512.png",
          sizes: "512x512",
          type: "image/png",
          purpose: "maskable"
        }
      ]
    },
    appleMobileWebAppCapable: 'yes',
    appleMobileWebAppStatusBarStyle: 'black',
    workboxOptions: {
      clientsClaim: true,
      skipWaiting: true,
      runtimeCaching: [
        {
          urlPattern: /\/api\//,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-cache',
            cacheableResponse: {
              statuses: [200],
            },
          },
        },
        {
          urlPattern: ({ url }) => url.href.includes('s3.amazonaws.com') && /\.(?:png|jpg|jpeg|svg|gif)$/.test(url.pathname),
          handler: 'CacheFirst',
          options: {
            cacheName: 'images',
            expiration: {
              maxEntries: 50,
              maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
            },
            cacheableResponse: {
              statuses: [0, 200],
            },
            // Normalize the URL by stripping query parameters
            matchOptions: {
              ignoreSearch: true,
            },
          },
        },
      ],
    },
  },
});