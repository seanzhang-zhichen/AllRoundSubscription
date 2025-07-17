/**
 * 测试运行器
 * 提供测试执行和报告功能
 */

import { execSync } from 'child_process'
import fs from 'fs'
import path from 'path'

class TestRunner {
  constructor() {
    this.testResults = {
      unit: null,
      integration: null,
      coverage: null
    }
  }

  /**
   * 运行所有测试
   */
  async runAllTests() {
    console.log('🚀 开始运行前端测试套件...\n')

    try {
      // 运行单元测试
      await this.runUnitTests()
      
      // 运行集成测试
      await this.runIntegrationTests()
      
      // 生成覆盖率报告
      await this.generateCoverageReport()
      
      // 生成测试报告
      this.generateTestReport()
      
      console.log('✅ 所有测试完成！')
      
    } catch (error) {
      console.error('❌ 测试执行失败:', error.message)
      process.exit(1)
    }
  }

  /**
   * 运行单元测试
   */
  async runUnitTests() {
    console.log('📋 运行单元测试...')
    
    try {
      const output = execSync('npm run test:run -- --reporter=json', {
        encoding: 'utf8',
        cwd: process.cwd()
      })
      
      this.testResults.unit = JSON.parse(output)
      console.log('✅ 单元测试完成')
      
    } catch (error) {
      console.error('❌ 单元测试失败')
      throw error
    }
  }

  /**
   * 运行集成测试
   */
  async runIntegrationTests() {
    console.log('🔗 运行集成测试...')
    
    try {
      const output = execSync('npm run test:run -- --reporter=json tests/integration/', {
        encoding: 'utf8',
        cwd: process.cwd()
      })
      
      this.testResults.integration = JSON.parse(output)
      console.log('✅ 集成测试完成')
      
    } catch (error) {
      console.error('❌ 集成测试失败')
      throw error
    }
  }

  /**
   * 生成覆盖率报告
   */
  async generateCoverageReport() {
    console.log('📊 生成覆盖率报告...')
    
    try {
      execSync('npm run test:coverage', {
        encoding: 'utf8',
        cwd: process.cwd()
      })
      
      // 读取覆盖率报告
      const coveragePath = path.join(process.cwd(), 'coverage', 'coverage-summary.json')
      if (fs.existsSync(coveragePath)) {
        this.testResults.coverage = JSON.parse(fs.readFileSync(coveragePath, 'utf8'))
      }
      
      console.log('✅ 覆盖率报告生成完成')
      
    } catch (error) {
      console.error('❌ 覆盖率报告生成失败')
      throw error
    }
  }

  /**
   * 生成测试报告
   */
  generateTestReport() {
    console.log('📄 生成测试报告...')
    
    const report = {
      timestamp: new Date().toISOString(),
      summary: this.generateSummary(),
      details: {
        unit: this.testResults.unit,
        integration: this.testResults.integration,
        coverage: this.testResults.coverage
      }
    }
    
    // 保存报告到文件
    const reportPath = path.join(process.cwd(), 'test-report.json')
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
    
    // 输出摘要到控制台
    this.printSummary(report.summary)
    
    console.log(`📄 测试报告已保存到: ${reportPath}`)
  }

  /**
   * 生成测试摘要
   */
  generateSummary() {
    const summary = {
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      skippedTests: 0,
      coverage: {
        lines: 0,
        functions: 0,
        branches: 0,
        statements: 0
      }
    }

    // 统计单元测试结果
    if (this.testResults.unit) {
      summary.totalTests += this.testResults.unit.numTotalTests || 0
      summary.passedTests += this.testResults.unit.numPassedTests || 0
      summary.failedTests += this.testResults.unit.numFailedTests || 0
      summary.skippedTests += this.testResults.unit.numPendingTests || 0
    }

    // 统计集成测试结果
    if (this.testResults.integration) {
      summary.totalTests += this.testResults.integration.numTotalTests || 0
      summary.passedTests += this.testResults.integration.numPassedTests || 0
      summary.failedTests += this.testResults.integration.numFailedTests || 0
      summary.skippedTests += this.testResults.integration.numPendingTests || 0
    }

    // 统计覆盖率
    if (this.testResults.coverage && this.testResults.coverage.total) {
      const total = this.testResults.coverage.total
      summary.coverage.lines = total.lines?.pct || 0
      summary.coverage.functions = total.functions?.pct || 0
      summary.coverage.branches = total.branches?.pct || 0
      summary.coverage.statements = total.statements?.pct || 0
    }

    return summary
  }

  /**
   * 打印测试摘要
   */
  printSummary(summary) {
    console.log('\n📊 测试摘要:')
    console.log('─'.repeat(50))
    console.log(`总测试数: ${summary.totalTests}`)
    console.log(`通过: ${summary.passedTests} ✅`)
    console.log(`失败: ${summary.failedTests} ❌`)
    console.log(`跳过: ${summary.skippedTests} ⏭️`)
    console.log(`成功率: ${((summary.passedTests / summary.totalTests) * 100).toFixed(2)}%`)
    
    console.log('\n📈 代码覆盖率:')
    console.log('─'.repeat(50))
    console.log(`行覆盖率: ${summary.coverage.lines.toFixed(2)}%`)
    console.log(`函数覆盖率: ${summary.coverage.functions.toFixed(2)}%`)
    console.log(`分支覆盖率: ${summary.coverage.branches.toFixed(2)}%`)
    console.log(`语句覆盖率: ${summary.coverage.statements.toFixed(2)}%`)
    
    // 覆盖率警告
    const minCoverage = 70
    const avgCoverage = (
      summary.coverage.lines + 
      summary.coverage.functions + 
      summary.coverage.branches + 
      summary.coverage.statements
    ) / 4
    
    if (avgCoverage < minCoverage) {
      console.log(`\n⚠️  警告: 平均覆盖率 ${avgCoverage.toFixed(2)}% 低于最低要求 ${minCoverage}%`)
    } else {
      console.log(`\n✅ 覆盖率达标: 平均覆盖率 ${avgCoverage.toFixed(2)}%`)
    }
  }

  /**
   * 运行特定测试文件
   */
  async runSpecificTest(testFile) {
    console.log(`🎯 运行特定测试: ${testFile}`)
    
    try {
      const output = execSync(`npm run test:run -- ${testFile}`, {
        encoding: 'utf8',
        cwd: process.cwd()
      })
      
      console.log(output)
      console.log('✅ 测试完成')
      
    } catch (error) {
      console.error('❌ 测试失败:', error.message)
      throw error
    }
  }

  /**
   * 监听模式运行测试
   */
  async runTestsInWatchMode() {
    console.log('👀 启动测试监听模式...')
    
    try {
      execSync('npm run test', {
        stdio: 'inherit',
        cwd: process.cwd()
      })
      
    } catch (error) {
      console.error('❌ 监听模式启动失败:', error.message)
      throw error
    }
  }
}

// 命令行接口
if (import.meta.url === `file://${process.argv[1]}`) {
  const runner = new TestRunner()
  const command = process.argv[2]
  const arg = process.argv[3]

  switch (command) {
    case 'all':
      runner.runAllTests()
      break
    case 'unit':
      runner.runUnitTests()
      break
    case 'integration':
      runner.runIntegrationTests()
      break
    case 'coverage':
      runner.generateCoverageReport()
      break
    case 'file':
      if (arg) {
        runner.runSpecificTest(arg)
      } else {
        console.error('请指定测试文件路径')
        process.exit(1)
      }
      break
    case 'watch':
      runner.runTestsInWatchMode()
      break
    default:
      console.log('使用方法:')
      console.log('  node testRunner.js all        # 运行所有测试')
      console.log('  node testRunner.js unit       # 运行单元测试')
      console.log('  node testRunner.js integration # 运行集成测试')
      console.log('  node testRunner.js coverage   # 生成覆盖率报告')
      console.log('  node testRunner.js file <path> # 运行特定测试文件')
      console.log('  node testRunner.js watch      # 监听模式')
      break
  }
}

export default TestRunner