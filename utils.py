# utils.py
def save_results(results, filename):
    """
    Save aggregated search results to a file.
    The results dictionary should have categories as keys and lists of result dictionaries as values.
    If a description exists, it is printed; otherwise only the URL is printed.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            for category, items in results.items():
                f.write(f"Category: {category}\n")
                for i, item in enumerate(items, 1):
                    if item.get("description"):
                        f.write(f"  {i}. {item['description']}\n")
                    f.write(f"       {item['url']}\n")
                f.write("\n")
        print(f"Results successfully saved to '{filename}'.")
    except Exception as e:
        print(f"Error saving results: {e}")
