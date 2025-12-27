from pr_creator import create_pr_from_patch

patch = """
--- a/calc.py
+++ b/calc.py
@@ -1,3 +1,3 @@
 def divide(a, b):
-    result = a / 0
+    result = a / b
     return result

--- a/service.js
+++ b/service.js
@@ -1,3 +1,3 @@
 function validate(x) {
-    return x == null;
+    return x === null;
 }
"""

print(create_pr_from_patch(patch, "Test multi-file fallback"))
