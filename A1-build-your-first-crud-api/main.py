from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "title is required and must not be empty"},
    )

seed_tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Call the dentist", "done": False},
    {"id": 3, "title": "Water the plants", "done": True},
]

tasks = [task.copy() for task in seed_tasks]
next_id = len(tasks) + 1


class TaskIn(BaseModel):
    title: str = Field(min_length=1, description="Task title, must not be empty")


@app.get("/")
async def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/tasks")
async def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=201)
async def create_task(task_in: TaskIn):
    global next_id
    task = {"id": next_id, "title": task_in.title, "done": False}
    tasks.append(task)
    next_id += 1
    return task
