
import os

def fix_inner_indentation():
    file_path = "app.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    
    # We want to target specific blocks where indentation seems shallow
    # We know line 927 is "            with st.container(border=True):" (12 spaces)
    # We expect lines inside to be 16 spaces.
    
    # Let's inspect line 927 and 930 dynamically
    
    line_927_idx = -1
    for i, line in enumerate(lines):
        if "st.container(border=True)" in line and "RENTCAST_API_KEY" not in line:
            # We found a container. Check if it's the one we want.
            # We can check context.
            if i + 3 < len(lines) and "RENTCAST_API_KEY" in lines[i+3]:
                line_927_idx = i
                break
            # Or maybe checking line 926 "RENTCAST INTEGRATION"
            if i > 0 and "RENTCAST INTEGRATION" in lines[i-1]:
                line_927_idx = i
                break

    if line_927_idx == -1:
        print("Could not find the target container line.")
        # Fallback dump to see what's going on around line 920
        for i in range(920, 940):
            if i < len(lines):
                print(f"{i}: {repr(lines[i])}")
        return

    print(f"Found container at line {line_927_idx}: {repr(lines[line_927_idx])}")
    
    # Determine proper indentation depth
    # The container line has indentation X.
    # The inside lines should have X + 4.
    
    container_indent = len(lines[line_927_idx]) - len(lines[line_927_idx].lstrip())
    expected_inner_indent = container_indent + 4
    
    print(f"Container indent: {container_indent}. Expected inner: {expected_inner_indent}")
    
    # Apply fix to this block
    # Logic: Iterate from line_927_idx + 1. 
    # If line is indented <= container_indent, stop (block ended).
    # If line is indented < expected_inner_indent (but > container_indent?), add spaces?
    # Actually, we saw line 930 is at 12 spaces (same as container).
    
    current_idx = line_927_idx + 1
    while current_idx < len(lines):
        line = lines[current_idx]
        stripped = line.lstrip()
        
        if not stripped:
            current_idx += 1
            continue
            
        curr_indent = len(line) - len(stripped)
        
        # If we hit Dedent (indented less than or equal to container), break
        # BUT we must look out for empty lines or comments? No, purely indentation.
        # Wait, if the inner lines are at SAME level as container (12), we treat them as inside and needing fix.
        # So we only break if indent < container_indent?
        # Actually, the NEXT container (AI Summary) will also be at 12 spaces.
        # So breaking at <= container_indent is correct. 
        # BUT the inner lines are mistakenly AT container_indent.
        # So we need to look for specific "End of block" markers or just assume contiguous block?
        
        # Risk: The next container (AI Summary) starts with "with st.container...".
        # That line will be at 12 spaces.
        # So loop will stop there. Correct.
        
        if curr_indent <= container_indent:
            # Check if it's the start of the next container which IS at this level
            # If so, we are done with THIS block.
            print(f"Stopping at line {current_idx} (Indent {curr_indent}): {repr(line)}")
            break
        
        # It shouldn't happen that inner lines are <= container_indent if they are children, 
        # unless they are malformed (which they are).
        # In python, finding the block end of malformed indentation is ambiguous.
        # But we know visually what belongs there.
        # Everything until "AI INSIGHT SUMMARY" or next "with st.container"
        
        # Wait, if line 930 is at 12 spaces, curr_indent == container_indent (12).
        # So my condition "break if <= container_indent" will break IMMEDIATELY.
        # I need to relax this detection.
        pass 
        current_idx += 1

    # Re-strategy:
    # Just iterate through the file.
    # If immediately after "with st.container...", the next non-empty line has SAME indentation,
    # indent it and subsequent lines until we hit something with LOWER indentation or SAME (that is a new block start).
    # How to distinguish "Same indent = content that needs indenting" vs "Same indent = new sibling block"?
    # Sibling block usually starts with Keyword (with, if, else, # comment header).
    # Content usually starts with variable assignment, function call, or `if` (logic).
    
    # Specific fix: The block from line 927 to "AI INSIGHT SUMMARY" (around 992)
    # The block from line 993 to ... "COLUMN 3" (around 1060)
    
    # Let's apply fixed range indentation based on markers
    
    range1_start_marker = "RENTCAST INTEGRATION" # Line 926
    range1_end_marker = "AI INSIGHT SUMMARY" # Line 992
    range2_start_marker = "AI INSIGHT SUMMARY"
    range2_end_marker = "COLUMN 3: MAP"
    
    in_r1 = False
    in_r2 = False
    
    # We want to indent contents of the containers.
    # The container definition itself is correct (12 spaces).
    # The content inside is 12 spaces (needs 16).
    
    final_lines = []
    
    for i, line in enumerate(lines):
        l_stripped = line.strip()
        
        # Detect R1 Start
        if "RENTCAST INTEGRATION" in line:
            final_lines.append(line)
            continue
            
        if "with st.container(border=True):" in line:
             # Check context
             if i > 0 and "RENTCAST INTEGRATION" in lines[i-1]:
                 in_r1 = True
                 final_lines.append(line)
                 continue
             if i > 0 and "AI INSIGHT SUMMARY" in lines[i-1]:
                 in_r2 = True
                 in_r1 = False # End R1
                 final_lines.append(line)
                 continue
        
        # Detect R2 End
        if "COLUMN 3: MAP" in line:
            in_r2 = False
            final_lines.append(line)
            continue
            
        # Check if line is a sibling container start (e.g. Map Visibility Check or End of Main Left)
        if "with main_left:" in line: # Should not happen inside
            pass
            
        if in_r1:
            # We are inside RentCast container.
            # If line is "AI INSIGHT SUMMARY", we are leaving R1.
            if "AI INSIGHT SUMMARY" in line:
                in_r1 = False
                final_lines.append(line)
                continue
                
            # Otherwise, indent if not empty
            if line.strip():
                final_lines.append("    " + line)
            else:
                final_lines.append(line)
                
        elif in_r2:
            # Inside AI Summary container.
            # Indent
            if line.strip():
                final_lines.append("    " + line)
            else:
                final_lines.append(line)
        else:
            final_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    
    print("Inner indentation fix applied.")

if __name__ == "__main__":
    fix_inner_indentation()
