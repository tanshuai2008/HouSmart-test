
import os

def fix_indentation():
    file_path = "app.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    
    # State flags
    in_else_block = False
    indent_target = False
    
    # Markers
    # We are looking for the 'else:' block inside 'with main_left:'
    # This 'else:' was introduced around line 922 in previous context
    
    for i, line in enumerate(lines):
        # Detect the specific else line
        # It should be "    else:" (4 spaces) followed by newline or comment
        # and checking context if needed.
        if "else:" in line and "if delivery_method_check" not in line and "SCREEN MODE" not in line:
            # Check indentation level (4 spaces)
            if line.startswith("    else:"):
                in_else_block = True
                new_lines.append(line)
                continue
        
        # Detect end of the block: "with col3:"
        if line.startswith("with col3:"):
            in_else_block = False
        
        if in_else_block:
            # We need to indent this line by 4 spaces
            # BUT only if it isn't already indented (e.g. comments I might have added manually)
            # The lines that caused error were at 4 spaces, need to be 8.
            # So we just add 4 spaces to everything.
            if line.strip(): # Don't indent empty lines specifically (optional)
                new_lines.append("    " + line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print("Indentation fix applied.")

if __name__ == "__main__":
    fix_indentation()
