with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if "'settings': {" in l:
        print(f'{i+1}: {l.strip()}')
        print(''.join(lines[i:i+30]))
