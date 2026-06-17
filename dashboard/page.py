"""Public page render.

One page, one job: show the latest briefing and let a reader subscribe. The
data readout is the page's signature, the run date and freshness set in a
monospace face like an instrument label, since timing is the whole point of a
pre-market product. Everything else stays quiet. Self-contained HTML so it
serves from one route with no asset pipeline.
"""

import html

PAGE_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #fbfbf9;
  color: #16181d;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55;
}
.wrap { max-width: 680px; margin: 0 auto; padding: 64px 24px 96px; }
.eyebrow {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase;
  color: #6b7280; margin: 0 0 8px;
}
h1 { font-size: 34px; font-weight: 650; letter-spacing: -0.02em; margin: 0 0 4px; }
.readout {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 13px; color: #16181d; margin: 0 0 40px;
  border-left: 2px solid #16181d; padding-left: 10px;
}
.commentary { font-size: 16px; }
.commentary p { margin: 0 0 14px; }
.empty { color: #6b7280; font-size: 16px; }
.signup { margin-top: 48px; padding-top: 28px; border-top: 1px solid #e6e4dd; }
.signup label { display: block; font-weight: 600; margin-bottom: 10px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; }
input[type=email] {
  flex: 1 1 240px; min-width: 0; padding: 11px 12px; font-size: 15px;
  border: 1px solid #c9c6bd; border-radius: 6px; background: #fff;
}
input[type=email]:focus-visible { outline: 2px solid #16181d; outline-offset: 1px; }
button {
  padding: 11px 20px; font-size: 15px; font-weight: 600; cursor: pointer;
  background: #16181d; color: #fff; border: none; border-radius: 6px;
}
button:focus-visible { outline: 2px solid #16181d; outline-offset: 2px; }
.fine { font-size: 13px; color: #6b7280; margin-top: 10px; }
.count {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 13px; color: #6b7280; margin-top: 6px;
}
footer { margin-top: 56px; font-size: 12px; color: #9aa0a6; line-height: 1.6; }
""".strip()


def _commentary_html(briefing):
    if briefing is None or not briefing.llm_output:
        return (
            '<p class="empty">The first briefing posts before the next '
            "market open.</p>"
        )
    paras = [p for p in briefing.llm_output.split("\n") if p.strip()]
    return "".join(f"<p>{html.escape(p)}</p>" for p in paras)


def _readout(briefing):
    if briefing is None:
        return "no briefing on record yet"
    captured = briefing.created_at.strftime("%H:%M UTC") if briefing.created_at else ""
    return f"{briefing.run_date.isoformat()} pre-market &middot; generated {captured}"


def render_page(briefing=None, subscriber_count=0, mailing_address=None):
    count_line = ""
    if subscriber_count > 0:
        noun = "reader" if subscriber_count == 1 else "readers"
        count_line = f'<p class="count">{subscriber_count} {noun} get this each morning.</p>'

    footer_bits = [
        "Not financial advice. Always do your own research. Past performance "
        "does not guarantee future results."
    ]
    if mailing_address:
        footer_bits.append(html.escape(mailing_address))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinSight Pre-Market Briefing</title>
<style>{PAGE_CSS}</style>
</head>
<body>
  <main class="wrap">
    <p class="eyebrow">Pre-market briefing</p>
    <h1>FinSight</h1>
    <p class="readout">{_readout(briefing)}</p>

    <div class="commentary">{_commentary_html(briefing)}</div>

    <section class="signup">
      <form method="post" action="/subscribe">
        <label for="email">Get the briefing by email</label>
        <div class="row">
          <input id="email" name="email" type="email" required
                 placeholder="you@example.com" autocomplete="email">
          <button type="submit">Subscribe</button>
        </div>
      </form>
      <p class="fine">One email each market morning. Unsubscribe anytime.</p>
      {count_line}
    </section>

    <footer>{"<br>".join(footer_bits)}</footer>
  </main>
</body>
</html>"""


def render_message(heading, body):
    """Small standalone page for confirm, unsubscribe, and post-signup states."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinSight</title>
<style>{PAGE_CSS}</style>
</head>
<body>
  <main class="wrap">
    <p class="eyebrow">FinSight</p>
    <h1>{html.escape(heading)}</h1>
    <p class="commentary">{html.escape(body)}</p>
    <p class="fine"><a href="/">Back to the briefing</a></p>
  </main>
</body>
</html>"""
