===== T8 =====
```python
def korean_number(n):
    if n == 0:
        return "영"
    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    units = ["", "십", "백", "천"]

    def under_10000(m):
        s = ""
        for i in range(3, -1, -1):
            d = (m // 10 ** i) % 10
            if d == 0:
                continue
            if d == 1 and i > 0:
                s += units[i]
            else:
                s += digits[d] + units[i]
        return s

    high, low = divmod(n, 10000)
    result = ""
    if high == 1:
        result = "만"
    elif high > 1:
        result = under_10000(high) + "만"
    result += under_10000(low)
    return result
```
===== T9 =====
3의 배수 합: 3×(1+…+33) = 3×561 = 1683
5의 배수 합: 5×(1+…+20) = 5×210 = 1050
15의 배수 합: 15×(1+…+6) = 15×21 = 315
3 또는 5의 배수 합 = 1683 + 1050 − 315 = 2418
여기서 15의 배수를 빼면 2418 − 315 = 2103
정답: 2103
===== T10 =====
금새 → 금세
뵈요 → 봬요
몇일 → 며칠
