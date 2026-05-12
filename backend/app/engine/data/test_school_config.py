"""
学校排课测试数据配置

基于《学校的要求.md》文档生成的真实测试数据。
包含完整的班级、教师、科目、场地、分层课配置。

使用方法：
    from app.engine.data.test_school_config import generate_real_school_data
    data = generate_real_school_data()
"""

from typing import List, Dict
from dataclasses import dataclass, field
from .models import Teacher, Class, Subject, Task, LayerGroup, Venue, ScheduleData


# ==============================================================================
# 一、班级配置
# ==============================================================================

# 小学部班级
PRIMARY_CLASSES = [
    # PK（学前班）
    {"name": "PK", "type": "I", "grade": "PK", "class_no": 1},
    
    # KG（幼儿园大班）
    {"name": "KG", "type": "I", "grade": "KG", "class_no": 1},
    
    # G1（一年级）
    {"name": "I1-1", "type": "I", "grade": "G1", "class_no": 1},
    {"name": "I1-2", "type": "I", "grade": "G1", "class_no": 2},
    {"name": "N1-1", "type": "N", "grade": "G1", "class_no": 3},
    {"name": "N1-2", "type": "N", "grade": "G1", "class_no": 4},
    
    # G2（二年级）
    {"name": "I2-1", "type": "I", "grade": "G2", "class_no": 1},
    {"name": "I2-2", "type": "I", "grade": "G2", "class_no": 2},
    {"name": "N2-1", "type": "N", "grade": "G2", "class_no": 3},
    {"name": "N2-2", "type": "N", "grade": "G2", "class_no": 4},
    
    # G3（三年级）
    {"name": "I3-1", "type": "I", "grade": "G3", "class_no": 1},
    {"name": "I3-2", "type": "I", "grade": "G3", "class_no": 2},
    {"name": "N3-1", "type": "N", "grade": "G3", "class_no": 3},
    {"name": "N3-2", "type": "N", "grade": "G3", "class_no": 4},
    
    # G4（四年级）
    {"name": "I4-1", "type": "I", "grade": "G4", "class_no": 1},
    {"name": "I4-2", "type": "I", "grade": "G4", "class_no": 2},
    {"name": "N4-1", "type": "N", "grade": "G4", "class_no": 3},
    
    # G5（五年级）
    {"name": "I5-1", "type": "I", "grade": "G5", "class_no": 1},
    {"name": "I5-2", "type": "I", "grade": "G5", "class_no": 2},
]

# 中学部班级
SECONDARY_CLASSES = [
    # G6（六年级）
    {"name": "I6-1", "type": "I", "grade": "G6", "class_no": 1},
    {"name": "I6-2", "type": "I", "grade": "G6", "class_no": 2},
    
    # G7（七年级）
    {"name": "I7-1", "type": "I", "grade": "G7", "class_no": 1},
    {"name": "I7-2", "type": "I", "grade": "G7", "class_no": 2},
    
    # G8（八年级）
    {"name": "I8-1", "type": "I", "grade": "G8", "class_no": 1},
    {"name": "I8-2", "type": "I", "grade": "G8", "class_no": 2},
    
    # G9（九年级）
    {"name": "I9-1", "type": "I", "grade": "G9", "class_no": 1},
    {"name": "I9-2", "type": "I", "grade": "G9", "class_no": 2},
    {"name": "N9-1", "type": "N", "grade": "G9", "class_no": 3},
    
    # G10（十年级）
    {"name": "I10-1", "type": "I", "grade": "G10", "class_no": 1},
    {"name": "I10-2", "type": "I", "grade": "G10", "class_no": 2},
    
    # G11（十一年级）
    {"name": "I11-1", "type": "I", "grade": "G11", "class_no": 1},
    {"name": "I11-2", "type": "I", "grade": "G11", "class_no": 2},
]


# ==============================================================================
# 二、教师配置
# ==============================================================================

# 小学部中教
PRIMARY_CN_TEACHERS = [
    # 语文教师
    {"name": "郭金莉", "subjects": ["语文"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "黄丽娜", "subjects": ["语文", "数学"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "赵立娜", "subjects": ["语文"], "max_hours": 24, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "李春香", "subjects": ["语文"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "李维雅", "subjects": ["语文"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "丛玉梅", "subjects": ["语文"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "杨文静", "subjects": ["语文", "书法"], "max_hours": 20, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "邱野", "subjects": ["语文"], "max_hours": 18},
    {"name": "张秀芳", "subjects": ["语文", "书法"], "max_hours": 24},
    {"name": "孙倩倩", "subjects": ["语文", "道德与法治", "书法"], "max_hours": 15},
    
    # 数学教师
    {"name": "温惠", "subjects": ["数学"], "max_hours": 22},
    {"name": "张玉", "subjects": ["数学"], "max_hours": 22},
    {"name": "王丽华", "subjects": ["数学"], "max_hours": 22},
    
    # 英语教师（中教）
    {"name": "甄臻", "subjects": ["英语"], "max_hours": 22},
    {"name": "王莹莹", "subjects": ["英语"], "max_hours": 15},
    {"name": "王辰辰", "subjects": ["英语", "道德与法治"], "max_hours": 15},
    {"name": "王新月", "subjects": ["英语"], "max_hours": 15},
    {"name": "张祥", "subjects": ["英语"], "max_hours": 22},
    
    # 艺术教师
    {"name": "陈岚", "subjects": ["音乐", "舞蹈"], "max_hours": 20},
    {"name": "刘美术", "subjects": ["美术"], "max_hours": 20},
    {"name": "李钢琴", "subjects": ["钢琴", "声乐"], "max_hours": 18},
    
    # 体育教师
    {"name": "运齐", "subjects": ["体育", "轮滑"], "max_hours": 22},
    {"name": "王体育", "subjects": ["体育", "游泳"], "max_hours": 22},
]

# 小学部外教
PRIMARY_EN_TEACHERS = [
    {"name": "Bing", "subjects": ["英语", "IEYC"], "max_hours": 18},
    {"name": "Josh B", "subjects": ["英语", "IEYC"], "max_hours": 18},
    {"name": "Andrew", "subjects": ["英语", "科学", "图书馆", "IPC"], "max_hours": 22},
    {"name": "Michael", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 22},
    {"name": "Francois", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 22},
    {"name": "Josh I", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 22},
    {"name": "Luke", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 20},
    {"name": "Sorcha", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 20},
    {"name": "Dion", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 20},
    {"name": "Dan", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 20},
    {"name": "Neil", "subjects": ["英语", "数学", "图书馆", "IPC"], "max_hours": 20},
]

# 中学部中教
SECONDARY_CN_TEACHERS = [
    # 语文教师
    {"name": "张语文", "subjects": ["语文"], "max_hours": 22, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "李语文", "subjects": ["语文"], "max_hours": 22, "tags": ["HOMEROOM_TEACHER"]},
    {"name": "王语文", "subjects": ["语文"], "max_hours": 20},
    
    # 数学教师
    {"name": "马昕光", "subjects": ["数学"], "max_hours": 26},
    {"name": "张红娟", "subjects": ["数学"], "max_hours": 26},
    {"name": "刘泽宇", "subjects": ["数学"], "max_hours": 26},
    {"name": "赵数学", "subjects": ["数学"], "max_hours": 24},
    
    # 英语教师（中教）
    {"name": "周英语", "subjects": ["英语"], "max_hours": 20},
    {"name": "吴英语", "subjects": ["英语"], "max_hours": 20},
    
    # 物理教师
    {"name": "张万达", "subjects": ["物理"], "max_hours": 20},
    {"name": "孙国忠", "subjects": ["物理"], "max_hours": 15},
    
    # 化学教师
    {"name": "秦旭华", "subjects": ["化学"], "max_hours": 18},
    {"name": "王化学", "subjects": ["化学"], "max_hours": 18},
    
    # 历史教师
    {"name": "崔朝晖", "subjects": ["历史"], "max_hours": 16},
    
    # 信息技术教师
    {"name": "韩雪", "subjects": ["信息技术"], "max_hours": 15},
    
    # 艺术教师
    {"name": "中音乐", "subjects": ["音乐", "声乐"], "max_hours": 18},
    {"name": "中美术", "subjects": ["美术"], "max_hours": 18},
    {"name": "中舞蹈", "subjects": ["舞蹈"], "max_hours": 18},
    {"name": "中设计", "subjects": ["设计"], "max_hours": 16},
]

# 中学部外教
SECONDARY_EN_TEACHERS = [
    {"name": "Stan", "subjects": ["体育"], "max_hours": 22},
    {"name": "Aleks", "subjects": ["体育"], "max_hours": 24},
    {"name": "Cass", "subjects": ["生物", "科学"], "max_hours": 20},
    {"name": "Tom", "subjects": ["英语", "历史"], "max_hours": 20},
    {"name": "Sarah", "subjects": ["英语", "科学"], "max_hours": 20},
    {"name": "外美术", "subjects": ["美术"], "max_hours": 18},
    {"name": "外数学", "subjects": ["数学"], "max_hours": 20},
]


# ==============================================================================
# 三、科目配置
# ==============================================================================

SUBJECTS = [
    # 文化课
    {"code": "CHINESE", "name": "语文", "category": "文化课", "is_main": True, "color": "#ef4444"},
    {"code": "MATH_CN", "name": "数学", "category": "文化课", "is_main": True, "color": "#3b82f6"},
    {"code": "MATH_EN", "name": "数学(外)", "category": "文化课", "is_main": True, "color": "#2563eb"},
    {"code": "ENGLISH_CN", "name": "英语", "category": "文化课", "is_main": True, "color": "#f59e0b"},
    {"code": "ENGLISH_EN", "name": "英语(外)", "category": "文化课", "is_main": True, "color": "#d97706"},
    
    # 科学类
    {"code": "SCIENCE", "name": "科学", "category": "科学", "is_main": False, "color": "#10b981"},
    {"code": "IPC", "name": "IPC", "category": "科学", "is_main": False, "color": "#06b6d4"},
    {"code": "IEYC", "name": "IEYC", "category": "科学", "is_main": False, "color": "#0ea5e9"},
    {"code": "PHYSICS", "name": "物理", "category": "科学", "is_main": False, "color": "#6366f1"},
    {"code": "CHEMISTRY", "name": "化学", "category": "科学", "is_main": False, "color": "#8b5cf6"},
    {"code": "BIOLOGY", "name": "生物", "category": "科学", "is_main": False, "color": "#a855f7"},
    
    # 人文类
    {"code": "HISTORY", "name": "历史", "category": "人文", "is_main": False, "color": "#ec4899"},
    {"code": "MORAL", "name": "道德与法治", "category": "人文", "is_main": False, "color": "#14b8a6"},
    {"code": "CALLIGRAPHY", "name": "书法", "category": "人文", "is_main": False, "color": "#64748b"},
    
    # 艺术类
    {"code": "ART", "name": "美术", "category": "艺术", "is_main": False, "color": "#f472b6", "venue": "美术教室"},
    {"code": "MUSIC", "name": "音乐", "category": "艺术", "is_main": False, "color": "#c084fc", "venue": "音乐教室"},
    {"code": "VOCAL", "name": "声乐", "category": "艺术", "is_main": False, "color": "#a78bfa", "venue": "音乐教室"},
    {"code": "PIANO", "name": "钢琴", "category": "艺术", "is_main": False, "color": "#818cf8", "venue": "钢琴中心"},
    {"code": "DANCE", "name": "舞蹈", "category": "艺术", "is_main": False, "color": "#fb7185", "venue": "舞蹈教室"},
    {"code": "DESIGN", "name": "设计", "category": "艺术", "is_main": False, "color": "#f97316"},
    
    # 体育类
    {"code": "PE", "name": "体育", "category": "体育", "is_main": False, "color": "#22c55e", "venue": "体育馆"},
    {"code": "SWIMMING", "name": "游泳", "category": "体育", "is_main": False, "color": "#06b6d4", "venue": "游泳池"},
    {"code": "SKATING", "name": "轮滑", "category": "体育", "is_main": False, "color": "#84cc16", "venue": "轮滑场"},
    {"code": "GOLF", "name": "高尔夫", "category": "体育", "is_main": False, "color": "#65a30d", "venue": "高尔夫场"},
    
    # 其他
    {"code": "IT", "name": "信息技术", "category": "技术", "is_main": False, "color": "#0891b2", "venue": "计算机教室"},
    {"code": "LIBRARY", "name": "图书馆", "category": "综合", "is_main": False, "color": "#84cc16", "venue": "图书馆"},
    {"code": "ASSEMBLY", "name": "班会", "category": "综合", "is_main": False, "color": "#a1a1aa"},
]


# ==============================================================================
# 四、场地配置
# ==============================================================================

VENUES = [
    # 体育场地
    {"name": "体育馆", "capacity": 4, "subjects": ["体育"]},  # 同时最多4个班
    {"name": "游泳池", "capacity": 2, "subjects": ["游泳"]},
    {"name": "轮滑场", "capacity": 2, "subjects": ["轮滑"]},
    {"name": "高尔夫场", "capacity": 1, "subjects": ["高尔夫"]},
    
    # 艺术教室
    {"name": "美术教室1", "capacity": 1, "subjects": ["美术"]},
    {"name": "美术教室2", "capacity": 1, "subjects": ["美术"]},  # 总共同时2个班
    {"name": "音乐教室", "capacity": 1, "subjects": ["音乐", "声乐"]},  # 同时1个班
    {"name": "钢琴中心", "capacity": 1, "subjects": ["钢琴"]},  # 同时1个班
    {"name": "舞蹈教室", "capacity": 2, "subjects": ["舞蹈"]},
    
    # 其他专用教室
    {"name": "科学实验室1", "capacity": 1, "subjects": ["科学", "物理", "化学", "生物"]},
    {"name": "科学实验室2", "capacity": 1, "subjects": ["科学", "物理", "化学", "生物"]},
    {"name": "计算机教室", "capacity": 2, "subjects": ["信息技术"]},
    {"name": "图书馆", "capacity": 2, "subjects": ["图书馆"]},
]


# ==============================================================================
# 五、各年级课时配置
# ==============================================================================

# 小学部课时配置
PRIMARY_GRADE_HOURS = {
    "PK": {
        "语文": 3, "IEYC": 4, "美术": 2, "钢琴": 1, 
        "音乐": 1, "体育": 4, "班会": 1
    },  # 共16节，外教课由IEYC覆盖
    
    "KG": {
        "语文": 6, "数学": 5, "英语(外)": 12, "IEYC": 3,
        "体育": 4, "轮滑": 1, "班会": 1
    },  # 共32节
    
    "G1": {
        "语文": 9, "数学": 7, "数学(外)": 1, "英语(外)": 8,
        "科学": 2, "IPC": 2, "体育": 4, "轮滑": 1,
        "音乐": 2, "美术": 2, "图书馆": 1, "班会": 1, "游泳": 1
    },  # 共41节（I班），N班略有不同
    
    "G2": {
        "语文": 9, "数学": 7, "数学(外)": 1, "英语(外)": 8,
        "科学": 2, "IPC": 2, "体育": 4, "轮滑": 1,
        "音乐": 2, "美术": 2, "图书馆": 1, "班会": 1, "游泳": 1
    },
    
    "G3": {
        "语文": 8, "数学": 6, "数学(外)": 2, "英语(外)": 8,
        "英语": 2, "科学": 3, "IPC": 2, "体育": 4,
        "音乐": 2, "美术": 2, "图书馆": 1, "班会": 1, "高尔夫": 1
    },
    
    "G4": {
        "语文": 8, "数学": 6, "数学(外)": 2, "英语(外)": 8,
        "英语": 2, "科学": 3, "IPC": 2, "体育": 4,
        "音乐": 2, "美术": 2, "图书馆": 1, "班会": 1, "高尔夫": 1
    },
    
    "G5": {
        "语文": 7, "数学": 6, "数学(外)": 2, "英语(外)": 8,
        "英语": 2, "科学": 4, "IPC": 2, "体育": 4,
        "音乐": 2, "美术": 2, "图书馆": 1, "班会": 1
    },
}

# 中学部课时配置
SECONDARY_GRADE_HOURS = {
    "G6": {
        "语文": 6, "数学": 6, "数学(外)": 3, "英语(外)": 9,
        "英语": 2, "科学": 3, "历史": 2, "美术": 2,
        "音乐": 2, "舞蹈": 2, "体育": 5, "班会": 1
    },  # 共44节（标准班）
    
    "G7": {
        "语文": 6, "数学": 6, "数学(外)": 3, "英语(外)": 9,
        "英语": 2, "生物": 2, "物理": 1, "历史": 2,
        "信息技术": 1, "设计": 2, "美术": 2, "音乐": 2,
        "舞蹈": 2, "体育": 5, "班会": 1
    },
    
    "G8": {
        "语文": 6, "数学": 6, "数学(外)": 3, "英语(外)": 9,
        "英语": 2, "生物": 2, "物理": 2, "化学": 2,
        "历史": 2, "美术": 2, "音乐": 2, "舞蹈": 2,
        "体育": 5, "班会": 1
    },
    
    "G9": {
        "语文": 5, "数学": 8, "英语(外)": 4, "生物": 4,
        "物理": 4, "化学": 4, "体育": 3, "班会": 1
    },
    
    "G10": {
        "语文": 5, "数学": 8, "英语(外)": 4, "生物": 4,
        "物理": 4, "化学": 4, "体育": 3, "班会": 1
    },
    
    "G11": {
        "语文": 4, "数学": 8, "英语(外)": 4, "生物": 4,
        "物理": 4, "化学": 4, "体育": 3, "班会": 1
    },
}


# ==============================================================================
# 六、分层课配置
# ==============================================================================

# 分层规则（来自学校要求）：
# - 数学：G3及以上分层
# - 语文：G4及以上分层
# - 英语：G3-G5年级为单位分两层，G6-G7混年级分成7层，G8-G9混年级分成6层

LAYER_GROUPS = [
    # 数学分层 - G3及以上，每个年级分2层
    {"subject": "数学", "grades": ["G3"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G4"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G5"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G6"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G7"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G8"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "数学", "grades": ["G9"], "layer_count": 2, "weekly_hours": 8, "continuous": True},
    {"subject": "数学", "grades": ["G10"], "layer_count": 2, "weekly_hours": 8, "continuous": True},
    {"subject": "数学", "grades": ["G11"], "layer_count": 2, "weekly_hours": 8, "continuous": True},
    
    # 语文分层 - G4及以上，每个年级分2层
    {"subject": "语文", "grades": ["G4"], "layer_count": 2, "weekly_hours": 8, "continuous": True},
    {"subject": "语文", "grades": ["G5"], "layer_count": 2, "weekly_hours": 7, "continuous": True},
    {"subject": "语文", "grades": ["G6"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "语文", "grades": ["G7"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "语文", "grades": ["G8"], "layer_count": 2, "weekly_hours": 6, "continuous": True},
    {"subject": "语文", "grades": ["G9"], "layer_count": 2, "weekly_hours": 5, "continuous": True},
    
    # 英语分层 - G3-G5 各年级分2层
    {"subject": "英语(外)", "grades": ["G3"], "layer_count": 2, "weekly_hours": 8, "continuous": False},
    {"subject": "英语(外)", "grades": ["G4"], "layer_count": 2, "weekly_hours": 8, "continuous": False},
    {"subject": "英语(外)", "grades": ["G5"], "layer_count": 2, "weekly_hours": 8, "continuous": False},
    
    # 英语分层 - G6-G7 混年级分7层（需要7位老师同时上）
    {"subject": "英语(外)", "grades": ["G6", "G7"], "layer_count": 7, "weekly_hours": 9, "continuous": False, "cross_grade": True},
    
    # 英语分层 - G8-G9 混年级分6层
    {"subject": "英语(外)", "grades": ["G8", "G9"], "layer_count": 6, "weekly_hours": 4, "continuous": False, "cross_grade": True},
]


# ==============================================================================
# 七、特殊约束配置
# ==============================================================================

SPECIAL_CONSTRAINTS = {
    # 早晚班约束
    "early_late_shift": {
        "cn_homeroom_no_monday_late": True,  # 中教班主任周一不安排晚班
        "cn_en_homeroom_different_day": True,  # 中外教班主任不同一天晚班
        "late_shift_teacher_no_morning": True,  # 晚班教师上午不排课
    },
    
    # 连堂约束
    "continuous_lessons": {
        "main_subjects_weekly_continuous": True,  # 语数英每周至少一个连堂
        "primary_art_continuous": True,  # 小学美术课连堂
    },
    
    # 游泳课约束（综素班）
    "swimming_constraints": {
        "G1_wednesday_afternoon": ["N1-1", "N1-2"],  # 一年级周三下午游泳
        "G2_thursday_afternoon": ["N2-1", "N2-2"],  # 二年级周四下午游泳
    },
    
    # 轮滑约束
    "skating_constraints": {
        "no_lunch_adjacent": True,  # 不安排午餐前后
        "no_dinner_before": True,   # 不安排晚饭前一节
    },
    
    # 第一节课约束
    "first_period_constraints": {
        "no_art_sports": True,  # 第一节不能上艺体课
    },
}


# ==============================================================================
# 八、数据生成函数
# ==============================================================================

def generate_real_school_data() -> ScheduleData:
    """
    生成基于学校真实配置的测试数据
    
    Returns:
        ScheduleData: 完整的排课数据集
    """
    # 生成班级
    classes = []
    class_id = 1
    
    for cls_config in PRIMARY_CLASSES:
        classes.append(Class(
            id=class_id,
            name=cls_config["name"],
            type=cls_config["type"],
            grade=cls_config["grade"],
            class_no=cls_config["class_no"],
            department="PRIMARY"
        ))
        class_id += 1
    
    for cls_config in SECONDARY_CLASSES:
        classes.append(Class(
            id=class_id,
            name=cls_config["name"],
            type=cls_config["type"],
            grade=cls_config["grade"],
            class_no=cls_config["class_no"],
            department="SECONDARY"
        ))
        class_id += 1
    
    # 生成教师
    teachers = []
    teacher_id = 1
    
    for t_config in PRIMARY_CN_TEACHERS:
        teachers.append(Teacher(
            id=teacher_id,
            name=t_config["name"],
            type="CN",
            department="PRIMARY",
            subjects=t_config["subjects"],
            max_weekly_hours=t_config["max_hours"],
            tags=t_config.get("tags", [])
        ))
        teacher_id += 1
    
    for t_config in PRIMARY_EN_TEACHERS:
        teachers.append(Teacher(
            id=teacher_id,
            name=t_config["name"],
            type="EN",
            department="PRIMARY",
            subjects=t_config["subjects"],
            max_weekly_hours=t_config["max_hours"],
            tags=[]
        ))
        teacher_id += 1
    
    for t_config in SECONDARY_CN_TEACHERS:
        teachers.append(Teacher(
            id=teacher_id,
            name=t_config["name"],
            type="CN",
            department="SECONDARY",
            subjects=t_config["subjects"],
            max_weekly_hours=t_config["max_hours"],
            tags=t_config.get("tags", [])
        ))
        teacher_id += 1
    
    for t_config in SECONDARY_EN_TEACHERS:
        teachers.append(Teacher(
            id=teacher_id,
            name=t_config["name"],
            type="EN",
            department="SECONDARY",
            subjects=t_config["subjects"],
            max_weekly_hours=t_config["max_hours"],
            tags=[]
        ))
        teacher_id += 1
    
    # 生成科目
    subjects = []
    subject_id = 1
    
    for s_config in SUBJECTS:
        subjects.append(Subject(
            id=subject_id,
            code=s_config["code"],
            name=s_config["name"],
            category=s_config["category"],
            is_main=s_config["is_main"],
            required_room_type=s_config.get("venue"),
            color=s_config["color"]
        ))
        subject_id += 1
    
    # 生成场地
    venues = []
    venue_id = 1
    
    for v_config in VENUES:
        venues.append(Venue(
            id=venue_id,
            name=v_config["name"],
            capacity=v_config["capacity"],
            subjects=v_config["subjects"]
        ))
        venue_id += 1
    
    # 生成分层组
    layer_groups = []
    layer_id = 1
    subject_map = {s.name: s for s in subjects}
    
    for lg_config in LAYER_GROUPS:
        subject = subject_map.get(lg_config["subject"])
        if subject:
            layer_groups.append(LayerGroup(
                id=layer_id,
                subject_id=subject.id,
                subject_name=subject.name,
                grades=lg_config["grades"],
                layer_count=lg_config["layer_count"],
                is_cross_grade=lg_config.get("cross_grade", False),
                weekly_hours=lg_config["weekly_hours"],
                needs_continuous=lg_config.get("continuous", False)
            ))
            layer_id += 1
    
    # 生成教学任务
    tasks = _generate_tasks(classes, teachers, subjects, layer_groups)
    
    # 构建数据集
    data = ScheduleData(
        teachers=teachers,
        classes=classes,
        subjects=subjects,
        tasks=tasks,
        layer_groups=layer_groups,
        venues=venues
    )
    
    return data


def _generate_tasks(
    classes: List[Class],
    teachers: List[Teacher],
    subjects: List[Subject],
    layer_groups: List[LayerGroup]
) -> List[Task]:
    """生成教学任务"""
    tasks = []
    task_id = 1
    
    # 构建映射
    subject_map = {s.name: s for s in subjects}
    teachers_by_subject = {}
    for t in teachers:
        for subj in t.subjects:
            if subj not in teachers_by_subject:
                teachers_by_subject[subj] = []
            teachers_by_subject[subj].append(t)
    
    # 为每个班级生成任务
    for cls in classes:
        # 获取年级课时配置
        grade = cls.grade
        if grade in PRIMARY_GRADE_HOURS:
            hours_config = PRIMARY_GRADE_HOURS[grade]
        elif grade in SECONDARY_GRADE_HOURS:
            hours_config = SECONDARY_GRADE_HOURS[grade]
        else:
            continue
        
        for subject_name, weekly_hours in hours_config.items():
            subject = subject_map.get(subject_name)
            if not subject:
                continue
            
            # 查找可用教师
            available_teachers = teachers_by_subject.get(subject_name, [])
            if not available_teachers:
                # 尝试匹配基础科目名
                base_name = subject_name.replace("(外)", "").replace("(中)", "")
                available_teachers = teachers_by_subject.get(base_name, [])
            
            if not available_teachers:
                continue
            
            # 轮流分配教师
            teacher = available_teachers[task_id % len(available_teachers)]
            
            # 检查是否属于分层组
            layer_group_id = None
            for lg in layer_groups:
                if lg.subject_name == subject_name and cls.grade in lg.grades:
                    layer_group_id = lg.id
                    break
            
            # 确定是否连堂
            is_continuous = (
                subject.is_main and weekly_hours >= 4  # 主科4节以上连堂
                or (grade in ["G1", "G2", "G3", "G4", "G5"] and subject_name == "美术")  # 小学美术连堂
            )
            
            task = Task(
                id=task_id,
                teacher_id=teacher.id,
                teacher_name=teacher.name,
                class_id=cls.id,
                class_name=cls.name,
                subject_id=subject.id,
                subject_name=subject.name,
                weekly_hours=weekly_hours,
                is_continuous=is_continuous,
                continuous_count=2 if is_continuous else 1,
                layer_group_id=layer_group_id,
                preferred_period="MORNING" if subject.is_main else "ANY",
                required_venue_type=subject.required_room_type
            )
            tasks.append(task)
            
            # 将任务添加到分层组
            if layer_group_id:
                for lg in layer_groups:
                    if lg.id == layer_group_id:
                        lg.task_ids.append(task_id)
                        break
            
            task_id += 1
    
    return tasks


# 便捷导出
__all__ = [
    'generate_real_school_data',
    'PRIMARY_CLASSES',
    'SECONDARY_CLASSES',
    'PRIMARY_CN_TEACHERS',
    'PRIMARY_EN_TEACHERS',
    'SECONDARY_CN_TEACHERS',
    'SECONDARY_EN_TEACHERS',
    'SUBJECTS',
    'VENUES',
    'PRIMARY_GRADE_HOURS',
    'SECONDARY_GRADE_HOURS',
    'LAYER_GROUPS',
    'SPECIAL_CONSTRAINTS',
]
