"""
Database models for the Work Schedule Planning System.
SQLAlchemy ORM models with full support for organizations, teams, employees, and shifts.
"""

from sqlalchemy import (
    Column, Integer, String, Date, Time, ForeignKey,
    Enum, Text, DateTime, Boolean, create_engine
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class ShiftStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ShiftType(str, enum.Enum):
    PLANNED = "planned"
    ACTUAL = "actual"


class EmployeeRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class Organization(Base):
    """Top-level organization. Supports multi-org scenarios."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")


class Team(Base):
    """
    Team / subdivision. Supports nested teams via parent_team_id.
    A team with parent_team_id=None is a root team in an organization.
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    parent_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="teams")
    parent_team = relationship("Team", remote_side=[id], back_populates="child_teams")
    child_teams = relationship("Team", back_populates="parent_team")
    employees = relationship("Employee", back_populates="team", cascade="all, delete-orphan")


class Employee(Base):
    """Employee record with built-in authentication (bcrypt password hash)."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=True)  # None = внешняя авторизация / не задан
    role = Column(Enum(EmployeeRole), default=EmployeeRole.EMPLOYEE, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    position = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="employees")
    shifts = relationship("Shift", foreign_keys="Shift.employee_id", back_populates="employee", cascade="all, delete-orphan")


class Shift(Base):
    """
    Individual work shift for an employee.
    Each shift has both a planned and optionally an actual record.
    Plan/fact confirmation is tracked via status field.
    """
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    shift_type = Column(Enum(ShiftType), default=ShiftType.PLANNED, nullable=False)
    status = Column(Enum(ShiftStatus), default=ShiftStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Actual shift reference (populated when manager confirms plan vs fact)
    actual_start_time = Column(Time, nullable=True)
    actual_end_time = Column(Time, nullable=True)
    confirmed_by_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship(
        "Employee", foreign_keys=[employee_id], back_populates="shifts"
    )
    confirmed_by = relationship("Employee", foreign_keys=[confirmed_by_id])
