#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成共振式学习多层框架可视化图表
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def create_framework_chart():
    # 创建图形
    fig, ax = plt.subplots(1, 1, figsize=(16, 20))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # 颜色方案
    colors = {
        'layer0': '#2C3E50',  # 深蓝灰 - 第零层
        'layer1': '#3498DB',  # 蓝色 - 认知层
        'layer2': '#27AE60',  # 绿色 - 交互层
        'layer3': '#E67E22',  # 橙色 - 产出层
        'text_white': '#FFFFFF',
        'text_dark': '#2C3E50',
        'bg_light': '#F8F9FA'
    }
    
    # ========== 第零层：人在回路原则 ==========
    layer0_y = 85
    layer0_height = 12
    
    # 外框
    rect0 = FancyBboxPatch((5, layer0_y), 90, layer0_height,
                            boxstyle="round,pad=0.02,rounding_size=1",
                            facecolor=colors['layer0'],
                            edgecolor='#1A252F',
                            linewidth=3)
    ax.add_patch(rect0)
    
    # 标题
    ax.text(50, layer0_y + 8, '第零层：人在回路原则', fontsize=18, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(50, layer0_y + 8, 'Human-in-the-Loop Principle', fontsize=11,
            ha='center', va='center', color='#BDC3C7', style='italic')
    
    # 说明文字
    ax.text(50, layer0_y + 3.5, '整个框架的根基：人的主体性、判断力与元认知',
            fontsize=12, ha='center', va='center', color='#ECF0F1')
    ax.text(50, layer0_y + 1.5, '不是独立的层次，而是贯穿所有层次的底层约束',
            fontsize=11, ha='center', va='center', color='#BDC3C7')
    
    # ========== 第一层：认知层 ==========
    layer1_y = 58
    layer1_height = 24
    
    # 外框
    rect1 = FancyBboxPatch((5, layer1_y), 90, layer1_height,
                            boxstyle="round,pad=0.02,rounding_size=1",
                            facecolor='#EBF5FB',
                            edgecolor=colors['layer1'],
                            linewidth=3)
    ax.add_patch(rect1)
    
    # 层标题
    ax.text(50, layer1_y + 20, '第一层：认知层', fontsize=16, fontweight='bold',
            ha='center', va='center', color=colors['layer1'])
    ax.text(50, layer1_y + 20, 'Cognitive Layer', fontsize=10,
            ha='center', va='center', color='#5DADE2', style='italic')
    
    # 规划性模块
    planning_rect = FancyBboxPatch((10, layer1_y + 2), 37, 14,
                                    boxstyle="round,pad=0.02,rounding_size=0.5",
                                    facecolor=colors['layer1'],
                                    edgecolor='#2980B9',
                                    linewidth=2)
    ax.add_patch(planning_rect)
    
    ax.text(28.5, layer1_y + 13, '规划性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(28.5, layer1_y + 13, 'Planning', fontsize=9,
            ha='center', va='center', color='#AED6F1', style='italic')
    
    # 规划性要点
    planning_points = ['· 问题分解', '· 优先级判断', '· 深度控制', '· 路径修正']
    for i, point in enumerate(planning_points):
        ax.text(28.5, layer1_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # 反思性模块
    reflection_rect = FancyBboxPatch((53, layer1_y + 2), 37, 14,
                                      boxstyle="round,pad=0.02,rounding_size=0.5",
                                      facecolor=colors['layer1'],
                                      edgecolor='#2980B9',
                                      linewidth=2)
    ax.add_patch(reflection_rect)
    
    ax.text(71.5, layer1_y + 13, '反思性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(71.5, layer1_y + 13, 'Reflection', fontsize=9,
            ha='center', va='center', color='#AED6F1', style='italic')
    
    # 反思性要点
    reflection_points = ['· 自我监控', '· 独立验证', '· 认知差距觉察', '· 依赖度评估']
    for i, point in enumerate(reflection_points):
        ax.text(71.5, layer1_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # ========== 第二层：交互层 ==========
    layer2_y = 31
    layer2_height = 24
    
    # 外框
    rect2 = FancyBboxPatch((5, layer2_y), 90, layer2_height,
                            boxstyle="round,pad=0.02,rounding_size=1",
                            facecolor='#EAFAF1',
                            edgecolor=colors['layer2'],
                            linewidth=3)
    ax.add_patch(rect2)
    
    # 层标题
    ax.text(50, layer2_y + 20, '第二层：交互层', fontsize=16, fontweight='bold',
            ha='center', va='center', color=colors['layer2'])
    ax.text(50, layer2_y + 20, 'Interaction Layer', fontsize=10,
            ha='center', va='center', color='#58D68D', style='italic')
    
    # 持续性模块
    continuity_rect = FancyBboxPatch((10, layer2_y + 2), 37, 14,
                                      boxstyle="round,pad=0.02,rounding_size=0.5",
                                      facecolor=colors['layer2'],
                                      edgecolor='#1E8449',
                                      linewidth=2)
    ax.add_patch(continuity_rect)
    
    ax.text(28.5, layer2_y + 13, '持续性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(28.5, layer2_y + 13, 'Continuity', fontsize=9,
            ha='center', va='center', color='#ABEBC6', style='italic')
    
    # 持续性要点
    continuity_points = ['· 上下文连续', '· 问题深化', '· 心智模型迭代', '· 学习时长管理']
    for i, point in enumerate(continuity_points):
        ax.text(28.5, layer2_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # 协流性模块
    coflow_rect = FancyBboxPatch((53, layer2_y + 2), 37, 14,
                                  boxstyle="round,pad=0.02,rounding_size=0.5",
                                  facecolor=colors['layer2'],
                                  edgecolor='#1E8449',
                                  linewidth=2)
    ax.add_patch(coflow_rect)
    
    ax.text(71.5, layer2_y + 13, '协流性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(71.5, layer2_y + 13, 'Co-flow', fontsize=9,
            ha='center', va='center', color='#ABEBC6', style='italic')
    
    # 协流性要点
    coflow_points = ['· 思考模式', '· 工具模式', '· 对话模式', '· 模态动态切换']
    for i, point in enumerate(coflow_points):
        ax.text(71.5, layer2_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # ========== 第三层：产出层 ==========
    layer3_y = 4
    layer3_height = 24
    
    # 外框
    rect3 = FancyBboxPatch((5, layer3_y), 90, layer3_height,
                            boxstyle="round,pad=0.02,rounding_size=1",
                            facecolor='#FEF5E7',
                            edgecolor=colors['layer3'],
                            linewidth=3)
    ax.add_patch(rect3)
    
    # 层标题
    ax.text(50, layer3_y + 20, '第三层：产出层', fontsize=16, fontweight='bold',
            ha='center', va='center', color=colors['layer3'])
    ax.text(50, layer3_y + 20, 'Output Layer', fontsize=10,
            ha='center', va='center', color='#F5B041', style='italic')
    
    # 工具性模块
    instrument_rect = FancyBboxPatch((10, layer3_y + 2), 37, 14,
                                      boxstyle="round,pad=0.02,rounding_size=0.5",
                                      facecolor=colors['layer3'],
                                      edgecolor='#D35400',
                                      linewidth=2)
    ax.add_patch(instrument_rect)
    
    ax.text(28.5, layer3_y + 13, '工具性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(28.5, layer3_y + 13, 'Instrumentality', fontsize=9,
            ha='center', va='center', color='#FAD7A0', style='italic')
    
    # 工具性要点
    instrument_points = ['· 认知脚手架', '· 实时反馈', '· 多模态输出', '· 自适应难度']
    for i, point in enumerate(instrument_points):
        ax.text(28.5, layer3_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # 实践性模块
    practice_rect = FancyBboxPatch((53, layer3_y + 2), 37, 14,
                                    boxstyle="round,pad=0.02,rounding_size=0.5",
                                    facecolor=colors['layer3'],
                                    edgecolor='#D35400',
                                    linewidth=2)
    ax.add_patch(practice_rect)
    
    ax.text(71.5, layer3_y + 13, '实践性', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['text_white'])
    ax.text(71.5, layer3_y + 13, 'Practicality', fontsize=9,
            ha='center', va='center', color='#FAD7A0', style='italic')
    
    # 实践性要点
    practice_points = ['· 真实问题驱动', '· 学用一体', '· 成果可验证', '· 知识可迁移']
    for i, point in enumerate(practice_points):
        ax.text(71.5, layer3_y + 9.5 - i*2.2, point, fontsize=10,
                ha='center', va='center', color='#ECF0F1')
    
    # ========== 添加连接箭头 ==========
    # 从第零层到第一层
    ax.annotate('', xy=(50, layer1_y + 24), xytext=(50, layer0_y),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=2))
    
    # 从第一层到第二层
    ax.annotate('', xy=(50, layer2_y + 24), xytext=(50, layer1_y),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=2))
    
    # 从第二层到第三层
    ax.annotate('', xy=(50, layer3_y + 24), xytext=(50, layer2_y),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=2))
    
    # ========== 添加标题 ==========
    ax.text(50, 98, '共振式学习多层框架', fontsize=24, fontweight='bold',
            ha='center', va='center', color=colors['layer0'])
    ax.text(50, 95, 'Resonant Learning Multi-layer Framework', fontsize=14,
            ha='center', va='center', color='#7F8C8D', style='italic')
    
    # 保存图片
    plt.tight_layout()
    plt.savefig('c:\\Users\\MECHREVO\\Desktop\\XfaCourseSchedulingSystem\\docs\\resonant_learning_framework.png',
                dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.savefig('c:\\Users\\MECHREVO\\Desktop\\XfaCourseSchedulingSystem\\docs\\resonant_learning_framework.svg',
                bbox_inches='tight', facecolor='white', edgecolor='none')
    
    print("图表已生成：")
    print("- resonant_learning_framework.png (高分辨率PNG)")
    print("- resonant_learning_framework.svg (矢量SVG)")
    
    return fig, ax

if __name__ == '__main__':
    create_framework_chart()
