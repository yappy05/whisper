# create_russian_audio.py
import wave
import numpy as np
import math


def create_audio_file():
    # Параметры аудио
    sample_rate = 44100  # Hz
    duration = 4.0  # seconds

    # Создаем массив сamples
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Создаем простую мелодию с разными тонами
    signal = np.zeros(num_samples)

    # Добавляем несколько тонов (имитация речи)
    frequencies = [220, 330, 440, 350, 280]  # Hz
    amplitudes = [0.3, 0.5, 0.7, 0.4, 0.2]

    for freq, amp in zip(frequencies, amplitudes):
        signal += amp * np.sin(2 * np.pi * freq * t)

    # Нормализуем сигнал
    signal = signal / np.max(np.abs(signal)) * 0.8

    # Сохраняем как WAV файл
    with wave.open("test_audio_ru.wav", "w") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16 bits
        wav_file.setframerate(sample_rate)
        wav_file.writeframes((signal * 32767).astype(np.int16).tobytes())

    print("✅ Создан test_audio_ru.wav")
    print("📁 Файл готов для тестирования API")


if __name__ == "__main__":
    create_audio_file()