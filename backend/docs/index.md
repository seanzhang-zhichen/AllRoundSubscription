# AllRoundSubscription 后端文档索引

欢迎使用AllRoundSubscription后端文档。本文档提供了项目的详细说明、架构设计和开发指南。

## 文档目录

### 项目概述

- [README](./README.md) - 项目简介和快速入门
- [系统架构](./system_architecture.md) - 系统整体架构设计
- [系统流程图](./system_flowcharts.md) - 主要业务流程图

### 技术设计

- [系统设计模式](./system_design_patterns.md) - 系统使用的设计模式和技术架构
- [项目结构](./project_structure.md) - 详细的项目目录结构和模块说明
- [代码文档](./code_documentation.md) - 详细的代码文件和函数说明

### API和数据

- [API路由](./api_routes.md) - API接口路由和使用说明
- [数据模型](./data_models.md) - 数据库模型和关系设计

### 新增文档

- [代码文档](./code_documentation.md) - 详细描述每个文件的作用及代码文件中每个类和函数的作用
- [项目结构](./project_structure.md) - 详细描述项目的目录结构和文件组织
- [系统设计模式](./system_design_patterns.md) - 描述系统设计模式和技术架构选择

## 开发指南

### 环境设置

1. 克隆项目仓库
2. 安装依赖: `pip install -r requirements.txt`
3. 配置环境变量或.env文件
4. 启动开发服务器: `python -m scripts.start-dev`

### Docker部署

详细的Docker部署说明请参考[Docker部署文档](../docs/docker.md)

### 测试

- 运行测试: `pytest`
- 查看测试覆盖率: `pytest --cov=app`

## 常见问题

### 如何添加新的搜索平台？

参考[代码文档](./code_documentation.md)中的搜索适配器部分，创建新的适配器类并注册到适配器注册表中。

### 如何修改数据库模型？

1. 修改`app/models/`目录下的相应模型文件
2. 运行`python -m scripts.migrate_db`创建数据库迁移
3. 更新`app/schemas/`下的相应模式定义

## 贡献指南

1. 创建功能分支
2. 提交更改
3. 确保测试通过
4. 提交Pull Request

## 联系方式

如有问题，请联系项目维护团队。 