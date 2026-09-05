"""Original (non-recreation) chapter: script -> ElevenLabs clips -> layout on real clip durations -> transcript_hi.txt + timing.json + narration.wav.
  VL_PROJECT=heart python3 original.py gen      # voice every sentence of projects/heart/script.py (cached per sentence hash)
  VL_PROJECT=heart python3 original.py layout   # place clips: GAP between sentences, PAUSE before each section (its 2D card), write timing + mix
Layout rules: sentence i starts at prev_end + GAP; a section boundary adds CARD seconds (the blue section card plays there);
the intro title sequence gets LEAD seconds before the first sentence of section 1; the outro sentence is followed by TAIL seconds."""
import sys, os, json, importlib, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narration
PROJ = os.environ.get('VL_PROJECT'); assert PROJ, 'set VL_PROJECT'
S = importlib.import_module(f'projects.{PROJ}.script')
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', PROJ, 'narr'); os.makedirs(WORK, exist_ok=True)
GAP = float(os.environ.get('VL_GAP', '0.55')); CARD = float(os.environ.get('VL_CARD', '2.6')); LEAD = float(os.environ.get('VL_LEAD', '1.2')); TAIL = float(os.environ.get('VL_TAIL', '6.0'))

def units():
    """(section_index, section_title, sentence) for every TTS unit, splitting on '।' like narration.sentences() does."""
    out = []
    def push(si, title, block):
        for line in block:
            for part in line.split('।'):
                part = part.strip()
                if part: out.append((si, title, part + '।'))
    push(0, 'intro', S.INTRO)
    for i, (title, lines) in enumerate(S.SECTIONS, 1): push(i, title, lines)
    push(len(S.SECTIONS) + 1, 'outro', S.OUTRO)
    return out

def gen():
    import urllib.request, time
    k = narration.key(); man = []; prev = ''
    for i, (si, title, s) in enumerate(units()):
        h = hashlib.sha1((s + '|' + os.environ.get('VL_SPEED', '1.0')).encode()).hexdigest()[:10]; fn = os.path.join(WORK, f'u_{h}.mp3')
        if not os.path.exists(fn):
            body = json.dumps({'text': s, 'model_id': narration.MODEL, 'language_code': 'hi', 'previous_text': prev[-300:] or None,
                               'voice_settings': {'stability': 0.55, 'similarity_boost': 0.8, 'style': 0.0, 'use_speaker_boost': True, 'speed': float(os.environ.get('VL_SPEED', '1.0'))}}).encode()
            req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{narration.VOICE}?output_format=mp3_44100_128', data=body, headers={'xi-api-key': k, 'Content-Type': 'application/json'})
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(req, timeout=120) as r: open(fn, 'wb').write(r.read()); break
                except Exception as e: print('retry', i, e); time.sleep(3 + attempt * 3)
        d = narration.trimmed_dur(fn); man.append(dict(i=i, sec=si, title=title, text=s, file=fn, dur=d)); prev = s
        print(f'{i:3d} s{si} {d:5.2f}s  {s[:70]}')
    json.dump(man, open(os.path.join(WORK, 'units.json'), 'w'), ensure_ascii=False, indent=1)
    print('units', len(man), 'speech', round(sum(m['dur'] for m in man), 1), 's')

def layout():
    man = json.load(open(os.path.join(WORK, 'units.json'))); t = LEAD; cur_sec = 0; timing = []; sections = []
    for m in man:
        if m['sec'] != cur_sec:
            if m['sec'] <= len(S.SECTIONS): sections.append(dict(i=m['sec'], title=m['title'], card_t0=round(t, 2), t0=round(t + CARD, 2))); t += CARD
            else: t += 1.0
            cur_sec = m['sec']
        m['t'] = round(t, 2); timing.append(dict(i=m['i'], sec=m['sec'], t0=round(t, 2), t1=round(t + m['dur'], 2), text=m['text'])); t += m['dur'] + GAP
    total = round(t - GAP + TAIL, 1)
    for k, sc in enumerate(sections): sc['t1'] = sections[k + 1]['card_t0'] if k + 1 < len(sections) else timing[[x['sec'] for x in timing].index(len(S.SECTIONS) + 1)]['t0']
    json.dump(dict(total=total, sections=sections, sentences=timing), open(os.path.join(WORK, '..', 'timing.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projects', PROJ, 'transcript_hi.txt'), 'w') as fh:
        for x in timing: fh.write(f"[{int(x['t0'])//60:02d}:{int(x['t0'])%60:02d}] {x['text']}\n")
    json.dump([dict(i=m['i'], t=m['t'], text=m['text'], file=m['file'], dur=m['dur']) for m in man], open(os.path.join(WORK, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    narration.mix(WORK, os.path.join(WORK, '..', 'narration.wav'), total=total)
    print('TOTAL', total, 'sections', [(s['i'], s['title'], s['card_t0'], s['t1']) for s in sections])
    for s in sections: print(f"  {s['i']}. {s['title']}: {int(s['t0'])//60:02d}:{int(s['t0'])%60:02d} - {int(s['t1'])//60:02d}:{int(s['t1'])%60:02d}")

if __name__ == '__main__': {'gen': gen, 'layout': layout}[sys.argv[1]]()
