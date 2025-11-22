#!/usr/bin/env python3
"""
Simple approach: Just use really good browser headers to bypass blocking.

Sometimes the simplest solution works - proper headers that make the request
look exactly like a real browser, without the complexity of proxies.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import sys
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import re


@dataclass
class LiveListing:
    """Represents a live listing from Cardmarket."""
    price: float
    condition: str
    seller: str
    seller_country: str = "Unknown"
    language: str = "Unknown"
    quantity: int = 1
    foil: bool = False


class SimpleBrowserScraper:
    """Simple scraper that just mimics a real browser perfectly."""
    
    def __init__(self, delay_range: tuple = (3.0, 5.0), max_retries: int = 1, save_images: bool = False, image_dir: str = "card_images"):
        """
        Initialize the simple browser scraper.
        
        Args:
            delay_range: Random delay range between requests (min, max) seconds (default: 3-5s, increases if rate limited)
            max_retries: Maximum number of retry attempts for failed requests
            save_images: Whether to save card images
            image_dir: Directory to save card images
        """
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.save_images = save_images
        self.image_dir = image_dir
        self.session = requests.Session()
        self.rate_limited = False  # Track if we've been rate limited
        
        # Create image directory if needed
        if self.save_images:
            import os
            os.makedirs(self.image_dir, exist_ok=True)
        
        # Set up session to look exactly like Chrome
        self._setup_realistic_session()
    
    def _setup_realistic_session(self):
        """Set up the session to look exactly like a real Chrome browser."""
        
        # Perfect Chrome headers (copied from real browser)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Cache-Control': 'max-age=0'
        })
        
        # Set a realistic timeout
        self.session.timeout = 30
    
    def _make_realistic_request(self, url: str, retry_attempt: int = 0) -> Optional[requests.Response]:
        """Make a request that looks exactly like a real browser with retry logic."""
        
        # Adaptive delay: start fast, slow down if rate limited
        if self.rate_limited:
            delay = random.uniform(9.0, 12.0)
        elif retry_attempt > 0:
            base_delay = random.uniform(*self.delay_range)
            retry_multiplier = 2 ** retry_attempt
            delay = base_delay * retry_multiplier
        else:
            delay = random.uniform(*self.delay_range)
        
        time.sleep(delay)
        
        try:
            # First, let's visit the main site to get cookies/session
            main_response = self.session.get('https://www.cardmarket.com/en/Magic', timeout=15)
            
            # Small delay
            time.sleep(random.uniform(1.0, 2.0))
            
            # Now make the actual request
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                return response
            else:
                # Retry on certain status codes with exponential backoff
                if response.status_code in [429, 503, 504] and retry_attempt < self.max_retries:
                    if response.status_code == 429:
                        self.rate_limited = True
                        # Exponential backoff: 30s, 60s, 120s
                        wait_time = 30 * (2 ** retry_attempt)
                        print(f"⚠️  Rate limited (attempt {retry_attempt + 1}/{self.max_retries + 1}), waiting {wait_time}s...")
                    else:
                        wait_time = 10 * (2 ** retry_attempt)
                        print(f"⚠️  Server error {response.status_code} (attempt {retry_attempt + 1}/{self.max_retries + 1}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_realistic_request(url, retry_attempt + 1)
                
                # If we exhausted retries due to rate limiting, stop the script
                if response.status_code == 429:
                    raise Exception(f"❌ RATE LIMITED: CardMarket is blocking requests after {retry_attempt + 1} attempts. Stopping script to avoid ban.")
                
                return None
                
        except requests.exceptions.Timeout:
            if retry_attempt < self.max_retries:
                return self._make_realistic_request(url, retry_attempt + 1)
            return None
        except requests.exceptions.ConnectionError as e:
            if retry_attempt < self.max_retries:
                return self._make_realistic_request(url, retry_attempt + 1)
            return None
        except requests.exceptions.RequestException as e:
            if retry_attempt < self.max_retries:
                return self._make_realistic_request(url, retry_attempt + 1)
            return None
    
    def fetch_listings(self, url: str, max_listings: int = 20, retry_count: int = 0) -> List[LiveListing]:
        """
        Fetch live listings from a Cardmarket product page.
        
        Args:
            url: The Cardmarket product URL
            max_listings: Maximum number of listings to fetch
            retry_count: Internal retry counter
            
        Returns:
            List of LiveListing objects
        """
        response = self._make_realistic_request(url)
        
        if not response:
            print("   ❌ Could not fetch live prices")
            return []
        
        # Decode the response properly (requests handles decompression automatically)
        try:
            html_content = response.text
            self._save_debug_html(html_content, url, "success")
        except Exception as e:
            # Try to get raw content as last resort
            try:
                html_content = response.content.decode('utf-8', errors='ignore')
                self._save_debug_html(html_content, url, "decompression_failed", str(e))
            except Exception as decode_error:
                self._save_debug_info(url, "decode_failed", f"Decompression error: {e}, Decode error: {decode_error}", response)
                return []
        
        # Check if we got the right page
        if 'cardmarket' not in html_content.lower():
            self._save_debug_html(html_content, url, "not_cardmarket")
            return []
        
        # Check for blocked/forbidden ONLY if there are no article listings
        # (Words may appear in tooltips/UI even on valid pages)
        if ('blocked' in html_content.lower() or 'forbidden' in html_content.lower()) and 'article-row' not in html_content:
            self._save_debug_html(html_content, url, "blocked")
            return []
        
        # Check if we landed on an expansion list instead of a card page
        # More specific check: multi-version pages have "Page 1 of" but NO article-row listings
        if 'Page 1 of' in html_content and 'Singles/' in url and 'article-row' not in html_content:
            # Extract card name from URL
            parts = url.split('/')
            if len(parts) >= 2:
                card_name_slug = parts[-1].split('?')[0]
                
                # Try multiple fallback strategies
                if retry_count == 0:
                    # First retry: Try with -V-1
                    if not card_name_slug.endswith('-V-1'):
                        print(f"   🔄 Multiple versions detected, trying {card_name_slug}-V-1...")
                        new_url = url.replace(f'/{card_name_slug}?', f'/{card_name_slug}-V-1?')
                        self._save_debug_html(html_content, url, "multiple_versions_retrying_v1")
                        return self.fetch_listings(new_url, max_listings, retry_count + 1)
                elif retry_count == 1:
                    # Second retry: Try collapsing internal hyphens (e.g., "Ifh-Biff-Efreet" → "IfhBiff-Efreet")
                    # This handles cases where CardMarket treats hyphenated names as compound words
                    if '-' in card_name_slug and card_name_slug.count('-') >= 2:
                        # Remove -V-1 if present for transformation
                        base_slug = card_name_slug.replace('-V-1', '')
                        # Split by hyphens and collapse all but the last one
                        slug_parts = base_slug.split('-')
                        if len(slug_parts) >= 2:
                            # Join all parts except last, then add hyphen and last part
                            collapsed = ''.join(slug_parts[:-1]) + '-' + slug_parts[-1]
                            print(f"   🔄 Trying without internal hyphens: {collapsed}...")
                            new_url = url.replace(f'/{card_name_slug}?', f'/{collapsed}?')
                            self._save_debug_html(html_content, url, "multiple_versions_retrying_collapsed")
                            return self.fetch_listings(new_url, max_listings, retry_count + 1)
                
                # All retries exhausted
                self._save_debug_html(html_content, url, "multiple_versions_failed")
                print("   ❌ Could not determine correct version")
                return []
            else:
                self._save_debug_html(html_content, url, "multiple_versions")
                return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = self._parse_listings_table(soup, max_listings)
            
            # If no listings found, save HTML for debugging
            if len(listings) == 0:
                self._save_debug_html(html_content, url, "no_listings_found")
                print("   ❌ No listings found")
                return []
            
            # Extract and save card image if enabled
            if self.save_images:
                self._extract_and_save_card_image(soup, url)
            
            return listings
            
        except Exception as e:
            # Save HTML when parsing fails
            self._save_debug_html(html_content, url, "parsing_failed", str(e))
            print(f"   ❌ Parse error: {e}")
            return []
    
    def _extract_and_save_card_image(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """
        Extract and save the card image from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: The page URL (for extracting card name)
            
        Returns:
            Path to saved image or None
        """
        import os
        
        try:
            # Find the main card image (class="is-front" on product page)
            main_images = soup.find_all('img', class_='is-front')
            
            for img in main_images:
                # Check both src and data-echo attributes
                img_url = img.get('src') or img.get('data-echo')
                alt_text = img.get('alt', '')
                
                # Only save product images from CardMarket's S3
                if img_url and 'product-images.s3.cardmarket.com' in img_url:
                    # Extract card name for filename
                    card_name = alt_text if alt_text else url.split('/')[-1].split('?')[0]
                    # Clean filename: remove illegal chars, replace spaces with underscores
                    card_name = re.sub(r'[<>:"/\\|?*]', '', card_name)
                    card_name = card_name.replace(' ', '_').replace(',', '').replace("'", "")
                    
                    # Determine file path
                    ext = img_url.split('.')[-1].split('?')[0]
                    if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                        ext = 'jpg'
                    
                    filename = f"{card_name}.{ext}"
                    filepath = os.path.join(self.image_dir, filename)
                    
                    # Skip download if image already exists
                    if os.path.exists(filepath):
                        return filepath
                    
                    # Download the image with appropriate headers
                    headers = {
                        'Referer': 'https://www.cardmarket.com/',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    }
                    
                    img_response = self.session.get(img_url, headers=headers, timeout=10)
                    img_response.raise_for_status()
                    
                    # Save the image
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    
                    print(f"   🖼️  Saved image: {filepath}")
                    return filepath
            
            return None
            
        except Exception as e:
            # Don't fail if image download fails
            print(f"   ⚠️  Could not save image: {e}")
            return None
    
    def _save_debug_html(self, html_content: str, url: str, status: str, error_msg: str = None):
        """Save HTML content for debugging with organized naming."""
        import os
        from datetime import datetime
        from urllib.parse import urlparse
        
        # Create debug directory if it doesn't exist
        debug_dir = "debug_html"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Extract card info from URL for filename
        try:
            path_parts = urlparse(url).path.split('/')
            card_info = path_parts[-1] if path_parts[-1] else "unknown_card"
            card_info = card_info.split('?')[0]  # Remove query params
        except:
            card_info = "unknown_card"
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename
        filename = f"{timestamp}_{card_info}_{status}.html"
        filepath = os.path.join(debug_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- DEBUG INFO -->\n")
                f.write(f"<!-- URL: {url} -->\n")
                f.write(f"<!-- Status: {status} -->\n")
                f.write(f"<!-- Timestamp: {timestamp} -->\n")
                if error_msg:
                    f.write(f"<!-- Error: {error_msg} -->\n")
                f.write(f"<!-- HTML Length: {len(html_content)} characters -->\n")
                f.write(f"<!-- END DEBUG INFO -->\n\n")
                f.write(html_content)
            
            # Silently save debug files (only print on errors)
            # Also save a summary log
            self._log_debug_summary(url, status, error_msg, len(html_content), filepath)
            
        except Exception as e:
            print(f"⚠️  Could not save debug HTML: {e}")
    
    def _save_debug_info(self, url: str, status: str, error_msg: str, response=None):
        """Save debug info when HTML can't be decoded."""
        import os
        from datetime import datetime
        from urllib.parse import urlparse
        
        debug_dir = "debug_html"
        os.makedirs(debug_dir, exist_ok=True)
        
        try:
            path_parts = urlparse(url).path.split('/')
            card_info = path_parts[-1] if path_parts[-1] else "unknown_card"
            card_info = card_info.split('?')[0]
        except:
            card_info = "unknown_card"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{card_info}_{status}.txt"
        filepath = os.path.join(debug_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"DEBUG INFO - Failed Request\n")
                f.write(f"URL: {url}\n")
                f.write(f"Status: {status}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Error: {error_msg}\n")
                if response:
                    f.write(f"Response Status: {response.status_code}\n")
                    f.write(f"Response Headers: {dict(response.headers)}\n")
                    f.write(f"Response Content Length: {len(response.content)}\n")
                    f.write(f"Response Content Type: {response.headers.get('content-type', 'unknown')}\n")
                    f.write(f"Response Encoding: {response.headers.get('content-encoding', 'none')}\n")
                f.write(f"\n")
            
            print(f"💾 Debug info saved: {filepath}")
            self._log_debug_summary(url, status, error_msg, 0, filepath)
            
        except Exception as e:
            print(f"⚠️  Could not save debug info: {e}")
    
    def _log_debug_summary(self, url: str, status: str, error_msg: str, content_length: int, filepath: str):
        """Maintain a summary log of all debug saves."""
        import os
        from datetime import datetime
        
        debug_dir = "debug_html"
        summary_file = os.path.join(debug_dir, "debug_summary.log")
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {status} | {url} | {content_length} chars | {filepath}")
                if error_msg:
                    f.write(f" | Error: {error_msg}")
                f.write(f"\n")
                
        except Exception as e:
            print(f"⚠️  Could not update debug summary: {e}")
    
    def _parse_listings_table(self, soup: BeautifulSoup, max_listings: int) -> List[LiveListing]:
        """Parse the listings from Cardmarket HTML (modern Bootstrap layout)."""
        listings = []
        
        # Look for article rows (this is the modern Cardmarket structure)
        article_rows = soup.find_all('div', class_=re.compile(r'article-row'))
        
        if article_rows:
            return self._parse_modern_listings(article_rows, max_listings)
        
        # Fallback: Look for common table patterns (legacy)
        tables = soup.find_all('table')
        
        for i, table in enumerate(tables):
            # Look for the table that has the most price-like content
            table_text = table.get_text()
            price_count = len(re.findall(r'€\s*\d+[.,]\d+', table_text))
            
            if price_count >= 3:  # Likely a listings table
                rows = table.find_all('tr')[1:]  # Skip header
                
                for j, row in enumerate(rows[:max_listings]):
                    try:
                        listing = self._parse_listing_row(row)
                        if listing and listing.price > 0:
                            listings.append(listing)
                            # Only print first 3 listings
                            if j < 3:
                                print(f"      €{listing.price:.2f} - {listing.condition} - {listing.seller}")
                    except Exception as e:
                        continue
                
                # If we found listings in this table, we're done
                if listings:
                    break
        
        if not listings:
            # Try to find individual price elements as fallback
            potential_listings = soup.find_all(['div', 'span', 'td'], 
                                             text=re.compile(r'€\s*\d+[.,]\d+'))
            
            for i, element in enumerate(potential_listings[:max_listings]):
                try:
                    element_text = element.get_text(strip=True)
                    price_match = re.search(r'€\s*(\d+[.,]\d+)', element_text)
                    
                    if price_match:
                        price_str = price_match.group(1).replace(',', '.')
                        price = float(price_str)
                        
                        listing = LiveListing(
                            price=price,
                            condition="Unknown",
                            seller="Unknown"
                        )
                        
                        listings.append(listing)
                        
                except Exception as e:
                    continue
        
        return listings
    
    def _parse_modern_listings(self, article_rows, max_listings: int) -> List[LiveListing]:
        """Parse modern Cardmarket listings from article-row divs."""
        listings = []
        
        for i, row in enumerate(article_rows[:max_listings]):
            try:
                listing = self._parse_modern_listing_row(row)
                if listing and listing.price > 0:
                    listings.append(listing)
                    # Only print first 3 listings
                    if i < 3:
                        print(f"      €{listing.price:.2f} - {listing.condition} - {listing.seller}")
            except Exception as e:
                continue
        
        return listings
    
    def _parse_modern_listing_row(self, row) -> Optional[LiveListing]:
        """Parse a single modern Cardmarket listing row."""
        try:
            row_text = row.get_text(' ', strip=True)
            
            # Price extraction - handle European number format (1.234,56)
            price = 0.0
            
            # First, try to find European format in price spans
            price_spans = row.find_all('span', class_=re.compile(r'color-primary.*fw-bold'))
            
            for span in price_spans:
                span_text = span.get_text(strip=True)
                
                # Try European format patterns first
                european_patterns = [
                    r'(\d{1,3}(?:\.\d{3})+,\d{2})',  # Multi-thousand format: 1.234,56
                    r'€\s*(\d{1,3}(?:\.\d{3})+,\d{2})',  # €1.234,56
                    r'(\d{1,3}(?:\.\d{3})+,\d{2})\s*€',  # 1.234,56 €
                ]
                
                european_matches = []
                for pattern in european_patterns:
                    matches = re.findall(pattern, span_text)
                    for match in matches:
                        try:
                            clean_match = match.replace('.', '').replace(',', '.')
                            value = float(clean_match)
                            european_matches.append((value, match))
                        except ValueError:
                            continue
                
                if european_matches:
                    price, _ = max(european_matches, key=lambda x: x[0])
                    break
                else:
                    # Fallback to simple pattern for this span
                    price_match = re.search(r'(\d+[.,]\d+)\s*€', span_text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '.')
                        price = float(price_str)
                        break
            
            if price <= 0:
                # Fallback: search in all text with European format
                european_patterns = [
                    r'(\d{1,3}(?:\.\d{3})+,\d{2})',  # Multi-thousand format: 1.234,56
                    r'€\s*(\d{1,3}(?:\.\d{3})+,\d{2})',  # €1.234,56
                    r'(\d{1,3}(?:\.\d{3})+,\d{2})\s*€',  # 1.234,56 €
                ]
                
                european_matches = []
                for pattern in european_patterns:
                    matches = re.findall(pattern, row_text)
                    for match in matches:
                        try:
                            clean_match = match.replace('.', '').replace(',', '.')
                            value = float(clean_match)
                            european_matches.append((value, match))
                        except ValueError:
                            continue
                
                if european_matches:
                    price, _ = max(european_matches, key=lambda x: x[0])
                else:
                    # Final fallback: simple pattern
                    price_match = re.search(r'(\d+[.,]\d+)\s*€', row_text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '.')
                        price = float(price_str)
            
            if price <= 0:
                return None
            
            # Condition extraction - look for condition badges
            condition = "Unknown"
            condition_badges = row.find_all('span', class_='badge')
            for badge in condition_badges:
                badge_text = badge.get_text(strip=True).upper()
                if badge_text in ['MT', 'NM', 'EX', 'GD', 'LP', 'PL', 'PO']:
                    condition = badge_text
                    break
            
            # Seller extraction - look for user links
            seller = "Unknown"
            seller_links = row.find_all('a', href=re.compile(r'/Users/'))
            if seller_links:
                seller = seller_links[0].get_text(strip=True)
            
            # Language - look for language icons or text
            language = "Unknown"
            if 'English' in row_text:
                language = "English"
            elif 'German' in row_text:
                language = "German"
            elif 'French' in row_text:
                language = "French"
            
            # Quantity - look for item-count
            quantity = 1
            qty_spans = row.find_all('span', class_='item-count')
            if qty_spans:
                qty_text = qty_spans[0].get_text(strip=True)
                if qty_text.isdigit():
                    quantity = int(qty_text)
            
            # Foil detection
            foil = 'foil' in row_text.lower()
            
            # Country extraction - look for "Item location:" in title attributes
            seller_country = "Unknown"
            # CardMarket uses title="Item location: Country" format on icon spans
            all_spans = row.find_all('span', title=True)
            for span in all_spans:
                title = span.get('title', '')
                if 'Item location:' in title or 'Item location' in title:
                    # Extract country name after "Item location: "
                    seller_country = title.replace('Item location:', '').strip()
                    break
            
            return LiveListing(
                price=price,
                condition=condition,
                seller=seller,
                seller_country=seller_country,
                language=language,
                quantity=quantity,
                foil=foil
            )
            
        except Exception as e:
            print(f"⚠️  Error parsing modern listing: {e}")
            return None
    
    def _parse_listing_row(self, row) -> Optional[LiveListing]:
        """Parse a single listing row."""
        try:
            cells = row.find_all(['td', 'th'])
            row_text = row.get_text(' ', strip=True)
            
            if len(cells) < 2:
                return None
            
            # Price extraction - handle European number format (1.234,56)
            price = 0.0
            
            # First, try to find the longest/most complete European format price
            european_patterns = [
                r'(\d{1,3}(?:\.\d{3})+,\d{2})',  # Multi-thousand format: 1.234,56 or 12.345,67
                r'€\s*(\d{1,3}(?:\.\d{3})+,\d{2})',  # €1.234,56
                r'(\d{1,3}(?:\.\d{3})+,\d{2})\s*€',  # 1.234,56 €
            ]
            
            # Find all European format matches and pick the highest value (most complete)
            european_matches = []
            for pattern in european_patterns:
                matches = re.findall(pattern, row_text)
                for match in matches:
                    try:
                        # Convert European format to float
                        clean_match = match.replace('.', '').replace(',', '.')
                        value = float(clean_match)
                        european_matches.append((value, match))
                    except ValueError:
                        continue
            
            if european_matches:
                # Use the highest value European format match
                price, price_str = max(european_matches, key=lambda x: x[0])
            else:
                # Fallback to simpler patterns
                fallback_patterns = [
                    r'€\s*(\d+,\d{2})',          # €234,56
                    r'(\d+,\d{2})\s*€',          # 234,56 €
                    r'€\s*(\d+\.\d{2})',         # €234.56
                    r'(\d+\.\d{2})\s*€',         # 234.56 €
                ]
                
                for pattern in fallback_patterns:
                    match = re.search(pattern, row_text)
                    if match:
                        price_str = match.group(1)
                        # Convert to float
                        if ',' in price_str:
                            price_str = price_str.replace(',', '.')
                        try:
                            price = float(price_str)
                            break
                        except ValueError:
                            continue
            
            if price <= 0:
                return None
            
            # Condition extraction
            condition = "Unknown"
            condition_keywords = ['mint', 'nm', 'near mint', 'excellent', 'ex', 'good', 'gd', 
                                'light played', 'lp', 'played', 'pl', 'poor', 'po']
            
            for keyword in condition_keywords:
                if keyword in row_text.lower():
                    condition = keyword.upper()
                    break
            
            # Seller extraction
            seller = "Unknown"
            # Look for links that might be seller profiles
            seller_links = row.find_all('a', href=True)
            for link in seller_links:
                href = link.get('href', '')
                if 'user' in href.lower():
                    seller = link.get_text(strip=True)
                    break
            
            # Language extraction
            language = "Unknown"
            if 'english' in row_text.lower():
                language = "English"
            elif 'german' in row_text.lower():
                language = "German"
            
            # Quantity extraction
            quantity = 1
            qty_match = re.search(r'(\d+)\s*x', row_text.lower())
            if qty_match:
                quantity = int(qty_match.group(1))
            
            # Foil detection
            foil = 'foil' in row_text.lower()
            
            # Country extraction - look for "Item location:" in title attributes
            seller_country = "Unknown"
            # CardMarket uses title="Item location: Country" format on icon spans
            all_spans = row.find_all('span', title=True)
            for span in all_spans:
                title = span.get('title', '')
                if 'Item location:' in title or 'Item location' in title:
                    # Extract country name after "Item location: "
                    seller_country = title.replace('Item location:', '').strip()
                    break
            
            return LiveListing(
                price=price,
                condition=condition,
                seller=seller,
                seller_country=seller_country,
                language=language,
                quantity=quantity,
                foil=foil
            )
            
        except Exception as e:
            return None


def main():
    """Test the simple browser scraper."""
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://www.cardmarket.com/en/Magic/Products/Singles/Alpha/Animate-Artifact?sellerCountry=7&language=1&minCondition=3"
    
    print("🃏 Cardmarket Simple Browser Scraper")
    print("=" * 60)
    print(f"🎯 Target: {test_url}")
    print()
    print("💡 This approach uses:")
    print("   - Perfect Chrome browser headers")
    print("   - Session cookies from main site first")
    print("   - Adaptive delays (3-5s fast, 9-12s if rate limited)")
    print("   - No proxies - just good headers")
    print()
    
    scraper = SimpleBrowserScraper(delay_range=(3.0, 5.0))
    listings = scraper.fetch_listings(test_url, max_listings=15)
    
    if listings:
        print("\n📊 LIVE LISTINGS FOUND!")
        print("=" * 40)
        
        # Sort by price
        sorted_listings = sorted(listings, key=lambda x: x.price)
        
        for i, listing in enumerate(sorted_listings, 1):
            foil_indicator = " (Foil)" if listing.foil else ""
            print(f"{i:2d}. €{listing.price:6.2f} - {listing.condition:12} - {listing.seller}{foil_indicator}")
            if listing.quantity > 1:
                print(f"     Quantity: {listing.quantity}")
        
        # Analysis
        prices = [l.price for l in listings if l.price > 0]
        if prices:
            print(f"\n💰 PRICE ANALYSIS:")
            print(f"   Cheapest: €{min(prices):.2f}")
            print(f"   Most expensive: €{max(prices):.2f}")
            print(f"   Average: €{sum(prices)/len(prices):.2f}")
        
        # Save results
        output_data = {
            "url": test_url,
            "timestamp": time.time(),
            "listings": [asdict(listing) for listing in sorted_listings],
            "analysis": {
                "total_listings": len(listings),
                "cheapest": min(prices) if prices else 0,
                "most_expensive": max(prices) if prices else 0,
                "average": sum(prices)/len(prices) if prices else 0
            }
        }
        
        output_file = f"data/live_listings_simple_{int(time.time())}.json"
        try:
            import os
            os.makedirs('data', exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"⚠️  Could not save results: {e}")
    
    else:
        print("❌ No listings found")
        print("\n🔧 Check debug_cardmarket_simple.html to see what we got")
        print("💡 If it shows Cardmarket content, the parsing needs adjustment")
        print("💡 If it shows blocking/error pages, headers need more work")


if __name__ == "__main__":
    main()
