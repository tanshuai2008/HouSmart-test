
def fix_ai_summary_indent():
    file_path = "app.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    
    # Target lines:
    # # 2. AI INSIGHT SUMMARY (Moved per user request)
    # with st.container(border=True):
    #
    # We want these to be at 12 spaces (currently likely 8).
    
    # We identify them by text content.
    
    lines_to_fix = [
        "# 2. AI INSIGHT SUMMARY (Moved per user request)",
        "with st.container(border=True):"
    ]
    
    # State
    found_summary = False
    
    for i, line in enumerate(lines):
        # Specific context check: around line 990
        if "AI INSIGHT SUMMARY" in line:
            # Check indentation
            current_indent = len(line) - len(line.lstrip())
            if current_indent == 8:
                # Add 4 spaces
                new_lines.append("    " + line)
                found_summary = True
                continue
        
        if found_summary and "with st.container(border=True):" in line:
            # This follows the summary comment immediately
            current_indent = len(line) - len(line.lstrip())
            if current_indent == 8:
                new_lines.append("    " + line)
                found_summary = False # Done fixing the header
                continue
        
        # Reset flag if we drift
        if found_summary and line.strip() and "st.container" not in line:
             found_summary = False

        new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print("Fixed AI Summary indentation.")

if __name__ == "__main__":
    fix_ai_summary_indent()
