import hashlib, os
out = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('node_modules', 'dist-e23', '.vite-cache', '__pycache__')]
    for f in files:
        p = os.path.join(root, f).replace(os.sep, '/')[2:]
        if p == 'E23_FILES_SHA256.txt':
            continue
        out.append((p, hashlib.sha256(open(p, 'rb').read()).hexdigest()))
open('E23_FILES_SHA256.txt', 'w', encoding='utf-8', newline='\n').write(''.join(f'{h}  {p}\n' for p, h in sorted(out)))
print(len(out), 'files hashed')
