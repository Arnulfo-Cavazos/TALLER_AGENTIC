from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .models import Employee, EmployeeCreate, EmployeeUpdate
from .excel_handler import (
    list_employees, get_employee_by_id, add_employee,
    update_employee, delete_employee, download_from_cos
)
import pandas as pd

app = FastAPI(title="Employees Excel + COS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Intentar sincronizar al inicio
@app.on_event("startup")
def startup_sync():
    # intenta descargar desde COS; si falla, si tienes data/employees.xlsx local se usará
    download_from_cos()

@app.get("/")
def root():
    return {"message": "API Employees con COS lista."}

@app.get("/employees", response_model=List[Employee])
def api_list_employees():
    df = list_employees()
    # convertir IDs a int y demás
    records = df.to_dict(orient="records")
    return records

@app.get("/employees/{emp_id}", response_model=Employee)
def api_get_employee(emp_id: int):
    row = get_employee_by_id(emp_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return row.to_dict()

@app.post("/employees", status_code=201)
def api_create_employee(payload: EmployeeCreate):
    data = payload.dict()
    try:
        new_id = add_employee(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "ID": new_id}

@app.put("/employees/{emp_id}")
def api_replace_employee(emp_id: int, payload: Employee):
    # Reemplaza todo el registro (incluye ID)
    data = payload.dict()
    if data.get("ID") != emp_id:
        raise HTTPException(status_code=400, detail="ID en payload debe coincidir con emp_id.")
    success = update_employee(emp_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return {"status": "ok", "message": "Empleado reemplazado."}

@app.patch("/employees/{emp_id}")
def api_update_employee(emp_id: int, payload: EmployeeUpdate = Body(...)):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar.")
    success = update_employee(emp_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return {"status": "ok", "message": "Empleado actualizado."}

@app.delete("/employees/{emp_id}")
def api_delete_employee(emp_id: int):
    success = delete_employee(emp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return {"status": "ok", "message": "Empleado eliminado."}
