import os
user_up = r"C:\Users\yashm\.gemini\antigravity\brain\f2c8165e-4c1c-4b8e-9e81-840977aaf3eb\.user_uploaded"
if os.path.exists(user_up):
    for f in os.listdir(user_up):
        p = os.path.join(user_up, f)
        print(f"{f}: {os.path.getsize(p)} bytes")
else:
    print("Not found")
