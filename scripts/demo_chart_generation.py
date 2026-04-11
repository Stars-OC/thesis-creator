# -*- coding: utf-8 -*-
"""
图表生成示例脚本

演示如何使用新模块生成各类图表
"""

import sys
from pathlib import Path

# 添加 scripts 目录到路径
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from chart_renderer_offline import OfflineChartRenderer
from llm_chart_generator import HybridChartGenerator


def demo_offline_render():
    """演示离线渲染 - 无需任何外部工具"""
    print("\n" + "="*60)
    print("演示: matplotlib 离线渲染")
    print("="*60)

    # 创建输出目录
    output_dir = scripts_dir / "demo_output"
    output_dir.mkdir(exist_ok=True)

    # 创建渲染器
    renderer = OfflineChartRenderer(output_dir=str(output_dir), theme="academic")

    # 1. 生成流程图
    print("\n[1] 生成流程图...")
    steps = [
        {'name': '用户输入用户名密码', 'type': 'io', 'node_id': 'B'},
        {'name': '系统验证用户信息', 'type': 'process', 'node_id': 'C'},
        {'name': '判断是否验证通过', 'type': 'decision', 'node_id': 'D'},
        {'name': '返回登录结果', 'type': 'io', 'node_id': 'E'},
    ]

    output_path = str(output_dir / "demo_flowchart.png")
    renderer.render_flowchart(steps, output_path, "用户登录流程", "图3-1")
    print(f"    输出: {output_path}")

    # 2. 生成时序图
    print("\n[2] 生成时序图...")
    participants = [
        {'id': 'U', 'name': '用户'},
        {'id': 'F', 'name': '前端'},
        {'id': 'B', 'name': '后端'},
        {'id': 'D', 'name': '数据库'},
    ]

    messages = [
        {'from': 'U', 'to': 'F', 'content': '发起登录请求', 'type': 'sync'},
        {'from': 'F', 'to': 'B', 'content': 'HTTP请求', 'type': 'sync'},
        {'from': 'B', 'to': 'D', 'content': '查询用户信息', 'type': 'sync'},
        {'from': 'D', 'to': 'B', 'content': '返回用户数据', 'type': 'return'},
        {'from': 'B', 'to': 'F', 'content': '登录成功响应', 'type': 'return'},
        {'from': 'F', 'to': 'U', 'content': '展示登录结果', 'type': 'return'},
    ]

    output_path = str(output_dir / "demo_sequence.png")
    renderer.render_sequence_diagram(participants, messages, output_path, "登录时序图")
    print(f"    输出: {output_path}")

    # 3. 生成 E-R 图
    print("\n[3] 生成 E-R 图...")
    entities = [
        {
            'name': '用户',
            'attributes': [
                {'name': 'id', 'type': 'bigint PK'},
                {'name': 'username', 'type': 'varchar'},
                {'name': 'password', 'type': 'varchar'},
                {'name': 'email', 'type': 'varchar'},
            ]
        },
        {
            'name': '订单',
            'attributes': [
                {'name': 'id', 'type': 'bigint PK'},
                {'name': 'user_id', 'type': 'bigint FK'},
                {'name': 'total', 'type': 'decimal'},
                {'name': 'status', 'type': 'varchar'},
            ]
        },
        {
            'name': '商品',
            'attributes': [
                {'name': 'id', 'type': 'bigint PK'},
                {'name': 'name', 'type': 'varchar'},
                {'name': 'price', 'type': 'decimal'},
            ]
        },
    ]

    relations = [
        {'from': '用户', 'to': '订单', 'type': '1:N'},
        {'from': '订单', 'to': '商品', 'type': 'N:M'},
    ]

    output_path = str(output_dir / "demo_er.png")
    renderer.render_er_diagram(entities, relations, output_path, "电商系统E-R图")
    print(f"    输出: {output_path}")

    print(f"\n离线渲染完成! 输出目录: {output_dir}")


def demo_hybrid_generate():
    """演示混合生成 - 生成 Mermaid 代码"""
    print("\n" + "="*60)
    print("演示: 混合图表生成 (模板 + LLM 兜底)")
    print("="*60)

    generator = HybridChartGenerator()

    # 1. 生成架构图 Mermaid 代码
    print("\n[1] 生成架构图 Mermaid 代码...")
    description = "Web系统采用前后端分离架构，前端使用Vue.js，后端使用Spring Boot，数据库使用MySQL"
    mermaid = generator.generate("架构图", description, "", "图2-1", "系统架构图")
    print("    生成的 Mermaid 代码:")
    print("-" * 40)
    print(mermaid[:500] + "..." if len(mermaid) > 500 else mermaid)

    # 2. 生成流程图 Mermaid 代码
    print("\n[2] 生成流程图 Mermaid 代码...")
    description = "用户注册流程：输入注册信息 -> 验证信息格式 -> 检查用户名是否已存在 -> 创建用户账号 -> 返回注册结果"
    mermaid = generator.generate("流程图", description, "", "图3-2", "用户注册流程图")
    print("    生成的 Mermaid 代码:")
    print("-" * 40)
    print(mermaid[:500] + "..." if len(mermaid) > 500 else mermaid)

    # 3. 生成 E-R 图 Mermaid 代码
    print("\n[3] 生成 E-R 图 Mermaid 代码...")
    description = "电商系统，包含用户、商品、订单三个核心实体，用户可以下订单购买商品"
    mermaid = generator.generate("E-R图", description, "", "图4-1", "电商系统E-R图")
    print("    生成的 Mermaid 代码:")
    print("-" * 40)
    print(mermaid[:600] + "..." if len(mermaid) > 600 else mermaid)


def demo_theme_change():
    """演示主题切换"""
    print("\n" + "="*60)
    print("演示: 主题切换")
    print("="*60)

    output_dir = scripts_dir / "demo_output" / "themes"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 同一流程图使用不同主题
    steps = [
        {'name': '开始', 'type': 'terminal', 'node_id': 'A'},
        {'name': '处理数据', 'type': 'process', 'node_id': 'B'},
        {'name': '判断结果', 'type': 'decision', 'node_id': 'C'},
        {'name': '结束', 'type': 'terminal', 'node_id': 'D'},
    ]

    themes = ['academic', 'business', 'minimal']

    for theme in themes:
        renderer = OfflineChartRenderer(output_dir=str(output_dir), theme=theme)
        output_path = str(output_dir / f"flowchart_{theme}.png")
        renderer.render_flowchart(steps, output_path, f"流程图 - {theme}主题", "")
        print(f"    [{theme}] {output_path}")

    print(f"\n主题对比图已保存到: {output_dir}")


def main():
    """主函数"""
    print("="*60)
    print("图表生成示例")
    print("="*60)

    print("\n请选择演示内容:")
    print("  1. 离线渲染演示 (生成PNG图片)")
    print("  2. 混合生成演示 (生成Mermaid代码)")
    print("  3. 主题切换演示")
    print("  4. 全部演示")

    try:
        choice = input("\n请输入选项 (1-4): ").strip()
    except EOFError:
        choice = "4"

    if choice == "1":
        demo_offline_render()
    elif choice == "2":
        demo_hybrid_generate()
    elif choice == "3":
        demo_theme_change()
    else:
        demo_offline_render()
        demo_hybrid_generate()
        demo_theme_change()

    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)


if __name__ == "__main__":
    main()