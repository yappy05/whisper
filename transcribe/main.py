import asyncio
import aio_pika
import json
import whisper
import tempfile
import os


async def main():
    # Настройки окружения
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    queue_name = os.getenv("TRANSCRIBE_QUEUE", "transcribe_queue")

    # Загружаем модель
    print("Загружаю модель Whisper...")
    model = whisper.load_model("base")
    print("Модель загружена!")

    # Подключаемся к RabbitMQ
    print(f"Подключаемся к RabbitMQ: {rabbitmq_url}")
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    # Объявляем очередь (Nest публикует прямо в очередь, паттерн в payload)
    queue = await channel.declare_queue(queue_name, durable=True)

    print("🚀 Transcribe service started!")
    print(f"📡 Listening on queue '{queue_name}' for patterns: health_check, transcribe_file")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                pattern = message.routing_key
                payload = json.loads(message.body.decode())

                # Сообщения от Nest обычно имеют форму { pattern, data }.
                # Бывают случаи, когда pattern равен имени очереди. Тогда пытаемся извлечь из data.pattern,
                # и только в самом крайнем случае используем routing_key.
                pattern_from_payload = payload.get("pattern")
                data = payload.get("data", payload)

                # Обрабатываем health check
                if pattern_from_payload == "health_check":
                    response = {"status": "healthy", "service": "transcribe", "data": data}
                    print("✅ Health check processed")

                # Обрабатываем транскрибацию
                elif pattern_from_payload == "transcribe_file":
                    try:
                        audio_data = data.get('audiFile', {})
                        audi_bytes = bytes(audio_data['data'])
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            tmp.write(audi_bytes)
                            tmp_path = tmp.name
                            print(f"✅ Temporary file created: {tmp_path}")
                        result = model.transcribe(tmp_path)
                        response = {"status": "success", "text": result.get("text", "")}
                        print("✅ Transcription completed")
                        os.unlink(tmp_path)

                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                        print(f"❌ Transcription error: {e}")
                else:
                    response = {"status": "error", "message": f"Unknown pattern: {pattern_from_payload}"}

                # Отправляем ответ обратно (RPC)
                if message.reply_to:
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(response).encode(),
                            correlation_id=message.correlation_id,
                        ),
                        routing_key=message.reply_to,
                    )


if __name__ == "__main__":
    asyncio.run(main())
