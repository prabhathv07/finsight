# Deploying FinSight

This is the exact sequence to take FinSight from the repo to a live URL with a
real database and working email. Every command is meant to be copied as-is.
Where a value is yours (a key, a URL), it is shown in angle brackets like
`<your-neon-url>`; replace the whole bracket including the brackets.

Plan for about 45 minutes the first time. Everything here uses free tiers.

## Accounts you will create

- GitHub (you have this)
- Neon, for Postgres: https://neon.tech
- Render, for the web service: https://render.com
- Resend, for email: https://resend.com

Make all three with the same email so they are easy to find later. None need a
credit card on the free tier.

## Step 1. Push the code to GitHub

From the unzipped `finsight` folder:

    cd finsight
    git remote add origin https://github.com/prabhathv07/finsight.git
    git branch -M main
    git push -u origin main

Create the empty `finsight` repo on GitHub first (no README, no gitignore, so
it does not conflict with what you are pushing). After the push, the Actions
tab will show the `tests` workflow running. Confirm it goes green.

## Step 2. Prove it works locally before touching the cloud

This catches key and data problems on your machine, where they are easy to
see, instead of in a deploy log.

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    cp .env.example .env

Start the local database:

    docker compose -f infra/docker-compose.yml up -d

Edit `.env` and set just these two for now:

    GEMINI_API_KEY=<your-gemini-key>
    EMAIL_BACKEND=smtp

Get a Gemini key at https://aistudio.google.com/apikey if you do not have one
handy. Then run the whole briefing once:

    python run_briefing.py

You want a line like `2026-06-17: 66 quotes, 16 indicators, analysis ok,
delivered 0`. `delivered 0` is correct here because you have no subscribers
yet and no `EMAIL_TO` set. Check the data and the logged analysis:

    docker exec -it finsight-postgres psql -U finsight -c \
      "select category, count(*) from raw_quotes group by category;"
    docker exec -it finsight-postgres psql -U finsight -c \
      "select run_date, status, model_name, latency_ms from briefings;"

If analysis shows `failed`, the Gemini key is wrong or rate limited. Read the
`error` column:

    docker exec -it finsight-postgres psql -U finsight -c \
      "select error from briefings;"

Once the local run is clean, move on.

## Step 3. Create the Neon database

1. Sign in to Neon and create a project. Any name. Pick the region closest to
   where you will deploy Render, to keep latency low.
2. On the project dashboard, find the connection string. It looks like
   `postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`.
3. Change the scheme so SQLAlchemy uses the psycopg2 driver. Take the Neon
   string and replace the leading `postgresql://` with `postgresql+psycopg2://`.
   Keep the `?sslmode=require` at the end. The result is your `DATABASE_URL`:

       postgresql+psycopg2://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

Save that value. You will paste it into Render in step 5.

## Step 4. Set up Resend for email

1. Sign in to Resend and create an API key. Copy it; this is `RESEND_API_KEY`.
2. For a first deploy you can send from `onboarding@resend.dev`, which Resend
   allows without verifying a domain. Set `EMAIL_FROM=onboarding@resend.dev`.
3. When you want email from your own address later, add and verify a domain in
   Resend, then set `EMAIL_FROM=briefing@yourdomain.com`. Domain verification
   is a few DNS records and is not needed to go live.

## Step 5. Deploy the API and dashboard on Render

The repo has a Render blueprint at `infra/render.yaml`.

1. In Render, choose New, then Blueprint, and connect your `finsight` repo.
   Render reads `infra/render.yaml` and proposes a web service called
   `finsight-api`.
2. Before the first deploy, set the environment variables. The blueprint marks
   the secret ones as values you enter in the dashboard. Set all of these:

       DATABASE_URL      = <your-neon-url from step 3>
       GEMINI_API_KEY    = <your-gemini-key>
       GEMINI_MODEL      = gemini-2.5-flash
       EMAIL_BACKEND     = resend
       RESEND_API_KEY    = <your-resend-key>
       EMAIL_FROM        = onboarding@resend.dev
       MAILING_ADDRESS   = <a real postal address>
       PUBLIC_BASE_URL   = <leave blank for now, fill in step 6>

3. Deploy. The container runs `python -m infra.init_db` on start, which creates
   all tables in Neon, then starts the API. Watch the deploy log for
   `tables ready` and then the uvicorn startup line.
4. When it is live, Render gives you a URL like
   `https://finsight-api.onrender.com`. Open `<that-url>/health`; it should
   return `{"status":"ok"}`. Open the root `<that-url>/`; you should see the
   page with the signup form and an empty-state message, since no briefing has
   been generated against Neon yet.

Note on the free tier: the web service sleeps after 15 minutes idle, so the
first request after a quiet spell takes a few seconds to wake. That is fine for
this. If you want it always warm, the Render Starter plan is 7 dollars a month.

## Step 6. Set the public base URL

Now that you have the Render URL, go back to the Render environment variables
and set:

    PUBLIC_BASE_URL = https://finsight-api.onrender.com

Use your real URL. This is what builds the confirm and unsubscribe links in
emails, so they have to point at the live site. Save, which triggers a redeploy.

## Step 7. Schedule the daily run

The daily briefing runs as a GitHub Actions job, not on the web service, so it
hits Neon directly and is unaffected by the web service sleeping.

1. In the GitHub repo, go to Settings, then Secrets and variables, then
   Actions. Add these repository secrets, same values as Render:

       DATABASE_URL, GEMINI_API_KEY, EMAIL_BACKEND, RESEND_API_KEY,
       EMAIL_FROM, MAILING_ADDRESS, PUBLIC_BASE_URL

   You can also add `EMAIL_TO` with your own address so you get a copy even
   before you have subscribers.
2. The workflow at `.github/workflows/daily.yml` already has a weekday cron and
   a manual trigger. Test it now: Actions tab, daily briefing, Run workflow.
   It should go green in a minute or two.
3. Check your inbox for the briefing email, and check the live site root, which
   should now show today's commentary.

GitHub's free cron can fire 30 to 90 minutes late. For an exact 9 AM Central
send, drive it from cron-job.org instead:

1. Create a GitHub fine-grained personal access token with Actions read and
   write permission on the `finsight` repo only.
2. In cron-job.org, create a job at your exact time, weekdays, that sends a
   POST request to:

       https://api.github.com/repos/prabhathv07/finsight/actions/workflows/daily.yml/dispatches

   with header `Authorization: Bearer <your-token>`, header
   `Accept: application/vnd.github+json`, and body `{"ref":"master"}`.

That fires the workflow on time; GitHub then runs the job.

## Step 8. The compliance gate, before you share the link

You now operate a public mailing list. The mechanics are built: signups are
double opt-in, and every email carries an unsubscribe link. Two things you set,
one thing you confirm:

- Set: `MAILING_ADDRESS` to a real postal address. It shows in every footer.
- Set: keep the "not financial advice" disclaimer, which is already in the
  footer and the LLM prompt.
- Confirm: you are comfortable running a public list. Bulk email to people who
  signed up carries obligations around honoring unsubscribes and identifying
  the sender. I am not a lawyer; this is the point to be sure you are fine
  operating it.

## Step 9. Open signups and get an honest count

1. Go to the live site, enter your own email, submit. You should land on the
   "Check your inbox" page.
2. Open the confirmation email, click Confirm. You should see the "You are
   subscribed" page.
3. Share the link. Each confirmed signup is a real row.
4. The number for your resume comes from a query, not a guess:

       select count(*) from subscribers where status = 'confirmed';

   Run it against Neon from the Neon SQL editor. That count is the honest N in
   "serving N daily subscribers."

## Troubleshooting

- Deploy log shows a database connection error: the `DATABASE_URL` scheme is
  probably still `postgresql://`. It must be `postgresql+psycopg2://`, and the
  `?sslmode=require` must stay on the end for Neon.
- `/health` works but `/` errors: tables may not exist. Confirm the deploy log
  printed `tables ready`. If not, the container could not reach Neon at start.
- Briefing email never arrives: check the `briefings` table status. If `ok`,
  the analysis ran and the send is the problem; verify `RESEND_API_KEY` and
  `EMAIL_FROM`. If `failed`, read the `error` column.
- Analysis status `failed` with a quota message: Gemini free tier rate limit.
  Wait and rerun, or check the key.
- The daily workflow runs but sends nothing: confirm the GitHub Actions secrets
  are set, especially `DATABASE_URL` and `RESEND_API_KEY`.

## What this costs

Nothing on the paths above. Neon free Postgres does not expire. GitHub Actions
minutes are free for this volume. Render free covers the web service with the
sleep behavior noted. The only optional spend is 7 dollars a month for an
always-warm Render service.
