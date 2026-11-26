with open('app.py', 'r', encoding='utf-8') as f:
    for i, l in enumerate(f):
        if '@app.route("/api/' in l:
            print(str(i+1) + ': ' + l.strip())
