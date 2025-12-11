import sys
import os

# Add the project root to sys.path so we can import from views
project_root = "/Users/usuario/Library/CloudStorage/OneDrive-SharedLibraries-uv.cl/REVISTA MATRONERÍA ACTUAL - Documentos/MAQUETACIÓN/XML"
sys.path.append(project_root)

# Mock Streamlit
import unittest.mock as mock
sys.modules['streamlit'] = mock.Mock()

try:
    from views.manual_usuario import create_professional_pdf, MANUAL_SECTIONS
    print("Successfully imported create_professional_pdf")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

try:
    print("Generating Full Professional PDF...")
    # Verify images exist first
    missing_images = []
    # Images in Step 203 were updated to 01.png, etc. by User.
    # I should check if they exist or if I need to update my conversion script logic effectively.
    # The previous convert_images script handled manual_home.png etc.
    # The user updated file names to resources/manual_images/01.png etc. 
    # I need to make sure these exist or are handled. 
    # If the user renamed them, they might exist. Let's assume they DO NOT exist if I didn't create them.
    # Wait, the user updated `manual_usuario.py` to point to `resources/manual_images/01.png`.
    # Did the user upload these files? "I have updated the User Manual..." implies they might have.
    # But I should verify.
    
    # Actually, I should probably check if image paths are valid in the code.
    for section in MANUAL_SECTIONS:
        if "image" in section:
             if not os.path.exists(section["image"]):
                print(f"WARNING: Image not found: {section['image']}")

    pdf = create_professional_pdf()
    output_path = "test_manual_formatted.pdf"
    pdf.output(output_path)
    print(f"PDF generated at {output_path}")
    
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"PDF size: {size} bytes")
        if size > 10000:
            print("Verification SUCCESS")
        else:
            print(f"Verification WARNING: File seems small ({size} bytes)")
    else:
        print("Verification FAILED: File created")
        
except Exception as e:
    print(f"Verification FAILED with error: {e}")
    import traceback
    traceback.print_exc()
