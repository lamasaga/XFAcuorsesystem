"""
========================================
教师数据库操作（CRUD）
========================================

CRUD 是四种基本数据库操作的缩写：
- Create（创建）: 插入新记录
- Read（读取）: 查询记录
- Update（更新）: 修改记录
- Delete（删除）: 删除记录

这个文件封装了所有与教师表相关的数据库操作。
路由（router.py）调用这里的函数来操作数据库。

为什么要单独封装 CRUD？
1. 关注点分离：数据库操作和 API 逻辑分开
2. 代码复用：同一个操作可以被多个地方调用
3. 易于测试：可以单独测试数据库操作
4. 便于维护：修改数据库操作只需改这个文件

使用方法：
    from app.modules.teachers import crud
    
    # 获取教师列表
    teachers = crud.get_teachers(db, skip=0, limit=10)
    
    # 创建教师
    new_teacher = crud.create_teacher(db, teacher_data)
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# List, Optional: 类型提示
from typing import List, Optional

# Session: SQLAlchemy 会话类型
from sqlalchemy.orm import Session
from sqlalchemy import or_

# 导入模型和模式
from app.modules.teachers.models import Teacher
from app.modules.teachers.schemas import TeacherCreate, TeacherUpdate


# -----------------------------------------
# 查询操作（Read）
# -----------------------------------------
def get_teacher(db: Session, teacher_id: int) -> Optional[Teacher]:
    """
    根据 ID 获取单个教师
    
    Args:
        db: 数据库会话
        teacher_id: 教师 ID
    
    Returns:
        Teacher | None: 找到返回教师对象，未找到返回 None
    
    Example:
        teacher = crud.get_teacher(db, teacher_id=1)
        if teacher:
            print(teacher.name)
    """
    # query(Teacher): 查询 Teacher 表
    # filter(): 添加过滤条件
    # first(): 返回第一条记录（或 None）
    return db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.is_deleted == False  # 排除已删除的
    ).first()


def get_teacher_by_name(db: Session, name: str) -> Optional[Teacher]:
    """
    根据姓名获取教师
    
    用于检查是否存在同名教师。
    
    Args:
        db: 数据库会话
        name: 教师姓名
    
    Returns:
        Teacher | None: 找到返回教师对象，未找到返回 None
    """
    return db.query(Teacher).filter(
        Teacher.name == name,
        Teacher.is_deleted == False
    ).first()


def get_teachers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None
) -> List[Teacher]:
    """
    获取教师列表
    
    支持分页和过滤。
    
    Args:
        db: 数据库会话
        skip: 跳过的记录数（用于分页）
        limit: 返回的最大记录数
        type: 教师类型过滤（CN/EN）
        department: 学部过滤（PRIMARY/SECONDARY）
        search: 搜索关键词（按姓名搜索）
    
    Returns:
        List[Teacher]: 教师列表
    
    Example:
        # 获取前 20 个教师
        teachers = crud.get_teachers(db, skip=0, limit=20)
        
        # 只获取中教
        cn_teachers = crud.get_teachers(db, type="CN")
        
        # 搜索姓名包含"张"的教师
        results = crud.get_teachers(db, search="张")
    """
    # 构建基础查询
    query = db.query(Teacher).filter(Teacher.is_deleted == False)
    
    # 添加类型过滤
    if type:
        query = query.filter(Teacher.type == type)
    
    # 添加学部过滤
    # 注意：BOTH（小中贯通）的教师在筛选小学部或中学部时都应该显示
    if department:
        if department == 'BOTH':
            # 只筛选 BOTH
            query = query.filter(Teacher.department == 'BOTH')
        else:
            # PRIMARY 或 SECONDARY 时，也包含 BOTH
            query = query.filter(
                or_(
                    Teacher.department == department,
                    Teacher.department == 'BOTH'
                )
            )
    
    # 添加搜索过滤（模糊匹配姓名）
    if search:
        # ilike: 不区分大小写的 LIKE 查询
        # %search%: 包含 search 的字符串
        query = query.filter(Teacher.name.ilike(f"%{search}%"))
    
    # 按 ID 排序，应用分页
    # offset(skip): 跳过前 skip 条
    # limit(limit): 最多返回 limit 条
    return query.order_by(Teacher.id).offset(skip).limit(limit).all()


def get_teachers_count(
    db: Session,
    type: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """
    获取教师总数
    
    用于分页时计算总页数。
    
    Args:
        db: 数据库会话
        type: 教师类型过滤
        department: 学部过滤
        search: 搜索关键词
    
    Returns:
        int: 教师总数
    """
    query = db.query(Teacher).filter(Teacher.is_deleted == False)
    
    if type:
        query = query.filter(Teacher.type == type)
    
    # 添加学部过滤（与 get_teachers 保持一致）
    if department:
        if department == 'BOTH':
            query = query.filter(Teacher.department == 'BOTH')
        else:
            query = query.filter(
                or_(
                    Teacher.department == department,
                    Teacher.department == 'BOTH'
                )
            )
    
    if search:
        query = query.filter(Teacher.name.ilike(f"%{search}%"))
    
    # count(): 返回记录总数
    return query.count()


# -----------------------------------------
# 创建操作（Create）
# -----------------------------------------
def create_teacher(db: Session, teacher: TeacherCreate) -> Teacher:
    """
    创建新教师
    
    将传入的数据保存到数据库中。
    
    Args:
        db: 数据库会话
        teacher: 教师创建数据（TeacherCreate 模式）
    
    Returns:
        Teacher: 创建后的教师对象（包含 ID 等数据库生成的字段）
    
    Example:
        teacher_data = TeacherCreate(name="张三", type="CN")
        new_teacher = crud.create_teacher(db, teacher_data)
        print(new_teacher.id)  # 输出自动生成的 ID
    
    工作流程：
    1. 使用传入的数据创建 Teacher 对象
    2. 将对象添加到会话（db.add）
    3. 提交事务（db.commit）
    4. 刷新对象以获取数据库生成的值（db.refresh）
    """
    # model_dump(): 将 Pydantic 模型转换为字典
    # **dict: 将字典展开为关键字参数
    db_teacher = Teacher(**teacher.model_dump())
    
    # 将对象添加到会话
    # 此时数据还没有写入数据库
    db.add(db_teacher)
    
    # 提交事务，将数据写入数据库
    # 如果出错会回滚
    db.commit()
    
    # 刷新对象，获取数据库生成的字段（如 id、created_at）
    db.refresh(db_teacher)
    
    return db_teacher


# -----------------------------------------
# 更新操作（Update）
# -----------------------------------------
def update_teacher(
    db: Session,
    teacher_id: int,
    teacher_update: TeacherUpdate
) -> Optional[Teacher]:
    """
    更新教师信息
    
    只更新提供的字段，未提供的字段保持原值。
    
    Args:
        db: 数据库会话
        teacher_id: 要更新的教师 ID
        teacher_update: 更新数据
    
    Returns:
        Teacher | None: 更新成功返回教师对象，教师不存在返回 None
    
    Example:
        # 只更新姓名
        update_data = TeacherUpdate(name="李四")
        updated = crud.update_teacher(db, teacher_id=1, teacher_update=update_data)
    """
    # 先查询教师是否存在
    db_teacher = get_teacher(db, teacher_id)
    
    if not db_teacher:
        return None
    
    # 获取更新数据，exclude_unset=True 表示只包含显式设置的字段
    # 这样未传入的字段不会被覆盖
    update_data = teacher_update.model_dump(exclude_unset=True)
    
    # 遍历更新数据，设置到模型对象上
    for field, value in update_data.items():
        setattr(db_teacher, field, value)
    
    # 提交更新
    db.commit()
    db.refresh(db_teacher)
    
    return db_teacher


# -----------------------------------------
# 删除操作（Delete）
# -----------------------------------------
def delete_teacher(db: Session, teacher_id: int) -> bool:
    """
    删除教师（软删除）
    
    不会真正从数据库中删除记录，而是将 is_deleted 标记为 True。
    
    为什么使用软删除？
    1. 数据安全：误删除可以恢复
    2. 数据完整：关联数据不会出现悬空引用
    3. 审计需求：保留历史记录
    
    Args:
        db: 数据库会话
        teacher_id: 要删除的教师 ID
    
    Returns:
        bool: 删除成功返回 True，教师不存在返回 False
    
    Example:
        success = crud.delete_teacher(db, teacher_id=1)
        if success:
            print("删除成功")
    """
    db_teacher = get_teacher(db, teacher_id)
    
    if not db_teacher:
        return False
    
    # 软删除：将 is_deleted 设为 True
    db_teacher.is_deleted = True
    
    db.commit()
    
    return True


# -----------------------------------------
# 批量操作
# -----------------------------------------
def create_teachers_batch(
    db: Session,
    teachers: List[TeacherCreate]
) -> List[Teacher]:
    """
    批量创建教师
    
    一次性创建多个教师，比逐个创建更高效。
    
    Args:
        db: 数据库会话
        teachers: 教师创建数据列表
    
    Returns:
        List[Teacher]: 创建后的教师对象列表
    
    Example:
        teachers_data = [
            TeacherCreate(name="张三", type="CN"),
            TeacherCreate(name="李四", type="EN"),
        ]
        new_teachers = crud.create_teachers_batch(db, teachers_data)
    """
    db_teachers = [Teacher(**t.model_dump()) for t in teachers]
    
    # add_all: 一次性添加多个对象
    db.add_all(db_teachers)
    db.commit()
    
    # 刷新所有对象
    for t in db_teachers:
        db.refresh(t)
    
    return db_teachers
