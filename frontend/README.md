# 内容聚合微信小程序前端

基于 uni-app 框架开发的多平台内容聚合微信小程序前端项目。

## 技术栈

- **框架**: uni-app 3.x
- **前端框架**: Vue 3
- **状态管理**: Pinia
- **构建工具**: Vite
- **测试框架**: Vitest + Playwright
- **UI组件**: uni-ui

## 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 开发环境启动

#### 微信小程序开发
```bash
npm run dev:mp-weixin
# 或者
npm run serve
```

#### 其他平台开发
```bash
# H5 开发
npm run dev:h5

# 支付宝小程序
npm run dev:mp-alipay

# 百度小程序
npm run dev:mp-baidu

# 字节跳动小程序
npm run dev:mp-toutiao

# QQ 小程序
npm run dev:mp-qq
```

### 3. 生产环境构建

```bash
# 构建微信小程序
npm run build:mp-weixin
# 或者
npm run build

# 构建其他平台
npm run build:h5          # H5
npm run build:mp-alipay   # 支付宝小程序
npm run build:mp-baidu    # 百度小程序
```

## 开发调试

### 微信小程序调试步骤

1. 启动开发服务器：
   ```bash
   npm run dev:mp-weixin
   ```

2. 打开微信开发者工具

3. 导入项目：选择 `dist/dev/mp-weixin` 目录

4. 开始调试开发

### 项目结构

```
frontend/
├── components/          # 公共组件
├── pages/              # 页面文件
├── static/             # 静态资源
├── stores/             # Pinia 状态管理
├── styles/             # 样式文件
├── utils/              # 工具函数
├── tests/              # 测试文件
├── App.vue             # 应用入口组件
├── main.js             # 应用入口文件
├── manifest.json       # 应用配置文件
├── pages.json          # 页面路由配置
└── package.json        # 项目配置
```

## 测试

### 单元测试
```bash
# 运行测试
npm run test

# 运行测试（单次）
npm run test:run

# 生成覆盖率报告
npm run test:coverage

# 测试 UI 界面
npm run test:ui
```

### E2E 测试
```bash
# 运行端到端测试
npm run test:e2e

# E2E 测试 UI 界面
npm run test:e2e:ui
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `npm run serve` | 启动微信小程序开发服务器 |
| `npm run build` | 构建微信小程序生产版本 |
| `npm run dev:h5` | 启动 H5 开发服务器 |
| `npm run test` | 运行单元测试 |
| `npm run test:e2e` | 运行端到端测试 |

## 开发注意事项

1. **平台兼容性**: 使用 uni-app 的条件编译确保多平台兼容
2. **组件使用**: 优先使用 uni-ui 组件库中的组件
3. **状态管理**: 使用 Pinia 进行全局状态管理
4. **样式规范**: 使用 rpx 单位确保多端适配
5. **API 调用**: 统一使用 uni.request 进行网络请求

## 部署说明

构建完成后，各平台的产物位于：
- 微信小程序: `dist/build/mp-weixin/`
- H5: `dist/build/h5/`
- 其他小程序平台: `dist/build/mp-{platform}/`

将对应平台的构建产物上传到相应的开发者平台即可。

## 问题排查

如果遇到问题，请检查：
1. Node.js 版本是否符合要求
2. 依赖是否正确安装
3. 微信开发者工具版本是否最新
4. 项目路径是否正确导入

更多问题请参考 [uni-app 官方文档](https://uniapp.dcloud.net.cn/)。