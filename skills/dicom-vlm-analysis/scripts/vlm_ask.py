#!/usr/bin/env python3
"""Ask a local Ollama vision model about an image (PNG/JPEG).

Usage:
  python vlm_ask.py IMAGE --model medgemma:4b --prompt "..."
  python vlm_ask.py /tmp/ct_png/s5_brain_11.png \
      --prompt "Describe what you see on this axial brain CT slice."

NOTE: medgemma (medical vision model) REFUSES diagnostic prompts
("stenosis? aneurysm?") and defers to a radiologist. Use DESCRIPTIVE
prompts only — it answers those reliably.
"""
import base64
import json
import argparse
import urllib.request


def ask(image_path, prompt, model='medgemma:4b', host='http://localhost:11434', temperature=0.1):
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        'model': model,
        'prompt': prompt,
        'images': [b64],
        'stream': False,
        'options': {'temperature': temperature, 'num_predict': 600},
    }
    req = urllib.request.Request(
        host + '/api/generate',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--model', default='medgemma:4b')
    ap.add_argument('--prompt', default='Describe what you see on this image. Factual, no diagnosis.')
    ap.add_argument('--host', default='http://localhost:11434')
    ap.add_argument('--temperature', type=float, default=0.1)
    a = ap.parse_args()
    res = ask(a.image, a.prompt, a.model, a.host, a.temperature)
    print(res.get('response', '—'))
    print(f"\n[tokens={res.get('eval_count')} | {round(res.get('total_duration', 0) / 1e9, 1)}s]")


if __name__ == '__main__':
    main()
