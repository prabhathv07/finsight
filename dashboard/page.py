"""Public page render."""

import html
import re


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def _md_to_html(text):
    """Convert the Markdown subset Gemini produces into safe HTML.

    Processing order matters: bullet lists must be extracted before bold/italic
    so the * markers are not consumed by the inline-emphasis regexes.
    """
    text = html.escape(text)

    # Block-level: headers
    text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$',  r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+)$',   r'<h2>\1</h2>', text, flags=re.MULTILINE)

    # Block-level: bullet lists (before bold/italic — protects * markers)
    lines = text.split('\n')
    in_list = False
    out = []
    for line in lines:
        m = re.match(r'^[*\-]\s+(.*)', line)
        if m:
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{m.group(1)}</li>')
        else:
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append(line)
    if in_list:
        out.append('</ul>')
    text = '\n'.join(out)

    # Inline: bold (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Inline: italic (*text*) — single line only, not adjacent to *
    text = re.sub(r'(?<!\*)\*([^\n*]{1,200}?)\*(?!\*)', r'<em>\1</em>', text)

    # Block-level: paragraphs (blank-line delimited)
    blocks = re.split(r'\n{2,}', text.strip())
    parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if re.match(r'^<(?:h[1-6]|ul|li)[\s>]', block):
            parts.append(block)
        else:
            parts.append(f'<p>{block.replace(chr(10), "<br>")}</p>')

    return '\n'.join(parts)


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:          #0b0e18;
  --surface:     #13172a;
  --surface-2:   #1c2035;
  --border:      #252a40;
  --accent:      #5b8cf5;
  --accent-glow: rgba(91,140,245,.15);
  --text:        #dde1f0;
  --text-dim:    #9ba3c0;
  --white:       #f0f2ff;
  --green:       #34d399;
  --red:         #f87171;
  --yellow:      #fbbf24;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --radius: 10px;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.7;
  min-height: 100vh;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Top bar ── */
.top-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(8px);
}
.logo {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--accent);
  text-transform: uppercase;
}
.live-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(52,211,153,.1);
  border: 1px solid rgba(52,211,153,.25);
  border-radius: 20px;
  padding: 3px 10px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--green);
  letter-spacing: 0.05em;
}
.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--green);
  flex-shrink: 0;
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52,211,153,.4); }
  50%       { opacity: .6; box-shadow: 0 0 0 4px rgba(52,211,153,.0); }
}

/* ── Layout ── */
.wrap { max-width: 720px; margin: 0 auto; padding: 48px 24px 96px; }

/* ── Date header ── */
.date-strip {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.date-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  opacity: .8;
}
.date-main {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--white);
}
.date-meta {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-dim);
  margin-left: auto;
}

/* ── Briefing card ── */
.briefing-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 32px;
}
.briefing-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}
.briefing-card-title {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.model-chip {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-dim);
  background: var(--border);
  border-radius: 4px;
  padding: 2px 7px;
}
.briefing-body { padding: 24px 28px 28px; }

/* ── Commentary typography ── */
.commentary { color: var(--text); font-size: 15px; line-height: 1.75; }

.commentary p { margin-bottom: 16px; }

.commentary p:last-child { margin-bottom: 0; }

.commentary strong { color: var(--white); font-weight: 600; }

.commentary em { color: #b4bcda; font-style: italic; }

.commentary h2 {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 28px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.commentary h2:first-child { margin-top: 0; }

.commentary h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--white);
  margin: 20px 0 8px;
}

.commentary ul {
  margin: 0 0 16px 0;
  padding: 0;
  list-style: none;
}
.commentary ul li {
  position: relative;
  padding: 6px 0 6px 20px;
  line-height: 1.65;
  border-bottom: 1px solid rgba(37,42,64,.5);
}
.commentary ul li:last-child { border-bottom: none; }
.commentary ul li::before {
  content: "›";
  position: absolute;
  left: 0;
  color: var(--accent);
  font-weight: 700;
  font-size: 16px;
  line-height: 1.5;
}

.empty-state {
  padding: 56px 32px;
  text-align: center;
  color: var(--text-dim);
}
.empty-icon { font-size: 32px; margin-bottom: 12px; }
.empty-state p { font-size: 14px; }

/* ── Divider ── */
.divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 32px 0;
}

/* ── Signup ── */
.signup-card {
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 32px;
  position: relative;
  overflow: hidden;
}
.signup-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.signup-card h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--white);
  margin-bottom: 6px;
}
.signup-card .sub {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 20px;
  line-height: 1.5;
}
.input-row { display: flex; gap: 8px; flex-wrap: wrap; }
.input-row input[type=email] {
  flex: 1 1 220px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 11px 14px;
  font-size: 14px;
  color: var(--text);
  outline: none;
  transition: border-color .15s;
}
.input-row input[type=email]::placeholder { color: var(--text-dim); }
.input-row input[type=email]:focus { border-color: var(--accent); }
.input-row button {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 11px 22px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity .15s, transform .1s;
}
.input-row button:hover { opacity: .88; }
.input-row button:active { transform: scale(.97); }
.signup-fine {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 10px;
}
.subscriber-count {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--green);
  margin-top: 8px;
}
.subscriber-count::before {
  content: '';
  display: inline-block;
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--green);
}

/* ── Footer ── */
footer {
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.8;
}

/* ── Message page ── */
.msg-wrap { max-width: 420px; margin: 0 auto; padding: 80px 24px; text-align: center; }
.msg-icon { font-size: 40px; margin-bottom: 20px; }
.msg-head { font-size: 26px; font-weight: 700; color: var(--white); margin-bottom: 10px; }
.msg-body { font-size: 15px; color: var(--text-dim); margin-bottom: 32px; line-height: 1.6; }
.back-link {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  padding: 11px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  transition: opacity .15s;
}
.back-link:hover { opacity: .88; text-decoration: none; }
""".strip()


# ── Template helpers ──────────────────────────────────────────────────────────

def _date_strip(briefing):
    if briefing is None:
        return ''
    parts = []
    if briefing.run_date:
        parts.append(f'<span class="date-main">{briefing.run_date.strftime("%B %d, %Y")}</span>')
    meta = []
    if briefing.created_at:
        meta.append(f'generated {briefing.created_at.strftime("%H:%M")} UTC')
    meta_str = ' · '.join(meta) if meta else ''
    return f'''
    <div class="date-strip">
      <span class="date-label">Pre-Market Briefing</span>
      {"".join(parts)}
      {"<span class='date-meta'>" + meta_str + "</span>" if meta_str else ""}
    </div>'''


def _commentary_block(briefing):
    model = getattr(briefing, 'model_name', '') or '' if briefing else ''
    if briefing is None or not briefing.llm_output:
        return '''
        <div class="briefing-card">
          <div class="briefing-card-header">
            <span class="briefing-card-title">Market Analysis</span>
          </div>
          <div class="briefing-body">
            <div class="empty-state">
              <div class="empty-icon">📊</div>
              <p>The first briefing will appear here before the next market open.</p>
            </div>
          </div>
        </div>'''
    model_chip = f'<span class="model-chip">{html.escape(model)}</span>' if model else ''
    return f'''
    <div class="briefing-card">
      <div class="briefing-card-header">
        <span class="briefing-card-title">Market Analysis</span>
        {model_chip}
      </div>
      <div class="briefing-body">
        <div class="commentary">{_md_to_html(briefing.llm_output)}</div>
      </div>
    </div>'''


def render_page(briefing=None, subscriber_count=0, mailing_address=None):
    live_chip = ''
    if briefing:
        live_chip = '<span class="live-chip"><span class="dot"></span>Live</span>'

    count_html = ''
    if subscriber_count > 0:
        noun = 'subscriber' if subscriber_count == 1 else 'subscribers'
        count_html = f'<p class="subscriber-count">{subscriber_count} {noun} receive this each morning</p>'

    footer_lines = ['Not financial advice. Always do your own research. Past performance does not guarantee future results.']
    if mailing_address:
        footer_lines.append(html.escape(mailing_address))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Daily pre-market briefing — futures, macro, sectors, and watchlist with AI commentary.">
<title>FinSight — Pre-Market Intelligence</title>
<style>{_CSS}</style>
</head>
<body>

<header class="top-bar">
  <span class="logo">FinSight</span>
  {live_chip}
</header>

<main class="wrap">

  {_date_strip(briefing)}

  {_commentary_block(briefing)}

  <p style="font-size:11px;color:var(--text-dim);margin-bottom:24px;">
    Not financial advice. Always do your own research. Past performance does not guarantee future results.
  </p>

  <div class="signup-card">
    <h2>Get this in your inbox</h2>
    <p class="sub">One briefing every market morning — futures, macro, sectors, and AI commentary — before the open. Free. Unsubscribe any time.</p>
    <form method="post" action="/subscribe">
      <div class="input-row">
        <input type="email" name="email" placeholder="you@example.com"
               autocomplete="email" required>
        <button type="submit">Subscribe</button>
      </div>
    </form>
    <p class="signup-fine">Confirmation email required · No spam · Unsubscribe from any email</p>
    {count_html}
  </div>

  <footer>
    {'<br>'.join(footer_lines)}
  </footer>

</main>
</body>
</html>"""


def render_message(heading, body):
    icon_map = {
        'subscribed': '✓',
        'unsubscribed': '✓',
        'inbox':       '✉',
        'not recognized': '✕',
    }
    icon = next((v for k, v in icon_map.items() if k in heading.lower()), 'ℹ')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinSight</title>
<style>{_CSS}</style>
</head>
<body>
<header class="top-bar">
  <span class="logo">FinSight</span>
</header>
<main class="msg-wrap">
  <div class="msg-icon">{icon}</div>
  <p class="msg-head">{html.escape(heading)}</p>
  <p class="msg-body">{html.escape(body)}</p>
  <a class="back-link" href="/">Back to briefing</a>
</main>
</body>
</html>"""
