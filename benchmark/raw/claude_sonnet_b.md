===== T8 =====
```python
def korean_number(n):
    if n == 0:
        return "영"
    digits = "영일이삼사오육칠팔구"

    def four(x):
        s = ""
        for v, u in ((1000, "천"), (100, "백"), (10, "십")):
            d = x // v % 10
            if d:
                s += (digits[d] if d > 1 else "") + u
        d = x % 10
        if d:
            s += digits[d]
        return s

    hi, lo = divmod(n, 10000)
    result = ""
    if hi:
        result += ("" if hi == 1 else four(hi)) + "만"
    result += four(lo)
    return result
```
===== T9 =====
3의 배수의 합: 3×(1+2+...+33) = 3×561 = 1683
5의 배수의 합: 5×(1+2+...+20) = 5×210 = 1050
15의 배수의 합: 15×(1+2+...+6) = 15×21 = 315

3의 배수이거나 5의 배수인 수의 합은 1683 + 1050 − 315 = 2418입니다.
여기서 15의 배수(315)를 제외해야 하므로 2418 − 315 = 2103입니다.

정답: 2103
===== T10 =====
금새 → 금세
뵈요 → 봬요
몇일 → 며칠
