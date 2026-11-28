# Real bill lines: matching and arithmetic

Source: Hugging Face `shaluyadav/newdatafiles` (19-row sample read through the dataset viewer). No licence is stated; used only to test this code, reported in aggregate.

Pages: 2. Bill lines: 19.

## Recognised as a price-capped item

0 of 19 lines. Check each by hand: a wrong match here would be a wrong claim.


## How quantity × rate relates to the amount (lines with all three)

5 lines have quantity, rate and amount.

| Pattern | Lines |
|---|---|
| rate_column_is_line_total | 2 |
| matches | 2 |
| less_than_qty_x_rate (discount or rate is total) | 1 |

Only the last pattern produces a red finding. Every such line must be read on the real bill
before the rule is trusted on this kind of bill:

