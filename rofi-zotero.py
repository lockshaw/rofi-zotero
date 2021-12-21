#!/usr/bin/env python3

import argparse
import os
import re
import sqlite3
import subprocess

HOME_DIR            = os.environ.get("HOME") 
DEF_ZOTERO_DIR      = os.path.join(HOME_DIR, "Zotero")
ZOTERO_STORAGE_DIR  = "storage"
ZOTERO_SQLITE_FILE  = "zotero.sqlite"

rofi_theme = ""

if rofi_theme:
  theming = ["-theme", rofi_theme]
else:
  theming = []


PDFS_QUERY = """ 
    SELECT attachmentInfo.key,  
           parentItemDataValues.value 
    FROM itemAttachments 
    INNER JOIN items AS attachmentInfo 
        ON attachmentInfo.itemID = itemAttachments.itemID 
    INNER JOIN itemData as attachmentItemData 
        ON attachmentItemData.itemID = attachmentInfo.itemID 
    INNER JOIN itemDataValues as attachmentItemDataValues 
        ON attachmentItemData.valueID = attachmentItemDataValues.valueID 
    INNER JOIN items AS parentInfo 
        ON itemAttachments.parentItemID = parentInfo.itemID 
    INNER JOIN itemData as parentItemData 
        ON parentItemData.itemID = parentInfo.itemID 
    INNER JOIN itemDataValues as parentItemDataValues 
        ON parentItemDataValues.valueID = parentItemData.valueID 
    WHERE attachmentItemData.fieldID = 1
      AND parentItemData.fieldID = 1
      AND (itemAttachments.contentType LIKE '%pdf%'
          OR itemAttachments.contentType LIKE '%djvu%')
""" 

def getPDFSet(zotero_dir):
  conn = sqlite3.connect(os.path.join(zotero_dir, ZOTERO_SQLITE_FILE))

  pdfs = conn.execute(PDFS_QUERY)
  seen_pdfs = set()
  pdf_list = []

  for pdf in pdfs:
    if pdf[1] not in seen_pdfs:
      pdf_list.append((pdf[0], pdf[1]))
      seen_pdfs.add(pdf[1])

  conn.close()

  return pdf_list


VALID_EXTENSIONS = ["pdf", "djvu"]
INVALID_PATTERNS = ["sync-conflict"]

def pick_file(files):
  valid_files = [f for f in files if \
    any((ext in f for ext in VALID_EXTENSIONS)) \
    and not any(invalid in f for invalid in INVALID_PATTERNS)]
  return valid_files[0]


parser = argparse.ArgumentParser( \
    description="Select a paper to open from Zotero using rofi")
parser.add_argument( \
    "-l", "--list", \
    action="store_true", \
    default=False,
    help="list PDFs instead of opening one")
parser.add_argument( \
    "-z", "--zotero", \
    action="store", 
    default=DEF_ZOTERO_DIR,
    help="set the Zotero directory")

args = parser.parse_args()
pdfs = getPDFSet(args.zotero)
pdfs_str = ""
labels = list(range(len(pdfs)))

for i, pdf in enumerate(pdfs):
  pdfs_str += "({}) {}\n".format(labels[i], pdf[1])

if args.list:
  print(pdfs_str)

else:
  rofi = subprocess.run(["rofi", "-threads", "0", "-dmenu", "-i", "-p", "paper"] + theming, \
      capture_output=True, text=True, input=pdfs_str)
  selected_pdf = rofi.stdout.strip()
  print(selected_pdf)
  if len(selected_pdf) > 0:
    re_result = re.match(r"\((?P<index>\w+)\)", selected_pdf)
    if re_result is not None:
      index = re_result.group("index")
      key = pdfs[int(index)][0]
      storage_dir = os.path.join(args.zotero, ZOTERO_STORAGE_DIR, key)
      file_to_open = pick_file(os.listdir(storage_dir))
      file_to_open_path = os.path.join(storage_dir, file_to_open)
      subprocess.Popen(["xdg-open", file_to_open_path])

