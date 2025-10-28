from pydantic import BaseModel, Field
from typing import Optional

class Employee(BaseModel):
    ID: int = Field(..., description="ID único del empleado")
    Name: str
    TimeOffBalance: float
    Job: str
    Address: str
    RequestedTimeOff: int

class EmployeeCreate(BaseModel):
    Name: str
    TimeOffBalance: float
    Job: str
    Address: str
    RequestedTimeOff: int

class EmployeeUpdate(BaseModel):
    Name: Optional[str] = None
    TimeOffBalance: Optional[float] = None
    Job: Optional[str] = None
    Address: Optional[str] = None
    RequestedTimeOff: Optional[int] = None
