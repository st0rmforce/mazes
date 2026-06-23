from numbercombos_data import COMBINATIONS

cache = {}


def number_to_base(number: int, base: int) -> list[int]:
    digits = []
    while number:
        digits.append(number % base)
        number //= base
    digits.reverse()
    return digits


def get_combinations(numbers: int):
    if numbers in COMBINATIONS:
        return list(COMBINATIONS[numbers])
    if numbers not in cache:
        combos = []
        for i in range(pow(numbers + 1, numbers)):
            combo = number_to_base(i, numbers + 1)
            if 0 not in combo:
                ok = True
                for check in range(1, numbers + 1):
                    if combo.count(check) > 1:
                        ok = False
                if ok:
                    combos.append(combo)
        cache[numbers] = combos
    else:
        combos = cache[numbers]
    return combos
