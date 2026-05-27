"""分层/合班课程教学任务同步（避免 router 与 service_import 循环导入）。"""
from sqlalchemy.orm import Session

from app.modules.tasks.models import TeachingTask
from app.modules.classes.models import Class as ClassModel
from . import models


def resolve_layer_scope(layer_group: models.LayerGroup) -> str:
    """解析分层范围（兼容无 layer_scope 列的旧数据）。"""
    scope = getattr(layer_group, "layer_scope", None) or ""
    if scope in ("GRADE", "CROSS_GRADE", "SINGLE_CLASS"):
        return scope
    return "CROSS_GRADE" if layer_group.is_cross_grade else "GRADE"


def sync_layer_tasks(db: Session, layer_group: models.LayerGroup):
    """
    同步分层/合班课程的教学任务。

    根据课程类型自动创建教学任务，确保排课时能正确锁定涉及班级的时间。
    """
    db.query(TeachingTask).filter(
        TeachingTask.layer_group_id == layer_group.id,
        TeachingTask.is_deleted == False,
    ).update({"is_deleted": True})

    teacher_ids = layer_group.teacher_ids or []
    if not teacher_ids:
        db.commit()
        return

    group_type = layer_group.group_type or "LAYER"
    target_classes = []
    class_ids = layer_group.class_ids or []

    if class_ids:
        target_classes = db.query(ClassModel).filter(
            ClassModel.id.in_(class_ids),
            ClassModel.is_deleted == False,
        ).all()
    elif group_type != "COMBINE":
        grades = layer_group.grades or []
        if grades:
            target_classes = db.query(ClassModel).filter(
                ClassModel.grade.in_(grades),
                ClassModel.is_deleted == False,
            ).all()
            if not target_classes:
                from sqlalchemy import or_

                conditions = [ClassModel.name.contains(g) for g in grades]
                target_classes = db.query(ClassModel).filter(
                    or_(*conditions),
                    ClassModel.is_deleted == False,
                ).all()

    if not target_classes:
        db.commit()
        return

    layer_scope = resolve_layer_scope(layer_group)

    if group_type == "LAYER" and layer_scope == "SINGLE_CLASS":
        if len(target_classes) != 1:
            db.commit()
            return
        cls = target_classes[0]
        for layer_idx, teacher_id in enumerate(teacher_ids[: layer_group.layer_count]):
            if not teacher_id or teacher_id <= 0:
                continue
            db.add(
                TeachingTask(
                    teacher_id=teacher_id,
                    class_id=cls.id,
                    subject_id=layer_group.subject_id,
                    weekly_hours=layer_group.weekly_hours,
                    is_continuous=layer_group.needs_continuous,
                    continuous_count=2 if layer_group.needs_continuous else 1,
                    layer_group_id=layer_group.id,
                    note=f"单班分层第{layer_idx + 1}层 - {cls.name}",
                )
            )
    else:
        for idx, cls in enumerate(target_classes):
            if group_type == "COMBINE":
                teacher_id = teacher_ids[0] if teacher_ids else None
                note = f"合班课程 - {cls.name}"
            else:
                teacher_idx = idx % len(teacher_ids)
                teacher_id = teacher_ids[teacher_idx]
                note = f"分层课程第{teacher_idx + 1}层 - {cls.name}"

            if not teacher_id or teacher_id <= 0:
                continue

            db.add(
                TeachingTask(
                    teacher_id=teacher_id,
                    class_id=cls.id,
                    subject_id=layer_group.subject_id,
                    weekly_hours=layer_group.weekly_hours,
                    is_continuous=layer_group.needs_continuous,
                    continuous_count=2 if layer_group.needs_continuous else 1,
                    layer_group_id=layer_group.id,
                    note=note,
                )
            )

    db.commit()
