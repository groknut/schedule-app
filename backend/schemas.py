"""
Pydantic schemas for request validation and response serialization.
Kept separate from ORM models for clean layering.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import date as _Date, time as _Time, datetime as _DateTime
from models import ShiftStatus, ShiftType, EmployeeRole

# Алиасы нужны чтобы Pydantic v2 на Python 3.14 корректно резолвил типы:
# без from __future__ import annotations аннотации вычисляются сразу в контексте
# модуля, где _Date = datetime.date, и не конфликтуют с именами полей класса.


# ─── Organization ────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None

class OrganizationOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: _DateTime

    class Config:
        from_attributes = True


# ─── Team ────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str
    organization_id: int
    parent_team_id: Optional[int] = None

class TeamOut(BaseModel):
    id: int
    name: str
    organization_id: int
    parent_team_id: Optional[int]
    created_at: _DateTime

    class Config:
        from_attributes = True


# ─── Employee ────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    name: str
    email: str
    password: str  # plain-text, будет захеширован в роуте
    role: EmployeeRole = EmployeeRole.EMPLOYEE
    team_id: Optional[int] = None
    position: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        return v

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[EmployeeRole] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    role: EmployeeRole
    team_id: Optional[int]
    position: Optional[str]
    is_active: bool
    created_at: _DateTime

    class Config:
        from_attributes = True


# ─── Shift ───────────────────────────────────────────────────────────────────

class ShiftCreate(BaseModel):
    employee_id: int
    date: _Date
    start_time: _Time
    end_time: _Time
    shift_type: ShiftType = ShiftType.PLANNED
    notes: Optional[str] = None

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end: _Time, info) -> _Time:
        start = info.data.get("start_time")
        if start and end <= start:
            raise ValueError("end_time must be after start_time")
        return end

class ShiftUpdate(BaseModel):
    employee_id: Optional[int] = None      # можно переназначить сотрудника
    date: Optional[_Date] = None
    start_time: Optional[_Time] = None
    end_time: Optional[_Time] = None
    shift_type: Optional[ShiftType] = None  # плановая / фактическая
    notes: Optional[str] = None            # None = поле не передано, "" = очистить
    status: Optional[ShiftStatus] = None

class ShiftConfirm(BaseModel):
    """Используется менеджером для подтверждения план/факт по смене.
    confirmed_by_id намеренно убран — берётся из JWT-токена на сервере.
    """
    actual_start_time: Optional[_Time] = None
    actual_end_time: Optional[_Time] = None
    status: ShiftStatus  # confirmed или rejected

class ShiftOut(BaseModel):
    id: int
    employee_id: int
    date: _Date
    start_time: _Time
    end_time: _Time
    shift_type: ShiftType
    status: ShiftStatus
    notes: Optional[str]
    actual_start_time: Optional[_Time]
    actual_end_time: Optional[_Time]
    confirmed_by_id: Optional[int]
    confirmed_at: Optional[_DateTime]
    created_at: _DateTime

    class Config:
        from_attributes = True


# ─── Reports ─────────────────────────────────────────────────────────────────

class PlanFactRow(BaseModel):
    employee_id: int
    employee_name: str
    date: _Date
    planned_start: Optional[_Time]
    planned_end: Optional[_Time]
    actual_start: Optional[_Time]
    actual_end: Optional[_Time]
    planned_hours: Optional[float]
    actual_hours: Optional[float]
    delta_hours: Optional[float]
    status: Optional[ShiftStatus]
