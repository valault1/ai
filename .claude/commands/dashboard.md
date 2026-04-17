Open the live stock analysis dashboard.

Get the Tailscale URL and open it:

```bash
python3 -c "
import subprocess, json
r = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True)
d = json.loads(r.stdout)
h = d.get('Self', {}).get('DNSName', '').rstrip('.')
print(f'http://{h}:7842' if h else 'http://localhost:7842')
"
```

Open that URL with `xdg-open <url>`.

If the server is not running, start it first:
```bash
systemctl --user start stocks-dashboard
```
