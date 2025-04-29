# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WorkoutSession(Base):
    """운동 세션 정보를 저장하는 모델"""
    __tablename__ = "workout_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.now)
    routine_type = Column(String, nullable=False)  # 'push', 'pull', 'leg'

class ExerciseSet(Base):
    """각 운동 세트의 정보를 저장하는 모델"""
    __tablename__ = "exercise_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_name = Column(String, nullable=False)
    set_number = Column(Integer, nullable=False)
    weight = Column(Float, default=0.0)
    status = Column(String, nullable=False)  # 'success', 'fail'