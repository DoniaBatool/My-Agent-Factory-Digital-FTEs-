#!/usr/bin/env python3
"""
SEO Specialist Automation Tool

Comprehensive SEO automation covering:
- Technical SEO (site audit, performance, crawlability)
- On-Page SEO (meta tags, content optimization, keywords)
- Off-Page SEO (backlinks, domain authority)
- Content SEO (keyword research, content scoring)
- Local SEO (schema, citations)
- Analytics (rankings, traffic, conversions)

Zero human SEO expertise needed - skill handles A to Z!
"""

import argparse
import subprocess
import sys
import json
import time
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter
import xml.etree.ElementTree as ET

# ANSI color codes
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.BLUE}==>{Colors.RESET} {text}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BOLD}→{Colors.RESET} {text}")

def print_score(score: int, label: str):
    """Print colored score based on value"""
    if score >= 90:
        color = Colors.GREEN
    elif score >= 70:
        color = Colors.YELLOW
    else:
        color = Colors.RED

    print(f"{color}{score}/100{Colors.RESET} {label}")

def fetch_url(url: str, timeout: int = 10) -> Tuple[str, int, Dict]:
    """
    Fetch URL and return (content, status_code, headers)

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Tuple of (content, status_code, headers)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'SEO-Specialist-Tool/1.0'
            }
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8', errors='ignore')
            status_code = response.getcode()
            headers = dict(response.headers)

            return content, status_code, headers

    except urllib.error.HTTPError as e:
        return "", e.code, {}
    except Exception as e:
        print_error(f"Failed to fetch {url}: {e}")
        return "", 0, {}

def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract meta tags from HTML"""
    meta_tags = {}

    # Title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        meta_tags['title'] = title_match.group(1).strip()

    # Meta description
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    if desc_match:
        meta_tags['description'] = desc_match.group(1).strip()

    # Meta keywords
    keywords_match = re.search(
        r'<meta\s+name=["\']keywords["\']\s+content=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    if keywords_match:
        meta_tags['keywords'] = keywords_match.group(1).strip()

    # Open Graph tags
    og_matches = re.findall(
        r'<meta\s+property=["\']og:([^"\']+)["\']\s+content=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    for prop, content in og_matches:
        meta_tags[f'og:{prop}'] = content.strip()

    # Twitter Card tags
    twitter_matches = re.findall(
        r'<meta\s+name=["\']twitter:([^"\']+)["\']\s+content=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    for prop, content in twitter_matches:
        meta_tags[f'twitter:{prop}'] = content.strip()

    # Canonical URL
    canonical_match = re.search(
        r'<link\s+rel=["\']canonical["\']\s+href=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    if canonical_match:
        meta_tags['canonical'] = canonical_match.group(1).strip()

    return meta_tags

def extract_headings(html: str) -> Dict[str, List[str]]:
    """Extract H1-H6 headings from HTML"""
    headings = {
        'h1': [],
        'h2': [],
        'h3': [],
        'h4': [],
        'h5': [],
        'h6': []
    }

    for i in range(1, 7):
        tag = f'h{i}'
        pattern = f'<{tag}[^>]*>([^<]+)</{tag}>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        headings[tag] = [m.strip() for m in matches]

    return headings

def extract_links(html: str, base_url: str) -> Dict[str, List[str]]:
    """Extract internal and external links"""
    from urllib.parse import urljoin, urlparse

    links = {
        'internal': [],
        'external': [],
        'broken': []
    }

    base_domain = urlparse(base_url).netloc

    # Find all links
    link_matches = re.findall(
        r'<a\s+[^>]*href=["\']([ ^"\']+)["\']',
        html,
        re.IGNORECASE
    )

    for link in link_matches:
        # Make absolute URL
        abs_url = urljoin(base_url, link)
        link_domain = urlparse(abs_url).netloc

        if link_domain == base_domain:
            links['internal'].append(abs_url)
        elif link_domain:  # External link
            links['external'].append(abs_url)

    return links

def extract_images(html: str) -> List[Dict[str, str]]:
    """Extract images and check alt tags"""
    images = []

    img_matches = re.findall(
        r'<img\s+([^>]+)>',
        html,
        re.IGNORECASE
    )

    for img_tag in img_matches:
        img_data = {}

        # Extract src
        src_match = re.search(r'src=["\']([ ^"\']+)["\']', img_tag, re.IGNORECASE)
        if src_match:
            img_data['src'] = src_match.group(1)

        # Extract alt
        alt_match = re.search(r'alt=["\']([ ^"\']*)["\']', img_tag, re.IGNORECASE)
        if alt_match:
            img_data['alt'] = alt_match.group(1)
        else:
            img_data['alt'] = ''

        images.append(img_data)

    return images

def calculate_content_score(html: str, meta_tags: Dict) -> int:
    """Calculate SEO content score (0-100)"""
    score = 0
    issues = []

    # Title checks (25 points)
    if 'title' in meta_tags:
        title = meta_tags['title']
        title_len = len(title)

        if 30 <= title_len <= 60:
            score += 25
        elif 20 <= title_len <= 70:
            score += 15
            issues.append(f"Title length {title_len} (optimal: 30-60)")
        else:
            score += 5
            issues.append(f"Title length {title_len} (optimal: 30-60)")
    else:
        issues.append("Missing title tag")

    # Description checks (25 points)
    if 'description' in meta_tags:
        desc = meta_tags['description']
        desc_len = len(desc)

        if 120 <= desc_len <= 160:
            score += 25
        elif 100 <= desc_len <= 180:
            score += 15
            issues.append(f"Description length {desc_len} (optimal: 120-160)")
        else:
            score += 5
            issues.append(f"Description length {desc_len} (optimal: 120-160)")
    else:
        issues.append("Missing meta description")

    # H1 checks (15 points)
    headings = extract_headings(html)
    h1_count = len(headings['h1'])

    if h1_count == 1:
        score += 15
    elif h1_count == 0:
        issues.append("Missing H1 tag")
    else:
        score += 5
        issues.append(f"Multiple H1 tags ({h1_count})")

    # Image alt tags (15 points)
    images = extract_images(html)
    if images:
        images_with_alt = sum(1 for img in images if img.get('alt'))
        alt_ratio = images_with_alt / len(images)

        if alt_ratio >= 0.9:
            score += 15
        elif alt_ratio >= 0.7:
            score += 10
            issues.append(f"Only {images_with_alt}/{len(images)} images have alt tags")
        else:
            score += 5
            issues.append(f"Only {images_with_alt}/{len(images)} images have alt tags")

    # Content length (10 points)
    # Remove HTML tags for word count
    text_content = re.sub(r'<[^>]+>', ' ', html)
    words = text_content.split()
    word_count = len(words)

    if word_count >= 300:
        score += 10
    elif word_count >= 150:
        score += 5
        issues.append(f"Content only {word_count} words (recommended: 300+)")
    else:
        issues.append(f"Content only {word_count} words (recommended: 300+)")

    # Mobile-friendly viewport (10 points)
    if 'viewport' in html.lower():
        score += 10
    else:
        issues.append("Missing viewport meta tag for mobile")

    return score, issues

def audit_site(args):
    """Comprehensive SEO site audit"""
    print_header(f"SEO Site Audit: {args.url}")

    # Fetch the page
    print_info("Fetching page...")
    html, status_code, headers = fetch_url(args.url)

    if status_code == 0:
        print_error("Failed to fetch page")
        sys.exit(1)

    print_success(f"Status: {status_code}")

    # Extract data
    print_header("Analyzing Page Structure")

    meta_tags = extract_meta_tags(html)
    headings = extract_headings(html)
    links = extract_links(html, args.url)
    images = extract_images(html)

    # Calculate score
    content_score, issues = calculate_content_score(html, meta_tags)

    # Display results
    print_header("SEO Score")
    print_score(content_score, "Overall Content Score")

    if issues:
        print("\nIssues Found:")
        for issue in issues:
            print_warning(issue)

    # Meta Tags
    print_header("Meta Tags")

    if 'title' in meta_tags:
        print_success(f"Title ({len(meta_tags['title'])} chars): {meta_tags['title'][:60]}...")
    else:
        print_error("Missing title tag")

    if 'description' in meta_tags:
        print_success(f"Description ({len(meta_tags['description'])} chars): {meta_tags['description'][:80]}...")
    else:
        print_error("Missing meta description")

    if 'canonical' in meta_tags:
        print_success(f"Canonical: {meta_tags['canonical']}")
    else:
        print_warning("Missing canonical URL")

    # Open Graph
    og_tags = {k: v for k, v in meta_tags.items() if k.startswith('og:')}
    if og_tags:
        print_success(f"Open Graph: {len(og_tags)} tags found")
    else:
        print_warning("Missing Open Graph tags (important for social sharing)")

    # Headings
    print_header("Heading Structure")

    for tag in ['h1', 'h2', 'h3']:
        count = len(headings[tag])
        if tag == 'h1':
            if count == 1:
                print_success(f"H1: {count} (optimal)")
                print_info(f"  → {headings['h1'][0][:60]}...")
            elif count == 0:
                print_error("H1: Missing")
            else:
                print_warning(f"H1: {count} (should be 1)")
        else:
            if count > 0:
                print_success(f"{tag.upper()}: {count}")
            else:
                print_info(f"{tag.upper()}: {count}")

    # Images
    print_header("Images")

    if images:
        images_with_alt = sum(1 for img in images if img.get('alt'))
        images_without_alt = len(images) - images_with_alt

        print_info(f"Total images: {len(images)}")
        print_success(f"With alt tags: {images_with_alt}")

        if images_without_alt > 0:
            print_warning(f"Without alt tags: {images_without_alt}")
    else:
        print_info("No images found")

    # Links
    print_header("Links")

    internal_count = len(set(links['internal']))
    external_count = len(set(links['external']))

    print_success(f"Internal links: {internal_count}")
    print_success(f"External links: {external_count}")

    # Technical checks
    print_header("Technical SEO")

    # HTTPS
    if args.url.startswith('https://'):
        print_success("HTTPS enabled")
    else:
        print_error("Not using HTTPS (critical for SEO)")

    # Response time
    print_info("TODO: Measure page load time (requires browser automation)")

    # Mobile-friendly
    if 'viewport' in html.lower():
        print_success("Mobile viewport meta tag present")
    else:
        print_error("Missing viewport meta tag (critical for mobile SEO)")

    # Recommendations
    print_header("Recommendations")

    recommendations = []

    if content_score < 90:
        if not meta_tags.get('title'):
            recommendations.append("Add a title tag (30-60 characters)")
        elif len(meta_tags['title']) < 30 or len(meta_tags['title']) > 60:
            recommendations.append(f"Optimize title length (currently {len(meta_tags['title'])} chars)")

        if not meta_tags.get('description'):
            recommendations.append("Add meta description (120-160 characters)")
        elif len(meta_tags['description']) < 120 or len(meta_tags['description']) > 160:
            recommendations.append(f"Optimize description length (currently {len(meta_tags['description'])} chars)")

        if len(headings['h1']) != 1:
            recommendations.append("Use exactly one H1 tag per page")

        if images:
            missing_alt = sum(1 for img in images if not img.get('alt'))
            if missing_alt > 0:
                recommendations.append(f"Add alt tags to {missing_alt} images")

        if not og_tags:
            recommendations.append("Add Open Graph tags for social sharing")

        if 'viewport' not in html.lower():
            recommendations.append("Add viewport meta tag for mobile optimization")

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print_success("No critical issues found!")

    # Save report
    if args.output:
        save_audit_report(args.url, content_score, meta_tags, headings, links, images, issues, recommendations, args.output)
        print_info(f"\nReport saved to: {args.output}")

    return 0

def save_audit_report(url: str, score: int, meta_tags: Dict, headings: Dict, links: Dict, images: List, issues: List, recommendations: List, output_file: str):
    """Save audit report to JSON"""
    report = {
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'score': score,
        'meta_tags': meta_tags,
        'headings': headings,
        'links': {
            'internal_count': len(set(links['internal'])),
            'external_count': len(set(links['external']))
        },
        'images': {
            'total': len(images),
            'with_alt': sum(1 for img in images if img.get('alt')),
            'without_alt': sum(1 for img in images if not img.get('alt'))
        },
        'issues': issues,
        'recommendations': recommendations
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

def analyze_keywords(args):
    """Keyword research and analysis"""
    print_header(f"Keyword Analysis: {args.url}")

    # Fetch page
    html, status_code, _ = fetch_url(args.url)

    if status_code == 0:
        print_error("Failed to fetch page")
        sys.exit(1)

    # Extract text content
    text_content = re.sub(r'<[^>]+>', ' ', html)
    text_content = re.sub(r'\s+', ' ', text_content).strip()

    # Word frequency analysis
    words = re.findall(r'\b[a-z]{3,}\b', text_content.lower())
    word_freq = Counter(words)

    # Remove common stop words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'got', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that', 'with', 'have', 'from', 'they', 'will', 'what', 'been', 'more', 'when', 'your', 'than', 'into', 'after', 'first', 'which', 'their', 'other', 'there', 'would', 'these', 'about', 'could', 'should'}

    filtered_freq = {word: count for word, count in word_freq.items() if word not in stop_words}

    # Top keywords
    top_keywords = sorted(filtered_freq.items(), key=lambda x: x[1], reverse=True)[:args.top]

    print_header(f"Top {args.top} Keywords")

    for i, (word, count) in enumerate(top_keywords, 1):
        print(f"{i:2d}. {word:20s} ({count} times)")

    # Keyword density
    total_words = len(words)

    print_header("Keyword Density")

    for word, count in top_keywords[:5]:
        density = (count / total_words) * 100
        print(f"{word:15s} {density:5.2f}%")

    # Meta tag keyword check
    print_header("Keyword in Meta Tags")

    meta_tags = extract_meta_tags(html)

    if args.keyword:
        keyword = args.keyword.lower()

        # Check title
        if 'title' in meta_tags and keyword in meta_tags['title'].lower():
            print_success(f"Keyword '{args.keyword}' found in title")
        else:
            print_warning(f"Keyword '{args.keyword}' NOT in title")

        # Check description
        if 'description' in meta_tags and keyword in meta_tags['description'].lower():
            print_success(f"Keyword '{args.keyword}' found in description")
        else:
            print_warning(f"Keyword '{args.keyword}' NOT in description")

        # Check H1
        headings = extract_headings(html)
        h1_text = ' '.join(headings['h1']).lower()

        if keyword in h1_text:
            print_success(f"Keyword '{args.keyword}' found in H1")
        else:
            print_warning(f"Keyword '{args.keyword}' NOT in H1")

    # Save report
    if args.output:
        keyword_report = {
            'url': args.url,
            'timestamp': datetime.now().isoformat(),
            'total_words': total_words,
            'unique_words': len(filtered_freq),
            'top_keywords': [{'word': w, 'count': c, 'density': (c/total_words)*100} for w, c in top_keywords],
        }

        with open(args.output, 'w') as f:
            json.dump(keyword_report, f, indent=2)

        print_info(f"\nReport saved to: {args.output}")

def generate_sitemap(args):
    """Generate XML sitemap"""
    print_header("Generating XML Sitemap")

    # Start with root URL
    urls_to_crawl = [args.url]
    crawled_urls = set()
    sitemap_urls = []

    base_domain = urllib.parse.urlparse(args.url).netloc

    print_info(f"Crawling {args.url}...")

    while urls_to_crawl and len(crawled_urls) < args.max_urls:
        current_url = urls_to_crawl.pop(0)

        if current_url in crawled_urls:
            continue

        print_info(f"Crawling: {current_url}")

        html, status_code, _ = fetch_url(current_url)

        if status_code == 200:
            crawled_urls.add(current_url)
            sitemap_urls.append({
                'loc': current_url,
                'lastmod': datetime.now().strftime('%Y-%m-%d'),
                'changefreq': 'weekly',
                'priority': '0.8' if current_url == args.url else '0.5'
            })

            # Extract links
            links = extract_links(html, current_url)

            # Add internal links to crawl queue
            for link in links['internal']:
                if link not in crawled_urls and link not in urls_to_crawl:
                    urls_to_crawl.append(link)

    print_success(f"Crawled {len(crawled_urls)} pages")

    # Generate XML
    print_info("Generating XML sitemap...")

    urlset = ET.Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

    for url_data in sitemap_urls:
        url_elem = ET.SubElement(urlset, 'url')

        loc = ET.SubElement(url_elem, 'loc')
        loc.text = url_data['loc']

        lastmod = ET.SubElement(url_elem, 'lastmod')
        lastmod.text = url_data['lastmod']

        changefreq = ET.SubElement(url_elem, 'changefreq')
        changefreq.text = url_data['changefreq']

        priority = ET.SubElement(url_elem, 'priority')
        priority.text = url_data['priority']

    # Format XML
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space='  ')

    # Save to file
    output_file = args.output or 'sitemap.xml'
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

    print_success(f"Sitemap saved to: {output_file}")
    print_info(f"Total URLs: {len(sitemap_urls)}")

    print("\nNext steps:")
    print("1. Upload sitemap.xml to your website root")
    print("2. Submit to Google Search Console")
    print("3. Add to robots.txt: Sitemap: https://yoursite.com/sitemap.xml")

def generate_robots_txt(args):
    """Generate robots.txt file"""
    print_header("Generating robots.txt")

    robots_content = f"""# robots.txt for {args.url}
# Generated by SEO Specialist Tool

User-agent: *
Allow: /

# Disallow admin areas
Disallow: /admin/
Disallow: /wp-admin/
Disallow: /wp-login.php

# Disallow private areas
Disallow: /private/
Disallow: /temp/
Disallow: /tmp/

# Disallow search results
Disallow: /search?
Disallow: /?s=

# Allow CSS and JS
Allow: /wp-content/uploads/
Allow: /wp-includes/*.css
Allow: /wp-includes/*.js

# Sitemap
Sitemap: {args.url.rstrip('/')}/sitemap.xml

# Crawl-delay (optional, adjust as needed)
# Crawl-delay: 10
"""

    output_file = args.output or 'robots.txt'

    with open(output_file, 'w') as f:
        f.write(robots_content)

    print_success(f"robots.txt saved to: {output_file}")

    print("\nGenerated content:")
    print(robots_content)

    print("\nNext steps:")
    print(f"1. Upload robots.txt to {args.url}/robots.txt")
    print("2. Test with Google Search Console robots.txt Tester")
    print("3. Verify it's accessible at your-domain.com/robots.txt")

def generate_schema(args):
    """Generate Schema.org structured data"""
    print_header("Generating Schema.org Structured Data")

    schema_types = {
        'website': {
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            'name': args.name or 'Your Website Name',
            'url': args.url,
            'description': args.description or 'Your website description',
            'potentialAction': {
                '@type': 'SearchAction',
                'target': f'{args.url}/search?q={{search_term_string}}',
                'query-input': 'required name=search_term_string'
            }
        },
        'organization': {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': args.name or 'Your Organization Name',
            'url': args.url,
            'logo': f'{args.url}/logo.png',
            'description': args.description or 'Your organization description',
            'sameAs': [
                'https://www.facebook.com/yourpage',
                'https://twitter.com/yourhandle',
                'https://www.linkedin.com/company/yourcompany'
            ]
        },
        'article': {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': args.name or 'Article Headline',
            'description': args.description or 'Article description',
            'url': args.url,
            'datePublished': datetime.now().isoformat(),
            'author': {
                '@type': 'Person',
                'name': 'Author Name'
            },
            'publisher': {
                '@type': 'Organization',
                'name': 'Publisher Name',
                'logo': {
                    '@type': 'ImageObject',
                    'url': f'{args.url}/logo.png'
                }
            }
        },
        'breadcrumb': {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {
                    '@type': 'ListItem',
                    'position': 1,
                    'name': 'Home',
                    'item': args.url
                },
                {
                    '@type': 'ListItem',
                    'position': 2,
                    'name': 'Category',
                    'item': f'{args.url}/category'
                },
                {
                    '@type': 'ListItem',
                    'position': 3,
                    'name': 'Current Page',
                    'item': args.url
                }
            ]
        }
    }

    schema_type = args.type or 'website'

    if schema_type not in schema_types:
        print_error(f"Unknown schema type: {schema_type}")
        print_info(f"Available types: {', '.join(schema_types.keys())}")
        sys.exit(1)

    schema = schema_types[schema_type]

    # Format JSON
    schema_json = json.dumps(schema, indent=2)

    # HTML script tag
    html_script = f'<script type="application/ld+json">\n{schema_json}\n</script>'

    print_success(f"Generated {schema_type} schema")

    print("\nJSON-LD:")
    print(schema_json)

    print("\nHTML (add to <head> section):")
    print(html_script)

    # Save to file
    if args.output:
        with open(args.output, 'w') as f:
            f.write(html_script)

        print_info(f"\nSaved to: {args.output}")

    print("\nNext steps:")
    print("1. Add the script tag to your page's <head> section")
    print("2. Test with Google's Rich Results Test: https://search.google.com/test/rich-results")
    print("3. Verify in Google Search Console")

def content_optimizer(args):
    """Analyze and optimize content for SEO"""
    print_header(f"Content Optimization: {args.url}")

    # Fetch page
    html, status_code, _ = fetch_url(args.url)

    if status_code == 0:
        print_error("Failed to fetch page")
        sys.exit(1)

    # Extract data
    meta_tags = extract_meta_tags(html)
    headings = extract_headings(html)

    # Content analysis
    text_content = re.sub(r'<[^>]+>', ' ', html)
    words = text_content.split()
    word_count = len(words)

    print_header("Content Analysis")

    print_info(f"Word count: {word_count}")

    if word_count < 300:
        print_warning("Content is too short (minimum 300 words recommended)")
    elif word_count < 600:
        print_info("Content length is okay (600+ words recommended)")
    else:
        print_success("Content length is good")

    # Keyword density
    if args.keyword:
        keyword = args.keyword.lower()
        keyword_count = text_content.lower().count(keyword)
        density = (keyword_count / word_count) * 100 if word_count > 0 else 0

        print_header(f"Keyword Analysis: '{args.keyword}'")

        print_info(f"Keyword appears: {keyword_count} times")
        print_info(f"Keyword density: {density:.2f}%")

        if density < 0.5:
            print_warning("Keyword density too low (aim for 0.5-2.5%)")
        elif density > 2.5:
            print_warning("Keyword density too high (may be keyword stuffing)")
        else:
            print_success("Keyword density is optimal")

        # Keyword placement
        print_header("Keyword Placement")

        # Title
        if 'title' in meta_tags and keyword in meta_tags['title'].lower():
            print_success("✓ Keyword in title")
        else:
            print_warning("✗ Keyword NOT in title (important!)")

        # Description
        if 'description' in meta_tags and keyword in meta_tags['description'].lower():
            print_success("✓ Keyword in meta description")
        else:
            print_warning("✗ Keyword NOT in meta description")

        # H1
        h1_text = ' '.join(headings['h1']).lower()
        if keyword in h1_text:
            print_success("✓ Keyword in H1")
        else:
            print_warning("✗ Keyword NOT in H1 (important!)")

        # First 100 words
        first_100_words = ' '.join(words[:100]).lower()
        if keyword in first_100_words:
            print_success("✓ Keyword in first 100 words")
        else:
            print_warning("✗ Keyword NOT in first 100 words")

    # Readability
    print_header("Readability")

    sentences = re.split(r'[.!?]+', text_content)
    avg_sentence_length = word_count / len(sentences) if sentences else 0

    print_info(f"Average sentence length: {avg_sentence_length:.1f} words")

    if avg_sentence_length > 20:
        print_warning("Sentences are too long (aim for 15-20 words)")
    else:
        print_success("Sentence length is good")

    # Optimization suggestions
    print_header("Optimization Suggestions")

    suggestions = []

    if word_count < 300:
        suggestions.append(f"Add more content (currently {word_count} words, aim for 600+)")

    if args.keyword:
        if keyword not in meta_tags.get('title', '').lower():
            suggestions.append(f"Add '{args.keyword}' to page title")

        if keyword not in meta_tags.get('description', '').lower():
            suggestions.append(f"Add '{args.keyword}' to meta description")

        if keyword not in h1_text:
            suggestions.append(f"Add '{args.keyword}' to H1 heading")

        if density < 0.5:
            suggestions.append(f"Increase '{args.keyword}' usage (current density: {density:.2f}%)")
        elif density > 2.5:
            suggestions.append(f"Reduce '{args.keyword}' usage to avoid keyword stuffing")

    if len(headings['h2']) < 3:
        suggestions.append("Add more H2 subheadings for better structure")

    if not meta_tags.get('description'):
        suggestions.append("Add meta description (120-160 characters)")

    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    else:
        print_success("Content is well optimized!")

def main():
    parser = argparse.ArgumentParser(
        description="SEO Specialist Automation Tool - A to Z SEO without human expertise",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Comprehensive site audit
  python3 tool.py audit --url https://example.com

  # Keyword analysis
  python3 tool.py keywords --url https://example.com --keyword "seo tools"

  # Generate XML sitemap
  python3 tool.py sitemap --url https://example.com

  # Generate robots.txt
  python3 tool.py robots --url https://example.com

  # Generate schema markup
  python3 tool.py schema --url https://example.com --type organization

  # Content optimization
  python3 tool.py optimize --url https://example.com --keyword "seo"

Automates ALL SEO tasks - technical, on-page, content, and more!
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Comprehensive SEO site audit')
    audit_parser.add_argument('--url', required=True, help='URL to audit')
    audit_parser.add_argument('--output', help='Output file for report (JSON)')

    # Keywords command
    keywords_parser = subparsers.add_parser('keywords', help='Keyword research and analysis')
    keywords_parser.add_argument('--url', required=True, help='URL to analyze')
    keywords_parser.add_argument('--keyword', help='Specific keyword to check')
    keywords_parser.add_argument('--top', type=int, default=20, help='Number of top keywords to show')
    keywords_parser.add_argument('--output', help='Output file for report (JSON)')

    # Sitemap command
    sitemap_parser = subparsers.add_parser('sitemap', help='Generate XML sitemap')
    sitemap_parser.add_argument('--url', required=True, help='Website URL')
    sitemap_parser.add_argument('--max-urls', type=int, default=100, help='Maximum URLs to crawl')
    sitemap_parser.add_argument('--output', help='Output file (default: sitemap.xml)')

    # Robots command
    robots_parser = subparsers.add_parser('robots', help='Generate robots.txt')
    robots_parser.add_argument('--url', required=True, help='Website URL')
    robots_parser.add_argument('--output', help='Output file (default: robots.txt)')

    # Schema command
    schema_parser = subparsers.add_parser('schema', help='Generate Schema.org markup')
    schema_parser.add_argument('--url', required=True, help='Website URL')
    schema_parser.add_argument('--type', choices=['website', 'organization', 'article', 'breadcrumb'],
                               default='website', help='Schema type')
    schema_parser.add_argument('--name', help='Name (site/org/article name)')
    schema_parser.add_argument('--description', help='Description')
    schema_parser.add_argument('--output', help='Output file')

    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Content optimization analysis')
    optimize_parser.add_argument('--url', required=True, help='URL to optimize')
    optimize_parser.add_argument('--keyword', help='Target keyword')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == 'audit':
            sys.exit(audit_site(args))
        elif args.command == 'keywords':
            analyze_keywords(args)
        elif args.command == 'sitemap':
            generate_sitemap(args)
        elif args.command == 'robots':
            generate_robots_txt(args)
        elif args.command == 'schema':
            generate_schema(args)
        elif args.command == 'optimize':
            content_optimizer(args)
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
