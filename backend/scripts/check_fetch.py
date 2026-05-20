import requests
h={'Origin':'http://localhost:54321'}
try:
    r=requests.get('http://127.0.0.1:5000/api/assistant/status', headers=h, timeout=5)
    print('status', r.status_code)
    print('headers:')
    for k,v in r.headers.items():
        print(k+':',v)
    print('text:', r.text[:400])
except Exception as e:
    print('error', e)
