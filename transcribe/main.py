import asyncio
import aio_pika
import json
import whisper
import tempfile
import os


async def main():
    # Настройки окружения
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://localhost:5672/")
    queue_name = os.getenv("TRANSCRIBE_QUEUE", "transcribe_queue")

    # Загружаем модель
    print("Загружаю модель Whisper...")
    model = whisper.load_model("base")
    print("Модель загружена!")

    # Подключаемся к RabbitMQ
    print(f"Подключаемся к RabbitMQ: {rabbitmq_url}")
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel: aio_pika.abc.AbstractChannel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    # Объявляем очередь (Nest публикует прямо в очередь, паттерн в payload)
    queue = await channel.declare_queue(queue_name, durable=True)

    print("🚀 Transcribe service started!")
    print(f"📡 Listening on queue '{queue_name}' for patterns: health_check, transcribe_file")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                pattern = message.routing_key
                try:
                    payload = json.loads(message.body.decode()) if message.body else {}
                except Exception:
                    payload = {}

                # Сообщения от Nest обычно имеют форму { pattern, data }.
                # Бывают случаи, когда pattern равен имени очереди. Тогда пытаемся извлечь из data.pattern,
                # и только в самом крайнем случае используем routing_key.
                pattern_from_payload = payload.get("pattern")
                data = payload.get("data", payload)
                if not isinstance(pattern_from_payload, str) or not pattern_from_payload or pattern_from_payload == queue_name:
                    candidate = None
                    if isinstance(data, dict):
                        candidate = data.get("pattern") or data.get("cmd")
                    pattern_from_payload = candidate or pattern

                print(f"📨 Received message. routing_key={pattern}, pattern={pattern_from_payload}")

                # Обрабатываем health check
                if pattern_from_payload == "health_check":
                    response = {"status": "healthy", "service": "transcribe"}
                    print("✅ Health check processed")

                # Обрабатываем транскрибацию
                elif pattern_from_payload == "transcribe_file":
                    try:
                        # Сохраняем временный файл
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            # Ожидаем, что content — это bytes; если пришла base64/список — обработать отдельно
                            content = data.get("content")
                            if isinstance(content, list):
                                content = bytes(content)
                            tmp.write(content)
                            tmp_path = tmp.name

                        # Транскрибируем
                        result = model.transcribe(tmp_path)
                        response = {"status": "success", "text": result.get("text", "")}
                        print("✅ Transcription completed")

                        # Удаляем временный файл
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

