"""
排课报告生成器

生成可读的排课结果报告，支持多种格式输出。
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from collections import defaultdict
from enum import Enum
from datetime import datetime
import json

if TYPE_CHECKING:
    from ..state import ScheduleState, ScheduleRecord
    from ..data.models import ScheduleData
    from .scorer import ScoreReport


class ReportFormat(Enum):
    """报告格式"""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class TimetableCell:
    """课表单元格"""
    subject_name: str
    teacher_name: str
    class_name: str
    task_id: int


class ScheduleReporter:
    """
    排课报告生成器
    
    生成排课结果的可视化报告，包括：
    - 班级课表
    - 教师课表
    - 统计摘要
    - 问题诊断
    
    Usage:
        reporter = ScheduleReporter(state, data)
        
        # 生成文本报告
        text_report = reporter.generate_report(ReportFormat.TEXT)
        
        # 生成某班级的课表
        timetable = reporter.get_class_timetable(class_id=1)
    """
    
    DAYS = ['', '周一', '周二', '周三', '周四', '周五']
    MAX_PERIOD = 9
    
    def __init__(
        self,
        state: 'ScheduleState',
        data: 'ScheduleData',
        score_report: 'ScoreReport' = None
    ):
        """
        初始化报告生成器
        
        Args:
            state: 课表状态
            data: 排课数据
            score_report: 评分报告（可选）
        """
        self.state = state
        self.data = data
        self.score_report = score_report
    
    def generate_report(self, format: ReportFormat = ReportFormat.TEXT) -> str:
        """
        生成完整报告
        
        Args:
            format: 报告格式
        
        Returns:
            str: 报告内容
        """
        if format == ReportFormat.TEXT:
            return self._generate_text_report()
        elif format == ReportFormat.JSON:
            return self._generate_json_report()
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report()
        elif format == ReportFormat.HTML:
            return self._generate_html_report()
        else:
            return self._generate_text_report()
    
    def get_class_timetable(self, class_id: int) -> Dict[int, Dict[int, Optional[TimetableCell]]]:
        """
        获取班级课表
        
        Args:
            class_id: 班级ID
        
        Returns:
            Dict[day][period] -> TimetableCell
        """
        timetable = {
            day: {period: None for period in range(1, self.MAX_PERIOD + 1)}
            for day in range(1, 6)
        }
        
        for record in self.state.schedule_records:
            if record.class_id == class_id:
                cell = TimetableCell(
                    subject_name=record.subject_name,
                    teacher_name=record.teacher_name,
                    class_name=record.class_name,
                    task_id=record.task_id
                )
                timetable[record.day][record.period] = cell
        
        return timetable
    
    def get_teacher_timetable(self, teacher_id: int) -> Dict[int, Dict[int, List[TimetableCell]]]:
        """
        获取教师课表
        
        教师可能同时教多个班，所以每个时段可能有多个单元格。
        
        Args:
            teacher_id: 教师ID
        
        Returns:
            Dict[day][period] -> List[TimetableCell]
        """
        timetable = {
            day: {period: [] for period in range(1, self.MAX_PERIOD + 1)}
            for day in range(1, 6)
        }
        
        for record in self.state.schedule_records:
            if record.teacher_id == teacher_id:
                cell = TimetableCell(
                    subject_name=record.subject_name,
                    teacher_name=record.teacher_name,
                    class_name=record.class_name,
                    task_id=record.task_id
                )
                timetable[record.day][record.period].append(cell)
        
        return timetable
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计数据
        """
        summary = self.state.get_schedule_summary()
        
        # 按班级统计
        class_stats = defaultdict(lambda: {"periods": 0, "teachers": set()})
        for record in self.state.schedule_records:
            class_stats[record.class_id]["periods"] += 1
            class_stats[record.class_id]["teachers"].add(record.teacher_id)
        
        # 按教师统计
        teacher_stats = defaultdict(lambda: {"periods": 0, "classes": set()})
        for record in self.state.schedule_records:
            teacher_stats[record.teacher_id]["periods"] += 1
            teacher_stats[record.teacher_id]["classes"].add(record.class_id)
        
        return {
            "summary": summary,
            "class_stats": {
                cid: {
                    "periods": stats["periods"],
                    "teacher_count": len(stats["teachers"])
                }
                for cid, stats in class_stats.items()
            },
            "teacher_stats": {
                tid: {
                    "periods": stats["periods"],
                    "class_count": len(stats["classes"])
                }
                for tid, stats in teacher_stats.items()
            }
        }
    
    def _generate_text_report(self) -> str:
        """生成文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("排课结果报告")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # 统计摘要
        stats = self.get_statistics()
        summary = stats["summary"]
        
        lines.append("【统计摘要】")
        lines.append(f"  总任务数: {summary['total_tasks']}")
        lines.append(f"  成功排课: {summary['scheduled_tasks']}")
        lines.append(f"  排课失败: {summary['failed_tasks']}")
        lines.append(f"  总课时数: {summary['records_count']}")
        lines.append(f"  教师空档: {summary['teacher_gaps']}")
        lines.append("")
        
        # 评分
        if self.score_report:
            lines.append("【评分报告】")
            lines.append(f"  总分: {self.score_report.total_score:.1f} ({self.score_report.level.value})")
            lines.append("")
            for metric in self.score_report.metrics:
                lines.append(f"  {metric.name}: {metric.score:.1f} (权重 {metric.weight:.0%})")
            lines.append("")
            
            if self.score_report.issues:
                lines.append("【发现问题】")
                for issue in self.score_report.issues:
                    lines.append(f"  - {issue}")
                lines.append("")
            
            if self.score_report.suggestions:
                lines.append("【改进建议】")
                for suggestion in self.score_report.suggestions:
                    lines.append(f"  - {suggestion}")
                lines.append("")
        
        # 班级课表示例
        lines.append("【班级课表示例】")
        if self.data.classes:
            first_class = self.data.classes[0]
            timetable = self.get_class_timetable(first_class.id)
            lines.append(f"  班级: {first_class.name}")
            lines.append("")
            lines.append(self._format_timetable_text(timetable))
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self) -> str:
        """生成Markdown格式报告"""
        lines = []
        lines.append("# 排课结果报告")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 统计摘要
        stats = self.get_statistics()
        summary = stats["summary"]
        
        lines.append("## 统计摘要")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总任务数 | {summary['total_tasks']} |")
        lines.append(f"| 成功排课 | {summary['scheduled_tasks']} |")
        lines.append(f"| 排课失败 | {summary['failed_tasks']} |")
        lines.append(f"| 总课时数 | {summary['records_count']} |")
        lines.append(f"| 教师空档 | {summary['teacher_gaps']} |")
        lines.append("")
        
        # 评分
        if self.score_report:
            lines.append("## 评分报告")
            lines.append("")
            lines.append(f"**总分: {self.score_report.total_score:.1f}** ({self.score_report.level.value})")
            lines.append("")
            lines.append("| 指标 | 得分 | 权重 | 加权分 |")
            lines.append("|------|------|------|--------|")
            for metric in self.score_report.metrics:
                lines.append(f"| {metric.name} | {metric.score:.1f} | {metric.weight:.0%} | {metric.weighted_score:.1f} |")
            lines.append("")
            
            if self.score_report.issues:
                lines.append("### 发现问题")
                lines.append("")
                for issue in self.score_report.issues:
                    lines.append(f"- {issue}")
                lines.append("")
            
            if self.score_report.suggestions:
                lines.append("### 改进建议")
                lines.append("")
                for suggestion in self.score_report.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json_report(self) -> str:
        """生成JSON格式报告"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "statistics": self.get_statistics(),
            "score": self.score_report.to_dict() if self.score_report else None,
            "records_count": len(self.state.schedule_records)
        }
        return json.dumps(report_data, ensure_ascii=False, indent=2)
    
    def _generate_html_report(self) -> str:
        """生成HTML格式报告"""
        # 简单的HTML报告
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>排课结果报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .score-excellent { color: #28a745; }
        .score-good { color: #17a2b8; }
        .score-fair { color: #ffc107; }
        .score-poor { color: #dc3545; }
    </style>
</head>
<body>
"""
        html += f"<h1>排课结果报告</h1>"
        html += f"<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        
        # 统计
        stats = self.get_statistics()
        summary = stats["summary"]
        html += "<h2>统计摘要</h2>"
        html += "<table>"
        html += "<tr><th>指标</th><th>数值</th></tr>"
        html += f"<tr><td>总任务数</td><td>{summary['total_tasks']}</td></tr>"
        html += f"<tr><td>成功排课</td><td>{summary['scheduled_tasks']}</td></tr>"
        html += f"<tr><td>排课失败</td><td>{summary['failed_tasks']}</td></tr>"
        html += f"<tr><td>总课时数</td><td>{summary['records_count']}</td></tr>"
        html += "</table>"
        
        # 评分
        if self.score_report:
            level_class = f"score-{self.score_report.level.value}"
            html += "<h2>评分报告</h2>"
            html += f"<p class='{level_class}'><strong>总分: {self.score_report.total_score:.1f}</strong></p>"
            html += "<table>"
            html += "<tr><th>指标</th><th>得分</th><th>权重</th></tr>"
            for metric in self.score_report.metrics:
                html += f"<tr><td>{metric.name}</td><td>{metric.score:.1f}</td><td>{metric.weight:.0%}</td></tr>"
            html += "</table>"
        
        html += "</body></html>"
        return html
    
    def _format_timetable_text(self, timetable: Dict[int, Dict[int, Optional[TimetableCell]]]) -> str:
        """格式化课表为文本"""
        lines = []
        
        # 表头
        header = "      " + "  ".join(f"{self.DAYS[d]:^8}" for d in range(1, 6))
        lines.append(header)
        lines.append("-" * len(header))
        
        # 每节课
        for period in range(1, self.MAX_PERIOD + 1):
            row = f"第{period}节 "
            for day in range(1, 6):
                cell = timetable[day][period]
                if cell:
                    content = f"{cell.subject_name[:4]:^8}"
                else:
                    content = f"{'':^8}"
                row += "  " + content
            lines.append(row)
            
            # 午休分隔
            if period == 4:
                lines.append("-" * len(header) + " (午休)")
        
        return "\n".join(lines)
