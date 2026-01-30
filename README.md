download_aozora_zip.py

This is a script for downloading all ZIP files linked from Aozora Bunko author works list page.

Example target:
https://www.aozora.gr.jp/index_pages/person1403.html#sakuhin_list_1

How it works:
1) Parse the author page and collect "図書カード" links.
2) For each card page, find links ending in ".zip".
3) Download each zip into output directory.

Output naming:
- Files are saved as sequential IDs in download order: 000001.zip, 000002.zip, ...
- Files are NOT unzipped.

aozora_unzip_utf8.py
This is a script for auto-unzipping AOZORA zip files and convert Shift_JIS text to UTF-8.

Input:  ./aozora_zips/
Output: ./aozora_utf8/

Behavior:
- For each .zip, extracts into ./aozora_utf8/<zip_stem>/
- Converts .txt/.htm/.html to UTF-8 (tries cp932, shift_jis, shift_jisx0213, shift_jis_2004)
- Leaves other files unchanged
