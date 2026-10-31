# Keyword Planner: getting search volumes

The lists come from the site map. Run `make site` and they appear in `packages/site/dist/keyword-planner/`:

| File | What it is |
|---|---|
| `search-volume-en.txt` | Every English keyword in the map (121) |
| `search-volume-hi.txt` | Every Hindi keyword (66, drafts) |
| `search-volume-mr.txt` | Every Marathi keyword (65, drafts) |
| `seed-keywords-en.txt` | 10 seed keywords for new ideas |
| `keyword-map.csv` | Which page each keyword belongs to (for me; do not upload) |

Google Ads labels move from time to time. If a button below has a slightly different name, look for the closest match.

## 1. Account

1. Sign in at [ads.google.com](https://ads.google.com) with the Google account D-SAP will keep for advertising.
2. A new account asks you to create a campaign. Choose **Switch to Expert Mode**, then **Create an account without a campaign**.
3. Billing country India, time zone (GMT+05:30) India Standard Time, currency Indian rupee. The currency cannot be changed later.

Without ad spend, Keyword Planner shows volume ranges instead of exact numbers. Ranges are enough to compare keywords.

## 2. Search volumes for our keywords (run three times)

1. Click **Tools** (the wrench icon), then **Planning**, then **Keyword Planner**.
2. Choose **Get search volume and forecasts**.
3. Open `search-volume-en.txt`, copy everything, paste it into the box (or use the file upload option), then **Get started**.
4. At the top of the results, set:
   - **Locations**: remove India, add **Pune, Maharashtra, India** and **Pimpri-Chinchwad, Maharashtra, India** (if Pimpri-Chinchwad is not offered, Pune district covers it).
   - **Language**: English.
   - **Search networks**: Google.
   - **Date range**: the last 12 months.
5. Open the **Historical metrics** tab, click **Download** (the arrow icon), choose **Historical metrics** as CSV.
6. Save it as `resources/keyword-planner/volumes-en.csv` in this project.
7. Repeat with `search-volume-hi.txt` and save as `volumes-hi.csv`, then `search-volume-mr.txt` as `volumes-mr.csv`. For these two, set **Language** to **All languages**. Many people who search in Hindi or Marathi keep their Google set to English, and a Hindi or Marathi filter would hide them.

## 3. New keyword ideas (run once)

1. In Keyword Planner choose **Discover new keywords**, then **Start with keywords**.
2. Paste the 10 lines from `seed-keywords-en.txt`.
3. Same locations, language English, then **Get results**.
4. Click **Download keyword ideas**, CSV, and save it as `resources/keyword-planner/ideas-en.csv`.

## 4. Hand it back

Tell me the four or five files are in `resources/keyword-planner/`. I import them, attach volumes to every page's keywords, flag any page whose primary keyword has little search, and suggest better ones from the ideas file. Keyword changes are then one line each in `packages/site/routes.json` or `site.json`.
