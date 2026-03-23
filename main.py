from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import g4f
import time

app = FastAPI()

# Serve the frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message")
    model_choice = data.get("model")
    image_data = data.get("image") # For Live Mode/Image Analysis

    start_time = time.time()

    # Map your UI dropdown to free models in g4f
    model_map = {
        "gpt-4": g4f.models.gpt_4,
        "gemini": g4f.models.gemini,
        "llama": g4f.models.llama_3_70b,
        "deepseek": g4f.models.deepseek_coder
    }
    
    selected_model = model_map.get(model_choice, g4f.models.gpt_4)

    try:
        # If there is an image (Live Mode), we append a note to the AI
        if image_data:
            user_message += "\n[System Note: An image frame from the user's screen was attached. Analyze the context of their screen based on your vision capabilities if supported by this free provider.]"

        response = g4f.ChatCompletion.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )
        ai_reply = response
    except Exception as e:
        ai_reply = f"Ciri Error: The free provider for {model_choice} is currently overloaded. Please click Retry or select another model."

    end_time = time.time()
    time_taken = round(end_time - start_time, 2)

    return {
        "text": ai_reply,
        "model": model_choice.upper(),
        "time": f"{time_taken}s"
    }
