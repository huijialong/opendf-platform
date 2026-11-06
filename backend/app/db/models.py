from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_sn = Column(String(64), unique=True, index=True)
    device_type = Column(String(32))  # UMI_GRIPPER / PICO_VR / EGO_CAM / ROBOT_ARM
    name = Column(String(128))
    status = Column(String(16), default="ONLINE")
    meta_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(32), unique=True, index=True)
    title = Column(String(128), nullable=False)
    scene_category = Column(String(64))
    priority = Column(String(16), default="MEDIUM")
    status = Column(String(32), default="PENDING")
    assignee = Column(String(64), nullable=True)
    sample_target = Column(Integer, default=50)
    completed_samples = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions = relationship("CaptureSession", back_populates="task", cascade="all, delete-orphan")

class CaptureSession(Base):
    __tablename__ = "capture_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String(64), unique=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    device_sn = Column(String(64))
    video_filename = Column(String(255))
    trajectory_filename = Column(String(255))
    duration_seconds = Column(Float, default=0.0)
    frame_count = Column(Integer, default=0)
    is_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="sessions")
    segments = relationship(
        "AnnotationSegment",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AnnotationSegment.start_time",
    )

class AnnotationSegment(Base):
    __tablename__ = "annotation_segments"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("capture_sessions.id"))
    action_label = Column(String(64))  # APPROACH / GRASP / LIFT / PLACE
    start_time = Column(Float)
    end_time = Column(Float)
    quality_score = Column(Integer, default=5)
    notes = Column(Text, nullable=True)
    review_status = Column(String(16), default="PENDING")  # PENDING / APPROVED / REJECTED
    reject_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CaptureSession", back_populates="segments")
