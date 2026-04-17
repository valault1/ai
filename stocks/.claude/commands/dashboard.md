Open the live stock analysis dashboard.

Run:
```bash
python3 -c "
import subprocess, sys
result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True)
import json
data = json.loads(result.stdout)
hostname = data.get('Self', {}).get('DNSName', '').rstrip('.')
if hostname:
    print(f'http://{hostname}:7842')
else:
    print('http://localhost:7842')
"
```

Open the URL printed above in the browser with:
```bash
xdg-open <URL>
```

If the server is not running, start it first:
```bash
systemctl --user start stocks-dashboard
```

Then open the URL.
