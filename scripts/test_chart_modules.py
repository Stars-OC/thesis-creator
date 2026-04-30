# -*- coding: utf-8 -*-
"""
图表模块测试套件

测试范围：
1. 关键词提取器 (keyword_extractor.py)
2. 模板加载器 (chart_template_loader.py)
3. 离线渲染器 (chart_renderer_offline.py)
4. LLM 混合生成器 (llm_chart_generator.py)
5. 修复后的 chart_renderer.py

运行方式：
    python test_chart_modules.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加 scripts 目录到路径
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# 测试结果收集
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': [],
    'start_time': None,
    'end_time': None,
}


def log_test(module: str, test_name: str, passed: bool, message: str = ""):
    """记录测试结果"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  [{module}] {test_name}: {status}")
    if message:
        print(f"    -> {message}")

    if passed:
        test_results['passed'] += 1
    else:
        test_results['failed'] += 1
        test_results['errors'].append(f"{module}.{test_name}: {message}")


def test_keyword_extractor():
    """测试关键词提取器"""
    print("\n" + "="*60)
    print("测试模块: keyword_extractor.py")
    print("="*60)

    try:
        from keyword_extractor import KeywordExtractor
        extractor = KeywordExtractor()

        # 测试 1: 实体提取
        test_text = """
        本系统采用Vue.js作为前端框架，Spring Boot作为后端服务框架，
        使用MySQL数据库存储数据。系统包含用户管理模块、订单管理模块和商品管理模块。
        用户和管理员都可以登录系统进行操作。
        """
        entities = extractor.extract_entities(test_text)

        has_systems = len(entities['systems']) > 0
        log_test("KeywordExtractor", "实体提取-系统", has_systems,
                f"提取到 {len(entities['systems'])} 个系统: {entities['systems']}")

        has_roles = len(entities['roles']) > 0
        log_test("KeywordExtractor", "实体提取-角色", has_roles,
                f"提取到 {len(entities['roles'])} 个角色: {entities['roles']}")

        has_tech = len(entities['tech_stack']) > 0
        log_test("KeywordExtractor", "实体提取-技术栈", has_tech,
                f"提取到 {len(entities['tech_stack'])} 个技术: {entities['tech_stack']}")

        # 测试 2: 流程步骤提取
        flow_text = """
        用户登录流程：
        1. 用户输入用户名和密码
        2. 系统验证用户信息
        3. 判断是否验证通过
        4. 返回登录结果
        """
        steps = extractor.extract_flow_steps(flow_text)

        has_steps = len(steps) >= 1  # 至少提取到1个步骤
        log_test("KeywordExtractor", "流程步骤提取", has_steps,
                f"提取到 {len(steps)} 个步骤: {[s['name'][:15]+'...' if len(s['name'])>15 else s['name'] for s in steps]}")

        if has_steps:
            has_decision = any(s['type'] == 'decision' for s in steps)
            log_test("KeywordExtractor", "决策节点识别", has_decision,
                    f"决策节点: {[s['name'] for s in steps if s['type'] == 'decision']}")

        # 测试 3: 关系提取
        relation_text = """
        前端调用后端API获取数据，后端访问数据库查询信息，
        用户模块管理用户信息。
        """
        relations = extractor.extract_relations(relation_text)

        has_relations = len(relations) > 0
        log_test("KeywordExtractor", "关系提取", has_relations,
                f"提取到 {len(relations)} 个关系")

        return True

    except Exception as e:
        log_test("KeywordExtractor", "模块导入", False, str(e))
        return False


def test_template_loader():
    """测试模板加载器"""
    print("\n" + "="*60)
    print("测试模块: chart_template_loader.py")
    print("="*60)

    try:
        from chart_template_loader import ChartTemplateLoader
        loader = ChartTemplateLoader()

        # 测试 1: 索引加载
        templates = loader.list_templates()
        has_templates = len(templates) > 0
        log_test("TemplateLoader", "索引加载", has_templates,
                f"加载了 {len(templates)} 种图表类型模板")

        # 测试 2: 模板匹配
        template = loader.find_template("架构图", "Web系统前后端分离架构设计")
        found_template = template is not None
        log_test("TemplateLoader", "模板匹配-架构图", found_template,
                template['name'] if template else "未找到")

        # 测试 3: 模板渲染
        if template:
            variables = {'frontend_name': 'Vue前端', 'backend_name': 'Spring Boot'}
            mermaid = loader.render_template(template, variables, "图2-1", "系统架构图")
            has_output = len(mermaid) > 50
            log_test("TemplateLoader", "模板渲染", has_output,
                    f"生成了 {len(mermaid)} 字符的 Mermaid 代码")

        # 测试 4: 不同类型模板匹配
        flow_template = loader.find_template("流程图", "用户登录业务流程")
        log_test("TemplateLoader", "模板匹配-流程图", flow_template is not None,
                flow_template['name'] if flow_template else "未找到")

        er_template = loader.find_template("E-R图", "电商订单商品")
        log_test("TemplateLoader", "模板匹配-E-R图", er_template is not None,
                er_template['name'] if er_template else "未找到")

        return True

    except Exception as e:
        log_test("TemplateLoader", "模块导入", False, str(e))
        return False


def test_offline_renderer():
    """测试离线渲染器"""
    print("\n" + "="*60)
    print("测试模块: chart_renderer_offline.py")
    print("="*60)

    try:
        from chart_renderer_offline import OfflineChartRenderer, FontConfig

        # 测试 1: 字体配置
        font_config = FontConfig()
        has_font = font_config.available_font is not None
        log_test("OfflineRenderer", "中文字体配置", has_font,
                f"使用字体: {font_config.available_font}")

        # 创建输出目录
        output_dir = Path(__file__).parent / "test_output"
        output_dir.mkdir(exist_ok=True)

        renderer = OfflineChartRenderer(output_dir=str(output_dir), theme="academic")

        # 测试 2: 主题获取
        themes = renderer.get_available_themes()
        log_test("OfflineRenderer", "主题列表", len(themes) >= 3,
                f"可用主题: {themes}")

        # 测试 3: 流程图渲染
        steps = [
            {'name': '用户输入用户名密码', 'type': 'io', 'node_id': 'B'},
            {'name': '系统验证用户信息', 'type': 'process', 'node_id': 'C'},
            {'name': '判断验证是否通过', 'type': 'decision', 'node_id': 'D'},
            {'name': '返回登录结果', 'type': 'io', 'node_id': 'E'},
        ]

        output_path = str(output_dir / "test_flowchart.png")
        success = renderer.render_flowchart(steps, output_path, "用户登录流程", "图3-1")
        log_test("OfflineRenderer", "流程图渲染", success,
                f"输出: {output_path}" if success else "渲染失败")

        # 验证文件存在
        if success:
            file_exists = Path(output_path).exists()
            file_size = Path(output_path).stat().st_size if file_exists else 0
            log_test("OfflineRenderer", "流程图文件", file_exists and file_size > 1000,
                    f"文件大小: {file_size} bytes")

        # 测试 4: 时序图渲染
        participants = [
            {'id': 'U', 'name': '用户'},
            {'id': 'F', 'name': '前端'},
            {'id': 'B', 'name': '后端'},
            {'id': 'D', 'name': '数据库'},
        ]

        messages = [
            {'from': 'U', 'to': 'F', 'content': '发起请求', 'type': 'sync'},
            {'from': 'F', 'to': 'B', 'content': 'HTTP请求', 'type': 'sync'},
            {'from': 'B', 'to': 'D', 'content': '查询数据', 'type': 'sync'},
            {'from': 'D', 'to': 'B', 'content': '返回结果', 'type': 'return'},
            {'from': 'B', 'to': 'F', 'content': 'HTTP响应', 'type': 'return'},
            {'from': 'F', 'to': 'U', 'content': '展示结果', 'type': 'return'},
        ]

        output_path = str(output_dir / "test_sequence.png")
        success = renderer.render_sequence_diagram(participants, messages, output_path, "登录时序图")
        log_test("OfflineRenderer", "时序图渲染", success,
                f"输出: {output_path}" if success else "渲染失败")

        # 测试 5: E-R图渲染
        entities = [
            {
                'name': '用户',
                'attributes': [
                    {'name': 'id', 'type': 'bigint'},
                    {'name': 'username', 'type': 'varchar'},
                    {'name': 'email', 'type': 'varchar'},
                ]
            },
            {
                'name': '订单',
                'attributes': [
                    {'name': 'id', 'type': 'bigint'},
                    {'name': 'user_id', 'type': 'bigint'},
                    {'name': 'total', 'type': 'decimal'},
                ]
            },
        ]

        relations = [
            {'from': '用户', 'to': '订单', 'type': '1:N'},
        ]

        output_path = str(output_dir / "test_er.png")
        success = renderer.render_er_diagram(entities, relations, output_path, "用户-订单关系")
        log_test("OfflineRenderer", "E-R图渲染", success,
                f"输出: {output_path}" if success else "渲染失败")

        # 测试 6: 主题切换
        renderer.set_theme("business")
        log_test("OfflineRenderer", "主题切换", renderer.theme.get('node_color') == '#2196F3',
                f"当前主题颜色: {renderer.theme.get('node_color', 'N/A')}")

        return True

    except ImportError as e:
        log_test("OfflineRenderer", "模块导入", False, f"缺少依赖: {e}")
        return False
    except Exception as e:
        log_test("OfflineRenderer", "未知错误", False, str(e))
        return False


def test_llm_generator():
    """测试 LLM 混合生成器"""
    print("\n" + "="*60)
    print("测试模块: llm_chart_generator.py")
    print("="*60)

    try:
        from llm_chart_generator import LLMChartGenerator, HybridChartGenerator

        # 测试 1: LLM 生成器初始化
        generator = LLMChartGenerator()
        log_test("LLMGenerator", "初始化", True,
                f"API Key 已配置: {bool(generator.api_key)}")

        # 测试 2: 成本估算
        description = "用户登录系统的业务流程，包含输入用户名密码、验证、判断是否通过、返回结果等步骤"
        cost = generator.estimate_cost(description, "")
        log_test("LLMGenerator", "成本估算", cost > 0,
                f"估算成本: ${cost:.6f}")

        # 测试 3: 复杂场景判断
        is_complex = generator.is_complex_scenario(description, "")
        log_test("LLMGenerator", "复杂场景判断", True,
                f"是否复杂: {is_complex}")

        # 测试 4: Prompt 模板存在性
        has_prompts = len(generator.CHART_PROMPTS) >= 5
        log_test("LLMGenerator", "Prompt模板", has_prompts,
                f"支持 {len(generator.CHART_PROMPTS)} 种图表类型")

        # 测试 5: 混合生成器
        hybrid = HybridChartGenerator()
        mermaid = hybrid.generate("流程图", description, "", "图3-1", "用户登录流程图")
        has_output = mermaid and len(mermaid) > 50
        log_test("HybridGenerator", "混合生成", has_output,
                f"生成了 {len(mermaid) if mermaid else 0} 字符的代码")

        # 测试 6: 默认生成（无 LLM）
        mermaid = hybrid._generate_default("架构图", "图2-1", "系统架构图", "Web系统")
        has_default = len(mermaid) > 50
        log_test("HybridGenerator", "默认生成", has_default,
                f"生成了 {len(mermaid)} 字符的代码")

        return True

    except Exception as e:
        log_test("LLMGenerator", "模块导入", False, str(e))
        return False


def test_chart_renderer_fixes():
    """测试 chart_renderer.py 的修复"""
    print("\n" + "="*60)
    print("测试模块: chart_renderer.py (修复验证)")
    print("="*60)

    try:
        # 测试 1: zlib 导入位置
        with open(scripts_dir / "chart_renderer.py", 'r', encoding='utf-8') as f:
            content = f.read()

        zlib_at_top = 'import zlib' in content[:1000]
        log_test("ChartRenderer", "zlib导入位置", zlib_at_top,
                "zlib 已移至文件顶部" if zlib_at_top else "zlib 导入位置不正确")

        # 测试 2: logger 使用
        uses_logger = 'self.logger' in content or 'get_logger()' in content
        log_test("ChartRenderer", "日志模块", uses_logger,
                "已使用 logger 替代 print" if uses_logger else "仍使用 print")

        # 测试 3: Kroki 错误处理
        has_http_error = 'HTTPError' in content
        has_url_error = 'URLError' in content
        has_timeout = 'TimeoutError' in content
        log_test("ChartRenderer", "Kroki错误处理", has_http_error and has_url_error and has_timeout,
                f"HTTPError: {has_http_error}, URLError: {has_url_error}, TimeoutError: {has_timeout}")

        # 测试 4: 模块导入测试
        from chart_renderer import ChartRenderer
        renderer = ChartRenderer(output_dir="test_output")
        log_test("ChartRenderer", "模块实例化", True, "成功创建实例")

        return True

    except Exception as e:
        log_test("ChartRenderer", "测试失败", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    test_results['start_time'] = datetime.now()

    print("\n" + "="*60)
    print("图表模块测试套件")
    print(f"开始时间: {test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 执行各模块测试
    test_keyword_extractor()
    test_template_loader()
    test_offline_renderer()
    test_llm_generator()
    test_chart_renderer_fixes()

    test_results['end_time'] = datetime.now()
    duration = (test_results['end_time'] - test_results['start_time']).total_seconds()

    # 输出汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"[PASS] 通过: {test_results['passed']}")
    print(f"[FAIL] 失败: {test_results['failed']}")
    print(f"[TIME] 耗时: {duration:.2f} 秒")

    if test_results['errors']:
        print("\n失败详情:")
        for error in test_results['errors']:
            print(f"  - {error}")

    # 输出测试文件列表
    output_dir = Path(__file__).parent / "test_output"
    if output_dir.exists():
        print(f"\n生成的测试文件 ({output_dir}):")
        for f in output_dir.iterdir():
            if f.is_file():
                size = f.stat().st_size
                print(f"  - {f.name} ({size:,} bytes)")

    # 返回成功状态
    return test_results['failed'] == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)