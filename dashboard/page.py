"""Public page render — redesigned."""

import html
import re


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def _md_to_html(text):
    """Convert the subset of Markdown Gemini produces into safe HTML."""
    # Escape first so we don't double-escape later
    text = html.escape(text)

    # Headers: ## Heading or ### Heading
    text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$',  r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+)$',   r'<h2>\1</h2>', text, flags=re.MULTILINE)

    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Italic: *text* (but not **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)

    # Bullet lists: lines starting with "* " or "- "
    def _list_block(m):
        items = re.split(r'\n[*\-]\s+', m.group(0))
        # first item starts with the marker already stripped by the split
        lis = ''.join(f'<li>{i.strip()}</li>' for i in items if i.strip())
        return f'<ul>{lis}</ul>'

    text = re.sub(
        r'(?:^[*\-]\s+.+\n?)+',
        _list_block,
        text,
        flags=re.MULTILINE,
    )

    # Paragraphs: blank line → new <p>
    blocks = re.split(r'\n{2,}', text.strip())
    parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith('<h') or block.startswith('<ul'):
            parts.append(block)
        else:
            # preserve single newlines inside a paragraph as <br>
            block = block.replace('\n', '<br>')
            parts.append(f'<p>{block}</p>')

    return '\n'.join(parts)


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --border: #2a2d3a;
  --accent: #4f8ef7;
  --accent-dim: #1e3a6e;
  --text: #e8eaf0;
  --muted: #7b7f94;
  --green: #34d399;
  --red: #f87171;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.65;
  min-height: 100vh;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Layout ── */
.top-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 10;
}
.logo {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--accent);
  text-transform: uppercase;
}
.top-badge {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.06em;
}

.wrap { max-width: 760px; margin: 0 auto; padding: 48px 24px 100px; }

/* ── Hero ── */
.hero { margin-bottom: 40px; }
.hero-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 10px;
}
.hero-title {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 12px;
}
.hero-meta {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.hero-meta span { display: flex; align-items: center; gap: 5px; }
.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--green);
  display: inline-block;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── Divider ── */
.divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 32px 0;
}

/* ── Commentary ── */
.commentary { font-size: 16px; color: var(--text); }

.commentary p {
  margin-bottom: 16px;
  line-height: 1.75;
}
.commentary strong { color: #fff; font-weight: 600; }
.commentary em { color: #c4c9e0; font-style: italic; }
.commentary h2 {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin: 28px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.commentary h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--accent);
  margin: 20px 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.commentary ul {
  margin: 0 0 16px 0;
  padding-left: 20px;
  list-style: none;
}
.commentary ul li {
  position: relative;
  padding-left: 16px;
  margin-bottom: 8px;
  line-height: 1.65;
}
.commentary ul li::before {
  content: "›";
  position: absolute;
  left: 0;
  color: var(--accent);
  font-weight: 700;
}

.empty-state {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 48px 32px;
  text-align: center;
  color: var(--muted);
}
.empty-state p { font-size: 15px; }

/* ── Signup ── */
.signup-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  margin-top: 48px;
}
.signup-card h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
}
.signup-card p {
  font-size: 14px;
  color: var(--muted);
  margin-bottom: 20px;
}
.input-row { display: flex; gap: 10px; flex-wrap: wrap; }
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
.input-row input[type=email]::placeholder { color: var(--muted); }
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
  transition: opacity .15s;
}
.input-row button:hover { opacity: 0.88; }
.signup-fine {
  font-size: 12px;
  color: var(--muted);
  margin-top: 10px;
}
.subscriber-count {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--green);
  margin-top: 6px;
}

/* ── Footer ── */
footer {
  margin-top: 64px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
  line-height: 1.7;
}

/* ── Message page ── */
.msg-icon { font-size: 40px; margin-bottom: 16px; }
.msg-head { font-size: 28px; font-weight: 700; margin-bottom: 10px; }
.msg-body { font-size: 15px; color: var(--muted); margin-bottom: 28px; }
.back-link {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
}
""".strip()


# ── Render helpers ─────────────────────────────────────────────────────────────

def _readout_meta(briefing):
    if briefing is None:
        return []
    parts = []
    if briefing.run_date:
        parts.append(f'<span>{briefing.run_date.strftime("%B %d, %Y")}</span>')
    if briefing.created_at:
        parts.append(f'<span>{briefing.created_at.strftime("%H:%M")} UTC</span>')
    if briefing.model_name:
        parts.append(f'<span>{briefing.model_name}</span>')
    return parts


def _commentary_block(briefing):
    if briefing is None or not briefing.llm_output:
        return '''
        <div class="empty-state">
          <p>The first briefing posts before the next market open.</p>
        </div>'''
    return f'<div class="commentary">{_md_to_html(briefing.llm_output)}</div>'


def render_page(briefing=None, subscriber_count=0, mailing_address=None):
    meta_parts = _readout_meta(briefing)
    meta_html = ' <span style="color:var(--border)">·</span> '.join(meta_parts) if meta_parts else ''

    count_html = ''
    if subscriber_count > 0:
        noun = 'subscriber' if subscriber_count == 1 else 'subscribers'
        count_html = f'<p class="subscriber-count">↑ {subscriber_count} {noun} receive this each morning</p>'

    footer_parts = [
        'Not financial advice. Past performance does not guarantee future results. Always do your own research.'
    ]
    if mailing_address:
        footer_parts.append(html.escape(mailing_address))

    live_dot = '<span class="dot"></span> Live' if briefing else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinSight — Pre-Market Intelligence</title>
<style>{_CSS}</style>
</head>
<body>

<header class="top-bar">
  <span class="logo">FinSight</span>
  <span class="top-badge">{live_dot}</span>
</header>

<main class="wrap">

  <div class="hero">
    <p class="hero-label">Pre-Market Intelligence</p>
    <h1 class="hero-title">Today's Market Briefing</h1>
    <div class="hero-meta">{meta_html}</div>
  </div>

  <hr class="divider">

  {_commentary_block(briefing)}

  <div class="signup-card">
    <h2>Get this in your inbox</h2>
    <p>One email every market morning, before the open. Free. Unsubscribe anytime.</p>
    <form method="post" action="/subscribe">
      <div class="input-row">
        <input type="email" name="email" placeholder="you@example.com"
               autocomplete="email" required>
        <button type="submit">Subscribe</button>
      </div>
    </form>
    <p class="signup-fine">Confirmation email required. No spam.</p>
    {count_html}
  </div>

  <footer>
    {'<br>'.join(footer_parts)}
  </footer>

</main>
</body>
</html>"""


def render_message(heading, body):
    icon_map = {
        'subscribed': '✓',
        'unsubscribed': '✓',
        'inbox': '✉',
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
<main class="wrap" style="text-align:center;padding-top:80px;">
  <div class="msg-icon">{icon}</div>
  <p class="msg-head">{html.escape(heading)}</p>
  <p class="msg-body">{html.escape(body)}</p>
  <a class="back-link" href="/">Back to briefing</a>
</main>
</body>
</html>"""
