"""Render a briefing as email HTML.

Table-based layout with no inline SVG, because that is what survived contact
with Gmail during the original build. The footer carries the disclaimer, the
mailing address, and the unsubscribe link, which a public mailing list needs.
"""

import html


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
    date_str = briefing.run_date.isoformat()
    commentary = html.escape(briefing.llm_output or "").replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;">
    <tr>
      <td style="padding:24px;">
        <h1 style="font-size:20px;margin:0 0 4px 0;">Pre-Market Intelligence</h1>
        <p style="font-size:13px;color:#666;margin:0 0 20px 0;">{date_str}</p>
        <div style="font-size:14px;line-height:1.5;">{commentary}</div>
        <hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0;">
        <p style="font-size:11px;color:#999;line-height:1.5;">
          {_footer(unsubscribe_url, mailing_address)}
        </p>
      </td>
    </tr>
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
