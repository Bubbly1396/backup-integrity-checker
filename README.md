Automated File Backup & Integrity Checker (Python)
    A Python tool that automatically backs up files, detects changes using SHA-256 hashing, and verifies file integrity to prevent corruption or data loss.

Key Features
  Incremental backup system (only new or modified files are copied)
  SHA-256 hashing for file integrity validation
  Detects corrupted or missing files
  Stores metadata in manifest.json
  Works on Windows and Linux
  No external libraries required

How to Run
  Backup command
     > python backup_tool.py --source "path_to_source" --backup "path_to_backup"


  Verify integrity  
     > python backup_tool.py --source "path" --backup "path" --verify

Technologies Used
  Python 3
  os
  hashlib
  shutil
  json
  argparse
  time
  datetime

 Author
Basheer Ali
