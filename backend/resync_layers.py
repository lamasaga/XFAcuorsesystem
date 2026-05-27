"""
分层组数据重新同步脚本

功能：
1. 遍历所有现有 LayerGroup
2. 对于 class_ids 为空的 LAYER 组：
   - 根据 description 中的关键字（"综素"→N、"国际"→I）推断班型
   - 查询正确的班级列表并更新 class_ids
3. 更新 class_ids 后，重新同步教学任务

运行方式：
    cd backend
    python resync_layers.py
"""

import sys
import os

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 stdout 编码，防止 GBK 编码错误
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from app.core.database import SessionLocal

# 导入所有模型，确保 SQLAlchemy 能正确解析 relationship
from app.modules.subjects.models import Subject  # noqa: F401
from app.modules.teachers.models import Teacher  # noqa: F401
from app.modules.classes.models import Class as ClassModel
from app.modules.tasks.models import TeachingTask  # noqa: F401
from app.modules.layers.models import LayerGroup
from app.modules.layers.sync_tasks import sync_layer_tasks


def infer_class_type(group: LayerGroup) -> str | None:
    """
    从分层组的 description 和 subject 名称推断班型。
    
    推断规则优先级：
    1. 科目名称以 I/N 开头（如 "I数学"→国际班, "N艺术综合"→综素班）
    2. 描述中包含"综素"/"国际"等关键字
    3. 科目名称中包含"综素"/"国际"等关键字
    
    Returns:
        "I" - 国际班
        "N" - 综素班
        None - 无法推断
    """
    # 从 subject 关系中获取名称
    subject_name = ""
    if group.subject:
        subject_name = group.subject.name or ""
    
    # 规则1：科目名称首字符 I/N
    if subject_name and len(subject_name) >= 2:
        first_char = subject_name[0].upper()
        if first_char == "I":
            return "I"
        if first_char == "N":
            return "N"
    
    # 规则2：描述中的关键字
    text = group.description or ""
    if "综素" in text or "综合素质" in text:
        return "N"
    if "国际" in text:
        return "I"
    
    # 规则3：科目名称中的关键字
    if "综素" in subject_name:
        return "N"
    if "国际" in subject_name:
        return "I"
    
    return None


def resync_all():
    """主函数：重新同步所有分层组的任务数据。"""
    db = SessionLocal()
    
    try:
        groups = db.query(LayerGroup).all()
        print(f"找到 {len(groups)} 个分层/合班组\n")
        
        warnings = []
        updated_count = 0
        skipped_count = 0
        
        for group in groups:
            group_type = group.group_type or "LAYER"
            subject_name = group.subject.name if group.subject else "未知科目"
            grades_str = ", ".join(group.grades) if group.grades else "无"
            existing_class_ids = group.class_ids or []
            
            print(f"--- 分层组 #{group.id}: {subject_name} ({group_type}) ---")
            print(f"    年级: {grades_str}")
            print(f"    描述: {group.description or '(无)'}")
            print(f"    现有 class_ids: {existing_class_ids}")
            
            layer_scope = getattr(group, "layer_scope", None) or (
                "CROSS_GRADE" if group.is_cross_grade else "GRADE"
            )
            if layer_scope == "SINGLE_CLASS":
                if existing_class_ids:
                    print(f"    [单班分层] 保持 class_ids，重新同步任务...")
                    sync_layer_tasks(db, group)
                    updated_count += 1
                else:
                    print(f"    [单班分层] ⚠ class_ids 为空，跳过")
                    warnings.append(
                        f"单班分层组 #{group.id} ({subject_name}): class_ids 为空"
                    )
                    skipped_count += 1
                continue

            if group_type == "COMBINE":
                # 合班组：class_ids 应已正确设置，直接重新同步任务
                if existing_class_ids:
                    print(f"    [合班] class_ids 已设置，重新同步任务...")
                    sync_layer_tasks(db, group)
                    updated_count += 1
                else:
                    print(f"    [合班] ⚠ class_ids 为空，跳过")
                    warnings.append(f"合班组 #{group.id} ({subject_name}): class_ids 为空")
                    skipped_count += 1
                continue
            
            # LAYER 类型：始终基于推断结果重新设置 class_ids
            inferred_type = infer_class_type(group)
            grades = group.grades or []
            
            if not grades:
                print(f"    [!] 年级为空，跳过")
                warnings.append(f"分层组 #{group.id} ({subject_name}): 年级为空")
                skipped_count += 1
                continue
            
            if inferred_type:
                # 成功推断班型 → 按年级+班型筛选
                target_classes = db.query(ClassModel).filter(
                    ClassModel.grade.in_(grades),
                    ClassModel.type == inferred_type,
                    ClassModel.is_deleted == False
                ).all()
                new_class_ids = [c.id for c in target_classes]
                new_class_names = [c.name for c in target_classes]
                
                type_label = '国际班' if inferred_type == 'I' else '综素班'
                print(f"    推断班型: {inferred_type} ({type_label})")
                print(f"    匹配班级: {new_class_names}")
                
                if new_class_ids:
                    group.class_ids = new_class_ids
                    db.add(group)
                    db.flush()
                    sync_layer_tasks(db, group)
                    updated_count += 1
                    print(f"    [OK] 已更新 class_ids 并重新同步任务")
                else:
                    print(f"    [!] 未找到匹配班级")
                    warnings.append(
                        f"分层组 #{group.id} ({subject_name}): "
                        f"推断班型为 {inferred_type}，但年级 {grades} 无匹配班级"
                    )
                    skipped_count += 1
            else:
                # 无法推断 → 按全部班级处理
                target_classes = db.query(ClassModel).filter(
                    ClassModel.grade.in_(grades),
                    ClassModel.is_deleted == False
                ).all()
                new_class_ids = [c.id for c in target_classes]
                new_class_names = [c.name for c in target_classes]
                
                print(f"    [!] 无法推断班型，默认使用全部班级")
                print(f"    匹配班级: {new_class_names}")
                
                warnings.append(
                    f"分层组 #{group.id} ({subject_name}): "
                    f"无法推断班型，已使用年级 {grades} 的全部班级。"
                    f"如有误请手动修改。"
                )
                
                if new_class_ids:
                    group.class_ids = new_class_ids
                    db.add(group)
                    db.flush()
                    sync_layer_tasks(db, group)
                    updated_count += 1
                    print(f"    [OK] 已更新 class_ids（全部班级）并重新同步任务")
                else:
                    skipped_count += 1
            
            print()
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"同步完成！更新: {updated_count}, 跳过: {skipped_count}")
        
        if warnings:
            print(f"\n⚠ 需要注意的警告 ({len(warnings)}):")
            for w in warnings:
                print(f"  - {w}")
        
        # 验证：打印每个班级的课时统计
        print("\n" + "=" * 60)
        print("课时验证：")
        
        all_classes = db.query(ClassModel).filter(
            ClassModel.is_deleted == False
        ).order_by(ClassModel.grade, ClassModel.name).all()
        
        for cls in all_classes:
            tasks = db.query(TeachingTask).filter(
                TeachingTask.class_id == cls.id,
                TeachingTask.is_deleted == False
            ).all()
            
            layer_hours = sum(t.weekly_hours for t in tasks if t.layer_group_id)
            normal_hours = sum(t.weekly_hours for t in tasks if not t.layer_group_id)
            total = layer_hours + normal_hours
            
            flag = " ⚠ 超出!" if total > 46 else ""
            print(f"  {cls.name}: 普通={normal_hours}, 分层={layer_hours}, 合计={total}{flag}")
    
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] 同步失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("分层组数据重新同步")
    print("=" * 60)
    print()
    resync_all()
