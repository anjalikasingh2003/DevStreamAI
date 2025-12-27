from pr_creator import split_patch_into_files

patch = """
--- a/service/auth.py
+++ b/service/auth.py
@@ -1,2 +1,2 @@
-old
+new

--- a/utils/validator.js
+++ b/utils/validator.js
@@ -2,1 +2,1 @@
-foo
+bar
"""

patches = split_patch_into_files(patch)

print("FILES FOUND:", patches.keys())
for fname, content in patches.items():
    print("\nFILE:", fname)
    print(content)
