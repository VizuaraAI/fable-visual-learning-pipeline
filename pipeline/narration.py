"""Narration: the reference's own Hindi script (from its captions), cleaned, voiced with ElevenLabs, and laid on the
original sentence timestamps so the voice lands on the same visuals. No music bed: the reference has digital silence
between sentences.  Usage:  python3 narration.py gen <transcript.txt> <workdir>   |   python3 narration.py mix <workdir> <out.wav>"""
import sys, os, re, json, subprocess, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VOICE = os.environ.get('VL_VOICE', '9FTUWXd0yHJL1ZiZ71RK')   # Anika - Engaging Teacher (female, Indian)
MODEL = 'eleven_multilingual_v2'
FIXES = [('बकर', 'बीकर'), ('स्पाइट लैंप', 'स्पिरिट लैंप'), ('जहां से कवर', 'जार से कवर'), ('हली रिएक्टिव', 'हाइली रिएक्टिव'),
         ('डजलिंग', 'डैज़लिंग'), ('रिबिन', 'रिबन'), ('वि एन एलिमेंट', 'व्हिच एन एलिमेंट'), ('डीकंपोजशन', 'डीकंपोज़िशन'), ('डीकंपोजीशन', 'डीकंपोज़िशन'),
         ('इनसॉलबल', 'इनसॉल्युबल'), ('इनसॉलुबल', 'इनसॉल्युबल'), ('रसिडिटी', 'रैंसिडिटी'), ('कोरोजन', 'कोरोज़न'), ('इंटैक्ट', 'इंटरैक्ट'),
         ('फैट्स और ऑल के', 'फैट्स और ऑयल के'), ('फैट और ऑल से', 'फैट और ऑयल से'), ('ऑल का इनकंप्लीट', 'ऑयल का इनकंप्लीट'),
         ('आयरन आयरन कॉपर आयरन को कॉपर सल्फेट सॉल्यूशन से रिप्लेस कर दिया जाता है', 'आयरन, कॉपर को कॉपर सल्फेट सॉल्यूशन से रिप्लेस कर देता है'),
         ('टेस्ट ट्यूब भी जिसमें', 'टेस्ट ट्यूब बी जिसमें'), ('प्रेजेंस ऑक्सीजन', 'प्रेज़ेंट ऑक्सीजन'), ('स्पॉनटेनियस इरिवर्सिबल', 'स्पॉन्टेनियस इर्रिवर्सिबल'),
         ('केमिकल रिएक्शनंस', 'केमिकल रिएक्शन्स'), ('मोस्टली किसी', 'मोस्टली किसी'), ('जैसेजैसे', 'जैसे-जैसे'), ('वैसेवैसे', 'वैसे-वैसे'),
         ('इफ यू लाइक दिस वीडियो', 'इफ यू लाइक्ड दिस वीडियो')]

def project_fixes():
    """projects/<VL_PROJECT>/fixes.py may define FIXES = [(wrong, right), ...] and SENTENCE_FIXES = {exact_sentence: replacement}."""
    import importlib
    try:
        m = importlib.import_module(f"projects.{os.environ.get('VL_PROJECT', 'chem')}.fixes"); return list(getattr(m, 'FIXES', [])), dict(getattr(m, 'SENTENCE_FIXES', {}))
    except Exception: return [], {}

def parse(path):
    lines = []
    for l in open(path, encoding='utf-8'):
        m = re.match(r'\[(\d\d):(\d\d)\] (.*)', l.strip())
        if m: lines.append((int(m.group(1)) * 60 + int(m.group(2)), m.group(3)))
    return lines

def sentences(lines):
    """Group caption lines into sentences ('।' terminated). Start time = time of the line where the sentence begins,
    plus a proportional offset when a sentence starts mid-line."""
    out = []; cur = ''; cur_t = None
    for i, (t, txt) in enumerate(lines):
        nxt_t = lines[i + 1][0] if i + 1 < len(lines) else t + 3
        pos = 0; parts = re.split(r'(।)', txt)
        for p in parts:
            if p == '':
                continue
            if p == '।':
                cur += '।'; out.append((cur_t, cur.strip())); cur = ''; cur_t = None; pos += 1; continue
            if cur_t is None: cur_t = t + (nxt_t - t) * (pos / max(1, len(txt)))
            cur += (' ' if cur else '') + p.strip(); pos += len(p)
    if cur.strip(): out.append((cur_t, cur.strip()))
    pf, sf = project_fixes(); fixed = []
    for t, s in out:
        for a, b in (FIXES if os.environ.get('VL_PROJECT', 'chem') == 'chem' else []) + pf: s = s.replace(a, b)
        if s == 'समझते हैं।' and os.environ.get('VL_PROJECT', 'chem') == 'chem': s = 'आइए इसे एक सिंपल एक्टिविटी से समझते हैं।'
        s = sf.get(s, s)
        fixed.append((round(t, 2), s))
    return fixed

def key():
    """ElevenLabs key: the ELEVENLABS_API_KEY environment variable, else a .env file in pipeline/ or the repo root (never committed)."""
    k = os.environ.get('ELEVENLABS_API_KEY')
    if k: return k
    here = os.path.dirname(os.path.abspath(__file__))
    for f in (os.path.join(here, '.env'), os.path.join(here, '..', '.env')):
        if os.path.exists(f):
            for l in open(f):
                if l.startswith('ELEVENLABS_API_KEY='): return l.split('=', 1)[1].strip().strip('"')
    raise SystemExit('ELEVENLABS_API_KEY is not set: export it, or copy .env.example to .env at the repo root and fill it in')

def gen(transcript, work):
    import urllib.request
    os.makedirs(work, exist_ok=True); sents = sentences(parse(transcript)); k = key()
    man = []; prev = ''
    for i, (t, s) in enumerate(sents):
        fn = os.path.join(work, f'n{i:03d}.mp3')
        if not os.path.exists(fn):
            body = json.dumps({'text': s, 'model_id': MODEL, 'language_code': 'hi', 'previous_text': prev[-300:] or None,
                               'voice_settings': {'stability': 0.55, 'similarity_boost': 0.8, 'style': 0.0, 'use_speaker_boost': True, 'speed': float(os.environ.get('VL_SPEED', '1.0'))}}).encode()
            req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128', data=body,
                                         headers={'xi-api-key': k, 'Content-Type': 'application/json'})
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(req, timeout=120) as r: open(fn, 'wb').write(r.read()); break
                except Exception as e:
                    print('retry', i, e); time.sleep(3 + attempt * 3)
        dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', fn]).decode().strip())
        man.append(dict(i=i, t=t, text=s, file=fn, dur=dur)); prev = s
        print(f'{i:3d} {t:7.2f}s  {dur:5.2f}s  {s[:60]}')
    json.dump(man, open(os.path.join(work, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    print('chars', sum(len(m['text']) for m in man), 'sentences', len(man))

def decode(fn, tempo=1.0, sr=44100, trim_db=-45.0):
    af = ['-af', f'atempo={tempo:.4f}'] if abs(tempo - 1) > 0.01 else []
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', fn] + af + ['-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'])
    a = np.frombuffer(raw, dtype=np.float32)
    # trim leading/trailing silence (ElevenLabs pads ~0.3-0.5 s) but keep 60 ms of air on each side
    thr = 10 ** (trim_db / 20); idx = np.where(np.abs(a) > thr)[0]
    if len(idx):
        i0 = max(0, idx[0] - int(0.06 * sr)); i1 = min(len(a), idx[-1] + int(0.06 * sr)); a = a[i0:i1]
    return a

def trimmed_dur(fn, sr=44100): return len(decode(fn, 1.0, sr)) / sr

def mix(work, out, total=792.2, sr=44100, gap=0.2, max_tempo=1.3):
    man = json.load(open(os.path.join(work, 'manifest.json'))); n = len(man)
    for m in man: m['tdur'] = trimmed_dur(m['file'], sr)
    track = np.zeros(int(total * sr) + sr, dtype=np.float32); shift = 0.0; placements = []
    for j, m in enumerate(man):
        start = m['t'] + shift
        nxt = man[j + 1]['t'] + shift if j + 1 < n else total
        avail = max(0.8, nxt - start - gap); tempo = 1.0
        if m['tdur'] > avail: tempo = min(max_tempo, m['tdur'] / avail)
        a = decode(m['file'], tempo); d = len(a) / sr
        if d > avail + 0.05: shift += d - avail          # cascade only what stretching could not absorb
        i0 = int(start * sr)
        if i0 >= len(track) - sr // 10: print('dropped past end', m['i']); continue
        if i0 + len(a) > len(track): a = a[:len(track) - i0]
        # 12 ms fades to avoid clicks
        f = int(0.012 * sr); a = a.copy(); a[:f] *= np.linspace(0, 1, f); a[-f:] *= np.linspace(1, 0, f)
        track[i0:i0 + len(a)] += a; placements.append(dict(i=m['i'], start=round(start, 2), dur=round(d, 2), tempo=round(tempo, 3), shift=round(shift, 2)))
    peak = np.abs(track).max(); track *= min(1.0, 0.89 / max(peak, 1e-6))
    track = track[:int(total * sr)]
    import wave, struct
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((track * 32767).astype(np.int16).tobytes())
    json.dump(placements, open(os.path.join(work, 'placements.json'), 'w'), indent=1)
    print('mixed', out, 'max shift', max(p['shift'] for p in placements), 'stretched', sum(1 for p in placements if p['tempo'] > 1.01))

if __name__ == '__main__':
    if sys.argv[1] == 'gen': gen(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'mix': mix(sys.argv[2], sys.argv[3], total=float(os.environ.get('VL_TOTAL', '792.2')))
    elif sys.argv[1] == 'show':
        for t, s in sentences(parse(sys.argv[2])): print(f'{t:7.2f}  {s}')
