"""Render a briefing as email HTML.

Table-based layout with no inline SVG, because that is what survived contact
with Gmail during the original build. The footer carries the disclaimer, the
mailing address, and the unsubscribe link, which a public mailing list needs.
"""

import html
import re


def _md_to_email_html(text):
    """Convert Gemini markdown to inline-safe email HTML."""
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'^###\s+(.+)$', r'<p style="font-size:13px;font-weight:700;color:#4f8ef7;text-transform:uppercase;letter-spacing:.05em;margin:20px 0 4px">\1</p>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$',  r'<p style="font-size:16px;font-weight:700;color:#111;margin:20px 0 6px;border-bottom:1px solid #eee;padding-bottom:4px">\1</p>', text, flags=re.MULTILINE)

    def _list_block(m):
        items = re.split(r'\n[*\-]\s+', m.group(0))
        lis = ''.join(
            f'<tr><td style="padding:3px 0 3px 0;color:#555">›</td>'
            f'<td style="padding:3px 0 3px 8px;font-size:14px;line-height:1.6">{i.strip()}</td></tr>'
            for i in items if i.strip()
        )
        return f'<table cellpadding="0" cellspacing="0" style="margin:8px 0 12px 0">{lis}</table>'

    text = re.sub(r'(?:^[*\-]\s+.+\n?)+', _list_block, text, flags=re.MULTILINE)

    blocks = re.split(r'\n{2,}', text.strip())
    parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith('<p') or block.startswith('<table'):
            parts.append(block)
        else:
            block = block.replace('\n', '<br>')
            parts.append(f'<p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#222">{block}</p>')
    return '\n'.join(parts)


def _footer(unsubscribe_url, mailing_address):
    parts = [
        "Not financial advice. Always do your own research. "
        "Past performance does not guarantee future results."
    ]
    if mailing_address:
        parts.append(html.escape(mailing_address))
    if unsubscribe_url:
        parts.append(
            f'<a href="{html.escape(unsubscribe_url)}">Unsubscribe</a>'
        )
    return "<br>".join(parts)


def render_html(briefing, unsubscribe_url=None, mailing_address=None):
    date_str = briefing.run_date.strftime("%B %d, %Y")
    commentary = _md_to_email_html(briefing.llm_output or "")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="padding:32px 16px;">

      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:#0f1117;padding:24px 32px;">
            <p style="margin:0;font-family:monospace;font-size:13px;font-weight:700;letter-spacing:.1em;color:#4f8ef7;text-transform:uppercase">FinSight</p>
            <p style="margin:6px 0 0;font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-.01em">Pre-Market Intelligence</p>
            <p style="margin:6px 0 0;font-family:monospace;font-size:12px;color:#7b7f94">{date_str}</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;font-family:Arial,Helvetica,sans-serif;">
            {commentary}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9f9fb;border-top:1px solid #ebebef;padding:20px 32px;">
            <p style="margin:0;font-size:11px;color:#999;line-height:1.6;">
              {_footer(unsubscribe_url, mailing_address)}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def subject_for(briefing):
    return f"Pre-Market Intelligence Report - {briefing.run_date.isoformat()}"


def confirmation_subject():
    return "Confirm your FinSight subscription"


def render_confirmation(confirm_url, mailing_address=None):
    safe_url = html.escape(confirm_url)
    footer = ""
    if mailing_address:
        footer = (
            f'<p style="font-size:11px;color:#999;">{html.escape(mailing_address)}</p>'
        )
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;">
    <tr>
      <td style="padding:24px;">
        <h1 style="font-size:20px;margin:0 0 12px 0;">Confirm your subscription</h1>
        <p style="font-size:14px;line-height:1.5;">
          You asked to receive the FinSight pre-market briefing. Confirm your
          address to start receiving it:
        </p>
        <p style="margin:20px 0;">
          <a href="{safe_url}" style="background:#1a1a1a;color:#ffffff;padding:10px 18px;text-decoration:none;border-radius:4px;font-size:14px;">Confirm subscription</a>
        </p>
        <p style="font-size:12px;color:#666;">
          If you did not request this, ignore this email and you will not be added.
        </p>
        {footer}
      </td>
    </tr>
  </table>
</body>
</html>"""
