import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
from bs4 import BeautifulSoup
import weasyprint
import os
from urllib.parse import urljoin, urlparse
import threading
from typing import List, Dict, Optional
import base64
import time

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class WebpagePDFDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Webpage PDF Downloader")
        self.root.geometry("800x600")
        
        # Variables
        self.pages_data = []
        self.selected_pages = {}
        self.session = requests.Session()
        self.driver = None
        
        self.setup_gui()
    
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL Input Section
        ttk.Label(main_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # Credentials Section
        cred_frame = ttk.LabelFrame(main_frame, text="Credentials (Optional)", padding="5")
        cred_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        cred_frame.columnconfigure(1, weight=1)
        
        ttk.Label(cred_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.username_entry = ttk.Entry(cred_frame, width=30)
        self.username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        ttk.Label(cred_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_entry = ttk.Entry(cred_frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        # JavaScript rendering option
        self.js_enabled = tk.BooleanVar()
        if SELENIUM_AVAILABLE:
            self.js_checkbox = ttk.Checkbutton(cred_frame, text="Enable JavaScript rendering (for modern websites)", 
                                             variable=self.js_enabled)
            self.js_checkbox.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        else:
            self.js_label = ttk.Label(cred_frame, text="Install selenium for JavaScript support", 
                                    foreground="gray")
            self.js_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.scan_button = ttk.Button(button_frame, text="Scan Website", command=self.scan_website)
        self.scan_button.pack(side=tk.LEFT, padx=5)
        
        self.select_all_button = ttk.Button(button_frame, text="Select All", command=self.select_all_pages, state=tk.DISABLED)
        self.select_all_button.pack(side=tk.LEFT, padx=5)
        
        self.download_button = ttk.Button(button_frame, text="Download Selected", command=self.download_selected, state=tk.DISABLED)
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Pages list
        pages_frame = ttk.LabelFrame(main_frame, text="Found Pages", padding="5")
        pages_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        pages_frame.columnconfigure(0, weight=1)
        pages_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Treeview for pages
        columns = ('Select', 'Title', 'URL')
        self.pages_tree = ttk.Treeview(pages_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.pages_tree.heading('Select', text='Select')
        self.pages_tree.heading('Title', text='Title')
        self.pages_tree.heading('URL', text='URL')
        
        # Configure column widths
        self.pages_tree.column('Select', width=60)
        self.pages_tree.column('Title', width=300)
        self.pages_tree.column('URL', width=400)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(pages_frame, orient=tk.VERTICAL, command=self.pages_tree.yview)
        self.pages_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.pages_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Bind treeview click
        self.pages_tree.bind('<Button-1>', self.on_tree_click)
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def setup_browser(self):
        """Setup and return a headless Chrome browser instance."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            error_str = str(e).lower()
            if "chrome binary" in error_str or "chromedriver" in error_str:
                raise Exception(
                    "Google Chrome browser is not installed or not found.\n\n"
                    "To fix this:\n"
                    "• Windows/Mac: Download Chrome from https://www.google.com/chrome/\n"
                    "• Ubuntu/Debian: sudo apt install google-chrome-stable\n"
                    "• CentOS/Fedora: sudo dnf install google-chrome-stable\n\n"
                    "Alternatively, uncheck 'JavaScript rendering' to use static mode."
                )
            else:
                raise Exception(f"Failed to setup browser: {str(e)}")
    
    def cleanup_browser(self):
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def scan_website(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        use_js = self.js_enabled.get() if SELENIUM_AVAILABLE else False
        
        # Start scanning in a separate thread
        threading.Thread(target=self._scan_website_thread, args=(url, use_js), daemon=True).start()
    
    def _scan_website_thread(self, url, use_js=False):
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.update_status("Scanning website..."))
            self.root.after(0, lambda: self.scan_button.config(state=tk.DISABLED))
            
            if use_js and SELENIUM_AVAILABLE:
                pages_data = self._scan_with_javascript(url)
            else:
                pages_data = self._scan_static_html(url)
            
            # Update GUI in main thread
            self.pages_data = pages_data
            self.root.after(0, self._update_pages_list)
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.update_status(f"Found {len(pages_data)} pages"))
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.select_all_button.config(state=tk.NORMAL))
            
        except Exception as e:
            error_msg = f"Failed to scan website: {str(e)}"
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.update_status("Error scanning website"))
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cleanup_browser())
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
    
    def _scan_static_html(self, url):
        """Scan website using traditional HTTP requests - works for static sites."""
        # Setup authentication if provided
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if username and password:
            self.session.auth = (username, password)
        
        # Get the main page
        response = self.session.get(url)
        response.raise_for_status()
        
        # Parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links
        links = set()
        base_domain = urlparse(url).netloc
        
        # Add the current page
        links.add(url)
        
        # Find all internal links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)
            parsed_url = urlparse(full_url)
            
            # Only include links from the same domain
            if parsed_url.netloc == base_domain:
                # Remove fragments and query parameters for cleaner URLs
                clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if clean_url not in links and clean_url != url:
                    links.add(clean_url)
        
        # Get page titles
        pages_data = []
        for link_url in links:
            try:
                page_response = self.session.get(link_url, timeout=10)
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                title_tag = page_soup.find('title')
                title = title_tag.text.strip() if title_tag else "No Title"
                pages_data.append({
                    'url': link_url,
                    'title': title,
                    'selected': False
                })
            except Exception as e:
                pages_data.append({
                    'url': link_url,
                    'title': f"Error loading: {str(e)[:50]}",
                    'selected': False
                })
        
        return pages_data
    
    def _scan_with_javascript(self, url):
        """Scan website using Selenium - works for JavaScript-heavy sites."""
        self.root.after(0, lambda: self.update_status("Setting up browser..."))
        
        try:
            self.driver = self.setup_browser()
            
            # Navigate to the main page
            self.root.after(0, lambda: self.update_status("Loading main page..."))
            self.driver.get(url)
            
            # Handle authentication if provided
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            
            if username and password:
                self.root.after(0, lambda: self.update_status("Attempting login..."))
                self._handle_selenium_auth(username, password)
            
            # Wait for initial page load
            time.sleep(3)
            
            # Find all clickable links and navigation elements
            self.root.after(0, lambda: self.update_status("Discovering pages..."))
            links = self._discover_javascript_links()
            
            base_domain = urlparse(url).netloc
            valid_links = set()
            
            # Add the current page
            valid_links.add(self.driver.current_url)
            
            # Filter links to same domain
            for link in links:
                try:
                    parsed_url = urlparse(link)
                    if parsed_url.netloc == base_domain or not parsed_url.netloc:
                        # Handle relative URLs
                        if not parsed_url.netloc:
                            link = urljoin(url, link)
                        
                        # Clean up the URL
                        parsed_clean = urlparse(link)
                        clean_url = f"{parsed_clean.scheme}://{parsed_clean.netloc}{parsed_clean.path}"
                        if clean_url not in valid_links:
                            valid_links.add(clean_url)
                except:
                    continue
            
            # Get page titles by visiting each link
            pages_data = []
            total_links = len(valid_links)
            
            for i, link_url in enumerate(valid_links):
                try:
                    self.root.after(0, lambda i=i, total=total_links: 
                                  self.update_status(f"Getting page info {i+1}/{total}..."))
                    
                    self.driver.get(link_url)
                    time.sleep(2)  # Wait for page to load
                    
                    title = self.driver.title or "No Title"
                    pages_data.append({
                        'url': link_url,
                        'title': title,
                        'selected': False
                    })
                except Exception as e:
                    pages_data.append({
                        'url': link_url,
                        'title': f"Error loading: {str(e)[:50]}",
                        'selected': False
                    })
            
            return pages_data
            
        finally:
            self.cleanup_browser()
    
    def _handle_selenium_auth(self, username, password):
        """Handle authentication in Selenium browser."""
        try:
            # Look for common login form elements
            username_selectors = [
                "input[name='username']", "input[name='user']", "input[name='email']",
                "input[id='username']", "input[id='user']", "input[id='email']",
                "input[type='email']", "#username", "#user", "#email"
            ]
            
            password_selectors = [
                "input[name='password']", "input[name='pass']",
                "input[id='password']", "input[id='pass']",
                "input[type='password']", "#password", "#pass"
            ]
            
            username_field = None
            password_field = None
            
            # Try to find username field
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            # Try to find password field
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if username_field and password_field:
                username_field.send_keys(username)
                password_field.send_keys(password)
                
                # Try to find and click login button
                login_selectors = [
                    "input[type='submit']", "button[type='submit']",
                    "input[value*='login']", "input[value*='Login']",
                    "button:contains('Login')", "button:contains('Sign')",
                    ".login-button", "#login", "#signin"
                ]
                
                for selector in login_selectors:
                    try:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        login_button.click()
                        time.sleep(3)  # Wait for login to process
                        break
                    except:
                        continue
                        
        except Exception as e:
            print(f"Auth handling failed: {e}")
    
    def _discover_javascript_links(self):
        """Discover links in JavaScript-heavy sites."""
        links = set()
        
        try:
            # Get all anchor tags
            anchor_elements = self.driver.find_elements(By.TAG_NAME, "a")
            for element in anchor_elements:
                href = element.get_attribute("href")
                if href:
                    links.add(href)
            
            # Get elements with click handlers that might be navigation
            clickable_selectors = [
                "[onclick]", "[data-href]", "[data-url]", 
                ".nav-link", ".menu-item", ".link",
                "[role='button']", ".button"
            ]
            
            for selector in clickable_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Try various attributes that might contain URLs
                    for attr in ['data-href', 'data-url', 'onclick']:
                        value = element.get_attribute(attr)
                        if value and ('http' in value or '/' in value):
                            # Extract URL from onclick or data attributes
                            if 'http' in value:
                                import re
                                urls = re.findall(r'https?://[^\s\'\"]+', value)
                                links.update(urls)
                            elif value.startswith('/'):
                                links.add(value)
            
            # Try to execute JavaScript to get more dynamic links
            try:
                js_links = self.driver.execute_script("""
                    var links = [];
                    var anchors = document.querySelectorAll('a[href]');
                    for (var i = 0; i < anchors.length; i++) {
                        links.push(anchors[i].href);
                    }
                    return links;
                """)
                links.update(js_links)
            except:
                pass
                
        except Exception as e:
            print(f"Link discovery error: {e}")
        
        return list(links)
    
    def _update_pages_list(self):
        # Clear existing items
        for item in self.pages_tree.get_children():
            self.pages_tree.delete(item)
        
        # Add new items
        for i, page in enumerate(self.pages_data):
            checkbox = "☐"  # Empty checkbox
            self.pages_tree.insert('', 'end', iid=i, values=(checkbox, page['title'], page['url']))
        
        self.selected_pages = {i: False for i in range(len(self.pages_data))}
    
    def on_tree_click(self, event):
        region = self.pages_tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.pages_tree.identify_row(event.y)
            column = self.pages_tree.identify_column(event.x)
            
            if column == '#1':  # Select column
                if item:
                    item_id = int(item)
                    # Toggle selection
                    self.selected_pages[item_id] = not self.selected_pages[item_id]
                    checkbox = "☑" if self.selected_pages[item_id] else "☐"
                    
                    # Update the item
                    current_values = list(self.pages_tree.item(item, 'values'))
                    current_values[0] = checkbox
                    self.pages_tree.item(item, values=current_values)
                    
                    # Update download button state
                    if any(self.selected_pages.values()):
                        self.download_button.config(state=tk.NORMAL)
                    else:
                        self.download_button.config(state=tk.DISABLED)
    
    def select_all_pages(self):
        for i in range(len(self.pages_data)):
            self.selected_pages[i] = True
            # Update checkbox in tree
            current_values = list(self.pages_tree.item(str(i), 'values'))
            current_values[0] = "☑"
            self.pages_tree.item(str(i), values=current_values)
        
        self.download_button.config(state=tk.NORMAL)
        self.update_status(f"Selected all {len(self.pages_data)} pages")
    
    def download_selected(self):
        selected_indices = [i for i, selected in self.selected_pages.items() if selected]
        if not selected_indices:
            messagebox.showwarning("Warning", "No pages selected")
            return
        
        # Choose output directory
        output_dir = filedialog.askdirectory(title="Choose Output Directory")
        if not output_dir:
            return
        
        # Start download in separate thread
        threading.Thread(target=self._download_pages_thread, args=(selected_indices, output_dir), daemon=True).start()
    
    def _download_pages_thread(self, selected_indices, output_dir):
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.download_button.config(state=tk.DISABLED))
            
            total_pages = len(selected_indices)
            use_js = self.js_enabled.get() if SELENIUM_AVAILABLE else False
            
            # Setup browser if using JavaScript
            if use_js:
                self.root.after(0, lambda: self.update_status("Setting up browser for downloads..."))
                self.driver = self.setup_browser()
                
                # Handle authentication if provided
                username = self.username_entry.get().strip()
                password = self.password_entry.get().strip()
                if username and password:
                    # Navigate to first page to set up authentication
                    first_page = self.pages_data[selected_indices[0]]
                    self.driver.get(first_page['url'])
                    self._handle_selenium_auth(username, password)
            
            for i, page_index in enumerate(selected_indices):
                page = self.pages_data[page_index]
                self.root.after(0, lambda p=page: self.update_status(f"Downloading: {p['title']}"))
                
                try:
                    if use_js and SELENIUM_AVAILABLE:
                        html_content = self._get_page_content_selenium(page['url'])
                    else:
                        html_content = self._get_page_content_requests(page['url'])
                    
                    # Create PDF filename
                    safe_title = "".join(c for c in page['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    if not safe_title:
                        safe_title = f"page_{page_index}"
                    
                    pdf_filename = f"{safe_title}.pdf"
                    pdf_path = os.path.join(output_dir, pdf_filename)
                    
                    # Handle duplicate filenames
                    counter = 1
                    while os.path.exists(pdf_path):
                        name, ext = os.path.splitext(pdf_filename)
                        pdf_filename = f"{name}_{counter}{ext}"
                        pdf_path = os.path.join(output_dir, pdf_filename)
                        counter += 1
                    
                    # Convert to PDF
                    html_doc = weasyprint.HTML(string=html_content, base_url=page['url'])
                    html_doc.write_pdf(pdf_path)
                    
                    progress_msg = f"Downloaded {i+1}/{total_pages}: {page['title']}"
                    self.root.after(0, lambda msg=progress_msg: self.update_status(msg))
                    
                except Exception as e:
                    error_msg = f"Error downloading {page['title']}: {str(e)}"
                    self.root.after(0, lambda msg=error_msg: self.update_status(msg))
                    continue
            
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cleanup_browser())
            self.root.after(0, lambda: self.update_status(f"Downloaded {total_pages} pages to {output_dir}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Downloaded {total_pages} pages successfully!"))
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cleanup_browser())
            self.root.after(0, lambda: self.update_status("Error during download"))
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
    
    def _get_page_content_requests(self, url):
        """Get page content using requests - for static sites."""
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
    
    def _get_page_content_selenium(self, url):
        """Get page content using Selenium - for JavaScript sites."""
        self.driver.get(url)
        time.sleep(3)  # Wait for page to fully load
        
        # Wait for body to be present
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # Get the fully rendered HTML
        return self.driver.page_source


def main():
    root = tk.Tk()
    app = WebpagePDFDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
