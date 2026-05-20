import requests
h={'Origin':'http://127.0.0.1:54321','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
try:
    r=requests.options('http://127.0.0.1:5000/api/parse', headers=h, timeout=5)
    print('status', r.status_code)
    print('headers:')
    for k,v in r.headers.items():
        print(k+':',v)
    print('text:', r.text[:200])
except Exception as e:
    print('error', e)
