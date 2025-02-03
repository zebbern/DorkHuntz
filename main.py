import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading, time, os, json, webbrowser, textwrap, requests
from config import NUM_RESULTS, PAUSE_TIME
from search import perform_google_dork_search_live
from utils import save_results

# Global proxy variables.
USE_PROXY = False
PROXY = None

# File used to store archive URLs
ARCHIVE_FILENAME = "archive_results.txt"

# Directly load the results structure from ResultsStructure.json.
with open("ResultsStructure.json", "r", encoding="utf-8") as f:
    RESULTS_STRUCTURE = json.load(f)

def categorize_url(url):
    """Return a category for the given URL based on RESULTS_STRUCTURE."""
    url_lower = url.lower()
    for category, keywords in RESULTS_STRUCTURE.items():
        for keyword in keywords:
            if keyword in url_lower:
                return category
    return "Other"

class PremiumOSINTGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Premium OSINT & BugBounty Tool")
        self.geometry("1200x800")
        self.minsize(800,600)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.search_running = False
        self.paused = False
        self.results_dict = {}         # Maps each dork query to its results.
        self.aggregated_results = {}   # Aggregated by category.
        self.predefined_files = []     # Predefined dork files from the "dorks" folder.
        self.bulk_vars = {}            # Mapping URL -> BooleanVar (for bulk selection).
        # For archive results we use the file ARCHIVE_FILENAME.
        self.archive_results = []      # Also keep an in‑memory copy (if needed)
        self.archive_bulk_vars = {}    # For bulk selection in archive.
        self.archive_filter_after_id = None  # For debouncing filter updates
        self.create_sidebar()
        self.create_pages()
        self.create_bottom_frame()
        self.show_input_page()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=150, corner_radius=15, fg_color="#1F1F1F")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=20)
        self.sidebar_frame.grid_propagate(False)
        bold_font = ctk.CTkFont(weight="bold")
        self.input_button = ctk.CTkButton(self.sidebar_frame, text="Input", font=bold_font,
                                          command=self.show_input_page, corner_radius=10)
        self.input_button.pack(padx=10, pady=10, fill="x")
        self.results_button = ctk.CTkButton(self.sidebar_frame, text="Results", font=bold_font,
                                            command=self.show_results_page, corner_radius=10)
        self.results_button.pack(padx=10, pady=10, fill="x")
        self.archive_button = ctk.CTkButton(self.sidebar_frame, text="Archive", font=bold_font,
                                            command=self.show_archive_page, corner_radius=10)
        self.archive_button.pack(padx=10, pady=10, fill="x")

    def create_pages(self):
        self.container = ctk.CTkFrame(self, corner_radius=15)
        self.container.grid(row=0, column=1, sticky="nsew", padx=(0,20), pady=20)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.input_frame = ctk.CTkFrame(self.container, corner_radius=15)
        self.input_frame.grid(row=0, column=0, sticky="nsew")
        self.results_frame = ctk.CTkFrame(self.container, corner_radius=15)
        self.results_frame.grid(row=0, column=0, sticky="nsew")
        self.archive_frame = ctk.CTkFrame(self.container, corner_radius=15)
        self.archive_frame.grid(row=0, column=0, sticky="nsew")
        self.create_input_page()
        self.create_results_page()
        self.create_archive_page()

    def create_bottom_frame(self):
        self.bottom_frame = ctk.CTkFrame(self, corner_radius=15)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0,20))
        bold_font = ctk.CTkFont(weight="bold")
        save_btn = ctk.CTkButton(self.bottom_frame, text="Save All Results", font=bold_font,
                                 command=lambda: self.save_all_results())
        save_btn.pack(side="right", padx=10, pady=10)

    def create_input_page(self):
        self.input_frame.grid_columnconfigure(0, weight=1)
        top_label = ctk.CTkLabel(self.input_frame, text="Enter Google Dork Queries (one per line):",
                                  font=ctk.CTkFont(size=18, weight="bold"))
        top_label.grid(row=0, column=0, padx=20, pady=(20,10), sticky="w")
        self.dork_text = ctk.CTkTextbox(self.input_frame, width=800, height=200)
        self.dork_text.grid(row=1, column=0, padx=20, pady=(0,20), sticky="ew")
        options_frame = ctk.CTkFrame(self.input_frame)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        options_frame.grid_columnconfigure(3, weight=1)
        results_label = ctk.CTkLabel(options_frame, text="Results per dork:", font=ctk.CTkFont(weight="bold"))
        results_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.results_entry = ctk.CTkEntry(options_frame, width=150, font=ctk.CTkFont(weight="bold"))
        self.results_entry.insert(0, str(NUM_RESULTS))
        self.results_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        delay_label = ctk.CTkLabel(options_frame, text="Delay per dork (sec):", font=ctk.CTkFont(weight="bold"))
        delay_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.delay_entry = ctk.CTkEntry(options_frame, width=150, font=ctk.CTkFont(weight="bold"))
        self.delay_entry.insert(0, str(PAUSE_TIME))
        self.delay_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        predefined_label = ctk.CTkLabel(options_frame, text="Predefined Dorks:", font=ctk.CTkFont(weight="bold"))
        predefined_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.predefined_optionmenu = ctk.CTkOptionMenu(options_frame, values=self.predefined_files,
                                                       command=lambda val: self.load_predefined_dorks_immediately(val),
                                                       font=ctk.CTkFont(weight="bold"))
        self.predefined_optionmenu.set("Select a file")
        self.predefined_optionmenu.grid(row=1, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        clear_btn = ctk.CTkButton(options_frame, text="Clear Dorks", font=ctk.CTkFont(weight="bold"), command=self.clear_dorks)
        clear_btn.grid(row=1, column=3, padx=5, pady=5, sticky="e")
        btn_frame1 = ctk.CTkFrame(self.input_frame)
        btn_frame1.grid(row=3, column=0, padx=20, pady=(10,5), sticky="ew")
        load_btn = ctk.CTkButton(btn_frame1, text="Load Dorks from File", font=ctk.CTkFont(weight="bold"), command=self.load_dorks)
        load_btn.grid(row=0, column=0, padx=10, pady=10)
        replace_btn = ctk.CTkButton(btn_frame1, text="Replace Text", font=ctk.CTkFont(weight="bold"), command=self.replace_text)
        replace_btn.grid(row=0, column=1, padx=10, pady=10)
        btn_frame2 = ctk.CTkFrame(self.input_frame)
        btn_frame2.grid(row=4, column=0, padx=20, pady=(5,20), sticky="ew")
        search_btn = ctk.CTkButton(btn_frame2, text="Search", font=ctk.CTkFont(weight="bold"), command=self.start_search)
        search_btn.grid(row=0, column=0, padx=10, pady=10)
        self.stop_btn = ctk.CTkButton(btn_frame2, text="Stop", font=ctk.CTkFont(weight="bold"), command=self.stop_search, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=10, pady=10)
        self.continue_btn = ctk.CTkButton(btn_frame2, text="Continue", font=ctk.CTkFont(weight="bold"), command=self.continue_search, state="disabled")
        self.continue_btn.grid(row=0, column=2, padx=10, pady=10)

    def create_results_page(self):
        top_results_frame = ctk.CTkFrame(self.results_frame)
        top_results_frame.pack(padx=20, pady=(20,10), fill="x")
        self.category_optionmenu = ctk.CTkOptionMenu(top_results_frame, values=[], command=self.update_results_buttons,
                                                     font=ctk.CTkFont(weight="bold"))
        self.category_optionmenu.pack(side="left", padx=5, pady=5)
        self.progress_label = ctk.CTkLabel(top_results_frame, text="0 / 0 dorks processed", font=ctk.CTkFont(weight="bold"))
        self.progress_label.pack(side="left", padx=20, pady=5)
        self.bulkopen_btn = ctk.CTkButton(top_results_frame, text="Bulk Open Selected", font=ctk.CTkFont(weight="bold"), command=self.bulk_open)
        self.bulkopen_btn.pack(side="left", padx=10, pady=5)
        self.scrollable_frame = ctk.CTkScrollableFrame(self.results_frame, height=500)
        self.scrollable_frame.pack(padx=20, pady=10, fill="both", expand=True)

    def create_archive_page(self):
        self.archive_frame.grid_columnconfigure(0, weight=1)
        archive_container = ctk.CTkFrame(self.archive_frame)
        archive_container.pack(padx=20, pady=20, fill="both", expand=True)
        header_frame = ctk.CTkFrame(archive_container)
        header_frame.pack(padx=5, pady=5, fill="x")
        domain_label = ctk.CTkLabel(header_frame, text="Domain:", font=ctk.CTkFont(weight="bold"))
        domain_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.domain_entry = ctk.CTkEntry(header_frame, font=ctk.CTkFont(weight="bold"))
        self.domain_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        self.archive_btn = ctk.CTkButton(header_frame, text="Archive Results", font=ctk.CTkFont(weight="bold"), command=self.start_archive)
        self.archive_btn.grid(row=0, column=2, padx=5, pady=5)
        self.archive_progress_label = ctk.CTkLabel(header_frame, text="0 links fetched", font=ctk.CTkFont(weight="bold"))
        self.archive_progress_label.grid(row=0, column=3, padx=10, pady=5)
        self.archive_bulk_btn = ctk.CTkButton(header_frame, text="Bulk Open", font=ctk.CTkFont(weight="bold"), command=self.archive_bulk_open)
        self.archive_bulk_btn.grid(row=0, column=4, padx=5, pady=5)
        display_container = ctk.CTkFrame(archive_container)
        display_container.pack(padx=5, pady=5, fill="both", expand=True)
        self.archive_filter_entry = ctk.CTkEntry(display_container, font=ctk.CTkFont(weight="bold"), placeholder_text="Filter archive results...")
        self.archive_filter_entry.pack(padx=5, pady=(5,10), fill="x")
        self.archive_filter_entry.bind("<KeyRelease>", self.schedule_archive_update)
        # Use a standard tkinter Listbox (which is faster for many lines) with a dark background.
        self.archive_list_frame = ctk.CTkFrame(display_container)
        self.archive_list_frame.pack(fill="both", expand=True)
        self.archive_listbox = tk.Listbox(self.archive_list_frame, font=("TkDefaultFont", 10),
                                          selectmode=tk.MULTIPLE,
                                          bg="#2E2E2E", fg="white", selectbackground="#333333", highlightbackground="#2E2E2E")
        self.archive_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(self.archive_list_frame, orient="vertical", command=self.archive_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.archive_listbox.config(yscrollcommand=scrollbar.set)
        self.archive_results = []
        self.archive_bulk_vars = {}
        self.archive_filter_after_id = None

    def schedule_archive_update(self, event):
        if self.archive_filter_after_id is not None:
            self.after_cancel(self.archive_filter_after_id)
        self.archive_filter_after_id = self.after(300, self.update_archive_display)

    def show_input_page(self):
        self.input_frame.tkraise()

    def show_results_page(self):
        self.results_frame.tkraise()
        self.update_category_list()

    def show_archive_page(self):
        self.archive_frame.tkraise()
        self.update_archive_display()

    def load_dorks(self):
        file_path = filedialog.askopenfilename(title="Select Dorks File", 
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                self.dork_text.delete("1.0", tk.END)
                self.dork_text.insert("1.0", content)
            except Exception as e:
                messagebox.showerror("Error", f"Error loading file: {e}")

    def load_predefined_dorks_immediately(self, filename):
        if filename and filename not in ["Select a file", "No files found"]:
            filepath = os.path.join("dorks", filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                self.dork_text.delete("1.0", tk.END)
                self.dork_text.insert("1.0", content)
            except Exception as e:
                messagebox.showerror("Error", f"Error loading file: {e}")

    def clear_dorks(self):
        self.dork_text.delete("1.0", tk.END)

    def show_replace_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Replace Text")
        dialog.geometry("400x220")
        dialog.grab_set()
        label_find = ctk.CTkLabel(dialog, text="Find:", font=ctk.CTkFont(weight="bold"))
        label_find.pack(padx=20, pady=(10,3), anchor="w")
        entry_find = ctk.CTkEntry(dialog)
        entry_find.pack(padx=20, pady=3, fill="x")
        label_replace = ctk.CTkLabel(dialog, text="Replace with:", font=ctk.CTkFont(weight="bold"))
        label_replace.pack(padx=20, pady=3, anchor="w")
        entry_replace = ctk.CTkEntry(dialog)
        entry_replace.pack(padx=20, pady=3, fill="x")
        def on_replace():
            find_text = entry_find.get()
            replace_text = entry_replace.get()
            current_text = self.dork_text.get("1.0", tk.END)
            new_text = current_text.replace(find_text, replace_text)
            self.dork_text.delete("1.0", tk.END)
            self.dork_text.insert("1.0", new_text)
            dialog.destroy()
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(padx=20, pady=10, fill="x")
        ok_btn = ctk.CTkButton(btn_frame, text="Replace", font=ctk.CTkFont(weight="bold"), command=on_replace, fg_color="transparent")
        ok_btn.pack(side="left", padx=10)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", font=ctk.CTkFont(weight="bold"), command=dialog.destroy, fg_color="transparent")
        cancel_btn.pack(side="right", padx=10)

    def replace_text(self):
        self.show_replace_dialog()

    def start_search(self):
        queries = self.dork_text.get("1.0", tk.END).strip().splitlines()
        queries = [q.strip() for q in queries if q.strip()]
        if not queries:
            messagebox.showerror("Error", "Please enter at least one dork query.")
            return
        try:
            num_res = int(self.results_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid integer for results per dork.")
            return
        try:
            delay_val = float(self.delay_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number for delay per dork.")
            return
        self.search_running = True
        self.paused = False
        self.stop_btn.configure(state="normal")
        threading.Thread(target=self.process_all_dorks, args=(queries, num_res, delay_val), daemon=True).start()

    def process_all_dorks(self, queries, num_res, delay_val):
        global USE_PROXY, PROXY
        total = len(queries)
        for idx, query in enumerate(queries, start=1):
            self.results_dict[query] = []
            while True:
                try:
                    for item in perform_google_dork_search_live(query, num_res, delay_val):
                        if any(existing["url"] == item["url"] for existing in self.results_dict[query]):
                            continue
                        item["category"] = categorize_url(item["url"])
                        self.results_dict[query].append(item)
                        self.update_category_list_async()
                    break
                except Exception as e:
                    if "429" in str(e):
                        answer = messagebox.askyesno("429 Error", 
                            "Received 429 Too Many Requests.\nWould you like to use a proxy to spoof your IP?")
                        if answer:
                            proxy = simpledialog.askstring("Enter Proxy", "Enter proxy address (e.g., http://IP:PORT):")
                            if proxy:
                                USE_PROXY = True
                                PROXY = proxy
                            else:
                                time.sleep(60)
                        else:
                            time.sleep(60)
                    else:
                        break
            self.progress_label.configure(text=f"{idx} / {total} dorks processed")
            while self.search_running and self.paused:
                time.sleep(1)
            time.sleep(delay_val)
        self.search_running = False
        self.update_category_list_async()
        self.stop_btn.configure(state="disabled")

    def stop_search(self):
        if self.search_running:
            self.paused = True
            self.stop_btn.configure(state="disabled")
            self.continue_btn.configure(state="normal")

    def continue_search(self):
        if self.search_running:
            self.paused = False
            self.stop_btn.configure(state="normal")
            self.continue_btn.configure(state="disabled")

    def update_category_list_async(self):
        self.after(0, self.update_category_list)

    def update_category_list(self):
        aggregated = {}
        for query in self.results_dict:
            for item in self.results_dict[query]:
                cat = item.get("category", "Other")
                aggregated.setdefault(cat, [])
                if not any(existing["url"] == item["url"] for existing in aggregated[cat]):
                    aggregated[cat].append(item)
        self.aggregated_results = aggregated
        categories = sorted(aggregated.keys())
        self.category_optionmenu.configure(values=categories)
        if categories:
            if self.category_optionmenu.get() not in categories:
                self.category_optionmenu.set(categories[0])
            self.update_results_buttons(self.category_optionmenu.get())
        else:
            self.category_optionmenu.set("")

    def update_results_buttons(self, selected_category):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        results = self.aggregated_results.get(selected_category, [])
        for i, item in enumerate(results, 1):
            wrapped_url = "\n".join(textwrap.wrap(item["url"], width=60))
            frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent", corner_radius=0)
            frame.pack(padx=2, pady=2, fill="x")
            if item["url"] not in self.bulk_vars:
                self.bulk_vars[item["url"]] = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame, text="", variable=self.bulk_vars[item["url"]])
            chk.pack(side="left", padx=(0,2))
            btn = ctk.CTkButton(frame, text=wrapped_url,
                                command=lambda url=item["url"]: webbrowser.open(url),
                                height=30, corner_radius=0, fg_color="transparent", hover_color="#333333",
                                font=ctk.CTkFont(weight="bold"), anchor="w")
            btn.pack(side="left", fill="x", expand=True)

    def bulk_open(self):
        for url, var in self.bulk_vars.items():
            if var.get():
                webbrowser.open(url)

    def show_results_page(self):
        self.results_frame.tkraise()
        self.update_category_list()

    def create_archive_page(self):
        self.archive_frame.grid_columnconfigure(0, weight=1)
        archive_container = ctk.CTkFrame(self.archive_frame)
        archive_container.pack(padx=20, pady=20, fill="both", expand=True)
        header_frame = ctk.CTkFrame(archive_container)
        header_frame.pack(padx=5, pady=5, fill="x")
        domain_label = ctk.CTkLabel(header_frame, text="Domain:", font=ctk.CTkFont(weight="bold"))
        domain_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.domain_entry = ctk.CTkEntry(header_frame, font=ctk.CTkFont(weight="bold"))
        self.domain_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        self.archive_btn = ctk.CTkButton(header_frame, text="Archive Results", font=ctk.CTkFont(weight="bold"), command=self.start_archive)
        self.archive_btn.grid(row=0, column=2, padx=5, pady=5)
        self.archive_progress_label = ctk.CTkLabel(header_frame, text="0 links fetched", font=ctk.CTkFont(weight="bold"))
        self.archive_progress_label.grid(row=0, column=3, padx=10, pady=5)
        self.archive_bulk_btn = ctk.CTkButton(header_frame, text="Bulk Open", font=ctk.CTkFont(weight="bold"), command=self.archive_bulk_open)
        self.archive_bulk_btn.grid(row=0, column=4, padx=5, pady=5)
        display_container = ctk.CTkFrame(archive_container)
        display_container.pack(padx=5, pady=5, fill="both", expand=True)
        self.archive_filter_entry = ctk.CTkEntry(display_container, font=ctk.CTkFont(weight="bold"), placeholder_text="Filter archive results...")
        self.archive_filter_entry.pack(padx=5, pady=(5,10), fill="x")
        self.archive_filter_entry.bind("<KeyRelease>", self.schedule_archive_update)
        # Use a standard tkinter Listbox for fast display.
        self.archive_list_frame = ctk.CTkFrame(display_container)
        self.archive_list_frame.pack(fill="both", expand=True)
        self.archive_listbox = tk.Listbox(self.archive_list_frame, font=("TkDefaultFont", 10),
                                          selectmode=tk.MULTIPLE,
                                          bg="#2E2E2E", fg="white", selectbackground="#333333", highlightbackground="#2E2E2E")
        self.archive_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(self.archive_list_frame, orient="vertical", command=self.archive_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.archive_listbox.config(yscrollcommand=scrollbar.set)
        # Clear any previous archive results.
        self.archive_results = []
        self.archive_bulk_vars = {}
        self.archive_filter_after_id = None

    def schedule_archive_update(self, event):
        if self.archive_filter_after_id is not None:
            self.after_cancel(self.archive_filter_after_id)
        self.archive_filter_after_id = self.after(300, self.update_archive_display)

    def show_archive_page(self):
        self.archive_frame.tkraise()
        self.update_archive_display()

    def start_archive(self):
        domain = self.domain_entry.get().strip()
        if not domain:
            messagebox.showerror("Error", "Please enter a domain.")
            return
        # Clear the file and in-memory results.
        with open(ARCHIVE_FILENAME, "w", encoding="utf-8") as f:
            f.write("")
        self.archive_results = []
        self.archive_bulk_vars = {}
        self.archive_progress_label.configure(text="0 links fetched")
        self.archive_listbox.delete(0, tk.END)
        threading.Thread(target=self.fetch_archive_urls, args=(domain,), daemon=True).start()

    def fetch_archive_urls(self, domain):
        base_url = "https://web.archive.org/cdx/search/cdx"
        params = {
            "url": f"{domain}*",
            "output": "text",
            "fl": "original",
            "collapse": "urlkey"
        }
        try:
            with requests.get(base_url, params=params, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = 0
                # Process lines as they arrive.
                for line in r.iter_lines(decode_unicode=True):
                    if line:
                        url = line.strip()
                        self.archive_results.append(url)
                        with open(ARCHIVE_FILENAME, "a", encoding="utf-8") as f:
                            f.write(url + "\n")
                        total += 1
                        # If total is a multiple of 1000, update progress immediately.
                        if total % 1000 == 0:
                            self.archive_progress_label.configure(text=f"{total} links fetched")
                            self.update_archive_display_async()
                self.archive_progress_label.configure(text=f"Fetch complete: {total} links")
                self.update_archive_display_async()
        except Exception as e:
            messagebox.showerror("Error", f"Error fetching archive URLs: {e}")

    def update_archive_display_async(self):
        self.after(0, self.update_archive_display)

    def update_archive_display(self):
        # Read archive URLs directly from the file.
        try:
            with open(ARCHIVE_FILENAME, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []
        filtered = [line.strip() for line in lines if self.archive_filter_entry.get().lower() in line.lower()]
        self.archive_listbox.delete(0, tk.END)
        max_display = 500
        for url in filtered[:max_display]:
            self.archive_listbox.insert(tk.END, url)
        if len(filtered) > max_display:
            self.archive_listbox.insert(tk.END, f"... showing first {max_display} of {len(filtered)} results")

    def archive_bulk_open(self):
        selected_indices = self.archive_listbox.curselection()
        for index in selected_indices:
            url = self.archive_listbox.get(index)
            if not url.startswith("..."):
                webbrowser.open(url)

    def update_category_list_async(self):
        self.after(0, self.update_category_list)

    def update_category_list(self):
        aggregated = {}
        for query in self.results_dict:
            for item in self.results_dict[query]:
                cat = item.get("category", "Other")
                aggregated.setdefault(cat, [])
                if not any(existing["url"] == item["url"] for existing in aggregated[cat]):
                    aggregated[cat].append(item)
        self.aggregated_results = aggregated
        categories = sorted(aggregated.keys())
        self.category_optionmenu.configure(values=categories)
        if categories:
            if self.category_optionmenu.get() not in categories:
                self.category_optionmenu.set(categories[0])
            self.update_results_buttons(self.category_optionmenu.get())
        else:
            self.category_optionmenu.set("")

    def update_results_buttons(self, selected_category):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        results = self.aggregated_results.get(selected_category, [])
        for i, item in enumerate(results, 1):
            wrapped_url = "\n".join(textwrap.wrap(item["url"], width=60))
            frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent", corner_radius=0)
            frame.pack(padx=2, pady=2, fill="x")
            if item["url"] not in self.bulk_vars:
                self.bulk_vars[item["url"]] = tk.BooleanVar()
            chk = ctk.CTkCheckBox(frame, text="", variable=self.bulk_vars[item["url"]])
            chk.pack(side="left", padx=(0,2))
            btn = ctk.CTkButton(frame, text=wrapped_url,
                                command=lambda url=item["url"]: webbrowser.open(url),
                                height=30, corner_radius=0, fg_color="transparent", hover_color="#333333",
                                font=ctk.CTkFont(weight="bold"), anchor="w")
            btn.pack(side="left", fill="x", expand=True)

    def bulk_open(self):
        for url, var in self.bulk_vars.items():
            if var.get():
                webbrowser.open(url)

    def show_results_page(self):
        self.results_frame.tkraise()
        self.update_category_list()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = PremiumOSINTGUI()
    dork_folder = "dorks"
    files = []
    if os.path.isdir(dork_folder):
        for f in os.listdir(dork_folder):
            if f.lower().endswith(".txt"):
                files.append(f)
    app.predefined_files = files
    app.predefined_optionmenu.configure(values=files)
    if files:
        app.predefined_optionmenu.set("Select a file")
    else:
        app.predefined_optionmenu.set("No files found")
    app.mainloop()
