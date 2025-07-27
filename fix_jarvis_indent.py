#!/usr/bin/env python3

# Read the file
with open('jarvis.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix the specific problematic lines
fixed_lines = []
for i, line in enumerate(lines):
    if i == 638:  # Line 639 (0-indexed)
        # Fix the incorrectly indented except block
        fixed_lines.append("                except Exception as e:\n")
    elif i == 639:  # Line 640
        fixed_lines.append("                    print(f\"Error searching {search_dir}: {e}\")\n")
    elif i == 640:  # Line 641
        fixed_lines.append("                    continue\n")
    elif i == 641:  # Line 642 - the problematic print statement
        fixed_lines.append("            \n")
    elif i == 642:  # Line 643
        fixed_lines.append("        print(f\"✅ Search complete - found {len(found_items)} items\")\n")
    elif i == 643:  # Line 644
        fixed_lines.append("        \n")
    elif i == 644:  # Line 645
        fixed_lines.append("        # Generate comprehensive results with web interface\n")
    elif i == 645:  # Line 646
        fixed_lines.append("        return self.generate_search_results_with_ui(found_items, query)\n")
    elif i == 646:  # Line 647
        fixed_lines.append("        \n")
    elif i == 647:  # Line 648
        fixed_lines.append("    except Exception as e:\n")
    elif i == 648:  # Line 649
        fixed_lines.append("        return f\"❌ Comprehensive search error: {str(e)}\"\n")
    else:
        fixed_lines.append(line)

# Write back the corrected file
with open('jarvis.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Fixed indentation errors in jarvis.py") 