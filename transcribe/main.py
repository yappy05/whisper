import tempfile

import whisper
from fastapi import FastAPI, File, UploadFile
import os

app = FastAPI()
print("Загружаю модель")
model = whisper.load_model("base")
print("модель загрузилась")


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    print(f"Получен файл: {file.filename}")
    print(f"работает модель: {model._get_name()}")

    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        print("Начинаем транскрибацию...")
        # Транскрибируем
        result = model.transcribe(tmp_path)
        print("Транскрибация завершена")
        return {"text": result["text"]}
    except Exception as e:
        print(f"Ошибка: {e}")
        return {"error": str(e)}
    finally:
        # Удаляем временный файл
        os.unlink(tmp_path)

@app.get("/")
def root():
    return {"message": "Welcome to Whisper"}

