"""Host-side audio delivery; Steam's runtime cannot see host /usr/bin/paplay."""
import json
import subprocess
import time
from pathlib import Path

def run_audio(data):
    queue = data / 'audio-queue'
    queue.mkdir(parents=True, exist_ok=True)
    while True:
        for request in sorted(queue.glob('*.json')):
            try:
                subprocess.run(['/usr/bin/paplay', '--client-name=Custom Achievements',
                                '--stream-name=Achievement unlocked', '--volume=65536',
                                str(data / 'achievement.wav')], check=True, timeout=5,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                status = {'playedAt': int(time.time()), 'request': request.name, 'ok': True}
                print('Achievement sound played:', request.name, flush=True)
            except (OSError, subprocess.SubprocessError) as error:
                status = {'playedAt': int(time.time()), 'request': request.name, 'ok': False, 'error': str(error)}
                print('Achievement sound failed:', error, flush=True)
            (data / 'audio-status.json').write_text(json.dumps(status))
            request.unlink(missing_ok=True)
        time.sleep(.1)
