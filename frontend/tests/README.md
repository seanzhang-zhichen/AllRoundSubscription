# 前端测试文档

本项目采用 Vitest 作为测试框架，提供完整的单元测试、集成测试和端到端测试覆盖。

## 测试架构

```
tests/
├── setup.js                 # 测试环境设置
├── testRunner.js            # 测试运行器
├── utils/                   # 工具函数测试
│   ├── cacheManager.test.js
│   ├── feedbackManager.test.js
│   └── networkManager.test.js
├── components/              # 组件测试
│   └── ContentCard.test.js
├── stores/                  # 状态管理测试
│   └── content.test.js
└── integration/             # 集成测试
    └── userFlow.test.js
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 运行测试

```bash
# 运行所有测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行测试（单次执行）
npm run test:run

# 启动测试UI界面
npm run test:ui
```

### 使用测试运行器

```bash
# 运行所有测试套件
node tests/testRunner.js all

# 只运行单元测试
node tests/testRunner.js unit

# 只运行集成测试
node tests/testRunner.js integration

# 生成覆盖率报告
node tests/testRunner.js coverage

# 运行特定测试文件
node tests/testRunner.js file tests/utils/cacheManager.test.js

# 启动监听模式
node tests/testRunner.js watch
```

## 测试类型

### 1. 单元测试

测试单个函数、组件或模块的功能。

**示例：**
```javascript
// tests/utils/cacheManager.test.js
describe('CacheManager', () => {
  it('应该能够设置和获取缓存', async () => {
    const cache = new CacheManager()
    await cache.set('key', 'value')
    const result = await cache.get('key')
    expect(result).toBe('value')
  })
})
```

### 2. 组件测试

测试 Vue 组件的渲染和交互。

**示例：**
```javascript
// tests/components/ContentCard.test.js
describe('ContentCard', () => {
  it('应该正确渲染文章标题', () => {
    const wrapper = mount(ContentCard, {
      props: { article: mockArticle }
    })
    expect(wrapper.find('.article-title').text()).toBe(mockArticle.title)
  })
})
```

### 3. 状态管理测试

测试 Pinia store 的状态变化和操作。

**示例：**
```javascript
// tests/stores/content.test.js
describe('Content Store', () => {
  it('应该能够获取动态流数据', async () => {
    const store = useContentStore()
    await store.fetchFeed()
    expect(store.feedList).toHaveLength(2)
  })
})
```

### 4. 集成测试

测试多个组件或模块之间的交互。

**示例：**
```javascript
// tests/integration/userFlow.test.js
describe('用户交互流程', () => {
  it('应该能够完成完整的内容浏览流程', async () => {
    // 测试从加载内容到用户交互的完整流程
  })
})
```

## 测试工具和Mock

### 1. uni-app API Mock

所有 uni-app API 都在 `setup.js` 中进行了 Mock：

```javascript
global.uni = {
  request: vi.fn(),
  showToast: vi.fn(),
  navigateTo: vi.fn(),
  // ... 更多 API
}
```

### 2. 组件Mock

对于复杂的子组件，可以使用 Mock：

```javascript
vi.mock('@/components/LazyImage.vue', () => ({
  default: {
    name: 'LazyImage',
    template: '<div class="mock-lazy-image"></div>'
  }
}))
```

### 3. 模块Mock

Mock 外部依赖模块：

```javascript
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))
```

## 测试最佳实践

### 1. 测试命名

- 使用描述性的测试名称
- 使用中文描述测试场景
- 遵循 "应该...当...时" 的格式

```javascript
it('应该在用户点击收藏按钮时更新收藏状态', () => {
  // 测试代码
})
```

### 2. 测试结构

使用 AAA 模式（Arrange, Act, Assert）：

```javascript
it('应该正确处理API错误', async () => {
  // Arrange - 准备测试数据
  const error = new Error('网络错误')
  mockRequest.get.mockRejectedValue(error)
  
  // Act - 执行操作
  await expect(store.fetchData()).rejects.toThrow('网络错误')
  
  // Assert - 验证结果
  expect(store.loading).toBe(false)
})
```

### 3. Mock 管理

- 在 `beforeEach` 中清理 Mock
- 使用具体的 Mock 返回值
- 验证 Mock 调用

```javascript
beforeEach(() => {
  vi.clearAllMocks()
})

it('应该调用正确的API', async () => {
  mockRequest.get.mockResolvedValue({ data: 'test' })
  
  await store.fetchData()
  
  expect(mockRequest.get).toHaveBeenCalledWith('/api/data')
})
```

### 4. 异步测试

正确处理异步操作：

```javascript
it('应该处理异步操作', async () => {
  const promise = store.fetchData()
  
  // 验证加载状态
  expect(store.loading).toBe(true)
  
  await promise
  
  // 验证完成状态
  expect(store.loading).toBe(false)
})
```

## 覆盖率要求

项目设置了以下覆盖率阈值：

- **分支覆盖率**: 70%
- **函数覆盖率**: 70%
- **行覆盖率**: 70%
- **语句覆盖率**: 70%

### 查看覆盖率报告

```bash
# 生成覆盖率报告
npm run test:coverage

# 查看HTML报告
open coverage/index.html
```

## 持续集成

### GitHub Actions 配置

```yaml
name: Frontend Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v3
```

### 预提交钩子

使用 husky 在提交前运行测试：

```json
{
  "husky": {
    "hooks": {
      "pre-commit": "npm run test:run"
    }
  }
}
```

## 调试测试

### 1. 使用调试器

```javascript
it('调试测试', () => {
  debugger // 在浏览器中会暂停执行
  expect(true).toBe(true)
})
```

### 2. 查看测试输出

```javascript
it('查看输出', () => {
  console.log('调试信息:', someVariable)
  expect(someVariable).toBeDefined()
})
```

### 3. 只运行特定测试

```javascript
it.only('只运行这个测试', () => {
  // 只有这个测试会运行
})

describe.skip('跳过这个测试套件', () => {
  // 这个套件会被跳过
})
```

## 常见问题

### 1. uni-app API 未定义

确保在 `setup.js` 中正确 Mock 了所有使用的 uni-app API。

### 2. 组件渲染错误

检查是否正确 Mock 了子组件和依赖模块。

### 3. 异步测试超时

增加测试超时时间或确保正确等待异步操作完成。

### 4. Mock 不生效

确保 Mock 在测试文件顶部声明，并在 `beforeEach` 中清理。

## 贡献指南

1. 为新功能编写测试
2. 确保测试覆盖率达标
3. 遵循测试命名规范
4. 添加必要的文档说明

## 相关资源

- [Vitest 官方文档](https://vitest.dev/)
- [Vue Test Utils 文档](https://test-utils.vuejs.org/)
- [Testing Library 最佳实践](https://testing-library.com/docs/guiding-principles)
- [Jest Mock 函数](https://jestjs.io/docs/mock-functions)