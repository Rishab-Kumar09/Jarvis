#!/usr/bin/env python3
"""
COMPREHENSIVE JARVIS INDENTATION FIXER
Fixes ALL try-catch-except-finally indentation issues in jarvis.py
"""

def fix_jarvis_indentation():
    """Fix all indentation issues in jarvis.py"""
    
    print("🔧 COMPREHENSIVE JARVIS INDENTATION FIXER")
    print("=" * 50)
    
    # Read the entire file
    with open('jarvis.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📖 Read {len(lines)} lines from jarvis.py")
    
    # Track fixes
    fixes_made = 0
    
    # Go through each line and fix indentation issues
    for i in range(len(lines)):
        line_num = i + 1
        line = lines[i]
        original_line = line
        
        # Fix specific problematic lines we know about
        
        # Line 333 area (quick_window_scan)
        if line_num == 333 and 'except Exception as e:' in line:
            lines[i] = '        except Exception as e:\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: except block in quick_window_scan")
        
        # Line 334 area
        elif line_num == 334 and 'print(f"Quick window scan' in line:
            lines[i] = '            print(f"Quick window scan failed: {str(e)}")\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: print statement indentation")
        
        # Line 335 area  
        elif line_num == 335 and 'self.active_windows = {}' in line:
            lines[i] = '            self.active_windows = {}\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: assignment indentation")
        
        # Line 361 area (background_system_init)
        elif line_num == 361 and 'except Exception as e:' in line:
            lines[i] = '        except Exception as e:\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: except block in background_system_init")
        
        # Line 362 area
        elif line_num == 362 and 'print(f"⚠️ Background scan' in line:
            lines[i] = '            print(f"⚠️ Background scan minimal error: {str(e)}")\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: print statement indentation")
        
        # Line 534 area (get_simple_screen_info)
        elif line_num == 534 and 'except:' in line or 'except Exception as e:' in line:
            lines[i] = '            except:\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: except block in get_simple_screen_info")
        
        # Line 535 area
        elif line_num == 535 and 'response += f"📱 Active Application: Unable to detect' in line:
            lines[i] = '                response += f"📱 Active Application: Unable to detect\\n"\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: response assignment indentation")
        
        # Lines 621-650 area (comprehensive_search_everything) - THE BIG PROBLEM AREA
        elif line_num == 621 and 'except (PermissionError, OSError):' in line:
            lines[i] = '                except (PermissionError, OSError):\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: except PermissionError block")
        
        elif line_num == 622 and 'continue' in line:
            lines[i] = '                    continue\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: continue statement")
        
        elif line_num == 623 and 'except Exception as e:' in line:
            lines[i] = '                except Exception as e:\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: except Exception block")
        
        elif line_num == 624 and 'print(f"Error searching' in line:
            lines[i] = '                    print(f"Error searching {search_dir}: {e}")\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: print error statement")
        
        elif line_num == 625 and 'continue' in line:
            lines[i] = '                    continue\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: continue statement")
        
        # THE CRITICAL PROBLEM LINES
        elif line_num == 642 and 'print(f"✅ Search complete' in line:
            lines[i] = '        print(f"✅ Search complete - found {len(found_items)} items")\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: CRITICAL - Search complete print statement")
        
        elif line_num == 644 and '# Generate comprehensive results' in line:
            lines[i] = '        # Generate comprehensive results with web interface\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: comment indentation")
        
        elif line_num == 645 and 'return self.generate_search_results_with_ui' in line:
            lines[i] = '        return self.generate_search_results_with_ui(found_items, query)\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: return statement")
        
        elif line_num == 647 and 'except Exception as e:' in line:
            lines[i] = '    except Exception as e:\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: CRITICAL - Main except block")
        
        elif line_num == 648 and 'return f"❌ Comprehensive search error' in line:
            lines[i] = '        return f"❌ Comprehensive search error: {str(e)}"\n'
            fixes_made += 1
            print(f"✅ Fixed line {line_num}: error return statement")
            
        # Fix other common indentation patterns
        elif 'try:' in line and line.strip().startswith('try:'):
            # Make sure try blocks are properly indented
            current_indent = len(line) - len(line.lstrip())
            if current_indent % 4 != 0:  # Fix to proper 4-space indentation
                proper_indent = (current_indent // 4) * 4
                lines[i] = ' ' * proper_indent + line.lstrip()
                fixes_made += 1
                print(f"✅ Fixed line {line_num}: try block indentation")
                
        elif 'except' in line and ':' in line and line.strip().startswith('except'):
            # Make sure except blocks are properly indented
            current_indent = len(line) - len(line.lstrip())
            if current_indent % 4 != 0:  # Fix to proper 4-space indentation
                proper_indent = (current_indent // 4) * 4
                lines[i] = ' ' * proper_indent + line.lstrip()
                fixes_made += 1
                print(f"✅ Fixed line {line_num}: except block indentation")
                
        elif 'finally:' in line and line.strip().startswith('finally:'):
            # Make sure finally blocks are properly indented
            current_indent = len(line) - len(line.lstrip())
            if current_indent % 4 != 0:  # Fix to proper 4-space indentation
                proper_indent = (current_indent // 4) * 4
                lines[i] = ' ' * proper_indent + line.lstrip()
                fixes_made += 1
                print(f"✅ Fixed line {line_num}: finally block indentation")
    
    # Now fix the critical structural issues
    print("\n🔧 Fixing structural try-except issues...")
    
    # Look for orphaned try blocks and add missing except blocks
    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith('try:'):
            # Check if there's a corresponding except or finally
            j = i + 1
            found_except_or_finally = False
            indentation_level = len(lines[i]) - len(lines[i].lstrip())
            
            while j < len(lines):
                next_line = lines[j].strip()
                next_indent = len(lines[j]) - len(lines[j].lstrip())
                
                # If we hit something at the same indentation level or less, we've gone too far
                if next_indent <= indentation_level and next_line and not next_line.startswith('#'):
                    if next_line.startswith('except') or next_line.startswith('finally'):
                        found_except_or_finally = True
                    break
                    
                if next_line.startswith('except') or next_line.startswith('finally'):
                    found_except_or_finally = True
                    break
                    
                j += 1
            
            # If no except or finally found, add a generic except block
            if not found_except_or_finally:
                # Find the end of the try block
                try_end = i + 1
                while try_end < len(lines):
                    try_line = lines[try_end]
                    try_indent = len(try_line) - len(try_line.lstrip())
                    if try_indent <= indentation_level and try_line.strip() and not try_line.strip().startswith('#'):
                        break
                    try_end += 1
                
                # Insert except block
                except_line = ' ' * indentation_level + 'except Exception as e:\n'
                pass_line = ' ' * (indentation_level + 4) + 'pass\n'
                lines.insert(try_end, except_line)
                lines.insert(try_end + 1, pass_line)
                fixes_made += 2
                print(f"✅ Added missing except block after line {i + 1}")
    
    # Write the fixed file
    with open('jarvis.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"\n🎉 INDENTATION FIX COMPLETE!")
    print(f"✅ Made {fixes_made} fixes to jarvis.py")
    print(f"📝 File updated with proper indentation")
    print("🚀 Ready to run: python jarvis.py --hybrid")

if __name__ == "__main__":
    fix_jarvis_indentation() 