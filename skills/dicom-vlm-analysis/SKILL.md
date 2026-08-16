---
name: dicom-vlm-analysis
description: Read DICOM/CT images with a local vision model (Ollama).
version: 1.0.0
author: Osmosy
license: MIT
metadata:
  hermes:
    tags: [dicom, ct, medical-imaging, vision, ollama, pydicom]
    category: medical-imaging
---

# DICOM → локальная vision-модель (пайплайн)

Превращает DICOM-снимки (КТ/МРТ) в PNG с корректным окном плотностей и прогоняет через
локальную мультимодальную модель Ollama (medgemma:4b) для описательного чтения.

## When to Use
- Пользователь дал флешку/папку с `.dcm` и просит «прочитать КТ/снимки».
- Нужен описательный разбор изображения без отправки данных в облако.
- Есть задача «что на этом срезе» (НЕ постановка диагноза — модель диагностику не даёт).

## Prerequisites
- Ollama с моделью: `ollama pull medgemma:4b` (медицинская vision, gemma3 4.3B).
  Запасной общий VLM: `qwen2.5vl:7b`.
- Python-окружение с pydicom + numpy + pillow:
  ```bash
  uv venv /tmp/dcmvenv
  uv pip install --python /tmp/dcmvenv/bin/python pydicom numpy pillow
  ```

## Procedure
1. **Найти флешку** (exFAT/NTFS монтируется автоматически):
   ```bash
   lsblk -o NAME,LABEL,MOUNTPOINT   # /run/media/$USER/<UUID> или /media/$USER/...
   ```
2. **Найти DICOM**: `find <mount> -name '*.dcm' | head`. Обычно структура:
   `<PatientName>/<StudyDate>/IMG-0001-*.dcm ... IMG-0005-*.dcm`.
3. **Снять метаданные** (кто пациент, аппарат, какие серии):
   ```python
   import pydicom; from pydicom import dcmread
   ds = dcmread("IMG-0002-00001.dcm", force=True)
   print(ds.PatientName, ds.PatientSex, ds.PatientAge, ds.ManufacturerModelName,
         ds.SeriesNumber, ds.SeriesDescription, ds.SliceThickness)
   ```
4. **Рендер в PNG** скриптом `scripts/render_ct.py` (мозговое окно W80/L40,
   костное W2000/L350):
   ```bash
   /tmp/dcmvenv/bin/python scripts/render_ct.py --root "<mount>/<Patient>/<Study>" --out /tmp/ct_png
   ```
5. **Спросить модель** скриптом `scripts/vlm_ask.py`:
   ```bash
   /tmp/dcmvenv/bin/python scripts/vlm_ask.py /tmp/ct_png/s5_brain_11.png \
     --model medgemma:4b --prompt "Опиши, что видишь на этом аксиальном КТ-срезе мозга"
   ```

## Pitfalls (проверено на реальном КТ)
- **Toshiba Aquilion** пишет часть серий с нестандартным заголовком: у них НЕТ
  SeriesInstanceUID/SOPClassUID (161 из 256 файлов). Читать строго `dcmread(..., force=True)`
  и через `getattr(ds, tag, fallback)` — иначе `AttributeError`. Определять серию по
  SeriesNumber, а при его отсутствии — по префиксу имени файла (IMG-0005-*).
- **Порог «>130 HU = кальцинат» ловит и кость черепа.** Чтобы отделить кальцинаты от кости,
  нужна сегментация (маска внутричерепного пространства) или зрение. Числа плотности годятся
  только как «есть/нет плотных структур», не как локализация.
- **medgemma отказывает на диагностический промпт** («стеноз? аневризма?») — отвечает
  «радиолог должен интерпретировать / I cannot see the images». Работает только
  ОПИСАТЕЛЬНЫЙ промпт («опиши структуры, что видишь»). Не проси поставить диагноз.
- **Скорость:** холодный запуск ~60 с (SigLIP-энкодер + загрузка), прогретый ~6 с.
  Первый запрос в сессии всегда медленный.
- **Пустой срез:** последние срезы серии могут быть за рамками головы → PNG в сотни байт,
  модель выдаст бессмыслицу. Выбирать средние срезы.
- **Версии:** `ollama show medgemma:4b` → `capabilities: vision` должно быть в списке.

## Verification
- PNG сгенерированы и непустые (нормальный срез ~40–50 КБ, пустой <2 КБ).
- Ответ модели содержит реальные анатомические термины (полушария, желудочки, орбиты,
  синусы), а не отказ/мусор.
- Описание согласуется с текстом заключения радиолога (если он есть).

## Scripts
- `scripts/render_ct.py` — DICOM → PNG (мозговое + костное окно), группировка по сериям.
- `scripts/vlm_ask.py` — PNG → локальная vision-модель Ollama (`/api/generate`, images=[base64]).
