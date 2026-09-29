# SEO Specialist Skill - Quick Start

**One-command SEO automation - No SEO expertise required!**

## 🚀 Quick Usage

### 1. Comprehensive Site Audit

Analyze your website's SEO health with a detailed audit:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py audit \
  --url https://yoursite.com
```

**Output:**
```
==> SEO Site Audit: https://yoursite.com

Meta Tags
✓ Title: Your Awesome Website (25 characters)
✓ Description: Best products and services for your needs (52 characters)
✓ Keywords: products, services, quality
✗ No Open Graph image found

Headings
✓ H1: Welcome to Our Store
✓ H2 tags: 5 found
✓ H3 tags: 12 found

Links
✓ Internal links: 45
✓ External links: 8
✗ 3 broken links found

Images
✓ Total images: 23
✗ 5 images missing alt text

Content Analysis
✓ Word count: 1,850 words
✓ Reading time: ~7 minutes

SEO Score: 78/100

Issues Found:
- Add Open Graph image for social sharing
- Fix 3 broken links
- Add alt text to 5 images
```

---

### 2. Keyword Research & Analysis

Discover important keywords on your page:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py keywords \
  --url https://yoursite.com \
  --min-length 3
```

**Output:**
```
==> Keyword Analysis: https://yoursite.com

Top Keywords (by frequency):
1. products (45 occurrences) - 2.4% density
2. quality (32 occurrences) - 1.7% density
3. services (28 occurrences) - 1.5% density
4. customer (24 occurrences) - 1.3% density
5. premium (20 occurrences) - 1.1% density

Meta Tags Keyword Coverage:
✓ "products" found in title
✓ "quality" found in description
✗ "services" NOT in meta tags

Recommendations:
- Add "services" to meta description
- Consider "customer" in title tag
- Good keyword density (1-3% range)
```

---

### 3. Generate XML Sitemap

Create an SEO-friendly XML sitemap:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py sitemap \
  --url https://yoursite.com \
  --output sitemap.xml \
  --max-urls 500
```

**Output:**
```
==> Generating Sitemap for: https://yoursite.com

Crawling website...
✓ Found: https://yoursite.com/ (priority: 1.0)
✓ Found: https://yoursite.com/about (priority: 0.8)
✓ Found: https://yoursite.com/products (priority: 0.8)
✓ Found: https://yoursite.com/contact (priority: 0.6)

Sitemap Statistics:
- Total URLs: 47
- Homepage: 1
- Category pages: 8
- Product pages: 32
- Info pages: 6

✓ Sitemap saved to: sitemap.xml

Next Steps:
1. Upload sitemap.xml to your website root
2. Submit to Google Search Console
3. Add to robots.txt: Sitemap: https://yoursite.com/sitemap.xml
```

---

### 4. Generate robots.txt

Create a search engine friendly robots.txt:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py robots \
  --domain https://yoursite.com \
  --output robots.txt
```

**Output:**
```
==> Generating robots.txt for: yoursite.com

✓ robots.txt created with best practices:
  - Allow all crawlers
  - Block admin and private areas
  - Specify sitemap location
  - Set crawl-delay for polite crawling

Content Preview:
---
User-agent: *
Allow: /

Disallow: /admin/
Disallow: /private/
Disallow: /api/
Disallow: /*.json$
Disallow: /*?*sort=
Disallow: /*?*filter=

Sitemap: https://yoursite.com/sitemap.xml
Crawl-delay: 1
---

✓ robots.txt saved!

Upload to: https://yoursite.com/robots.txt
```

---

### 5. Add Schema Markup (Structured Data)

Improve search appearance with schema.org markup:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py schema \
  --type website \
  --name "Your Awesome Store" \
  --url https://yoursite.com \
  --description "Best products and services"
```

**Output:**
```
==> Generating Schema Markup: website

✓ Schema.org JSON-LD created:

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Your Awesome Store",
  "url": "https://yoursite.com",
  "description": "Best products and services",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://yoursite.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>

Add this to your <head> section!

Benefits:
✓ Rich search results
✓ Site search box in Google
✓ Better click-through rates
```

---

### 6. Content Optimization Analysis

Optimize your content for target keywords:

```bash
python3 .claude/skills/seo-specialist/scripts/tool.py optimize \
  --url https://yoursite.com/blog/seo-tips \
  --keyword "seo tips"
```

**Output:**
```
==> Content Optimization: https://yoursite.com/blog/seo-tips
Target Keyword: "seo tips"

Keyword Placement:
✓ In URL: /blog/seo-tips
✓ In Title: "10 Essential SEO Tips for Beginners"
✓ In Description: "Learn the best SEO tips to improve..."
✓ In H1: "Essential SEO Tips"
✗ NOT in first paragraph
✓ In body: 8 occurrences

Keyword Density: 1.2% (optimal: 1-2%)

Content Quality:
✓ Word count: 1,450 (good length)
✓ Reading level: Grade 8 (readable)
✓ Images: 6 (good for engagement)
✓ Internal links: 5
✓ External links: 3

Optimization Score: 82/100

Recommendations:
1. Add "seo tips" to first paragraph (important!)
2. Add 2-3 more internal links
3. Consider adding FAQ schema markup
4. Increase keyword usage by 2-3 times
```

---

## 📋 All Commands

```bash
# Comprehensive site audit
tool.py audit --url URL

# Keyword research
tool.py keywords --url URL [--min-length N] [--top N]

# Generate XML sitemap
tool.py sitemap --url URL [--output FILE] [--max-urls N]

# Generate robots.txt
tool.py robots --domain URL [--output FILE]

# Generate schema markup
tool.py schema --type TYPE --name NAME --url URL [--description DESC] [--image URL] [--author NAME]

# Content optimization
tool.py optimize --url URL --keyword KEYWORD
```

---

## 💡 Common SEO Workflows

### Workflow 1: New Website SEO Setup (30 minutes)

```bash
# Step 1: Run comprehensive audit
python3 .claude/skills/seo-specialist/scripts/tool.py audit \
  --url https://yoursite.com

# Step 2: Generate sitemap
python3 .claude/skills/seo-specialist/scripts/tool.py sitemap \
  --url https://yoursite.com \
  --output sitemap.xml

# Step 3: Create robots.txt
python3 .claude/skills/seo-specialist/scripts/tool.py robots \
  --domain https://yoursite.com \
  --output robots.txt

# Step 4: Add website schema
python3 .claude/skills/seo-specialist/scripts/tool.py schema \
  --type website \
  --name "Your Site" \
  --url https://yoursite.com \
  --description "Your site description"

# Step 5: Upload files to your server
# - Upload sitemap.xml to website root
# - Upload robots.txt to website root
# - Add schema JSON-LD to <head> section

# Done! Basic SEO setup complete ✅
```

---

### Workflow 2: Content Optimization (15 minutes)

```bash
# Step 1: Analyze existing content
python3 .claude/skills/seo-specialist/scripts/tool.py optimize \
  --url https://yoursite.com/blog/my-article \
  --keyword "target keyword"

# Step 2: Fix issues from recommendations
# - Add keyword to first paragraph
# - Improve meta description
# - Add internal/external links
# - Optimize images with alt text

# Step 3: Verify improvements
python3 .claude/skills/seo-specialist/scripts/tool.py audit \
  --url https://yoursite.com/blog/my-article

# Done! Content optimized ✅
```

---

### Workflow 3: Keyword Strategy (20 minutes)

```bash
# Step 1: Analyze homepage keywords
python3 .claude/skills/seo-specialist/scripts/tool.py keywords \
  --url https://yoursite.com

# Step 2: Identify gaps and opportunities
# Look for:
# - High-frequency keywords NOT in meta tags
# - Low keyword density (< 1%)
# - Missing important terms

# Step 3: Update content with target keywords
# - Add to title tag
# - Add to meta description
# - Add to H1/H2 headings
# - Add naturally to content

# Step 4: Verify keyword usage
python3 .claude/skills/seo-specialist/scripts/tool.py keywords \
  --url https://yoursite.com

# Done! Keyword strategy optimized ✅
```

---

### Workflow 4: Monthly SEO Health Check (10 minutes)

```bash
# Run comprehensive audit
python3 .claude/skills/seo-specialist/scripts/tool.py audit \
  --url https://yoursite.com

# Check for issues:
# - SEO score below 70? → Fix critical issues
# - Broken links? → Update or remove
# - Missing alt text? → Add to images
# - Low content score? → Improve meta tags

# Update sitemap if new pages added
python3 .claude/skills/seo-specialist/scripts/tool.py sitemap \
  --url https://yoursite.com \
  --output sitemap.xml

# Done! Monthly check complete ✅
```

---

## 🎯 Understanding SEO Scores

### Content Score (0-100)

The audit command calculates a content score based on:

| Component | Max Points | What It Checks |
|-----------|-----------|---------------|
| **Title Tag** | 25 | 30-60 characters, keyword present |
| **Meta Description** | 25 | 120-160 characters, compelling copy |
| **H1 Tag** | 15 | One H1 tag, descriptive, keyword-rich |
| **Image Alt Text** | 15 | All images have descriptive alt text |
| **Content Length** | 10 | Minimum 300 words |
| **Mobile Viewport** | 10 | Mobile-friendly meta tag |

**Score Interpretation:**
- **90-100**: Excellent SEO setup
- **70-89**: Good, minor improvements needed
- **50-69**: Fair, several issues to fix
- **Below 50**: Poor, requires immediate attention

---

### Keyword Density Guidelines

**Optimal Range:** 1-2% for target keywords

- **< 0.5%**: Too low - keyword not emphasized enough
- **0.5-1%**: Low - consider adding more naturally
- **1-2%**: Perfect - natural keyword usage
- **2-3%**: High - may look forced, reduce slightly
- **> 3%**: Over-optimization - risk of keyword stuffing

---

## 🆘 Common SEO Issues & Fixes

### Issue 1: "Low SEO Score (< 70)"

**Fix:**
```bash
# Run audit to identify issues
python3 .claude/skills/seo-specialist/scripts/tool.py audit \
  --url https://yoursite.com

# Common fixes:
# - Add meta description (120-160 chars)
# - Optimize title tag (30-60 chars)
# - Add H1 heading
# - Add alt text to images
# - Increase content length (> 300 words)
```

---

### Issue 2: "Keyword Not Ranking"

**Fix:**
```bash
# Check current keyword usage
python3 .claude/skills/seo-specialist/scripts/tool.py keywords \
  --url https://yoursite.com/page

# Optimize content for target keyword
python3 .claude/skills/seo-specialist/scripts/tool.py optimize \
  --url https://yoursite.com/page \
  --keyword "target keyword"

# Follow recommendations:
# - Add to title tag
# - Add to meta description
# - Add to first paragraph
# - Maintain 1-2% density
```

---

### Issue 3: "Not Indexed by Google"

**Fix:**
```bash
# Create sitemap
python3 .claude/skills/seo-specialist/scripts/tool.py sitemap \
  --url https://yoursite.com \
  --output sitemap.xml

# Create robots.txt
python3 .claude/skills/seo-specialist/scripts/tool.py robots \
  --domain https://yoursite.com \
  --output robots.txt

# Upload both files to website root
# Submit sitemap to Google Search Console
```

---

### Issue 4: "Poor Click-Through Rate"

**Fix:**
```bash
# Add schema markup for rich results
python3 .claude/skills/seo-specialist/scripts/tool.py schema \
  --type article \
  --name "Article Title" \
  --url https://yoursite.com/article \
  --description "Compelling description" \
  --image https://yoursite.com/image.jpg \
  --author "Author Name"

# Add to <head> section for:
# - Star ratings
# - Author info
# - Publication date
# - Breadcrumbs
```

---

## 📚 SEO Best Practices (Without Being an Expert)

### 1. Title Tags
- **Length**: 30-60 characters
- **Format**: Primary Keyword | Brand Name
- **Example**: "Best Running Shoes 2026 | ShoesStore"

### 2. Meta Descriptions
- **Length**: 120-160 characters
- **Include**: Target keyword + call-to-action
- **Example**: "Discover the best running shoes of 2026. Free shipping on orders over $50. Shop now!"

### 3. Headings
- **H1**: One per page, describes main topic
- **H2**: Section headings (3-5 per page)
- **H3**: Subsection headings

### 4. Content
- **Minimum**: 300 words (longer is better for ranking)
- **Target**: 1,000-2,000 words for blog posts
- **Quality**: Original, valuable, answers user questions

### 5. Images
- **Always**: Add descriptive alt text
- **Format**: image-name-with-keywords.jpg
- **Size**: Optimize for fast loading (< 200KB)

### 6. Links
- **Internal**: Link to 3-5 related pages
- **External**: Link to 1-2 authoritative sources
- **Anchor text**: Use descriptive keywords

---

## ✨ Features

- ✅ No SEO expertise required - Just run commands!
- ✅ Comprehensive site audits with scoring
- ✅ Keyword research and density analysis
- ✅ Automatic sitemap generation
- ✅ robots.txt best practices
- ✅ Schema.org structured data
- ✅ Content optimization recommendations
- ✅ Clear actionable insights
- ✅ Industry-standard SEO practices

---

## 📊 Example: Complete SEO Analysis

```bash
# Full SEO analysis in one workflow
cd .claude/skills/seo-specialist/scripts

# 1. Audit
python3 tool.py audit --url https://example.com > seo-audit.txt

# 2. Keywords
python3 tool.py keywords --url https://example.com > keywords.txt

# 3. Sitemap
python3 tool.py sitemap --url https://example.com --output sitemap.xml

# 4. robots.txt
python3 tool.py robots --domain https://example.com --output robots.txt

# 5. Schema
python3 tool.py schema --type website --name "Example" --url https://example.com

# Review all outputs and implement recommendations
# Upload sitemap.xml and robots.txt
# Add schema markup to HTML

# Done! Complete SEO setup ✅
```

---

**Last Updated:** 2026-02-09
**Status:** Production-ready ✅
**No SEO expertise required:** Just follow the commands! 🚀
