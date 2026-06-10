import urllib.parse, http.server, threading, requests, json, webbrowser

CLIENT_ID     = "41956"
CLIENT_SECRET = input("Client secret: ").strip()
REDIRECT_URI  = "http://localhost:8000/oauth/callback"
SCOPE         = "accesslink.read_all"

auth_url = (
    "https://flow.polar.com/oauth2/authorization"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={urllib.parse.quote(SCOPE)}"
)

print(f"\nOuvre cette URL dans ton navigateur:\n{auth_url}\n")

code_received = threading.Event()
auth_code = [None]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        if "code" in q:
            auth_code[0] = q["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK - tu peux fermer cet onglet")
            code_received.set()
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("0.0.0.0", 8000), Handler)
t = threading.Thread(target=srv.serve_forever)
t.daemon = True
t.start()

print("En attente du callback...")
code_received.wait(timeout=120)
srv.shutdown()

if not auth_code[0]:
    print("Timeout — relance le script")
    exit(1)

r = requests.post(
    "https://polarremote.com/v2/oauth2/token",
    data={
        "grant_type": "authorization_code",
        "code": auth_code[0],
        "redirect_uri": REDIRECT_URI,
    },
    auth=(CLIENT_ID, CLIENT_SECRET)
)
print("Status:", r.status_code)
token_data = r.json()
print("Token:", json.dumps(token_data, indent=2))

if "access_token" in token_data:
    token_data["saved_at"] = __import__("datetime").datetime.now().isoformat()
    json.dump(token_data, open("/root/polar/tokens.json","w"), indent=2)
    print("\n✅ tokens.json mis à jour")
