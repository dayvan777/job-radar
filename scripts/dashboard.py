#!/usr/bin/env python3
"""Build dashboard.html (static, opens in any browser) from data/*.json.
Visual reference: Nixtio "Crextio HR Management Dashboard" (dribbble.com/shots/25121521),
the most-liked dashboard shot in Dribbble's popular dashboard search on 2026-11-01.
Run from the project root: python3 scripts/dashboard.py"""
import json, os, html, datetime, collections, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today()
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
          "сентябрь", "октябрь", "ноябрь", "декабрь"]
MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
              "сентября", "октября", "ноября", "декабря"]
WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def load(c):
    p = os.path.join(ROOT, "data", f"{c}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


jobs, events, signals, postings = load("jobs"), load("events"), load("signals"), load("postings")
meta = load("meta").get("run", {})
insights = load("insights")
profile = insights.get("profile", {})
market = insights.get("market", {})
strategy = insights.get("strategy", {})
projects, conferences, courses = load("projects"), load("conferences"), load("courses")
app = load("apps").get("app", {})  # optional, filled by scripts/appstore.py
first_name = profile.get("firstName") or ""
full_name = profile.get("name") or first_name
city = profile.get("city") or ""
PHOTO = "cv/tpl/photo.jpg" if os.path.exists(os.path.join(ROOT, "cv", "tpl", "photo.jpg")) else ""
initials = "".join(w[0] for w in full_name.split()[:2]).upper() or "JR"
e = lambda s: html.escape(str(s if s is not None else ""))


def date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def ru_date(d):
    return f"{d.day} {MONTHS_GEN[d.month - 1]}" if d else ""


def plural(n, one, few, many):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def arrow(href):
    return f'<a class="circ" href="{e(href)}" aria-label="Открыть"><svg viewBox="0 0 16 16"><path d="M5 11 11 5M6 5h5v5"/></svg></a>'


# ---------- jobs pipeline ----------
def bucket(j):
    st = j.get("status", "new")
    if st in ("applied", "interview", "offer"):
        return "sent"
    if st in ("rejected", "skipped") or (j.get("score") or 0) < 75:
        return "below"
    return "blocked" if (j.get("apply") or {}).get("autoSkip") else "ready"


B_LABEL = {"sent": "Отклики", "blocked": "Ждут тебя", "ready": "В очереди", "below": "Ниже порога"}
by_bucket = collections.Counter(bucket(j) for j in jobs.values())
seg_html = ""
total = max(len(jobs), 1)
for b in ("sent", "blocked", "ready", "below"):
    n = by_bucket.get(b, 0)
    if n:
        seg_html += (f'<div class="seg" style="flex:{max(n / total, .12):.3f}"><span class="seg-l">{B_LABEL[b]}</span>'
                     f'<span class="seg-p s-{b}">{n}</span></div>')
sent_n = sum(1 for j in jobs.values() if bucket(j) == "sent")

# ---------- checklist (computed from real state) ----------
todo = []


def trust_ok():
    try:
        d = json.load(open(os.path.expanduser("~/.claude.json"), encoding="utf-8"))
        return bool(d.get("projects", {}).get(ROOT, {}).get("hasTrustDialogAccepted"))
    except (OSError, ValueError):
        return False


def sleep_ok():
    try:
        out = subprocess.run(["pmset", "-g"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[0] == "sleep":
                return parts[1] == "0"
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return False


djinni_blocked = [j["company"] for j in jobs.values()
                  if "verify your e-mail" in str((j.get("apply") or {}).get("autoSkip", "")) and j.get("status") == "new"]
djinni_terms = [j["company"] for j in jobs.values()
                if "Start search" in str((j.get("apply") or {}).get("autoSkip", "")) and j.get("status") == "new"]
if djinni_blocked:
    todo.append(("Подтвердить почту на Djinni и заполнить профиль", "Откроет отклики: " + ", ".join(djinni_blocked), False))
djinni_mod = [j["company"] for j in jobs.values()
              if "на модерации" in str((j.get("apply") or {}).get("autoSkip", "")) and j.get("status") == "new"]
if djinni_terms:
    todo.append(("Djinni: принять условия и включить «Start search»", "Откроет отклики: " + ", ".join(djinni_terms[:3]) + (" и др." if len(djinni_terms) > 3 else ""), False))
elif djinni_mod:
    todo.append(("Djinni: условия приняты, профиль на модерации", "Ждём одобрения, потом уйдут " + ", ".join(djinni_mod), True))
for jid, j in sorted(jobs.items(), key=lambda kv: -(kv[1].get("score") or 0)):
    skip = str((j.get("apply") or {}).get("autoSkip", ""))
    if bucket(j) != "blocked" or "verify your e-mail" in skip or "Start search" in skip or "на модерации" in skip:
        continue
    if "compensation" in skip:
        todo.append((f"{j['company']}: зарплатные ожидания", "Сумма и валюта для обязательного поля формы", False))
    elif "Eintrittstermin" in skip:
        until = (j.get("apply") or {}).get("validThrough")
        todo.append((f"{j['company']}: дата выхода и «отправляй»",
                     f"Eintrittstermin для письма{', отклики до ' + ru_date(date(until)) if until else ''}", False))
    elif "Решение за тобой" in skip:
        todo.append((f"{j['company']}: подаваться или нет", "Пакет готов, условия спорные", False))
    else:
        todo.append((f"{j['company']}: {skip[:48]}", "", False))
todo.append(("Доверить папку проекта в Claude", "Запусти claude в папке проекта и прими диалог", trust_ok()))
todo.append(("Отключить сон Mac", "Иначе почасовые прогоны не стартуют", sleep_ok()))
todo_done = sum(1 for t in todo if t[2])
todo_html = "".join(
    f'<li class="{"done" if ok else ""}"><span class="ti"><svg viewBox="0 0 16 16"><path d="M4 8.5 7 11l5-6"/></svg></span>'
    f'<span><b>{e(t)}</b><small>{e(s)}</small></span></li>' for t, s, ok in todo)

# ---------- activity (vacancies scanned per day, last 7 days) ----------
per_day = collections.defaultdict(int)
for h in meta.get("history", []):
    d = date(h.get("at"))
    if d:
        per_day[d] = max(per_day[d], int(h.get("scanned") or 0))
days = [TODAY - datetime.timedelta(days=i) for i in range(6, -1, -1)]
vals = [per_day.get(d, 0) for d in days]
vmax = max(vals + [1])
bars = ""
for d, v in zip(days, vals):
    hpct = max(v / vmax * 100, 4)
    cls = "bar today" if d == TODAY else ("bar" if v else "bar zero")
    tip = f'<span class="bar-tip">{v}</span>' if d == TODAY or v == vmax and v else ""
    bars += (f'<div class="bcol" title="{ru_date(d)}: {v} просмотрено"><div class="btrack"><div class="{cls}" style="height:{hpct:.0f}%">{tip}</div></div>'
             f'<span>{WD[d.weekday()]}</span></div>')
week_total = sum(vals)

# ---------- ring: own app rating if configured, else best fit ----------
rating = app.get("rating") or 0
best_fit = max([min(j.get("score") or 0, 100) for j in jobs.values()] + [0])
ticks = ""
N = 60
filled = round(N * rating / 5) if app else round(N * best_fit / 100)
for i in range(N):
    ticks += f'<line class="{"on" if i < filled else ""}" x1="60" y1="7" x2="60" y2="15" transform="rotate({i * 6} 60 60)"/>'
nav_rank = app.get("navRank")

# ---------- learning progress ----------
c_status = collections.Counter((c.get("status") or "todo") for c in courses.values())
c_tot = max(len(courses), 1)
c_done, c_doing, c_todo = c_status.get("done", 0), c_status.get("doing", 0), c_status.get("todo", 0)
learn_pct = round(100 * c_done / c_tot) if courses else 0

# ---------- top jobs accordion ----------
acc = ""
top = [j for j in sorted(jobs.values(), key=lambda j: -(j.get("score") or 0)) if bucket(j) != "below"][:5]
for i, j in enumerate(top):
    ap = j.get("apply") or {}
    state = "Отклик отправлен" if bucket(j) == "sent" else (ap.get("autoSkip") or "Пакет готов, в очереди")
    cv = j.get("cvUrl")
    acc += (f'<details {"open" if i == 0 else ""}><summary><span>{e(j.get("company"))}</span><em>{j.get("score", "")}</em></summary>'
            f'<div class="acc-b"><a href="{e(j.get("url"))}" target="_blank">{e(j.get("title"))}</a>'
            f'<p>{e(state[:220])}</p>{f"<a class=pill-s href={e(cv)}>CV</a>" if cv else ""}</div></details>')

# ---------- events timeline (next 4 months) ----------
start = TODAY.replace(day=1)
end_m = (start.month + 2) % 12 + 1
end = start.replace(year=start.year + (start.month + 2) // 12, month=end_m)
span = (end - start).days
dated = sorted([c for c in conferences.values() if c.get("datesConfirmed") and date(c.get("start")) and start <= date(c.get("start")) < end
                and (date(c.get("end")) or date(c.get("start"))) >= TODAY], key=lambda c: c["start"])
month_cols = ""
m = start
while m < end:
    nm = m.replace(year=m.year + m.month // 12, month=m.month % 12 + 1)
    month_cols += f'<div class="tl-m" style="left:{(m - start).days / span * 100:.2f}%"><span>{MONTHS[m.month - 1]}</span></div>'
    m = nm
today_x = (TODAY - start).days / span * 100
rows = ""
for c in dated[:4]:
    s, en = date(c["start"]), date(c.get("end")) or date(c["start"])
    left = (s - start).days / span * 100
    width = max(((en - s).days + 1) / span * 100, 1)
    side = "r" if left > 55 else "l"
    rows += (f'<div class="tl-row"><a class="tl-p {"wk" if c.get("weekend") else ""} side-{side}" href="{e(c.get("url"))}" target="_blank" '
             f'style="--x:{left:.2f}%;--w:{width:.2f}%"><i></i><span><b>{e(c.get("name"))}</b><small>{ru_date(s)} · {e(c.get("city"))}</small></span></a></div>')
weekend_n = sum(1 for c in dated if c.get("weekend"))
next_ev = dated[0] if dated else None
days_to = (date(next_ev["start"]) - TODAY).days if next_ev else None

# ---------- application status tracker ----------
STAGES = ["Отправлен", "Ответ", "Интервью", "Оффер"]
CHANNEL = {"email": "Email", "dou": "DOU", "djinni": "Djinni", "site": "Сайт компании"}


def stage_of(j):
    st = j.get("status")
    if st == "offer":
        return 3
    if st == "interview":
        return 2
    return 1 if j.get("reply") else 0


apps = [j for j in jobs.values() if j.get("status") in ("applied", "interview", "offer", "rejected")]
apps.sort(key=lambda j: str((j.get("apply") or {}).get("sentAt") or ""), reverse=True)
replied_n = sum(1 for j in apps if j.get("reply") or j.get("status") in ("interview", "offer", "rejected"))
app_rows = ""
for j in apps:
    ap = j.get("apply") or {}
    sent = ap.get("sentAt")
    sd = date(sent)
    when = (f"{ru_date(sd)}, {str(sent)[11:16]}" if sd else "дата не записана")
    waited = (TODAY - sd).days if sd else None
    ch = CHANNEL.get(ap.get("method"), ap.get("method") or "")
    if ap.get("method") == "site" and "PeopleForce" in str(ap.get("sentNote", "")):
        ch = "PeopleForce"
    if not sd and "уже был отклик" in str(ap.get("note", "")) + str(j.get("why", "")):
        ch = "Сам, сайт компании"
    rejected = j.get("status") == "rejected"
    cur = stage_of(j)
    steps = ""
    for i, name in enumerate(STAGES):
        cls = "done" if i < cur else ("cur" if i == cur and not rejected else "")
        if rejected and i == cur:
            cls, name = "rej", "Отказ"
        steps += f'<span class="sp {cls}">{name}</span>'
    if rejected:
        nxt = e(j.get("reply") or "Отказ")
    elif cur == 0:
        fu = sd + datetime.timedelta(days=14) if sd else None
        nxt = ("ждём ответа" + (f"; follow-up {ru_date(fu)}" if fu and ap.get("method") == "email" else
                                (f"; без ответа к {ru_date(fu)} отметка «тишина»" if fu else "")))
    else:
        nxt = e(j.get("reply") or "")
    rv = (ap.get("review") or {}).get("wouldInterview")
    links = f'<a href="{e(j.get("url"))}" target="_blank">вакансия</a>'
    if ap.get("threadId"):
        links += f' · <a href="https://mail.google.com/mail/u/0/#all/{e(ap["threadId"])}" target="_blank">письмо</a>'
    app_rows += (f'<div class="ap"><div class="ap-h"><b>{e(j.get("company"))}</b><small>{e(j.get("title"))}</small></div>'
                 f'<div class="ap-m"><span class="pill-s">{e(ch)}</span><span class="sub">{e(when)}'
                 f'{f" · {waited} дн." if waited else (" · сегодня" if waited == 0 else "")}{f" · ревью {rv}/5" if rv else ""}</span></div>'
                 f'<div class="ap-s">{steps}</div><div class="ap-n"><span class="sub">{nxt}</span><span class="sub">{links}</span></div></div>')
queued = [j for j in jobs.values() if j.get("status") == "new" and "на модерации" in str((j.get("apply") or {}).get("autoSkip", ""))]
for j in sorted(queued, key=lambda j: -(j.get("score") or 0)):
    app_rows += (f'<div class="ap ap-q"><div class="ap-h"><b>{e(j.get("company"))}</b><small>{e(j.get("title"))}</small></div>'
                 f'<div class="ap-m"><span class="pill-s yl">Djinni</span><span class="sub">в очереди · приоритет {j.get("score", "")}</span></div>'
                 f'<div class="ap-s"><span class="sp q">Профиль на модерации</span></div>'
                 f'<div class="ap-n"><span class="sub">уйдёт после одобрения профиля, по дневному лимиту</span>'
                 f'<span class="sub"><a href="{e(j.get("url"))}" target="_blank">вакансия</a></span></div></div>')
sent_today = sum(1 for j in apps if date((j.get("apply") or {}).get("sentAt")) == TODAY)

# ---------- full jobs list ----------
STATUS = {"new": "Новая", "applied": "Отклик", "interview": "Интервью", "offer": "Оффер",
          "rejected": "Отказ", "skipped": "Пропуск"}
job_rows = ""
for jid, j in sorted(jobs.items(), key=lambda kv: -(kv[1].get("score") or 0)):
    ap = j.get("apply") or {}
    b = bucket(j)
    gaps = j.get("gaps")
    gaps = ", ".join(gaps) if isinstance(gaps, list) else str(gaps or "")
    cv = j.get("cvUrl")
    job_rows += f"""<div class="jr b-{b}"><div class="jr-s">{j.get('score', '')}</div>
<div class="jr-m"><a href="{e(j.get('url'))}" target="_blank">{e(j.get('title'))}</a>
<div class="sub">{e(j.get('company'))} · {e(j.get('source'))} · {e(j.get('remote') or j.get('region') or '')}</div>
<p>{e(j.get('why'))}</p>{f'<p class="gap">Пробел: {e(gaps)}</p>' if gaps else ''}</div>
<div class="jr-r"><span class="pill-st st-{b}">{B_LABEL[b] if b != 'below' else STATUS.get(j.get('status', 'new'), '')}</span>
{f'<a class="pill-s" href="{e(cv)}">CV</a>' if cv else ''}{f'<p class="sub">{e(ap.get("autoSkip"))}</p>' if ap.get('autoSkip') and b == 'blocked' else ''}</div></div>"""

# ---------- strategy ----------
strat = ""
for i, s in enumerate(strategy.get("items", [])):
    ev = f'<p class="sub">Основание: {e(s["evidence"])}</p>' if s.get("evidence") else ""
    when = f'<span class="pill-s">{e(s["when"])}</span>' if s.get("when") else ""
    strat += f'<div class="st-c"><span class="st-n">{i + 1:02d}</span><h3>{e(s.get("title"))}</h3><p>{e(s.get("text"))}</p>{ev}{when}</div>'

# ---------- courses ----------
C_ST = {"todo": "Впереди", "doing": "В процессе", "done": "Готово"}
course_html, course_more = "", ""
for i, c in enumerate(sorted(courses.values(), key=lambda c: c.get("order", 99))):
    st = c.get("status") or "todo"
    cost = "бесплатно" if str(c.get("cost", "")).lower().startswith("free") else c.get("cost")
    meta_bits = " · ".join(x for x in [c.get("provider"), cost, f'{c["hours"]} ч' if c.get("hours") else None,
                                       "сертификат" if c.get("certificate") else None] if x)
    card = (f'<a class="co c-{st}" href="{e(c.get("url"))}" target="_blank"><span class="co-n">{c.get("order", "")}</span>'
            f'<span class="co-b"><span class="tag">{e(c.get("gap"))}</span><b>{e(c.get("title"))}</b>'
            f'<small>{e(meta_bits)}</small><em>{e(c.get("why"))}</em></span><span class="pill-st st-c{st}">{C_ST.get(st, st)}</span></a>')
    if i < 6 or st != "todo":
        course_html += card
    else:
        course_more += card

# ---------- conferences list ----------
def conf_date(c):
    return date(c.get("start")) if c.get("datesConfirmed") else None


def conf_key(c):
    d = conf_date(c)
    if d:
        return (0, d)
    em = date((c.get("expectedMonth") or "") + "-01")
    return (1, em) if em else (2, datetime.date(2099, 12, 1))


conf_html = ""
for c in sorted(conferences.values(), key=conf_key):
    d = conf_date(c)
    if d and (date(c.get("end")) or d) < TODAY:
        continue
    if d:
        top_l, big = MONTHS[d.month - 1][:3], str(d.day)
    elif date((c.get("expectedMonth") or "") + "-01"):
        em = date(c["expectedMonth"] + "-01")
        top_l, big = f"ожид. {em.year}", MONTHS[em.month - 1][:3]
    elif c.get("recurring"):
        top_l, big = "регулярно", "↻"
    else:
        top_l, big = "дата", "?"
    pills = "".join(f'<span class="pill-s {k}">{e(t)}</span>' for t, k in [
        ("выходные" if c.get("weekend") else "будни", "dk" if c.get("weekend") else ""),
        (f'{c.get("kmFromHome")} км' if c.get("kmFromHome") is not None else "", ""),
        (c.get("price") or "", ""), ("есть карьерная зона" if c.get("careerArea") else "", "yl"),
        ("дата не подтверждена" if not c.get("datesConfirmed") and not c.get("recurring") else "", "")] if t)
    conf_html += (f'<a class="cf" href="{e(c.get("url"))}" target="_blank"><span class="cf-d"><small>{top_l}</small><b>{big}</b></span>'
                  f'<span class="cf-b"><b>{e(c.get("name"))}</b><small>{e(c.get("city"))}{" · " + e(c.get("recurring")) if c.get("recurring") else ""}</small>'
                  f'<em>{e(c.get("why"))}</em><span class="pills">{pills}</span></span></a>')

# ---------- market ----------
cut = (TODAY - datetime.timedelta(days=60)).isoformat()
cnt, n_sig = collections.Counter(), 0
for s in signals.values():
    if str(s.get("date", "")) >= cut:
        n_sig += 1
        cnt.update(set(s.get("skills") or []))
have, partial = set(profile.get("have") or []), set(profile.get("partial") or [])
skills_html = ""
for k, v in cnt.most_common(14):
    pct = round(100 * v / max(n_sig, 1))
    st = "have" if k in have else ("part" if k in partial else "gap")
    word = {"have": "есть", "part": "частично", "gap": "пробел"}[st]
    skills_html += (f'<div class="sk" title="{e(k)}: {v} из {n_sig} вакансий"><span class="sk-n">{e(k)}</span>'
                    f'<span class="sk-t"><span class="sk-b sk-{st}" style="width:{pct}%"></span><span class="sk-v">{pct}%</span></span>'
                    f'<span class="sk-w w-{st}">{word}</span></div>')
sal_html = "".join(
    f'<div class="sal"><small>{e(s.get("label"))}</small><b>{e(s.get("value"))}</b>'
    f'<span class="sub">{e(s.get("note"))} · <a href="{e(s.get("url"))}" target="_blank">источник</a></span></div>'
    for s in market.get("salaryCards", []))
chan_html = "".join(
    f'<li><a href="{e(c.get("url"))}" target="_blank">{e(c.get("name"))}</a><span class="sub">{e(c.get("note") or "")}</span></li>'
    for c in market.get("channelCards", []))
lead_html = ""
for l in market.get("leads", []):
    pay = f'<span class="pill-s yl">{e(l["salary"])}</span>' if l.get("salary") else ""
    v = {"fit": ("dk", "подходит"), "sent": ("dk", "отклик отправлен"), "no": ("", "не подходит"), "maybe": ("yl", "под вопросом")}.get(l.get("verdict"))
    vpill = f'<span class="pill-s {v[0]}">{v[1]}</span>' if v else ""
    vnote = f'<em class="vn">{e(l["verdictNote"])}</em>' if l.get("verdictNote") else ""
    lead_html += (f'<a class="ld {"ld-no" if l.get("verdict") == "no" else ""}" href="{e(l.get("url"))}" target="_blank"><span><b>{e(l.get("title"))}</b>'
                  f'<small>{e(l.get("company"))} · {e(l.get("city"))}</small><em>{e(l.get("note"))}</em>{vnote}</span>'
                  f'<span class="ld-p">{vpill}{pay}</span></a>')

# ---------- own app section (optional) ----------
hist = app.get("history", [])
spark = ""
pts = [(h["date"], h["navRank"]) for h in hist if h.get("navRank")]
if len(pts) >= 2:
    worst = max(r for _, r in pts)
    W, H = 300, 70
    xy = [(i * W / (len(pts) - 1), 6 + (r - 1) / max(worst - 1, 1) * (H - 12)) for i, (_, r) in enumerate(pts)]
    spark = (f'<svg class="spark" viewBox="0 0 {W} {H}" preserveAspectRatio="none"><polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in xy)}"/>'
             f'<circle cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="4"/></svg><p class="sub">Место в топе бесплатных «{e(app.get("genreName", ""))}», {e(app.get("country", ""))}. Выше линия, выше место.</p>')
else:
    spark = f'<p class="sub">История места в топе копится с {ru_date(date(hist[0]["date"])) if hist else "первого прогона"}: каждый прогон добавляет точку.</p>'
lead = "".join(
    f'<li class="{"me" if t.get("self") else ""}"><span>{t["rank"]}</span>{e(t["name"])}</li>' for t in app.get("navTop", []))
press = "".join(f'<a class="pill-s" href="{e(p["url"])}" target="_blank">{e(p["title"])}</a>' for p in app.get("press", []))

# ---------- projects ----------
P_ST = {"active": "в работе", "idea": "идея", "done": "готово"}
proj_html = ""
for pid, p in sorted(projects.items(), key=lambda kv: kv[1].get("status") != "active"):
    closes = f'<p class="sub">Закрывает: {e(", ".join(p["skills"]))}</p>' if p.get("skills") else ""
    proj_html += (f'<div class="pj"><span class="pill-st st-p{e(p.get("status"))}">{P_ST.get(p.get("status"), e(p.get("status")))}</span>'
                  f'<b>{e(p.get("title", pid))}</b><small>{e(p.get("stack", ""))} · {e(p.get("hours", ""))}</small>'
                  f'<p>{e(p.get("pitch", ""))}</p>{closes}</div>')

hist_rows = "".join(
    f"<tr><td>{e(h.get('at', '')[:16].replace('T', ' '))}</td><td class='num'>{e(h.get('scanned', ''))}</td><td class='num'>{e(h.get('added', ''))}</td>"
    f"<td class='num'>{e(h.get('sent', ''))}</td><td>{e(h.get('note', ''))}</td></tr>"
    for h in reversed(meta.get("history", [])[-30:]))

CSS = """
:root{--ink:#1d1d1b;--ink2:#5f5f5b;--mut:#9b9b96;--dark:#2b2b2a;--dark2:#3a3a38;--yl:#f4d35e;--yl2:#fbe9a8;
--card:rgba(255,255,255,.66);--card2:rgba(255,255,255,.88);--line:rgba(29,29,27,.08);--r:26px;color-scheme:light}
*{box-sizing:border-box}
html{background:#ecebe8}
body{margin:0;min-height:100vh;color:var(--ink);font:15px/1.45 Onest,ui-sans-serif,system-ui,sans-serif;
background:radial-gradient(1100px 620px at 92% -8%,rgba(250,221,118,.55),transparent 62%),
radial-gradient(900px 700px at 100% 70%,rgba(251,233,168,.45),transparent 60%),
linear-gradient(115deg,#ecebe8 0%,#efeee9 42%,#f6f0da 78%,#f8edc4 100%);background-attachment:fixed}
a{color:inherit}
.wrap{max-width:1360px;margin:0 auto;padding:22px 28px 60px}
header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logo{border:1.5px solid var(--ink2);border-radius:999px;padding:7px 18px;font-size:19px;font-weight:400;letter-spacing:-.01em}
nav{display:flex;gap:6px;margin-left:auto;overflow-x:auto;max-width:100%;scrollbar-width:none}
nav a{white-space:nowrap;text-decoration:none;font-size:13px;padding:9px 15px;border-radius:999px;background:var(--card2)}
nav a.on{background:var(--dark);color:#fff}
.who{display:flex;align-items:center;gap:8px}
.who .upd{font-size:12px;color:var(--ink2);background:var(--card2);border-radius:999px;padding:9px 14px;white-space:nowrap}
.who img{width:38px;height:38px;border-radius:50%;object-fit:cover;filter:grayscale(1)}
.who .av{width:38px;height:38px;border-radius:50%;background:var(--dark);color:#fff;display:grid;place-items:center;font-size:13px;font-weight:500}
.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:28px;flex-wrap:wrap;margin:34px 0 26px}
h1{font-weight:400;font-size:46px;letter-spacing:-.025em;margin:0 0 18px;line-height:1.05}
.hero>div:first-child{flex:1 1 480px;max-width:640px}
.pipe{display:flex;gap:8px;width:100%}
.seg{display:flex;flex-direction:column;gap:7px}
.seg-l{font-size:13px;color:var(--ink2);white-space:nowrap}
.seg-p{height:40px;border-radius:999px;display:flex;align-items:center;padding:0 16px;font-size:13px}
.s-sent{background:var(--dark);color:#fff}.s-blocked{background:var(--yl)}
.s-ready{background:repeating-linear-gradient(135deg,rgba(29,29,27,.16) 0 1.5px,transparent 1.5px 7px),rgba(255,255,255,.5)}
.s-below{border:1.5px solid rgba(29,29,27,.28)}
.stats{display:flex;gap:34px;flex-wrap:wrap}
.stat{display:flex;align-items:flex-end;gap:10px}
.stat b{font-weight:300;font-size:64px;line-height:.9;letter-spacing:-.03em}
.stat span{font-size:12px;color:var(--ink2);display:flex;flex-direction:column;gap:6px;padding-bottom:4px}
.stat svg{width:18px;height:18px;stroke:var(--ink2);fill:none;stroke-width:1.4;background:var(--card2);border-radius:50%;padding:3px}
.bento{display:grid;gap:16px;grid-template-columns:repeat(4,minmax(0,1fr));
grid-template-areas:"photo act ring side" "acc cal cal side";grid-template-rows:310px 330px}
.card{background:var(--card);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-radius:var(--r);padding:20px 22px;position:relative;min-width:0}
.card h2{font-size:21px;font-weight:400;margin:0;letter-spacing:-.01em}
.circ{position:absolute;top:16px;right:16px;width:38px;height:38px;border-radius:50%;background:var(--card2);display:grid;place-items:center}
.circ svg{width:15px;height:15px;stroke:var(--ink);fill:none;stroke-width:1.6;stroke-linecap:round}
.photo{grid-area:photo;padding:0;overflow:hidden;background:#cfcfcb}
.photo img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 25%;filter:grayscale(1) contrast(1.02)}
.photo .ph-i{position:absolute;inset:0;display:grid;place-items:center;font-size:96px;font-weight:300;letter-spacing:-.04em;color:var(--ink2);background:linear-gradient(160deg,var(--yl2),#cfcfcb)}
.photo .ov{position:absolute;inset:auto 0 0 0;padding:70px 18px 18px;background:linear-gradient(transparent,rgba(20,20,20,.62));color:#fff;display:flex;align-items:flex-end;justify-content:space-between;gap:10px}
.photo .ov b{font-weight:500;font-size:19px;display:block}.photo .ov small{opacity:.8;font-size:12px}
.photo .ov .glass{border:1px solid rgba(255,255,255,.55);border-radius:999px;padding:8px 14px;font-size:13px;white-space:nowrap;backdrop-filter:blur(6px)}
.act{grid-area:act;display:flex;flex-direction:column}
.big{display:flex;align-items:baseline;gap:10px;margin:14px 0 0}
.big b{font-size:40px;font-weight:300;letter-spacing:-.02em}.big span{font-size:12px;color:var(--ink2);line-height:1.25}
.bars{flex:1;display:flex;gap:10px;align-items:stretch;margin-top:8px;padding-top:24px}
.bcol{flex:1;display:flex;flex-direction:column;align-items:center;gap:8px;font-size:12px;color:var(--mut)}
.btrack{flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center;
background:radial-gradient(circle,rgba(29,29,27,.14) 1px,transparent 1.4px) center/100% 7px repeat-y}
.bar{width:8px;background:var(--dark);border-radius:4px;position:relative}
.bar.zero{background:rgba(29,29,27,.12)}.bar.today{background:var(--yl);width:10px}
.bar-tip{position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:var(--yl);border-radius:999px;padding:3px 8px;font-size:11px;color:var(--ink);white-space:nowrap}
.ring{grid-area:ring;display:flex;flex-direction:column}
.ring .rv{flex:1;display:grid;place-items:center;position:relative}
.ring svg.dial{width:min(170px,100%);height:auto}
.dial line{stroke:rgba(29,29,27,.14);stroke-width:2.2;stroke-linecap:round}.dial line.on{stroke:var(--yl)}
.ring .ctr{position:absolute;text-align:center}.ring .ctr b{font-size:32px;font-weight:400;display:block;letter-spacing:-.02em}
.ring .ctr small{font-size:11px;color:var(--ink2)}
.ring .rb{display:flex;gap:8px;align-items:center}
.pill-s{display:inline-flex;align-items:center;gap:6px;font-size:12px;padding:6px 12px;border-radius:999px;background:var(--card2);text-decoration:none;white-space:nowrap}
.pill-s.dk{background:var(--dark);color:#fff}.pill-s.yl{background:var(--yl2)}
.rb .go{margin-left:auto;width:38px;height:38px;border-radius:50%;background:var(--dark);display:grid;place-items:center}
.rb .go svg{width:15px;height:15px;stroke:#fff;fill:none;stroke-width:1.6;stroke-linecap:round}
.side{grid-area:side;display:flex;flex-direction:column;gap:12px;min-width:0}
.learn .pct{position:absolute;top:16px;right:22px;font-size:34px;font-weight:300;letter-spacing:-.02em}
.lbars{display:flex;gap:6px;margin-top:18px}
.lbars div{display:flex;flex-direction:column;gap:6px;font-size:12px;color:var(--ink2);white-space:nowrap}
.lbars i{height:34px;border-radius:999px;display:flex;align-items:center;padding:0 12px;font-style:normal;font-size:12px}
.lb-done{background:var(--yl)}.lb-doing{background:var(--dark);color:#fff}.lb-todo{background:rgba(29,29,27,.22)}
.todo{flex:1;background:var(--dark);color:#fff;border-radius:var(--r);padding:20px 18px;min-height:0;overflow:auto}
.todo .th{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
.todo h2{font-size:19px;font-weight:400;margin:0}.todo .th b{font-size:30px;font-weight:300}
.todo ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
.todo li{display:flex;gap:11px;align-items:flex-start}
.todo li b{font-weight:400;font-size:14px;display:block}.todo li small{color:#a9a9a4;font-size:12px}
.ti{flex:none;width:30px;height:30px;border-radius:50%;border:1.5px solid #5b5b58;display:grid;place-items:center}
.ti svg{width:14px;height:14px;stroke:transparent;fill:none;stroke-width:2;stroke-linecap:round}
.todo li.done .ti{background:var(--yl);border-color:var(--yl)}.todo li.done .ti svg{stroke:var(--dark)}
.todo li.done b{color:#a9a9a4;text-decoration:line-through}
.acc{grid-area:acc;overflow:auto;padding:12px 18px}
details{border-bottom:1px solid var(--line);padding:10px 0}details:last-child{border:0}
summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;font-size:15px}
summary::-webkit-details-marker{display:none}
summary em{font-style:normal;font-size:12px;color:var(--ink2);display:flex;align-items:center;gap:8px}
summary em::after{content:"";width:7px;height:7px;border-right:1.5px solid var(--ink2);border-bottom:1.5px solid var(--ink2);transform:rotate(45deg);margin:-3px 2px 0}
details[open] summary em::after{transform:rotate(-135deg);margin-top:3px}
.acc-b{padding-top:8px;font-size:13px}.acc-b a{font-weight:500}.acc-b p{margin:6px 0 8px;color:var(--ink2)}
.cal{grid-area:cal;display:flex;flex-direction:column;overflow:hidden}
.cal .ch{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
.tl{position:relative;flex:1;margin-top:12px;padding-top:26px;overflow:hidden}
.tl-m{position:absolute;top:0;bottom:0;border-left:1px solid var(--line)}
.tl-m span{position:absolute;top:0;left:8px;font-size:12px;color:var(--ink2);text-transform:capitalize}
.tl-now{position:absolute;top:22px;bottom:0;border-left:1.5px solid var(--ink)}
.tl-now::before{content:"сегодня";position:absolute;bottom:-2px;left:4px;font-size:10px;background:var(--dark);color:#fff;border-radius:999px;padding:1px 6px}
.tl-row{position:relative;height:45px}
.tl-p{position:absolute;top:3px;text-decoration:none;display:flex;align-items:center;gap:8px}
.tl-p.side-l{left:var(--x)}.tl-p.side-r{right:calc(100% - var(--x) - var(--w));flex-direction:row-reverse;text-align:right}
.tl-p i{width:max(var(--wpx,10px),10px);height:10px;border-radius:999px;background:#fff;border:1.5px solid var(--dark);flex:none}
.tl-p.wk i{background:var(--dark)}
.tl-p span{background:var(--card2);border-radius:14px;padding:4px 10px;max-width:250px}
.tl-p.wk span{background:var(--dark);color:#fff}
.tl-p b{font-weight:500;font-size:12px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tl-p small{font-size:11px;opacity:.7;white-space:nowrap}
.lg{display:flex;gap:12px;font-size:12px;color:var(--ink2)}.lg i{display:inline-block;width:10px;height:10px;border-radius:50%;border:1.5px solid var(--dark);margin-right:5px;vertical-align:-1px}
.lg i.f{background:var(--dark)}
section{margin-top:48px}
.sh{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.sh h2{font-size:30px;font-weight:400;letter-spacing:-.02em;margin:0}.sh p{margin:0;color:var(--ink2);font-size:14px;max-width:560px}
.sub{color:var(--ink2);font-size:12px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.st-c{background:var(--card);border-radius:var(--r);padding:22px}
.st-n{font-size:13px;color:var(--ink2);border:1.5px solid rgba(29,29,27,.25);border-radius:999px;padding:3px 10px}
.st-c h3{font-weight:500;font-size:17px;margin:14px 0 6px}.st-c p{margin:0 0 10px;font-size:14px;color:var(--ink2)}
.jl{background:var(--card);border-radius:var(--r);padding:6px 22px}
.jr{display:grid;grid-template-columns:64px minmax(0,1fr) 240px;gap:18px;padding:16px 0;border-bottom:1px solid var(--line)}
.jr:last-child{border:0}.jr-s{font-size:34px;font-weight:300;letter-spacing:-.02em;line-height:1}
.jr-m a{font-weight:500;font-size:16px;text-decoration:none}.jr-m a:hover{text-decoration:underline}
.jr-m p{margin:6px 0 0;font-size:13px}.jr-m .gap{color:#9a6a00}
.jr-r{display:flex;flex-direction:column;align-items:flex-start;gap:8px}.jr-r p{margin:0}
.b-below{opacity:.62}
.pill-st{font-size:12px;padding:6px 12px;border-radius:999px;white-space:nowrap;display:inline-block}
.st-sent{background:var(--dark);color:#fff}.st-blocked{background:var(--yl)}
.st-ready{background:repeating-linear-gradient(135deg,rgba(29,29,27,.16) 0 1.5px,transparent 1.5px 7px),#fff}
.st-below{border:1.5px solid rgba(29,29,27,.25)}
.st-ctodo{border:1.5px solid rgba(29,29,27,.25)}.st-cdoing{background:var(--dark);color:#fff}.st-cdone{background:var(--yl)}
.st-pactive{background:var(--dark);color:#fff}.st-pidea{border:1.5px solid rgba(29,29,27,.25)}.st-pdone{background:var(--yl)}
.co-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.co{display:flex;gap:16px;align-items:flex-start;background:var(--card);border-radius:22px;padding:18px 20px;text-decoration:none}
.co:hover,.cf:hover{background:var(--card2)}
.co-n{flex:none;width:36px;height:36px;border-radius:50%;background:var(--dark);color:#fff;display:grid;place-items:center;font-size:14px}
.co-b{flex:1;display:flex;flex-direction:column;gap:3px;min-width:0}.co-b b{font-weight:500}
.co-b small{color:var(--ink2);font-size:12px}.co-b em{font-style:normal;font-size:13px;color:var(--ink2)}
.tag{align-self:flex-start;font-size:11px;background:var(--yl2);border-radius:999px;padding:2px 9px;margin-bottom:3px}
.cf-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.cf{display:flex;gap:16px;background:var(--card);border-radius:22px;padding:16px 18px;text-decoration:none}
.cf-d{flex:none;width:62px;height:66px;border-radius:18px;background:var(--card2);display:flex;flex-direction:column;align-items:center;justify-content:center}
.cf-d small{font-size:11px;color:var(--ink2)}.cf-d b{font-size:24px;font-weight:400;line-height:1.1}
.cf-b{display:flex;flex-direction:column;gap:3px;min-width:0}.cf-b b{font-weight:500}.cf-b small{color:var(--ink2);font-size:12px}
.cf-b em{font-style:normal;font-size:13px;color:var(--ink2)}.pills{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.mk{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:16px}
.sk{display:grid;grid-template-columns:170px minmax(0,1fr) 74px;gap:12px;align-items:center;padding:6px 0;font-size:13px}
.sk-t{position:relative;height:14px;display:flex;align-items:center;gap:8px}
.sk-b{display:block;height:10px;border-radius:0 4px 4px 0}.sk-v{font-size:12px;color:var(--ink2);font-variant-numeric:tabular-nums}
.sk-have{background:var(--dark)}.sk-gap{background:var(--yl)}
.sk-part{background:repeating-linear-gradient(135deg,rgba(29,29,27,.55) 0 1.5px,transparent 1.5px 5px),rgba(29,29,27,.1)}
.sk-w{font-size:12px}.w-gap{font-weight:600}.w-have{color:var(--ink2)}
.sal{padding:12px 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:2px}.sal:last-child{border:0}
.sal small{font-size:12px;color:var(--ink2)}.sal b{font-size:22px;font-weight:400}
.mt{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:16px}
.mt-h{display:flex;gap:16px;align-items:center}.mt-h img{width:76px;height:76px;border-radius:18px}
.mt-k{display:flex;gap:28px;flex-wrap:wrap;margin:18px 0}.mt-k div{display:flex;flex-direction:column}
.mt-k b{font-size:36px;font-weight:300;letter-spacing:-.02em;line-height:1}.mt-k span{font-size:12px;color:var(--ink2);margin-top:4px}
.spark{width:100%;height:90px}.spark polyline{fill:none;stroke:var(--dark);stroke-width:2;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.spark circle{fill:var(--yl);stroke:#fff;stroke-width:2}
.lead{list-style:none;margin:14px 0 10px;padding:0;columns:2;column-gap:16px;font-size:13px}
.lead li{display:flex;gap:10px;align-items:center;padding:6px 10px;border-radius:999px;break-inside:avoid}
.lead li span{width:20px;color:var(--ink2);font-variant-numeric:tabular-nums}.lead li.me{background:var(--dark);color:#fff}.lead li.me span{color:var(--yl)}
.ld-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.ld{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;background:var(--card);border-radius:22px;padding:16px 18px;text-decoration:none}
.ld:hover{background:var(--card2)}.ld>span:first-child{display:flex;flex-direction:column;gap:3px;min-width:0}.ld b{font-weight:500}
.ld small{color:var(--ink2);font-size:12px}.ld em{font-style:normal;font-size:13px;color:var(--ink2)}
.ld em.vn{color:var(--ink);margin-top:4px}.ld-p{display:flex;flex-direction:column;align-items:flex-end;gap:6px}.ld-no{opacity:.6}
.chan{list-style:none;margin:10px 0 0;padding:0}.chan li{padding:9px 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:2px}
.chan li:last-child{border:0}.chan a{font-weight:500;text-decoration:none}.chan a:hover{text-decoration:underline}
details.more{margin-top:12px;background:transparent;padding:0;border:0}details.more>summary{padding:12px 4px;color:var(--ink2);font-size:14px}
details.more .co-list{margin-top:8px}
.ap-list{background:var(--card);border-radius:var(--r);padding:6px 22px}
.ap{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) minmax(0,1.6fr) minmax(0,1.1fr);gap:16px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}
.ap:last-child{border:0}.ap-h{display:flex;flex-direction:column;gap:2px;min-width:0}.ap-h b{font-weight:500;font-size:16px}
.ap-h small{color:var(--ink2);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ap-m{display:flex;flex-direction:column;align-items:flex-start;gap:6px}.ap-n{display:flex;flex-direction:column;gap:4px}
.ap-s{display:flex;gap:4px}.sp{flex:1;text-align:center;font-size:11px;padding:7px 4px;border-radius:999px;border:1.5px solid rgba(29,29,27,.18);color:var(--ink2);white-space:nowrap}
.sp.done{background:var(--dark);border-color:var(--dark);color:#fff}.sp.cur{background:var(--yl);border-color:var(--yl);color:var(--ink)}
.sp.rej{background:transparent;border-color:var(--ink);color:var(--ink)}
.sp.q{background:repeating-linear-gradient(135deg,rgba(29,29,27,.14) 0 1.5px,transparent 1.5px 7px),#fff;border-color:transparent;color:var(--ink)}
.ap-q{opacity:.85}
.pj-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.pj{background:var(--card);border-radius:var(--r);padding:22px;display:flex;flex-direction:column;gap:6px}
.pj b{font-weight:500;font-size:17px}.pj small{color:var(--ink2)}.pj p{margin:0;font-size:14px;color:var(--ink2)}.pj .pill-st{align-self:flex-start}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--ink2);font-weight:400}.num{text-align:right;font-variant-numeric:tabular-nums}
.empty{color:var(--ink2);font-size:14px;background:var(--card);border-radius:var(--r);padding:22px}
.foot{margin-top:40px;font-size:12px;color:var(--mut)}
@media (max-width:1120px){.bento{grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:auto;
grid-template-areas:"photo act" "ring side" "acc side" "cal cal"}.photo{min-height:300px}.act,.ring{min-height:300px}.cal{min-height:330px}
.grid3{grid-template-columns:1fr 1fr}.mk,.mt{grid-template-columns:1fr}}
@media (max-width:720px){.wrap{padding:16px 16px 48px}h1{font-size:34px}.hero{margin:22px 0 18px}
.bento{grid-template-columns:minmax(0,1fr);grid-template-areas:"side" "photo" "act" "ring" "acc" "cal"}
.seg-p{padding:0 12px}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;width:100%}.stat{flex-direction:column-reverse;align-items:flex-start;gap:6px}.stat b{font-size:42px}.stat span{padding:0}
.grid3,.co-list,.cf-list,.pj-list,.ld-list{grid-template-columns:minmax(0,1fr)}
.ap{grid-template-columns:minmax(0,1fr);gap:10px}.ap-m{flex-direction:row;align-items:center}.sp{font-size:10px;padding:6px 2px}.lead{columns:1}
.pills .pill-s{white-space:normal}.cf{padding:14px}.co{padding:16px}.co .pill-st{display:none}
.jr{grid-template-columns:44px minmax(0,1fr)}.jr-s{font-size:26px}.jr-r{grid-column:2}
.sk{grid-template-columns:118px minmax(0,1fr) 62px}nav{margin-left:0;order:3;width:100%}.who{margin-left:auto}
.tl-p span{max-width:170px}.sh h2{font-size:26px}}
"""

ICON_JOB = '<svg viewBox="0 0 16 16"><rect x="3" y="5" width="10" height="8" rx="2"/><path d="M6 5V4h4v1"/></svg>'
ICON_SEND = '<svg viewBox="0 0 16 16"><path d="M3 8h9M9 5l3 3-3 3"/></svg>'
ICON_APP = '<svg viewBox="0 0 16 16"><rect x="4.5" y="2.5" width="7" height="11" rx="2"/></svg>'
upd = datetime.datetime.now()

above = sum(1 for j in jobs.values() if (j.get("score") or 0) >= 75)
ring_html = f"""<div class="card ring"><h2>{e(app.get('name', ''))[:22]}</h2>{arrow(app.get('url', '#metro'))}<div class="rv"><svg class="dial" viewBox="0 0 120 120">{ticks}</svg>
<div class="ctr"><b>{rating or '–'}</b><small>рейтинг · {app.get('ratings', 0)} {plural(app.get('ratings', 0), 'оценка', 'оценки', 'оценок')}</small></div></div>
<div class="rb"><span class="pill-s">{'#' + str(nav_rank) + ' ' + e(app.get('genreName', '')) + ' ' + e(app.get('country', '')) if nav_rank else 'вне топ-200'}</span><span class="pill-s">v{e(app.get('version', ''))}</span>
<a class="go" href="#metro" aria-label="Подробнее"><svg viewBox="0 0 16 16"><path d="M5 11 11 5M6 5h5v5"/></svg></a></div></div>""" if app else f"""<div class="card ring"><h2>Лучший fit</h2>{arrow('#jobs')}<div class="rv"><svg class="dial" viewBox="0 0 120 120">{ticks}</svg>
<div class="ctr"><b>{best_fit or '–'}</b><small>из 100 · порог 75</small></div></div>
<div class="rb"><span class="pill-s">{above} {plural(above, 'вакансия', 'вакансии', 'вакансий')} выше порога</span>
<a class="go" href="#jobs" aria-label="Подробнее"><svg viewBox="0 0 16 16"><path d="M5 11 11 5M6 5h5v5"/></svg></a></div></div>"""
metro_html = f"""<section id="metro"><div class="sh"><h2>{e(app.get('name', ''))}</h2><p>Публичные данные App Store, обновляются каждый прогон.</p></div>
<div class="mt"><div class="card"><div class="mt-h">{f'<img src="{e(app.get("icon"))}" alt="">' if app.get('icon') else ''}<div><h2>{e(app.get('name', ''))}</h2>
<span class="sub">Версия {e(app.get('version', ''))} от {ru_date(date(app.get('updated')))} · в App Store с {ru_date(date(app.get('released')))} {e(str(app.get('released', ''))[:4])}</span></div></div>
<div class="mt-k"><div><b>{'#' + str(nav_rank) if nav_rank else '–'}</b><span>топ бесплатных «{e(app.get('genreName', ''))}», {e(app.get('country', ''))}</span></div><div><b>{rating or '–'}</b><span>рейтинг, {app.get('ratings', 0)} {plural(app.get('ratings', 0), 'оценка', 'оценки', 'оценок')}</span></div></div>
<div class="pills"><a class="pill-s dk" href="{e(app.get('url', '#'))}" target="_blank">App Store</a>{f'<a class="pill-s" href="{e(app.get("site"))}" target="_blank">сайт</a>' if app.get('site') else ''}{press}</div></div>
<div class="card"><h2>Место в топе</h2>{f'<ol class="lead">{lead}</ol>' if lead else ''}{spark}<p class="sub">Проверено {e(str(app.get('checkedAt', '')).replace('T', ' '))}.{' В резюме: ' + e(app.get('claims')) + '.' if app.get('claims') else ''}</p></div></div></section>""" if app else ""

page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header><span class="logo">Job Radar</span>
<nav><a class="on" href="#top">Обзор</a><a href="#status">Отклики</a><a href="#jobs">Вакансии</a><a href="#plan">План</a><a href="#learn">Курсы</a><a href="#events">События</a><a href="#market">Рынок</a>{'<a href="#metro">' + e(app.get("name", "")) + '</a>' if app else ''}</nav>
<div class="who"><span class="upd">Обновлено {upd:%d.%m %H:%M}</span>{f'<img src="{PHOTO}" alt="">' if PHOTO else f'<span class="av">{e(initials)}</span>'}</div></header>

<div class="hero" id="top"><div><h1>Привет{", " + e(first_name) if first_name else ""}</h1><div class="pipe">{seg_html}</div></div>
<div class="stats"><div class="stat"><span>{ICON_JOB}{plural(len(jobs), 'вакансия', 'вакансии', 'вакансий')}<br>в работе</span><b>{len(jobs)}</b></div>
<div class="stat"><span>{ICON_SEND}{plural(sent_n, 'отклик', 'отклика', 'откликов')}<br>отправлено</span><b>{sent_n}</b></div>
{f'<div class="stat"><span>{ICON_APP}{e(app.get("name", ""))[:18]}<br>в «{e(app.get("genreName", "топе"))}»</span><b>{"#" + str(nav_rank) if nav_rank else "–"}</b></div>' if app else f'<div class="stat"><span>{ICON_APP}{plural(replied_n, "ответ", "ответа", "ответов")}<br>от компаний</span><b>{replied_n}</b></div>'}</div></div>

<div class="bento">
<div class="card photo">{f'<img src="{PHOTO}" alt="{e(full_name)}">' if PHOTO else f'<span class="ph-i">{e(initials)}</span>'}<div class="ov"><div><b>{e(full_name or "Job Radar")}</b><small>{e(" · ".join(x for x in (profile.get("headline", ""), city) if x))}</small></div><span class="glass">{e(profile.get("workMode") or "Remote")}</span></div></div>

<div class="card act"><h2>Активность</h2>{arrow('#history')}<div class="big"><b>{week_total}</b><span>вакансий<br>просмотрено за 7 дней</span></div><div class="bars">{bars}</div></div>

{ring_html}

<div class="side"><div class="card learn"><h2>Обучение</h2><span class="pct">{learn_pct}%</span>
<div class="lbars"><div style="flex:{max(c_done, .35)}">Готово<i class="lb-done">{c_done}</i></div><div style="flex:{max(c_doing, .35)}">В процессе<i class="lb-doing">{c_doing}</i></div><div style="flex:{max(c_todo, .35)}">Впереди<i class="lb-todo">{c_todo}</i></div></div></div>
<div class="todo"><div class="th"><h2>Ждёт тебя</h2><b>{todo_done}/{len(todo)}</b></div><ul>{todo_html}</ul></div></div>

<div class="card acc">{acc or '<p class=sub>Нет вакансий выше порога</p>'}</div>

<div class="card cal"><div class="ch"><h2>Ближайшие события</h2><div class="lg"><span><i class="f"></i>выходные</span><span><i></i>будни</span></div></div>
<div class="tl">{month_cols}<div class="tl-now" style="left:{today_x:.2f}%"></div>{rows or '<p class=sub style="position:relative">Событий с подтверждёнными датами пока нет</p>'}</div>
<div class="sub">{f'Ближайшее через {days_to} {plural(days_to, "день", "дня", "дней")} · ' if next_ev else ''}{weekend_n} в выходные за 3 месяца · <a href="#events">все {len(conferences)} событий</a></div></div>
</div>

<section id="status"><div class="sh"><h2>Статус откликов</h2><p>{len(apps)} {plural(len(apps), 'отклик', 'отклика', 'откликов')} · {replied_n} {plural(replied_n, 'ответ', 'ответа', 'ответов')} · сегодня отправлено {sent_today} из 6. Ответы и отказы радар забирает из Gmail каждый прогон.</p></div>
{f'<div class="ap-list">{app_rows}</div>' if app_rows else '<div class="empty">Откликов пока нет.</div>'}</section>

<section id="plan"><div class="sh"><h2>Как найти работу быстрее</h2><p>{e(strategy.get('summary', ''))}</p></div>
{f'<div class="grid3">{strat}</div>' if strat else '<div class="empty">План появится после исследования рынка.</div>'}
{f'<div class="sh" style="margin-top:28px"><h2 style="font-size:22px">Нашлось рядом с домом</h2><p>{e(market.get("leadsNote", ""))}</p></div><div class="ld-list">{lead_html}</div>' if lead_html else ''}</section>

<section id="jobs"><div class="sh"><h2>Вакансии</h2><p>Порог отправки 75. Оценка считается по полному тексту вакансии и фактам из профиля.</p></div>
<div class="jl">{job_rows}</div></section>

<section id="learn"><div class="sh"><h2>Курсы</h2><p>Под самые частые пробелы из вакансий, в порядке прохождения. Статус меняется, когда скажешь, что прошёл.</p></div>
{f'<div class="co-list">{course_html}</div>' if course_html else '<div class="empty">Курсы ещё не подобраны.</div>'}
{f'<details class="more"><summary><span>Ещё {len(courses) - 6} {plural(len(courses) - 6, "курс", "курса", "курсов")}</span><em></em></summary><div class="co-list">{course_more}</div></details>' if course_more else ''}</section>

<section id="events"><div class="sh"><h2>Конференции и встречи</h2><p>AI-события с расстоянием от дома. Тёмная метка: выходные, можно ехать без отгула.</p></div>
{f'<div class="cf-list">{conf_html}</div>' if conf_html else '<div class="empty">События ещё не собраны.</div>'}</section>

<section id="market"><div class="sh"><h2>Рынок</h2><p>Спрос на навыки по {n_sig} вакансиям за 60 дней: доля вакансий, где навык обязателен.</p></div>
<div class="mk"><div class="card">{skills_html}</div><div class="card"><h2>Зарплаты</h2>{sal_html or '<p class=sub>Данных пока нет</p>'}
{f'<h2 style="margin-top:22px">Где искать</h2><ul class="chan">{chan_html}</ul>' if chan_html else ''}</div></div></section>

{metro_html}

<section id="projects"><div class="sh"><h2>Проекты под рынок</h2><p>В резюме и письма попадают только после твоего подтверждения (статус done).</p></div><div class="pj-list">{proj_html}</div></section>

<section id="history"><details class="card"><summary><span>История прогонов</span><em>{len(meta.get('history', []))}</em></summary>
<div style="overflow-x:auto"><table><tr><th>Когда</th><th class="num">Смотрел</th><th class="num">Добавил</th><th class="num">Отправил</th><th>Заметка</th></tr>{hist_rows}</table></div></details></section>
<p class="foot">Последний прогон {e(str(meta.get('lastRun', '')).replace('T', ' ')[:16])} · корпус postings: {len(postings)} · signals: {len(signals)} · дизайн по мотивам Crextio (Nixtio, Dribbble)</p>
</div></body></html>"""
open(os.path.join(ROOT, "dashboard.html"), "w", encoding="utf-8").write(page)
print("ok dashboard.html")
