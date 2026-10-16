===== T8 =====
```python
DIGITS = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
UNITS = ["", "십", "백", "천"]


def _read_group(n):
    """1 <= n <= 9999 를 한자어 수로 읽는다."""
    out = ""
    for power in (3, 2, 1, 0):
        d = n // 10 ** power % 10
        if d == 0:
            continue
        if power == 0:
            out += DIGITS[d]
        else:
            out += ("" if d == 1 else DIGITS[d]) + UNITS[power]
    return out


def korean_number(n):
    if n == 0:
        return "영"
    man, rest = divmod(n, 10000)
    result = ""
    if man:
        result += ("" if man == 1 else _read_group(man)) + "만"
    if rest:
        result += _read_group(rest)
    return result
```
===== T9 =====
풀이
- 3의 배수 중 15의 배수가 아닌 수의 합: 3의 배수 합 3×(1+…+33) = 1683, 15의 배수 합 15×(1+…+6) = 315 → 1683 − 315 = 1368
- 5의 배수 중 15의 배수가 아닌 수의 합: 5의 배수 합 5×(1+…+20) = 1050 → 1050 − 315 = 735
- 3의 배수와 5의 배수가 겹치는 수는 15의 배수뿐이므로 두 집합은 서로 겹치지 않는다. 따라서 합은 1368 + 735 = 2103

정답: 2103
===== T10 =====
금새 → 금세
뵈요 → 봬요
몇일 → 며칠
