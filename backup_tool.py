import os 
import shutil
import hashlib
import json
import time
from datetime import datetime
import argparse

MANIFEST_FILE_NAME = "manifest.json"

def calculate_file_hash(file_path: str, chunk_size: int = 4096) -> str:
    """
    This function is used to calculate the hash of a file.
    It read data in given chunk size. if data not found to read it will break the loop.
    If file not exists it stop the function.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()
    
def load_manifest(manifest_path: str) -> dict:
    """
    it reads the existing manifest. If manifest not found it returns the empty dictionary.
    """
    if not os.path.exists(manifest_path):
        return {}
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
            if not content:
                #Empty file -> treat as no manifest
                return {}           
            f.seek(0)
            return json.load(f)
    except json.JSONDecodeError:
        print("Warning: manifest.json is corrupted. Starting with an empty manifest.")
        return {}
        
def save_manifest(manifest_path: str, manifest_data: dict) -> None:
    """
    It saves the manifest data to json file. It doesnot return anything.
    """
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4)
        
def ensure_directory(path: str) -> None:
    """
    It checks the given path is exists or not. If file/folder is not found it creates new file/folder.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        
def backup_file(source_file: str, source_root: str, backup_root: str) -> str:
    """
    It copies on file into a backup folder while keeping the same folder strecute as the original source.
    """
    rel_path = os.path.relpath(source_file, source_root)
    backup_file_path = os.path.join(backup_root, rel_path)
    
    #check the folder is exists or not else create new folder
    backup_dir = os.path.dirname(backup_file_path)
    ensure_directory(backup_dir)
    
    shutil.copy2(source_file, backup_file_path)   #copy2 preserves the metadata
    return backup_file_path

def scan_and_backup(source_dir: str, backup_dir: str, manifest_path: str) -> None:
    """
    This function:
        Walks through all files in a given source directory.
        Checks if each file is:new, or modified since last backup (using a hash comparison).
        If new/modified → backs it up and updates a manifest.
        If unchanged → skips the file.
        Writes updated backup info to manifest.json.
        Prints a summary at the end.
    """
    ensure_directory(backup_dir)
    
    manifest = load_manifest(manifest_path)
    updated_manifest = manifest.copy()
    
    backed_up_files = 0
    skipped_files = 0
    
    start_time = time.time()
    
    for root, dirs, files in os.walk(source_dir):
        for file_name in files:
            source_file_path = os.path.join(root, file_name)
            
            #ignore the manifest file if it is inside the source directory
            if os.path.basename(source_file_path) == MANIFEST_FILE_NAME:
                continue
               
            file_hash = calculate_file_hash(source_file_path)
            rel_path = os.path.relpath(source_file_path, source_dir)
            
            previous_entry = manifest.get(rel_path)
            backup_file_path = os.path.join(backup_dir, rel_path)
            
            #check if backup file exists
            backup_exists = os.path.exists(backup_file_path)
            
            if previous_entry is None or previous_entry["hash"] != file_hash or not backup_exists:
                #New or changed file == backup
                backup_file_path = backup_file(source_file_path, source_dir, backup_dir)
                updated_manifest[rel_path] = {
                    "hash": file_hash,
                    "last_backup_time": datetime.now().isoformat(), 
                    "backup_path": backup_file_path,
                }
                backed_up_files += 1
                print(f"[BACKUP] {rel_path}")
            else:
                #no change -> skip
                skipped_files += 1
                print(f"[SKIP] {rel_path}")
                
    save_manifest(manifest_path, updated_manifest)
    
    end_time = time.time()
    print("\n=== Backup Summary ===")
    print(f"Source directory : {source_dir}")
    print(f"Backup directory : {backup_dir}")
    print(f"Total files scanned : {backed_up_files + skipped_files}")
    print(f"Files backed up      : {backed_up_files}")
    print(f"Files unchanged      : {skipped_files}")
    print(f"Time taken (seconds) : {end_time - start_time:.2f}")
    
def verify_backup_integrity(source_dir: str, backup_dir: str, manifest_path: str) -> None:
    """
    it checks the file in backup folder is still matches the hash value which recoreded in manifest.
    it detects missing files which files present in manifest but not present in backup folder and 
    detects mismatched hashes which files that present in backup folder but file is changed or corrupted.
    """
    manifest = load_manifest(manifest_path)
    if not manifest:
        print("No Manifest Found. Run Backup first")
        return
        
    mismatches = []
    missing_files = []
    total_files = len(manifest)
    
    for rel_path, meta in manifest.items():
        soruce_file_path = os.path.join(source_dir, rel_path)
        backup_file_path = os.path.join(backup_dir, rel_path)
        
        if not os.path.exists(backup_file_path):
            missing_files.append(rel_path)
            continue
            
        current_hash = calculate_file_hash(backup_file_path)
        if current_hash != meta["hash"]:
            mismatches.append(rel_path)
            
    print("\n=== Integrity Check Report ===")
    print(f"Total files in manifest  : {total_files}")
    print(f"Missing Files            : {len(missing_files)}")
    print(f"Hash Mismatches          : {len(mismatches)}")
    
    if missing_files:
        print("\nMissing Files in Backup: ")
        for i in missing_files:
            print(f"    :{i}")
        
    if mismatches:
        print(f"Files with hash mismatches (changed files or corrupted files).")
        for i in mismatches:
            print(f"    :{i}")
         
    if not missing_files and not mismatches:
        print("\nAll backed up files passed integrity check.")
        
def parse_arguments():
    """
    This function uses pythons argparse module to define and parse command-line arguments for backup script.
    it tells program 
        -where the source file is located
        -where the backup should go
        -whether to run verificarion instead of backup
        -where the manifest file is located
    it returns the parsed arguments as an objects. (args.source, args.backup ect..)
    """
    parser = argparse.ArgumentParser(
            description="Automated File Backup And Integrity Checker"
            )
    
    parser.add_argument(
            "--source",
            required=True,
            help="Source directory to scan (file to Backup).",
            )
            
    parser.add_argument(
            "--backup",
            required=True,
            help="Backup directory where files will be stored.",
            )
            
    parser.add_argument(
            "--verify",
            action="store_true",
            help="Run Integrity Verification instead of backup.",
            )
            
    parser.add_argument(
            "--manifest",
            default=MANIFEST_FILE_NAME,
            help="path to manifest JSON file (default: manifest.json in current directory",
            )
            
    return parser.parse_args()
    

def main():
    """
    This is the entry point of backup script 
    its job is to 
        - run command line arguments
        - normalize paths
        - validate inputs
        - decide whether to run a backu or run integrity verification
    """
    args = parse_arguments()
    
    source_dir = os.path.abspath(args.source)
    backup_dir = os.path.abspath(args.backup)
    manifest_path = os.path.abspath(args.manifest)
    
    if not os.path.exists(source_dir):
        print(f"Source directory does not exists: {source_dir}")
        return
        
    if args.verify:
        verify_backup_integrity(source_dir, backup_dir, manifest_path)
    else:
        scan_and_backup(source_dir,backup_dir,manifest_path)
        

if __name__ == "__main__":
    main()