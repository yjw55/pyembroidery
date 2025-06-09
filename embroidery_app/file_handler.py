import os
# Ensure pyembroidery can be imported. This might require sys.path manipulation
# if pyembroidery is not installed and this module is run standalone or by an IDE
# that doesn't automatically add the project root to PYTHONPATH.
# However, this should ideally be handled by the main execution script (main.py).
from pyembroidery import EmbPattern, read, write, supported_formats # Use write instead of write_embroidery

class FileHandler:
    def __init__(self):
        pass

    def get_supported_read_formats(self, as_dict=False):
        """Returns a filter string for QFileDialog or a dict of formats based on pyembroidery's read capabilities."""
        formats_info = supported_formats()
        
        read_formats_dict = {}
        all_read_extensions_list = [] # For creating the combined filter string

        for fmt_info in formats_info:
            if fmt_info.get("reader", None):
                description = fmt_info.get("description", "Embroidery File")
                extensions = fmt_info.get("extension", [])
                if isinstance(extensions, str):
                    extensions = [extensions]
                
                valid_extensions = [ext.lower() for ext in extensions if ext and ext.strip()]
                if not valid_extensions:
                    continue
                
                all_read_extensions_list.extend(valid_extensions)

                if description not in read_formats_dict:
                    read_formats_dict[description] = []
                read_formats_dict[description].extend(valid_extensions)
                # Ensure uniqueness within each description's list
                read_formats_dict[description] = sorted(list(set(read_formats_dict[description])))

        if as_dict:
            return read_formats_dict

        # Create the combined filter string
        if not all_read_extensions_list:
            return "All Files (*)"
        
        unique_asterisked_extensions = sorted(list(set(['*.' + ext for ext in all_read_extensions_list])))
        all_supported_filter = f"All Supported Embroidery Files ({' '.join(unique_asterisked_extensions)})"
        
        # As per user request, only the combined filter and "All Files"
        return f"{all_supported_filter};;All Files (*)"

    def get_supported_write_formats(self):
        """Returns a dictionary for QFileDialog mapping filter string to extension for write formats."""
        formats_dict = {}
        for fmt_info in supported_formats():
            if fmt_info.get('writer'):
                ext = fmt_info['extension']
                description = fmt_info.get('description', f"{ext.upper()} Format")
                formats_dict[f"{description} (*.{ext})"] = ext
        return formats_dict

    def read_pattern(self, file_path):
        """Reads an embroidery pattern from the given file path."""
        # 在read_pattern方法中增加pattern存在性检查
        try:
            pattern = read(file_path)
            if pattern:
                # Basic validation or normalization if needed
                if not hasattr(pattern, 'stitches') or not hasattr(pattern, 'threadlist'):
                    print(f"Warning: File {file_path} loaded a pattern with missing attributes.")
                elif not pattern.stitches and not pattern.threadlist:
                    print(f"Warning: File {file_path} loaded an empty pattern.")
                
                # Moved debug print here to ensure pattern and its attributes exist
                if hasattr(pattern, 'threadlist'):
                    print(f"Debug: Loaded pattern for {file_path}, threadlist: {pattern.threadlist}")
                else:
                    print(f"Debug: Loaded pattern for {file_path}, but threadlist attribute is missing.")

                # Add pyembroidery import for COLOR_CHANGE if it's not already at the top of the file
                # This is a placeholder, actual import should be at the top
                # from pyembroidery import COLOR_CHANGE 
                if hasattr(pattern, 'stitches') and pattern.stitches:
                    print(f"Total stitches: {len(pattern.stitches)}")
                    # The following lines related to COLOR_CHANGE are commented out to prevent NameError
                    # Ensure pyembroidery is imported to access COLOR_CHANGE
                    # This might require adding 'import pyembroidery' at the top if not present
                    # For now, assuming pyembroidery.COLOR_CHANGE is accessible via an import
                    # from pyembroidery import COLOR_CHANGE # This line is illustrative
                    # color_change_flag = getattr(pyembroidery, 'COLOR_CHANGE', None) # Safely get COLOR_CHANGE
                    # if color_change_flag is not None:
                    #    print(f"Color changes based on stitch command: {sum(1 for s in pattern.stitches if s[2] & color_change_flag)}")
                    # else:
                    #    print("pyembroidery.COLOR_CHANGE not found, cannot count color changes from stitches.")
                elif hasattr(pattern, 'stitches'):
                     print(f"Total stitches: 0")
                else:
                    print("Pattern object missing stitches attribute for count.")

                return pattern
            else:
                # read might return None if the format is unsupported or file is corrupt
                print(f"Error: Could not read or decode file: {file_path}. Format might be unsupported or file invalid.")
                return None
        except Exception as e:
            print(f"Exception while reading file {file_path}: {e}")
            # import traceback
            # traceback.print_exc()
            return None

    def write_pattern(self, pattern: EmbPattern, file_path: str, target_format_extension: str) -> bool:
        """Writes the embroidery pattern to the given file path in the specified format."""
        if not pattern:
            print("Error: No pattern data to write.")
            return False
        
        # Verify the target_format_extension is supported for writing by pyembroidery
        is_supported_writer = any(
            fmt_info['extension'].lower() == target_format_extension.lower() and fmt_info.get('writer')
            for fmt_info in supported_formats()
        )

        if not is_supported_writer:
            print(f"Error: Format '{target_format_extension}' is not supported for writing by pyembroidery.")
            return False

        try:
            # pyembroidery's write_embroidery function determines the writer based on the file_path's extension.
            # Ensure the file_path has the correct extension for the intended target_format_extension.
            # QFileDialog should provide this, but a check or forced extension might be good.
            # For example, if user types "myfile" and selects PES, file_path might be "myfile".
            # It should be "myfile.pes". This is handled in MainWindow's export_file.
            
            write(pattern, file_path)
            print(f"Pattern successfully written to {file_path} as {target_format_extension}")
            return True
        except Exception as e:
            print(f"Exception while writing file {file_path} (intended format {target_format_extension}): {e}")
            # import traceback
            # traceback.print_exc()
            return False

if __name__ == '__main__':
    # This is for testing FileHandler independently.
    # Ensure pyembroidery is in PYTHONPATH or installed.
    # Example: Add project root to sys.path if pyembroidery is a submodule/sibling directory
    # import sys
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # project_root_dir = os.path.dirname(current_dir) # embroidery_app -> pyembroidery (folder)
    # sys.path.insert(0, os.path.dirname(project_root_dir)) # pyembroidery (folder) -> pyembroidery0530
    # sys.path.insert(0, project_root_dir) # Add 'pyembroidery' folder to path

    handler = FileHandler()
    
    print("--- Supported Read Formats Filter String ---")
    read_filter = handler.get_supported_read_formats()
    print(read_filter)
    # print(read_filter.replace(";; ", "\n")) # For easier reading

    print("\n--- Supported Write Formats Dictionary ---")
    write_fmts = handler.get_supported_write_formats()
    if write_fmts:
        for desc, ext in write_fmts.items():
            print(f"  '{desc}': '{ext}'")
    else:
        print("  No writable formats found.")

    # Create a dummy pattern for testing write (if pyembroidery is available)
    try:
        from pyembroidery import EmbPattern, STITCH, END
        test_pattern = EmbPattern()
        test_pattern.add_stitch_absolute(0, 0, STITCH)
        test_pattern.add_stitch_absolute(10, 0, STITCH)
        test_pattern.add_stitch_absolute(10, 10, STITCH)
        test_pattern.add_stitch_absolute(0, 0, END)
        test_pattern.add_thread({'color':0xFF0000, 'description':'red'})

        # Test writing (will create a file in the current dir if successful)
        # Ensure you have write permissions here.
        # test_file_name = "test_output.dst"
        # if handler.write_pattern(test_pattern, test_file_name, "dst"):
        #     print(f"Successfully wrote {test_file_name}")
        #     # os.remove(test_file_name) # Clean up
        # else:
        #     print(f"Failed to write {test_file_name}")
        pass # Avoid actual file IO in basic test run without explicit files

    except ImportError:
        print("\nCould not import EmbPattern for write test. Ensure pyembroidery is accessible.")
    except Exception as e:
        print(f"\nError during write test: {e}")