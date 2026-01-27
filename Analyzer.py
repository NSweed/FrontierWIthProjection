import os
import re


def extract_verdicts_to_table(directory_path, output_file="results.txt"):
    results = []
    pattern = re.compile(r"VERDICT:\s*(\d+\.?\d*)")

    # Get the absolute folder name to avoid confusion
    folder_name = os.path.basename(os.path.normpath(directory_path))

    for filename in sorted(os.listdir(directory_path)):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding="utf-8") as f:
                    content = f.read()
                    match = pattern.search(content)
                    if match:
                        results.append((filename, match.group(1)))
            except Exception as e:
                print(f"Skipping {filename}: {e}")

    if results:
        with open(output_file, 'a', encoding="utf-8") as out_f:
            # We record the directory name in the header and in every row
            out_f.write(f"\n--- DATA BATCH FROM DIR: {folder_name} ---\n")
            for name, val in results:
                # Format: Directory | Filename | Verdict
                out_f.write(f"{folder_name:<20} | {name:<60} | {val:<10}\n")
        print(f"Appended {len(results)} results from '{folder_name}' to {output_file}")


import re
from collections import defaultdict

import re
from collections import defaultdict


def group_results_by_subject(input_file, output_file="grouped_results.txt"):
    grouped_data = defaultdict(list)

    # This pattern looks for the subject name and captures the number following it
    # It works for 'biology_4_web' and 'physics_30.txt'
    subject_regex = re.compile(r"(biology|physics|chemistry)_(\d+)", re.IGNORECASE)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 1. Skip lines that are headers or empty
                if line.startswith("---") or "|" not in line:
                    continue

                # 2. Split the line into 3 columns
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 3:
                    continue

                dir_name = parts[0]
                full_filename = parts[1]
                verdict_val = parts[2]

                # 3. Extract subject and number from filename
                match = subject_regex.search(full_filename)
                if match:
                    subject = match.group(1).lower()
                    subject_id = match.group(2)
                    key = f"{subject}_{subject_id}"

                    grouped_data[key].append({
                        'dir': dir_name,
                        'file': full_filename,
                        'val': verdict_val
                    })

        # 4. Write the final grouped file
        if not grouped_data:
            print("No data was grouped. Check the subject names in your filenames.")
            return

        with open(output_file, 'w', encoding='utf-8') as out_f:
            # Sort keys: first by subject name, then by numeric ID
            sorted_keys = sorted(grouped_data.keys(),
                                 key=lambda x: (x.split('_')[0], int(x.split('_')[1])))

            for key in sorted_keys:
                out_f.write(f"\n======= GROUP: {key.upper()} =======\n")
                # Table header for this group
                out_f.write(f"{'DIRECTORY':<30} | {'FILENAME':<65} | {'VERDICT'}\n")
                out_f.write("-" * 110 + "\n")

                # Write each entry under this subject
                for entry in grouped_data[key]:
                    out_f.write(f"{entry['dir']:<30} | {entry['file']:<65} | {entry['val']}\n")
                out_f.write("\n")

        print(f"Successfully organized {len(grouped_data)} subjects into '{output_file}'")

    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")


# Usage Example:
# extract_verdicts_to_table("./experiment_alpha")
# extract_verdicts_to_table("./experiment_beta")
# group_results_with_metadata("results.txt")


# extract_verdicts_to_table(os.path.join("Responses", "Grading from projection"))
# extract_verdicts_to_table(os.path.join("Responses", "Grading default"))
group_results_by_subject("results.txt")