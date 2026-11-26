import importlib.metadata
dists = importlib.metadata.distributions()
for d in sorted(dists, key=lambda x: x.metadata['Name'].lower()):
    print(f"{d.metadata['Name']}: {d.version}")
