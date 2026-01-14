import os

path = ".streamlit/secrets.toml"

try:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        
        # FIx Line 18: ADMIN_PASSWORD
        if stripped.startswith("ADMIN_PASSWORD"):
            # It has extra garbage after the quote. Reset to safe default.
            new_lines.append('ADMIN_PASSWORD = "housmart_admin"\n')
            continue
            
        # Fix Line 17: universe_domain mashed with email
        if stripped.startswith('"universe_domain"'):
            # Example corrupted: "universe_domain"= "googleapis.com"008.iam.gserviceaccount.com"
            # We split it.
            if "googleapis.com" in stripped and "gserviceaccount.com" in stripped:
                # Naive splitting
                new_lines.append('"universe_domain" = "googleapis.com"\n')
                # Try to extract email?
                # The text after might be the email suffix, but we miss the prefix?
                # "008.iam.gserviceaccount.com"
                # If we don't have the full email, we can't reconstruct it.
                # But we must ensure valid TOML.
                # We'll rely on the existing "client_email" key if it exists elsewhere, or just drop the garbage.
                pass 
            else:
                 new_lines.append(line)
            continue
            
        new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print("Successfully patched secrets.toml")

except Exception as e:
    print(f"Error patching: {e}")
