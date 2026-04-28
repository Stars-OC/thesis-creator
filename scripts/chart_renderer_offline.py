# -*- coding: utf-8 -*-
"""
matplotlib 离线图表渲染器 - 纯 Python 渲染图表，无需外部工具

功能：
1. 使用 matplotlib 绑定绘制流程图、E-R图、时序图
2. 完全离线运行，无需 mmdc/playwright
3. 支持中文字体显示
4. 支持样式主题定制

使用方法：
    from chart_renderer_offline import OfflineChartRenderer
    renderer = OfflineChartRenderer()
    renderer.render_flowchart(steps, output_path)
"""

import os
import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Polygon
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

# 导入日志模块
try:
    from logger import get_logger
except ImportError:
    import logging
    def get_logger():
        """get_logger"""
        return logging.getLogger()


class FontConfig:
    """字体配置管理"""

    # 常见中文字体
    CHINESE_FONT_FAMILY = [
        'SimHei',      # 黑体 (Windows)
        'Microsoft YaHei',  # 微软雅黑 (Windows)
        'SimSun',      # 宋体 (Windows)
        'KaiTi',       # 楷体 (Windows)
        'FangSong',    # 仿宋 (Windows)
        'STHeiti',     # 华文黑体 (Mac)
        'STSong',      # 华文宋体 (Mac)
        'PingFang SC', # 苹方 (Mac)
        'Noto Sans CJK SC',  # 思源黑体 (Linux)
        'WenQuanYi Micro Hei',  # 文泉驿微米黑 (Linux)
        'DejaVu Sans', # 备用字体
    ]

    def __init__(self):
        """__init__"""
        self.logger = get_logger()
        self.available_font = None
        self._configure_chinese_font()

    def _configure_chinese_font(self) -> str:
        """配置中文字体"""
        import matplotlib.font_manager as fm

        # 获取系统所有字体
        available_fonts = [f.name for f in fm.fontManager.ttflist]

        # 尝试找到可用的中文字体
        for font_name in self.CHINESE_FONT_FAMILY:
            if font_name in available_fonts:
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
                self.available_font = font_name
                self.logger.info(f"已配置中文字体: {font_name}")
                return font_name

        # 如果没有找到，尝试手动添加字体路径
        self.logger.warning("未找到系统中文字体，尝试加载备用字体")

        # 尝试从常见路径加载
        font_paths = [
            # Windows
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
            'C:/Windows/Fonts/simsun.ttc',
            # Mac
            '/System/Library/Fonts/PingFang.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            # Linux
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    fm.fontManager.addfont(path)
                    prop = fm.FontProperties(fname=path)
                    plt.rcParams['font.sans-serif'] = [prop.get_name()]
                    self.available_font = prop.get_name()
                    self.logger.info(f"已加载字体文件: {path}")
                    return self.available_font
                except Exception as e:
                    self.logger.debug(f"加载字体失败 {path}: {e}")

        self.logger.warning("中文字体配置失败，将使用默认字体")
        return None

    def get_font_properties(self):
        """获取字体属性"""
        import matplotlib.font_manager as fm
        if self.available_font:
            return fm.FontProperties(family=self.available_font)
        return None


class OfflineChartRenderer:
    """matplotlib 离线图表渲染器"""

    # 图表样式主题
    THEMES = {
        'academic': {
            'bg_color': '#FFFFFF',
            'node_color': '#E8F4FD',
            'edge_color': '#333333',
            'text_color': '#000000',
            'arrow_color': '#666666',
            'decision_color': '#FFF3E0',
            'io_color': '#E8F5E9',
            'title_fontsize': 14,
            'node_fontsize': 11,
        },
        'business': {
            'bg_color': '#F5F5F5',
            'node_color': '#2196F3',
            'edge_color': '#1976D2',
            'text_color': '#FFFFFF',
            'arrow_color': '#424242',
            'decision_color': '#FF9800',
            'io_color': '#4CAF50',
            'title_fontsize': 14,
            'node_fontsize': 11,
        },
        'minimal': {
            'bg_color': '#FFFFFF',
            'node_color': '#FFFFFF',
            'edge_color': '#333333',
            'text_color': '#333333',
            'arrow_color': '#333333',
            'decision_color': '#FFFFFF',
            'io_color': '#FFFFFF',
            'title_fontsize': 12,
            'node_fontsize': 10,
        },
    }

    def __init__(self, output_dir: str = "images", theme: str = "academic"):
        """__init__"""
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.theme = self.THEMES.get(theme, self.THEMES['academic'])
        self.font_config = FontConfig()

        # DPI 设置（影响输出质量）
        self.dpi = 150

    def render_flowchart(
        self,
        steps: List[Dict[str, Any]],
        output_path: str,
        title: str = "",
        chart_id: str = ""
    ) -> bool:
        """
        渲染流程图

        Args:
            steps: 步骤列表 [{name, type, node_id}]
            output_path: 输出文件路径
            title: 图表标题
            chart_id: 图表编号

        Returns:
            是否成功
        """
        if not steps:
            self.logger.warning("步骤列表为空")
            return False

        try:
            # 计算布局参数
            node_spacing = 1.6  # 节点垂直间距
            node_heights = {
                'terminal': 0.25,
                'process': 0.30,
                'decision': 0.70,  # 菱形垂直半高
                'io': 0.25,
            }

            total_height = (len(steps) + 2) * node_spacing + 1

            fig, ax = plt.subplots(figsize=(10, total_height * 0.55))
            ax.set_facecolor(self.theme['bg_color'])
            ax.set_xlim(0, 10)
            ax.set_ylim(-1, total_height + 1)

            ax.axis('off')

            if title or chart_id:
                title_text = f"{chart_id} {title}" if chart_id else title
                ax.text(5, total_height + 0.3, title_text,
                        ha='center', va='center',
                        fontsize=self.theme['title_fontsize'],
                        color=self.theme['text_color'],
                        fontproperties=self.font_config.get_font_properties())

            center_x = 5
            positions = []

            start_y = total_height - 0.5
            positions.append((center_x, start_y, 'terminal', '开始'))

            current_y = start_y
            for step in steps:
                current_y -= node_spacing
                step_type = step.get('type', 'process')
                step_name = step.get('name', f'步骤')
                positions.append((center_x, current_y, step_type, step_name))

            end_y = current_y - node_spacing
            positions.append((center_x, end_y, 'terminal', '结束'))

            # 绘制所有节点
            for x, y, node_type, name in positions:
                self._draw_node(ax, x, y, name, node_type,
                               fontproperties=self.font_config.get_font_properties())

            # 绘制连接箭头
            for i in range(len(positions) - 1):
                x1, y1, type1, _ = positions[i]
                x2, y2, type2, _ = positions[i + 1]

                h1 = node_heights.get(type1, 0.3)
                h2 = node_heights.get(type2, 0.3)

                if type1 == 'decision':
                    # 决策节点：菱形底部有两个出口
                    # "是"分支：继续向下
                    arrow_start = (center_x, y1 - h1)  # 菱形底部尖端
                    arrow_end = (center_x, y2 + h2 + 0.05)
                    self._draw_arrow(ax, arrow_start[0], arrow_start[1], arrow_end[0], arrow_end[1], label='是')

                    # "否"分支：向右再向下到结束
                    branch_x = center_x + 2.2
                    # 从菱形右角出发
                    self._draw_arrow(ax, center_x + 0.85, y1, branch_x, y1, label='否')
                    # 向下
                    self._draw_arrow(ax, branch_x, y1 - 0.2, branch_x, end_y + 0.35)
                    # 向左到结束
                    self._draw_arrow(ax, branch_x - 0.1, end_y + 0.35, center_x + 0.7, end_y + 0.35)
                else:
                    # 普通节点
                    arrow_start_y = y1 - h1
                    arrow_end_y = y2 + h2 + 0.05
                    self._draw_arrow(ax, x1, arrow_start_y, x2, arrow_end_y)

            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight',
                       facecolor=self.theme['bg_color'])
            plt.close()

            self.logger.info(f"流程图已保存: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"渲染流程图失败: {e}")
            plt.close()
            return False

    def _draw_node(self, ax, x: float, y: float, text: str, node_type: str,
                   fontproperties=None) -> None:
        """绘制节点"""
        if node_type == 'terminal':
            # 开始/结束节点：圆角矩形（胶囊形）
            width, height = 1.4, 0.5
            patch = FancyBboxPatch((x - width/2, y - height/2),
                                   width, height,
                                   boxstyle="round,pad=0.02,rounding_size=0.25",
                                   facecolor=self.theme['node_color'],
                                   edgecolor=self.theme['edge_color'],
                                   linewidth=1.5)
            ax.add_patch(patch)

        elif node_type == 'decision':
            # 决策节点：菱形
            size = 0.7
            diamond = Polygon([(x, y + size), (x + size * 1.2, y),
                              (x, y - size), (x - size * 1.2, y)],
                             facecolor=self.theme['decision_color'],
                             edgecolor=self.theme['edge_color'],
                             linewidth=1.5)
            ax.add_patch(diamond)

        elif node_type == 'io':
            # 输入输出节点：平行四边形
            width, height = 1.6, 0.5
            offset = 0.25
            parallelogram = Polygon([
                (x - width/2 + offset, y + height/2),
                (x + width/2 + offset, y + height/2),
                (x + width/2 - offset, y - height/2),
                (x - width/2 - offset, y - height/2)
            ], facecolor=self.theme['io_color'],
               edgecolor=self.theme['edge_color'],
               linewidth=1.5)
            ax.add_patch(parallelogram)

        else:  # process
            # 处理节点：矩形
            width, height = 1.8, 0.6
            patch = Rectangle((x - width/2, y - height/2),
                              width, height,
                              facecolor=self.theme['node_color'],
                              edgecolor=self.theme['edge_color'],
                              linewidth=1.5)
            ax.add_patch(patch)

        # 添加文本
        ax.text(x, y, text, ha='center', va='center',
               fontsize=self.theme['node_fontsize'],
               color=self.theme['text_color'],
               fontproperties=fontproperties)

    def _draw_arrow(self, ax, x1: float, y1: float, x2: float, y2: float,
                   label: str = None) -> None:
        """绘制箭头"""
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle='->,head_length=0.3,head_width=0.15',
                                color=self.theme['arrow_color'],
                                linewidth=1.5,
                                mutation_scale=15)
        ax.add_patch(arrow)

        # 添加标签
        if label:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x + 0.1, mid_y + 0.1, label,
                   fontsize=9, color=self.theme['text_color'],
                   fontproperties=self.font_config.get_font_properties())

    def render_sequence_diagram(
        self,
        participants: List[Dict[str, str]],
        messages: List[Dict[str, str]],
        output_path: str,
        title: str = ""
    ) -> bool:
        """
        渲染时序图

        Args:
            participants: 参与者列表 [{id, name}]
            messages: 消息序列 [{from, to, content}]
            output_path: 输出路径
            title: 标题

        Returns:
            是否成功
        """
        if not participants or not messages:
            self.logger.warning("参与者或消息列表为空")
            return False

        try:
            n_participants = len(participants)
            fig, ax = plt.subplots(figsize=(max(12, n_participants * 2), 8))
            ax.set_facecolor(self.theme['bg_color'])

            # 计算参与者位置
            x_positions = np.linspace(1, n_participants * 2 - 1, n_participants)

            # 绘制参与者
            for i, (x, p) in enumerate(zip(x_positions, participants)):
                # 绘制参与者方框
                box = FancyBboxPatch((x - 0.5, len(messages) + 1),
                                     1, 0.5,
                                     boxstyle="round,pad=0.05",
                                     facecolor=self.theme['node_color'],
                                     edgecolor=self.theme['edge_color'])
                ax.add_patch(box)
                ax.text(x, len(messages) + 1.25, p['name'],
                       ha='center', va='center',
                       fontsize=self.theme['node_fontsize'],
                       fontproperties=self.font_config.get_font_properties())

                # 绘制生命线
                ax.plot([x, x], [len(messages) + 0.5, 0.5],
                       '--', color=self.theme['edge_color'], linewidth=1)

            # 绘制消息
            for i, msg in enumerate(messages):
                from_idx = next((idx for idx, p in enumerate(participants)
                                if p['id'] == msg['from'] or p['name'] == msg['from']), 0)
                to_idx = next((idx for idx, p in enumerate(participants)
                              if p['id'] == msg['to'] or p['name'] == msg['to']), 1)

                y_pos = len(messages) - i

                x1, x2 = x_positions[from_idx], x_positions[to_idx]

                # 绘制箭头
                arrow_type = msg.get('type', 'sync')
                if arrow_type == 'return':
                    arrow = FancyArrowPatch((x1, y_pos), (x2, y_pos),
                                           arrowstyle='<-,head_length=0.2',
                                           color=self.theme['arrow_color'],
                                           linestyle='dashed',
                                           linewidth=1)
                else:
                    arrow = FancyArrowPatch((x1, y_pos), (x2, y_pos),
                                           arrowstyle='->,head_length=0.2',
                                           color=self.theme['arrow_color'],
                                           linewidth=1)
                ax.add_patch(arrow)

                # 添加消息文本
                mid_x = (x1 + x2) / 2
                ax.text(mid_x, y_pos + 0.15, msg['content'],
                       ha='center', va='bottom', fontsize=9,
                       fontproperties=self.font_config.get_font_properties())

            ax.set_xlim(0, n_participants * 2)
            ax.set_ylim(0, len(messages) + 2)
            ax.axis('off')

            # 保存
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight',
                       facecolor=self.theme['bg_color'])
            plt.close()

            self.logger.info(f"时序图已保存: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"渲染时序图失败: {e}")
            plt.close()
            return False

    def render_er_diagram(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, str]],
        output_path: str,
        title: str = ""
    ) -> bool:
        """
        渲染 E-R 图

        Args:
            entities: 实体列表 [{name, attributes}]
            relations: 关系列表 [{from, to, type}]
            output_path: 输出路径
            title: 标题

        Returns:
            是否成功
        """
        if not entities:
            self.logger.warning("实体列表为空")
            return False

        try:
            n_entities = len(entities)
            # 计算布局：尝试矩形布局
            cols = min(4, n_entities)
            rows = (n_entities // cols) + 1

            fig, ax = plt.subplots(figsize=(cols * 4, rows * 3))
            ax.set_facecolor(self.theme['bg_color'])

            # 计算实体位置
            positions = {}
            for i, entity in enumerate(entities):
                col = i % cols
                row = i // cols
                x = col * 4 + 2
                y = (rows - row - 1) * 3 + 1.5
                positions[entity['name']] = (x, y)

                # 绘制实体框
                width = 2.5
                n_attrs = len(entity.get('attributes', []))
                height = 0.5 + n_attrs * 0.3

                # 实体名称框
                header = Rectangle((x - width/2, y + height/2 - 0.4),
                                  width, 0.4,
                                  facecolor=self.theme['node_color'],
                                  edgecolor=self.theme['edge_color'],
                                  linewidth=2)
                ax.add_patch(header)
                ax.text(x, y + height/2 - 0.2, entity['name'],
                       ha='center', va='center',
                       fontsize=self.theme['title_fontsize'],
                       fontweight='bold',
                       fontproperties=self.font_config.get_font_properties())

                # 属性框
                if n_attrs > 0:
                    attr_box = Rectangle((x - width/2, y + height/2 - height),
                                        width, height - 0.4,
                                        facecolor='#FFFFFF',
                                        edgecolor=self.theme['edge_color'],
                                        linewidth=1)
                    ax.add_patch(attr_box)

                    for j, attr in enumerate(entity.get('attributes', [])):
                        attr_text = f"{attr['name']} : {attr['type']}"
                        ax.text(x, y + height/2 - 0.5 - j * 0.3, attr_text,
                               ha='center', va='center', fontsize=9,
                               fontproperties=self.font_config.get_font_properties())

            # 绘制关系
            for rel in relations:
                from_pos = positions.get(rel['from'])
                to_pos = positions.get(rel['to'])

                if from_pos and to_pos:
                    self._draw_relation_line(ax, from_pos, to_pos, rel.get('type', ''))

            ax.set_xlim(0, cols * 4)
            ax.set_ylim(0, rows * 3)
            ax.axis('off')

            # 保存
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight',
                       facecolor=self.theme['bg_color'])
            plt.close()

            self.logger.info(f"E-R图已保存: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"渲染E-R图失败: {e}")
            plt.close()
            return False

    def _draw_relation_line(self, ax, from_pos: Tuple, to_pos: Tuple,
                           rel_type: str) -> None:
        """绘制关系连线"""
        x1, y1 = from_pos
        x2, y2 = to_pos

        # 计算连线角度和长度
        angle = np.arctan2(y2 - y1, x2 - x1)
        offset = 1.0  # 从实体边缘开始

        start_x = x1 + offset * np.cos(angle)
        start_y = y1 + offset * np.sin(angle)
        end_x = x2 - offset * np.cos(angle)
        end_y = y2 - offset * np.sin(angle)

        # 绘制连线
        ax.plot([start_x, end_x], [start_y, end_y],
               '-', color=self.theme['edge_color'], linewidth=1.5)

        # 绘制关系类型文本
        mid_x, mid_y = (start_x + end_x) / 2, (start_y + end_y) / 2
        if rel_type:
            ax.text(mid_x, mid_y + 0.2, rel_type,
                   ha='center', va='center', fontsize=9,
                   color=self.theme['text_color'],
                   fontproperties=self.font_config.get_font_properties())

    def set_theme(self, theme_name: str) -> None:
        """设置主题"""
        if theme_name in self.THEMES:
            self.theme = self.THEMES[theme_name]
            self.logger.info(f"已切换主题: {theme_name}")
        else:
            self.logger.warning(f"未知主题: {theme_name}")

    def get_available_themes(self) -> List[str]:
        """获取可用主题列表"""
        return list(self.THEMES.keys())


def main():
    """测试离线渲染器"""
    renderer = OfflineChartRenderer(output_dir="test_output")

    print("可用主题:", renderer.get_available_themes())
    print("当前字体:", renderer.font_config.available_font)

    # 测试流程图渲染
    steps = [
        {'name': '用户输入用户名密码', 'type': 'io', 'node_id': 'B'},
        {'name': '系统验证用户信息', 'type': 'process', 'node_id': 'C'},
        {'name': '判断验证是否通过', 'type': 'decision', 'node_id': 'D'},
        {'name': '返回登录结果', 'type': 'io', 'node_id': 'E'},
    ]

    output_path = str(renderer.output_dir / "test_flowchart.png")
    success = renderer.render_flowchart(steps, output_path, "用户登录流程", "图3-1")
    print(f"流程图渲染: {success}")

    # 测试时序图渲染
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

    output_path = str(renderer.output_dir / "test_sequence.png")
    success = renderer.render_sequence_diagram(participants, messages, output_path)
    print(f"时序图渲染: {success}")

    print(f"\n测试输出目录: {renderer.output_dir}")


if __name__ == "__main__":
    main()
