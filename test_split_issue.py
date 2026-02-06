"""Test split issue with depreciation"""

# Depreciation string from database
dep_str = "$12,670/yr, $12,720/yr, $11,850/yr, $11,970/yr, $13,060/yr"

print("Original string:")
print(dep_str)

print("\n\nSplit by ', ' (comma-space):")
parts = dep_str.split(', ')
for i, part in enumerate(parts, 1):
    print(f"{i}. {part}")

print(f"\nTotal parts: {len(parts)}")

print("\n\nExpected: 5 items")
print("Actual: 10 items (wrong!)")

print("\n\nProblem: $12,670/yr contains comma inside the value")
print("Solution: Need to use different separator or escape commas")
