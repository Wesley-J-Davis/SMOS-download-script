#!/usr/bin/bash
set -x
echo $(pwd)
for file in $(ls $(pwd)/SM_*); do
    # Skip if no files match the pattern
    [ -e "$file" ] || continue
    
    # Extract the 5th field (the start timestamp)
    timestamp=$( basename ${file} | cut -d'_' -f5)
    
    # Extract Year (first 4 characters) and Month (next 2 characters)
    YYYY=${timestamp:0:4}
    MM=${timestamp:4:2}
    
    # Construct the target directory path
    target_dir="Y${YYYY}/M${MM}"
    
    # Create the directory structure if it doesn't exist (-p prevents errors if it does)
    mkdir -p "$(pwd)/$target_dir"
    
    # Move the file into the new directory
    mv "$file" "$(pwd)/$target_dir/"
done
