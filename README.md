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
