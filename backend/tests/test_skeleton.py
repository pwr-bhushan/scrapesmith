"""dom_skeleton_hash: same structure -> same hash regardless of dynamic ids/classes."""
from app.skeleton import dom_skeleton_hash

# two "product pages", identical structure, different dynamic id/data-*/generated classes
PAGE_A = """
<html><body>
  <div id="prod-8837" class="css-1a2b3c" data-asin="B00ABC">
    <h1 class="product-title">iPhone 15</h1>
    <span class="price" itemprop="price">1000</span>
  </div>
</body></html>
"""
PAGE_B = """
<html><body>
  <div id="prod-9921" class="css-9z8y7x" data-asin="B99XYZ">
    <h1 class="product-title">Galaxy S24</h1>
    <span class="price" itemprop="price">1200</span>
  </div>
</body></html>
"""
# structurally different: extra wrapper div
PAGE_C = """
<html><body>
  <div><div class="product-title"><h1>x</h1></div></div>
</body></html>
"""


def test_same_structure_hashes_equal():
    assert dom_skeleton_hash(PAGE_A) == dom_skeleton_hash(PAGE_B)


def test_different_structure_hashes_differ():
    assert dom_skeleton_hash(PAGE_A) != dom_skeleton_hash(PAGE_C)


def test_stable_class_and_role_kept():
    # dropping the stable class 'price' must change the hash -> proves it's part of the fingerprint
    without = PAGE_A.replace('class="price" itemprop="price"', "")
    assert dom_skeleton_hash(PAGE_A) != dom_skeleton_hash(without)


def test_empty_is_stable():
    assert dom_skeleton_hash("") == dom_skeleton_hash("   ")
