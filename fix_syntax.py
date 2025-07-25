# Fix syntax errors in jarvis.py
with open('jarvis.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the orphaned except block in background_system_init method
# The problem is the indentation and missing try block
content = content.replace(
    '''            print("✅ JARVIS: Lightweight mode active!")
                
            except Exception as e:
            print(f"⚠️ Background scan minimal error: {str(e)}")''',
    '''            print("✅ JARVIS: Lightweight mode active!")
                
        except Exception as e:
            print(f"⚠️ Background scan minimal error: {str(e)}")'''
)

# Write the fixed content back
with open('jarvis.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed syntax errors in jarvis.py!") 