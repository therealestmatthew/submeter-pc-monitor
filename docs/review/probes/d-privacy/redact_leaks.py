"""Feed realistic command lines to redact_cmdline and say which secrets survive into the output.

Run:  uv run python docs/review/probes/d-privacy/redact_leaks.py

Every secret is fake. Each case is the argument list a process provider would hand over, as
psutil splits it on Linux and on Windows. The probe calls one function and prints the result.
It stores nothing and sends nothing. "ctrl" cases are ones the redactor should already catch.
"""

from __future__ import annotations

from collections import Counter

from submeter.privacy.redact import redact_cmdline

PW = "FAKEpw-7x"  # a short password: no shape to recognise
TOK = "FAKEtok0123456789abcdef"  # 23 characters, under the 32-character opaque rule
B64 = "RkFLRTpodW50ZXIy"  # base64 of FAKE:hunter2
HOST = "https://api.example.test/v1"
BEARER = f"Authorization: Bearer {TOK}"

# (class, argument list, the secret that must not survive)
CASES: list[tuple[str, list[str], str]] = [
    ("header", ["curl", "-H", BEARER, HOST], TOK),
    ("header", ["curl", "--header", f"X-Api-Key: {TOK}", HOST], TOK),
    ("header", ["curl", "-H", f"Authorization: Basic {B64}", HOST], B64),
    ("header", ["curl", "-H", f"Authorization: Basic {B64}=", HOST], B64),
    ("header", ["wget", f"--header={BEARER}", HOST], TOK),
    ("header", ["git", "-c", f"http.extraheader=AUTHORIZATION: basic {B64}", "fetch"], B64),
    ("header", ["npx", "mcp-remote", f"{HOST}/sse", "--header", BEARER], TOK),
    ("header", ["wscat", "-c", "wss://api.example.test", "-H", f"Cookie: sid={TOK}"], TOK),
    ("header ctrl", ["curl", "-H", "x-api-key: sk-ant-api03-FAKEfake0123456789", HOST], "sk-ant"),
    ("user:pass", ["curl", "-u", f"alice:{PW}", HOST], PW),
    ("user:pass", ["curl", "--user", f"alice:{PW}", HOST], PW),
    ("user:pass", ["sshpass", "-p", PW, "ssh", "build.example.test"], PW),
    ("user:pass", ["docker", "login", "-u", "alice", "-p", PW, "registry.example.test"], PW),
    ("user:pass", ["net", "use", "Z:", r"\\srv\share", PW, r"/user:CORP\alice"], PW),
    ("user:pass", ["PsExec.exe", r"\\host", "-u", "alice", "-p", PW, "cmd"], PW),
    ("user:pass", ["sqlcmd", "-S", "db", "-U", "sa", "-P", PW], PW),
    ("user:pass", ["redis-cli", "-a", PW, "ping"], PW),
    ("user:pass", ["smbclient", "//srv/share", "-U", f"alice%{PW}"], PW),
    ("user:pass", ["htpasswd", "-b", ".htpasswd", "alice", PW], PW),
    ("user:pass ctrl", ["mysql", "--user", "root", "--password", PW], PW),
    ("attached", ["mysql", "-uroot", f"-p{PW}", "appdb"], PW),
    ("attached", ["mysqldump", "-pMyPassFAKE-7x", "appdb"], "MyPassFAKE-7x"),
    ("attached", ["7z", "a", f"-p{PW}", "out.7z", "src"], PW),
    ("attached", ["ldapsearch", "-D", "cn=admin", f"-w{PW}"], PW),
    ("opt=NAME=value", ["docker", "run", f"--env=API_TOKEN={PW}", "img"], PW),
    ("opt=NAME=value", ["docker", "build", f"--build-arg=NPM_TOKEN={PW}", "."], PW),
    # the next one is hidden only because the whole argument happens to be 33 opaque characters
    ("opt=NAME=value", ["kubectl", "create", "secret", f"--from-literal=password={PW}"], PW),
    ("opt=NAME=value", ["helm", "upgrade", "app", "chart", f"--set=auth.password={PW}"], PW),
    ("opt=NAME=value", ["terraform", "apply", f"-var=db_password={PW}"], PW),
    ("opt=NAME=value ctrl", ["docker", "run", "-e", f"API_TOKEN={TOK}", "img"], TOK),
    ("opt=NAME=value ctrl", ["java", f"-Ddb.password={PW}", "-jar", "app.jar"], PW),
    ("slash option", ["cmdkey", "/add:srv", "/user:alice", f"/pass:{PW}"], PW),
    ("slash option", ["schtasks", "/create", "/tn", "T", "/ru", "alice", "/rp", PW], PW),
    ("slash option", ["xfreerdp", "/u:alice", f"/p:{PW}", "/v:host"], PW),
    ("slash option", ["tool.exe", "/password", PW], PW),
    ("slash option", ["tool.exe", f"/token:{TOK}"], TOK),
    ("slash option", ["msdeploy", f"-dest:auto,userName=alice,password={PW}"], PW),
    ("slash option ctrl", ["msbuild", f"/p:Password={PW}"], PW),
    ("connection", ["app", f"Server=db;Database=a;User Id=sa;Password={PW};"], PW),
    ("connection", ["app", f"host=db user=alice password={PW} dbname=a"], PW),
    ("connection", ["java", f"jdbc:postgresql://db/a?user=alice&password={PW}"], PW),
    ("connection", ["az", f"DefaultEndpointsProtocol=https;AccountKey={B64}==;"], B64),
    ("connection", ["redis-cli", "-u", f"redis://:{PW}@cache:6379/0"], PW),
    ("connection", ["psql", "postgres://alice:FAKE@tail9Z@db/a"], "tail9Z"),
    ("connection ctrl", ["psql", f"postgres://alice:{PW}@db/a"], PW),
    ("json", ["curl", "-d", f'{{"user":"alice","password":"{PW}"}}', HOST], PW),
    ("json", ["agent", "--mcp-config", f'{{"env":{{"GH_TOKEN":"github_pat_11{TOK}"}}}}'], TOK),
    ("json", ["ansible-playbook", "x.yml", "--extra-vars", f'{{"become_pass":"{PW}"}}'], PW),
    ("url", ["git", "clone", f"https://{TOK}@git.example.test/o/r.git"], TOK),
    ("url", ["curl", f"{HOST}/items?user=alice&token={TOK}"], TOK),
    ("url", ["curl", f"{HOST}/geo?key=AIzaSyFAKE{TOK}"], TOK),
    ("url", ["curl", f"{HOST}/blob?sv=2022-11-02&sp=r&sig={B64}%3D"], B64),
    # a browser opened on the dashboard with the API token in the address
    ("url", ["chrome", f"http://127.0.0.1:8787/?range=1h&token={TOK}"], TOK),
    ("url ctrl", ["chrome", f"http://127.0.0.1:8787/#token={TOK}"], TOK),
    ("url ctrl", ["curl", f"{HOST}/items?token={TOK}&user=alice"], TOK),
    ("url ctrl", ["git", "clone", f"https://oauth2:{TOK}@git.example.test/o/r.git"], TOK),
    # the form the baseline test covers, but run the way agents run everything: through a shell
    ("wrapper", ["bash", "-c", f"tool --api-key {TOK} --max-tokens 4096"], TOK),
    ("wrapper", ["cmd.exe", "/d", "/s", "/c", f"tool.exe --password {PW}"], PW),
    ("wrapper", ["sh", "-c", f"curl -u alice:{PW} {HOST}"], PW),
    ("wrapper", ["bash", "-c", f"DEBUG=1 API_TOKEN={TOK} ./run.sh"], TOK),
    ("wrapper", ["sh", "-c", f"echo {PW} | sudo -S apt-get update"], PW),
    ("wrapper", ["cmd.exe", "/c", f'curl -H "{BEARER}" {HOST}'], TOK),
    ("wrapper", ["powershell", "-Command", f"$p = ConvertTo-SecureString '{PW}' -AsPlainText"], PW),
    ("wrapper", ["pwsh", "-c", f"docker login -u alice -p {PW}"], PW),
    ("wrapper", ["wsl.exe", "-e", "bash", "-c", f"mysql -p{PW} appdb"], PW),
    ("wrapper", ["python", "-c", f"import r; r.get('{HOST}', headers={{'X-Key': '{TOK}'}})"], TOK),
    ("wrapper ctrl", ["bash", "-lc", f"export API_TOKEN={TOK}; ./run.sh"], TOK),
    ("wrapper ctrl", ["cmd.exe", "/c", f"set PGPASSWORD={PW}&& psql"], PW),
    ("provider shape", ["tool", "login", "glpat-FAKEfakeFAKE01234567"], "glpat-FAKE"),
    ("provider shape", ["tool", "login", "rk_test_FAKEfake01234567"], "rk_test_FAKE"),
    ("provider shape", ["tool", "SG.FAKEfake0123456789ab.FAKEfake0123456789abcdefgh"], "SG.FAKE"),
    ("provider shape", ["bot", "123456789:AAFAKEfake0123456789FAKEfake01234"], "AAFAKE"),
    ("provider shape", ["vault", "login", "hvs.CAESFAKEfake0123456789FAKEfake01"], "hvs.CAES"),
    ("provider shape", ["az", "login", "-u", "app", "-p", f"FAKE~{TOK}.fake_Q", "-t", "x"], TOK),
    ("provider shape", ["gpg", "--batch", "correct-horse-battery-staple-FAKE-phrase"], "FAKE"),
    ("provider shape ctrl", ["tool", "login", f"github_pat_11{TOK}FAKEfake01234567"], TOK),
    ("provider shape ctrl", ["tool", "login", "ghp_FAKEfake0123456789FAKEfake"], "ghp_FAKE"),
    ("secret name", ["tool", "--auth", TOK], TOK),
    ("secret name", ["tool", "--key", TOK], TOK),
    ("secret name", ["tool", "--encryption-key", TOK], TOK),
    ("secret name", ["curl", "--cookie", f"sid={TOK}", HOST], TOK),
    ("secret name", ["gh", "secret", "set", "DEPLOY", "--body", PW], PW),
    ("secret name", ["openssl", "enc", "-aes-256-cbc", "-k", PW], PW),
    ("secret name", ["tool", "--pin", "4321"], "4321"),
]


def main() -> None:
    tally: Counter[tuple[str, str]] = Counter()
    for klass, args, secret in CASES:
        shown = " ".join(redact_cmdline(args))
        verdict = "LEAK" if secret in shown else "ok"
        tally[(klass, verdict)] += 1
        print(f"{verdict:<5}{klass:<21}{shown}")
    print()
    for klass in dict.fromkeys(name for name, _, _ in CASES):
        leaked, hidden = tally[(klass, "LEAK")], tally[(klass, "ok")]
        print(f"{klass:<21}{leaked} leaked, {hidden} hidden")
    plain = [case for case in CASES if not case[0].endswith("ctrl")]
    leaks = sum(count for (klass, verdict), count in tally.items() if verdict == "LEAK")
    print(f"\n{len(CASES)} cases, {len(plain)} of them not controls; {leaks} leaked in all")


if __name__ == "__main__":
    main()
