import json, os, time, urllib.request, urllib.error
URL = 'https://api.typesafe.ai/v1/systemone'
# the key is read from the environment when the request is built; nothing secret lives in this file
HEADERS = {'Content-Type': 'application/json', 'Authorization': 'Bearer $TYPESAFE_API_KEY'}
def ask(state, questions, model='jev-latest', retries=4):
    body = json.dumps({'state': state, 'model': model, 'questions': questions}).encode()
    for i in range(retries):
        req = urllib.request.Request(URL, body, {k: os.path.expandvars(v) for k, v in HEADERS.items()})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and i < retries - 1:
                time.sleep(2 ** i); continue
            raise RuntimeError(f'HTTP {e.code}: {e.read()[:300]!r}')
