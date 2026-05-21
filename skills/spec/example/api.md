# API Endpoints Reference

All endpoints provided by the web-scraper service. For web scraping endpoints (`/web/crawl4ai`, `/web/crawl4ai-collect`, Batch series), see [crawl4ai-compare.md](crawl4ai-compare.md).

## Endpoint Summary

| Route                   | Method | Purpose                                    | Data Source         |
| ----------------------- | ------ | ------------------------------------------ | ------------------- |
| `/web`                  | POST   | Legacy web scraping (Selenium + OpenAI)    | automationConfig    |
| `/web/manual`           | POST   | Scrape from explicit URL list              | User-provided URLs  |
| `/web/selector`         | POST   | AI-detect CSS selector for a website       | User-provided URL   |
| `/web/crawl4ai`         | POST   | Single-site scraping (Playwright + OpenAI) | automationConfig    |
| `/web/crawl4ai-collect` | POST   | Batch free scraping (Playwright + rules)   | automationConfig    |
| `/web/batch-collect`    | POST   | Phase 1: collect HTML to GCS               | automationConfig    |
| `/web/batch-submit`     | POST   | Phase 2: submit Batch API job              | GCS pending         |
| `/web/batch-status`     | POST   | Phase 3: check batch job status            | GCS batch-jobs      |
| `/facebook`             | POST   | Facebook page post scraping                | automationConfig    |
| `/threads`              | POST   | Threads post scraping                      | User-provided query |
| `/map`                  | POST   | Google Maps place + reviews                | User-provided query |
| `/outboundip`           | GET    | Server outbound IP check                   | —                   |

---

## POST /web — Legacy Web Scraper

Scrape articles from a configured website using Selenium + OpenAI extraction. See [crawl4ai-compare.md](crawl4ai-compare.md) for detailed flow and comparison with newer endpoints.

### Request

```json
{
  "county": "taipei", // required — automationConfig county ID
  "website_id": "abc123", // required — Firestore website ID
  "url_only": false // optional — only return links, skip content extraction
}
```

### Response

Returns `website.to_dict()` — the website object with scraped articles. See [crawl4ai-compare.md](crawl4ai-compare.md#post-web--legacy-爬蟲) for full response structure.

### Implementation

```
Request { county, website_id, url_only }
  │
  ├─ 1. WebScraper(county) init
  │     └─ Load config from Firestore automationConfig/{county}
  │
  ├─ 2. Website.scrape_articles()
  │     │
  │     ├─ [Has CSS Selector (link_selector is set)]
  │     │   ├─ Launch Chrome driver (headless)
  │     │   ├─ Load listing page, extract <a> tags via CSS Selector
  │     │   ├─ Pagination loop (max 5 pages)
  │     │   │   ├─ Extract links → ArticleExtractor per article
  │     │   │   ├─ Stop when max_posts reached or date < end_date_cursor
  │     │   │   └─ Sleep 2s → next page
  │     │   └─ driver.quit()
  │     │
  │     └─ [No CSS Selector]
  │         └─ _scrape_with_ai_fallback()
  │             ├─ Fetch HTML: requests → Apify Proxy → Selenium
  │             └─ LiteLLM (Gemini) AI filters article links
  │
  ├─ 3. Per-article extraction (ArticleExtractor.get_article_content())
  │     ├─ Fetch HTML → OpenAI API structured extraction
  │     ├─ Firestore dedup (match by title)
  │     ├─ Fix future dates
  │     └─ save_article() → Firestore webdata
  │
  └─ 4. update_website_result() → update website status
        └─ On errors: write scraper_alerts
```

### Reference

| Component             | File                 |
| --------------------- | -------------------- |
| Endpoint handler      | `main.py`            |
| `WebScraper.scrape()` | `src/web_scraper.py` |

---

## POST /web/manual — Manual URL Scraping

Scrape articles from a list of explicitly provided URLs, bypassing the link discovery step. Useful for one-off imports or URLs that don't follow the standard listing page pattern.

### Request

```json
{
  "county": "taipei", // required — county ID
  "urls": [
    // required — list of article URLs to scrape
    "https://example.com/article1",
    "https://example.com/article2"
  ],
  "source_name": "台北市政府", // optional — override source name
  "tags": ["news"] // optional — tags for the source
}
```

### Response

Returns the WebScraper result with extracted articles from the provided URLs.

### Implementation

```
Request { county, urls, source_name?, tags? }
  │
  ├─ 1. WebScraper(county) init
  │
  ├─ 2. Per-URL processing (skips link discovery, extracts directly)
  │     ├─ ArticleExtractor(url).get_article_content()
  │     │   └─ Fetch HTML → OpenAI API structured extraction
  │     ├─ Firestore dedup (match by title)
  │     ├─ save_article() → Firestore webdata
  │     └─ On failure: save error stub with error_message field
  │
  └─ 3. Return Website source object (includes all success/failure articles)
```

### Reference

| Component                            | File                 |
| ------------------------------------ | -------------------- |
| Endpoint handler                     | `main.py`            |
| `WebScraper.add_articles_manually()` | `src/web_scraper.py` |

---

## POST /web/selector — CSS Selector Detection

Analyze a webpage and use AI to detect the CSS selector for article links. Used to configure new websites in `automationConfig` before scraping.

### Request

```json
{
  "url": "https://www.taipei.gov.tw/news", // required — listing page URL
  "example_article": {
    // optional — hint for pattern matching
    "title": "文章標題",
    "url": "https://..."
  }
}
```

### Response

```json
{
  "selector": "div.news-list a.title", // detected CSS selector
  "articles": [
    // articles found using the selector
    { "title": "文章標題", "url": "https://..." }
  ],
  "next_page_selector": "a.next-page", // pagination selector (if found)
  "url": "https://www.taipei.gov.tw/news",
  "error": "" // error message if detection failed
}
```

### Implementation

```
Request { url, example_article? }
  │
  ├─ 1. Choose detection method based on example_article
  │     │
  │     ├─ [Has example_article.url] → get_selector_css()
  │     │   ├─ Launch Chrome driver (headless)
  │     │   ├─ Load target URL, wait 5s
  │     │   ├─ JS: find all <a> elements matching example URL path
  │     │   ├─ Collect candidate CSS selectors
  │     │   ├─ AI (OpenAI) picks best selector from candidates
  │     │   └─ driver.quit()
  │     │
  │     └─ [No example_article] → get_selector_html()
  │         ├─ get_html() fetch page HTML
  │         ├─ clean_html() remove noise
  │         ├─ Extract all links
  │         └─ AI (OpenAI) identifies article selector from links
  │
  ├─ 2. validate_selector_with_soup()
  │     ├─ Parse HTML with BeautifulSoup
  │     ├─ Apply detected selector to find elements
  │     └─ Extract {title, url} list as validation
  │
  └─ 3. Return { selector, articles, next_page_selector, url, error }
```

### Reference

| Component            | File                         |
| -------------------- | ---------------------------- |
| Endpoint handler     | `main.py`                    |
| `SelectorIdentifier` | `src/selector_identifier.py` |

---

## POST /facebook — Facebook Page Scraping

Scrape posts from configured Facebook pages for a county, using Apify. Fetches posts published after the specified date.

### Request

```json
{
  "county": "taoyuan", // required — county ID
  "date": "2025-02-01" // required — fetch posts after this date (ISO format)
}
```

### Response

Returns `FacebookScraper.scrape_posts()` result — list of posts saved to Firestore `webdata` collection with `type: "facebook_page"`.

### Output Schema

Articles are saved with `type: "facebook_page"`. See `../../.github/schema/webdata.md` for the full schema including `content`, `comments_count`, `likes_count`, `shares_count`, `share_content`, `comments`, `apify_data`.

### Implementation

```
Request { county, date }
  │
  ├─ 1. Load Facebook page list from Firestore for the county
  │
  ├─ 2. Apify scrape_page_posts()
  │     └─ Call Apify Actor to scrape all pages (posts after date)
  │
  ├─ 3. Per-page processing — process_page()
  │     ├─ Deduplicate posts by URL
  │     ├─ Firestore dedup (match by title, first 200 chars)
  │     ├─ transform_apify_data() → webdata schema
  │     │   ├─ Extract content, published_date, published_by
  │     │   ├─ Extract images, comments_count, likes_count, shares_count
  │     │   └─ Handle sharedPost / link → share_content
  │     └─ save_article() → Firestore webdata (type: "facebook_page")
  │
  └─ 4. Return { articles: [...] }
```

### Reference

| Component         | File                      |
| ----------------- | ------------------------- |
| Endpoint handler  | `main.py`                 |
| `FacebookScraper` | `src/facebook_scraper.py` |
| Apify integration | `src/apify.py`            |

---

## POST /threads — Threads Post Scraping

Scrape posts from the Threads platform matching a search query, for a specific county.

### Request

```json
{
  "county": "hualien", // required — county ID
  "query": "花蓮", // required — search query
  "tags": ["activity"] // optional — tags to attach to the source
}
```

### Response

Returns `ThreadsScraper.scrape_posts()` result — list of posts saved to Firestore `webdata` collection with `type: "threads_post"`.

### Output Schema

Articles are saved with `type: "threads_post"`. See `../../.github/schema/webdata.md`.

### Implementation

```
Request { county, query, tags? }
  │
  ├─ 1. Apify scrape_thread_posts(query)
  │     └─ Call Apify Actor to search Threads for matching posts
  │
  ├─ 2. Per-post processing — process_posts()
  │     ├─ Extract content from caption text
  │     ├─ Firestore dedup (match by content, first 200 chars)
  │     ├─ transform_apify_data() → webdata schema
  │     │   ├─ Extract post_id, username, post_url, like_count
  │     │   ├─ Extract comments_count, repost_count, quote_count
  │     │   ├─ Extract images (highest quality from image_versions2)
  │     │   └─ Convert taken_at timestamp → ISO format
  │     └─ save_article() → Firestore webdata (type: "threads_post")
  │
  └─ 3. Return { articles: [...] }
```

### Reference

| Component        | File                     |
| ---------------- | ------------------------ |
| Endpoint handler | `main.py`                |
| `ThreadsScraper` | `src/threads_scraper.py` |

---

## POST /map — Google Maps Scraping

Scrape place details and reviews from Google Maps for a given search query.

### Request

```json
{
  "query": "花蓮東大門夜市", // required — Google Maps search query
  "raw": false, // optional — return raw data without processing
  "max_reviews": 100 // optional, default 100 — max reviews to fetch
}
```

### Response

Returns place details including reviews, or `{"error": "No place found"}` if no match.

### Implementation

```
Request { query, raw?, max_reviews? }
  │
  ├─ 1. Search for place
  │     │
  │     ├─ [Has Google Maps API key] → Places API v1
  │     │   ├─ POST text search with query (lang=zh-TW, region=tw)
  │     │   ├─ Extract name, address, phone, opening hours, photos
  │     │   └─ Parse county/district from address
  │     │
  │     └─ [No API key] → PlaywrightMapScraper
  │         ├─ search_and_scrape() via browser automation
  │         └─ Extract name, address, phone, website, reviews
  │
  ├─ 2. Fetch reviews (if max_reviews > 0, API key mode only)
  │     └─ _get_reviews_with_fallback()
  │         ├─ Try Playwright: PlaywrightMapScraper.get_reviews()
  │         └─ Fallback Selenium: GoogleMapReviewScraper.process()
  │             ├─ Load page, click reviews tab
  │             ├─ Sort by newest
  │             ├─ Scroll loop (max 60 iterations) to load reviews
  │             ├─ scrapeReviews() — extract name, content, rating, date
  │             ├─ AI fallback if content hit rate < 30%
  │             └─ Deduplicate reviews
  │
  └─ 3. Return place details + reviews
        ├─ raw=true: include full API response + scrape metadata
        └─ raw=false: cleaned output without raw API data
```

### Reference

| Component                  | File                            |
| -------------------------- | ------------------------------- |
| Endpoint handler           | `main.py`                       |
| `MapScraper`               | `src/map_scraper.py`            |
| `PlaywrightMapScraper`     | `src/map_scraper_playwright.py` |
| `GoogleMapReviewScraper`   | `src/map_scraper.py`            |

---

## GET /outboundip — Server IP Check

Returns the server's outbound IP address. Useful for debugging proxy and firewall configurations.

### Request

No parameters.

### Response

Plain text IP address, e.g. `"59.120.213.129"`
