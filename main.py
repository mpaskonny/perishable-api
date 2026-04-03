from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationParams, SimulationResponse
from simulations.milk_uniform import run_milk_uniform
from simulations.milk_normal import run_milk_normal
from simulations.tomatoes_uniform import run_tomatoes_uniform
from simulations.tomatoes_normal import run_tomatoes_normal

app = FastAPI(
    title="Симулятор продуктов с ограниченным сроком годности",
    description="API для 4 комбинаций: молоко/помидоры × равномерный/нормальный",
    version="1.0.0"
)

# Разрешаем CORS для любого фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "API симулятора продуктов",
        "endpoints": [
            "/simulate/milk_uniform",
            "/simulate/milk_normal",
            "/simulate/tomatoes_uniform",
            "/simulate/tomatoes_normal",
            "/docs"
        ]
    }

@app.post("/simulate/milk_uniform", response_model=SimulationResponse)
async def simulate_milk_uniform(params: SimulationParams):
    """Симуляция молока с равномерным распределением спроса"""
    try:
        return run_milk_uniform(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate/milk_normal", response_model=SimulationResponse)
async def simulate_milk_normal(params: SimulationParams):
    """Симуляция молока с нормальным распределением спроса"""
    try:
        return run_milk_normal(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate/tomatoes_uniform", response_model=SimulationResponse)
async def simulate_tomatoes_uniform(params: SimulationParams):
    """Симуляция помидоров с равномерным распределением спроса"""
    try:
        return run_tomatoes_uniform(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate/tomatoes_normal", response_model=SimulationResponse)
async def simulate_tomatoes_normal(params: SimulationParams):
    """Симуляция помидоров с нормальным распределением спроса"""
    try:
        return run_tomatoes_normal(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/info")
async def get_info():
    """Информация о доступных симуляциях"""
    return {
        "products": ["milk", "tomatoes"],
        "distributions": ["uniform", "normal"],
        "combinations": [
            {"product": "milk", "distribution": "uniform", "endpoint": "/simulate/milk_uniform"},
            {"product": "milk", "distribution": "normal", "endpoint": "/simulate/milk_normal"},
            {"product": "tomatoes", "distribution": "uniform", "endpoint": "/simulate/tomatoes_uniform"},
            {"product": "tomatoes", "distribution": "normal", "endpoint": "/simulate/tomatoes_normal"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)