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


class WebpagePDFDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Webpage PDF Downloader")
        self.root.geometry("800x600")
        
        # Variables
        self.pages_data = []
        self.selected_pages = {}
        self.session = requests.Session()
        
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
    
    def scan_website(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        # Start scanning in a separate thread
        threading.Thread(target=self._scan_website_thread, args=(url,), daemon=True).start()
    
    def _scan_website_thread(self, url):
        try:
            self.root.after(0, lambda: self.progress.start())
            self.root.after(0, lambda: self.update_status("Scanning website..."))
            self.root.after(0, lambda: self.scan_button.config(state=tk.DISABLED))
            
            # Setup authentication if provided
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            
            if username and password:
                # Try basic auth first
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
                    # If we can't fetch a page, still add it but note the error
                    pages_data.append({
                        'url': link_url,
                        'title': f"Error loading: {str(e)[:50]}",
                        'selected': False
                    })
            
            # Update GUI in main thread
            self.pages_data = pages_data
            self.root.after(0, self._update_pages_list)
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.update_status(f"Found {len(pages_data)} pages"))
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.select_all_button.config(state=tk.NORMAL))
            
        except Exception as e:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.update_status("Error scanning website"))
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to scan website: {str(e)}"))
    
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
            
            for i, page_index in enumerate(selected_indices):
                page = self.pages_data[page_index]
                self.root.after(0, lambda p=page: self.update_status(f"Downloading: {p['title']}"))
                
                try:
                    # Get page content
                    response = self.session.get(page['url'])
                    response.raise_for_status()
                    
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
                    html_doc = weasyprint.HTML(string=response.text, base_url=page['url'])
                    html_doc.write_pdf(pdf_path)
                    
                    progress_msg = f"Downloaded {i+1}/{total_pages}: {page['title']}"
                    self.root.after(0, lambda msg=progress_msg: self.update_status(msg))
                    
                except Exception as e:
                    error_msg = f"Error downloading {page['title']}: {str(e)}"
                    self.root.after(0, lambda msg=error_msg: self.update_status(msg))
                    continue
            
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.update_status(f"Downloaded {total_pages} pages to {output_dir}"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Downloaded {total_pages} pages successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.update_status("Error during download"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Download failed: {str(e)}"))


def main():
    root = tk.Tk()
    app = WebpagePDFDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
