#!/usr/bin/env python3
import re
from extract_file import extract_archive_file

kantable_h = extract_archive_file('Poison Pink (Japan)/DATA/SYSTEM', 'kantable.h').decode('latin1')
numbers = [int(x.strip()) for x in re.findall(r'-?\d+', kantable_h)]

# In Shift-JIS:
# Double byte characters start at 0x8140.
# 0x8140 is fullwidth space: index 1 in numbers?
# Let's check:
# 0x8140:
# Row 0x81: lead byte 0x81.
# Trail bytes: 0x40 - 0x7e (63 bytes), 0x80 - 0xfc (125 bytes) -> total 188 trail bytes.
# If index = (lead - 0x81) * 188 + trail_offset:
# Lead 0x81:
# 0x8140 -> trail_offset 0 -> index = 0? Or 1?
# In numbers:
# index 0: 16 (or -1?)
# index 1: 0 (Glyph 0 = fullwidth space!)
# index 2: 1 (Glyph 1 = 、)
# index 3: 2 (Glyph 2 = 。)
# 0x8141 = 、
# 0x8142 = 。
# 0x8143 = ， (comma) -> index 4: -1 (missing!)
# 0x8144 = ． (period) -> index 5: 3
# 0x8145 = ・ (middle dot) -> index 6: 4
# 0x8146 = ： (colon) -> index 7: 5
# 0x8147 = ； (semicolon) -> index 8: -1
# 0x8148 = ？ (question mark) -> index 9: 6
# 0x8149 = ！ (exclamation) -> index 10: 7

print("Formula check:")
# 0x8140 is index 1
# 0x8141 is index 2
# 0x8142 is index 3
# 0x8144 is index 5
# 0x8148 is index 9
print("Index for 0x8140 is 1!")
print(f"numbers[1] (0x8140 = '　'): {numbers[1]}")
print(f"numbers[2] (0x8141 = '、'): {numbers[2]}")
print(f"numbers[3] (0x8142 = '。'): {numbers[3]}")
print(f"numbers[5] (0x8144 = '．'): {numbers[5]}")
print(f"numbers[9] (0x8148 = '？'): {numbers[9]}")
print(f"numbers[10] (0x8149 = '！'): {numbers[10]}")

